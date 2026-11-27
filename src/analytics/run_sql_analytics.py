"""
CommerceIQ - SQL Business Analytics Runner & Reconciler (Phase 8)

Executes all SQL scripts in `sql/03_analytics/` against the MySQL warehouse,
captures result tables and timings, verifies KPI reconciliation against the
warehouse, and generates `reports/sql_analytics_report.md` + CSV summaries.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection, get_database_name
from src.database.load_database import split_sql_statements


def configure_logger() -> logging.Logger:
    log_path = PROJECT_ROOT / "logs" / "sql_analytics.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("commerceiq.sql_analytics")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        h.close()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def run_sql_analytics() -> dict[str, Any]:
    logger = configure_logger()
    t0 = perf_counter()
    db_name = get_database_name()
    sql_dir = PROJECT_ROOT / "sql" / "03_analytics"
    out_csv_dir = PROJECT_ROOT / "reports" / "sql_analytics_results"
    out_csv_dir.mkdir(parents=True, exist_ok=True)

    scripts = sorted(sql_dir.glob("*.sql"))
    conn = get_connection(database=db_name)
    cursor = conn.cursor()

    execution_records: list[dict[str, Any]] = []
    captured_tables: dict[str, pd.DataFrame] = {}

    try:
        for script_path in scripts:
            stmts = split_sql_statements(script_path.read_text(encoding="utf-8"))
            q_idx = 0
            for stmt in stmts:
                if stmt.strip().upper().startswith("USE "):
                    cursor.execute(stmt)
                    continue
                t_q = perf_counter()
                cursor.execute(stmt)
                if cursor.with_rows:
                    q_idx += 1
                    rows = cursor.fetchall()
                    cols = [desc[0] for desc in cursor.description]
                    df = pd.DataFrame(rows, columns=cols)
                    tag = f"{script_path.stem}__q{q_idx:02d}"
                    captured_tables[tag] = df
                    df.to_csv(out_csv_dir / f"{tag}.csv", index=False, encoding="utf-8")
                    elapsed_q = perf_counter() - t_q
                    execution_records.append(
                        {
                            "script": script_path.name,
                            "query_tag": tag,
                            "rows_returned": len(df),
                            "elapsed_sec": round(elapsed_q, 3),
                            "status": "PASS",
                        }
                    )
                    logger.info("Executed %-48s | %4d rows | %.2fs", tag, len(df), elapsed_q)
                else:
                    # DDL/temp table statements inside 06_execution_plans
                    while cursor.nextset():
                        pass

        # Key KPI reconciliations against warehouse baseline
        exec_base = captured_tables["01_executive_and_revenue__q01"]
        total_orders = int(exec_base["total_orders"].sum())
        delivered_orders = int(exec_base["delivered_orders"].sum())
        recorded_gmv = sum(Decimal(str(x)) for x in exec_base["recorded_gmv_all_statuses_brl"])
        recorded_pay = sum(Decimal(str(x)) for x in exec_base["recorded_payment_all_statuses_brl"])
        assert total_orders == 99441
        assert delivered_orders == 96478
        assert recorded_gmv == Decimal("13591643.70")
        assert recorded_pay == Decimal("16008872.12")

        cust_summary = captured_tables["03_customer_analytics__q01"].iloc[0]
        assert int(cust_summary["total_delivered_orders"]) == 96478

        log_summary = captured_tables["05_logistics_geo_payment_marketing_experience__q01"].iloc[0]
        assert int(log_summary["eligible_sla_orders"]) == 96470

        summary_df = pd.DataFrame(execution_records)
        summary_df.to_csv(out_csv_dir / "execution_summary.csv", index=False, encoding="utf-8")

        total_sec = perf_counter() - t0
        write_sql_report(summary_df, captured_tables, total_sec)
        logger.info("SQL Analytics suite completed (%d queries) in %.2fs", len(summary_df), total_sec)
        return {"summary": summary_df, "tables": captured_tables, "elapsed_seconds": total_sec}
    finally:
        cursor.close()
        conn.close()


def write_sql_report(
    summary_df: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    total_sec: float,
) -> None:
    exec_base = tables["01_executive_and_revenue__q01"]
    cust = tables["03_customer_analytics__q01"].iloc[0]
    log_q = tables["05_logistics_geo_payment_marketing_experience__q01"].iloc[0]
    mkt_q = tables["05_logistics_geo_payment_marketing_experience__q07"]
    pareto_p = tables["04_product_and_seller_analytics__q02"].iloc[0]
    seller_conc = tables["04_product_and_seller_analytics__q06"].iloc[0]

    lines = [
        "# CommerceIQ — SQL Business Analytics Execution Report (Phase 8)",
        "",
        f"**Execution Timestamp (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Target Database:** `{get_database_name()}` (MySQL 8.0)",
        f"**Queries Executed:** {len(summary_df)} (All PASS)",
        f"**Total Execution Time:** {total_sec:.2f} seconds",
        "",
        "## 1. Headline Findings From Executed SQL",
        "",
        f"- **Order & Merchandise Baseline:** {int(exec_base['total_orders'].sum()):,} placed orders ({int(exec_base['delivered_orders'].sum()):,} delivered), **BRL {sum(Decimal(str(x)) for x in exec_base['delivered_merchandise_brl']):,.2f}** delivered merchandise value, **BRL {sum(Decimal(str(x)) for x in exec_base['recorded_gmv_all_statuses_brl']):,.2f}** total recorded GMV across all statuses.",
        f"- **Customer Repeat Behavior (`customer_unique_id`):** {int(cust['unique_delivered_customers']):,} unique delivered customers, **{int(cust['repeat_customers']):,}** repeat customers (**{float(cust['repeat_purchase_rate_pct']):.2f}%** repeat rate), average spend **BRL {float(cust['avg_observed_spend_brl']):,.2f}**.",
        f"- **Product & Seller Concentration:** **{int(pareto_p['products_contributing_80pct']):,}** of {int(pareto_p['total_sold_products']):,} sold products (**{float(pareto_p['pct_of_products_for_80pct_sales']):.2f}%**) drive 80% of delivered sales; Top 10% of sellers generate **{float(seller_conc['top10pct_share_pct']):.2f}%** of delivered sales.",
        f"- **Logistics SLA:** {int(log_q['eligible_sla_orders']):,} eligible SLA deliveries with **{float(log_q['on_time_rate_pct']):.4f}%** on-time rate ({int(log_q['late_orders']):,} late orders; mean delivery **{float(log_q['mean_total_delivery_days']):.2f}** days; mean positive delay **{float(log_q['mean_positive_delay_days']):.2f}** days).",
        f"- **Marketing Funnel:** {int(mkt_q['qualified_leads'].sum()):,} qualified leads, **{int(mkt_q['closed_deals'].sum()):,}** recorded closed deals.",
        "",
        "## 2. Query Execution Log",
        "",
        "| Script | Query Tag | Rows | Elapsed (s) | Status |",
        "|---|---|---:|---:|---|",
    ]
    for r in summary_df.itertuples(index=False):
        lines.append(f"| `{r.script}` | `{r.query_tag}` | {r.rows_returned} | {r.elapsed_sec:.3f} | {r.status} |")

    lines.append("")
    (PROJECT_ROOT / "reports" / "sql_analytics_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    res = run_sql_analytics()
    print(res["summary"].to_string(index=False))
    print(f"\nExecuted {len(res['summary'])} analytical SQL queries in {res['elapsed_seconds']:.2f} sec")
