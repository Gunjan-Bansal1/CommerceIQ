"""
CommerceIQ - Analytical Data Warehouse Builder & Reconciler (Phase 6)

Creates the star/constellation schema (7 dimensions, 5 facts), builds the
9 analytical data mart views, reconciles all row counts and financial totals
against the operational database, and writes reconciliation documentation.
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
from src.database.load_database import execute_sql_file

WAREHOUSE_TABLES = [
    "dim_date",
    "dim_geography",
    "dim_customer",
    "dim_seller",
    "dim_product",
    "dim_payment_type",
    "dim_marketing_channel",
    "fact_orders",
    "fact_order_items",
    "fact_payments",
    "fact_reviews",
    "fact_marketing_funnel",
]

DATA_MARTS = [
    "mart_executive_monthly",
    "mart_customer_intelligence",
    "mart_product_category_performance",
    "mart_seller_performance",
    "mart_delivery_logistics",
    "mart_customer_satisfaction",
    "mart_marketing_funnel",
    "mart_geographic_performance",
    "mart_payment_reconciliation",
]


def configure_logger() -> logging.Logger:
    log_path = PROJECT_ROOT / "logs" / "warehouse_build.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("commerceiq.warehouse")
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


def validate_warehouse(cursor: Any) -> dict[str, Any]:
    """Validate warehouse grain, dimension uniqueness, and financial reconciliation."""
    counts: dict[str, int] = {}
    for tbl in WAREHOUSE_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        counts[tbl] = int(cursor.fetchone()[0])

    # Expected exact row counts
    assert counts["dim_date"] == 1828, f"dim_date unexpected count: {counts['dim_date']}"
    assert counts["dim_geography"] == 19012, f"dim_geography unexpected count: {counts['dim_geography']}"
    assert counts["dim_customer"] == 99441
    assert counts["dim_seller"] == 3096
    assert counts["dim_product"] == 32951
    assert counts["fact_orders"] == 99441
    assert counts["fact_order_items"] == 112650
    assert counts["fact_payments"] == 103886
    assert counts["fact_reviews"] == 99224
    assert counts["fact_marketing_funnel"] == 8000

    # Financial reconciliation across fact_orders, fact_order_items, fact_payments, and ops tables
    cursor.execute(
        """
        SELECT
            (SELECT SUM(merchandise_value) FROM fact_orders),
            (SELECT SUM(price) FROM fact_order_items),
            (SELECT SUM(price) FROM order_items),
            (SELECT SUM(freight_value) FROM fact_orders),
            (SELECT SUM(freight_value) FROM fact_order_items),
            (SELECT SUM(total_payment_value) FROM fact_orders),
            (SELECT SUM(payment_value) FROM fact_payments),
            (SELECT SUM(payment_value) FROM payments),
            (SELECT SUM(declared_monthly_revenue) FROM fact_marketing_funnel)
        """
    )
    vals = [Decimal(str(x)) for x in cursor.fetchone()]
    (
        fo_merch, foi_merch, ops_merch,
        fo_freight, foi_freight,
        fo_pay, fp_pay, ops_pay,
        fm_decl,
    ) = vals

    assert fo_merch == foi_merch == ops_merch == Decimal("13591643.70")
    assert fo_freight == foi_freight == Decimal("2251909.54")
    assert fo_pay == fp_pay == ops_pay == Decimal("16008872.12")
    assert fm_decl == Decimal("61784006.00")

    # Mart reconciliation
    cursor.execute("SELECT SUM(total_orders), SUM(recorded_gmv_brl) FROM mart_executive_monthly")
    mart_orders, mart_gmv = cursor.fetchone()
    assert int(mart_orders) == 99441
    assert Decimal(str(mart_gmv)) == Decimal("13591643.70")

    mart_counts: dict[str, int] = {}
    for mart in DATA_MARTS:
        cursor.execute(f"SELECT COUNT(*) FROM {mart}")
        mart_counts[mart] = int(cursor.fetchone()[0])
        assert mart_counts[mart] > 0, f"Mart {mart} is empty!"

    return {
        "table_counts": counts,
        "mart_counts": mart_counts,
        "financials": {
            "fact_orders_merch_brl": fo_merch,
            "fact_order_items_merch_brl": foi_merch,
            "fact_orders_freight_brl": fo_freight,
            "fact_orders_payment_brl": fo_pay,
            "fact_payments_brl": fp_pay,
            "fact_marketing_declared_rev_brl": fm_decl,
        },
    }


def write_reconciliation_report(validation: dict[str, Any], elapsed_sec: float) -> None:
    rows = [
        {"object_name": k, "object_type": "dimension_or_fact", "row_count": v}
        for k, v in validation["table_counts"].items()
    ] + [
        {"object_name": k, "object_type": "data_mart_view", "row_count": v}
        for k, v in validation["mart_counts"].items()
    ]
    pd.DataFrame(rows).to_csv(
        PROJECT_ROOT / "data" / "metadata" / "warehouse_summary.csv",
        index=False,
        encoding="utf-8",
    )

    lines = [
        "# CommerceIQ — Data Warehouse Reconciliation Report",
        "",
        f"**Execution Timestamp (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Warehouse Schema:** `{get_database_name()}`",
        f"**Build Duration:** {elapsed_sec:.2f} seconds",
        "",
        "## 1. Dimension & Fact Table Counts",
        "",
        "| Table | Role | Row Count |",
        "|---|---|---:|",
    ]
    for tbl, cnt in validation["table_counts"].items():
        role = "Dimension" if tbl.startswith("dim_") else "Fact"
        lines.append(f"| `{tbl}` | {role} | {cnt:,} |")

    lines.extend([
        "",
        "## 2. Analytical Data Mart Views",
        "",
        "| View | Row Count |",
        "|---|---:|",
    ])
    for mart, cnt in validation["mart_counts"].items():
        lines.append(f"| `{mart}` | {cnt:,} |")

    lines.extend([
        "",
        "## 3. Financial & Grain Fan-Out Reconciliation",
        "",
        "| Check | Warehouse Total (BRL) | Status |",
        "|---|---:|---|",
    ])
    for k, v in validation["financials"].items():
        lines.append(f"| `{k}` | {v:,.2f} | EXACT MATCH |")

    lines.extend([
        "",
        "- `fact_orders` pre-aggregates `order_items`, `payments`, and `reviews` at `order_id` grain prior to joining, preventing fan-out across 99,441 orders.",
        "- Unknown dimension members (`date_key = -1`, `geo_key = -1`, `seller_key = -1`) preserve unmatched optional references cleanly.",
        "",
    ])
    (PROJECT_ROOT / "reports" / "warehouse_reconciliation_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def build_warehouse() -> dict[str, Any]:
    logger = configure_logger()
    t0 = perf_counter()
    db_name = get_database_name()
    logger.info("Building CommerceIQ analytical warehouse in `%s`", db_name)

    wh_dir = PROJECT_ROOT / "sql" / "02_warehouse"
    conn = get_connection(database=db_name)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        for script_name in [
            "01_create_warehouse_schema.sql",
            "02_build_warehouse_tables.sql",
            "03_create_data_marts.sql",
        ]:
            t_step = perf_counter()
            execute_sql_file(cursor, wh_dir / script_name)
            conn.commit()
            logger.info("Executed %-36s in %.2f sec", script_name, perf_counter() - t_step)

        validation = validate_warehouse(cursor)
        elapsed = perf_counter() - t0
        write_reconciliation_report(validation, elapsed)
        logger.info("Warehouse build and reconciliation PASSED in %.2f sec", elapsed)
        return {"validation": validation, "elapsed_seconds": elapsed}
    except Exception:
        conn.rollback()
        logger.exception("Warehouse build failed; rolled back transaction.")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    res = build_warehouse()
    for tbl, cnt in res["validation"]["table_counts"].items():
        print(f"{tbl:24s} : {cnt:>8,}")
    print(f"\nWarehouse build & reconciliation completed in {res['elapsed_seconds']:.2f} sec")
