"""
CommerceIQ - Operational MySQL Database Loader & Validator (Phase 5)

Loads the 13 cleaned Parquet datasets into MySQL 8.0 (`commerceiq`),
executes DDL/index scripts idempotently, preserves optional relationship gaps,
enforces required foreign keys, and validates counts and exact monetary totals.
"""

from __future__ import annotations

import logging
import re
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

LOAD_ORDER = [
    "category_translation",
    "geolocation_lookup",
    "geolocation",
    "brazil_holidays",
    "marketing_leads",
    "sellers",
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
    "reviews",
    "closed_deals",
]

DATE_COLUMNS = {
    "brazil_holidays": {"date"},
    "marketing_leads": {"first_contact_date"},
    "orders": {"order_estimated_delivery_date", "purchase_date"},
    "reviews": {"review_creation_date"},
}

EXPECTED_FINANCIALS = {
    "recorded_merchandise_brl": Decimal("13591643.70"),
    "recorded_freight_brl": Decimal("2251909.54"),
    "recorded_item_total_brl": Decimal("15843553.24"),
    "recorded_payment_brl": Decimal("16008872.12"),
    "declared_monthly_revenue_brl": Decimal("61784006.00"),
}

EXPECTED_OPTIONAL_GAPS = {
    "customers->geolocation_lookup_unmatched": 279,
    "sellers->geolocation_lookup_unmatched": 7,
    "closed_deals->sellers_unmatched": 462,
}


def configure_logger() -> logging.Logger:
    log_path = PROJECT_ROOT / "logs" / "database_load.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("commerceiq.database")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def split_sql_statements(sql_text: str) -> list[str]:
    """Split a MySQL script respecting DELIMITER directives and SQL comments."""
    statements: list[str] = []
    delimiter = ";"
    buffer: list[str] = []

    for raw_line in sql_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        m = re.match(r"^DELIMITER\s+(\S+)$", stripped, flags=re.IGNORECASE)
        if m:
            if buffer:
                chunk = "\n".join(buffer).strip()
                if chunk:
                    statements.append(chunk)
                buffer.clear()
            delimiter = m.group(1)
            continue

        buffer.append(raw_line)
        joined = "\n".join(buffer)
        while delimiter in joined:
            idx = joined.index(delimiter)
            stmt = joined[:idx].strip()
            if stmt:
                statements.append(stmt)
            joined = joined[idx + len(delimiter) :]
        buffer = [joined] if joined.strip() else []

    if buffer:
        tail = "\n".join(buffer).strip()
        if tail:
            statements.append(tail)
    return statements


def execute_sql_file(cursor: Any, sql_path: Path) -> list[list[tuple[Any, ...]]]:
    """Execute all statements in a SQL file, returning any result sets."""
    text = sql_path.read_text(encoding="utf-8")
    results: list[list[tuple[Any, ...]]] = []
    for stmt in split_sql_statements(text):
        cursor.execute(stmt)
        if cursor.with_rows:
            results.append(cursor.fetchall())
    return results


def dataframe_to_records(df: pd.DataFrame, table_name: str) -> list[tuple[Any, ...]]:
    """Convert a typed Pandas DataFrame into MySQL-safe row tuples."""
    date_cols = DATE_COLUMNS.get(table_name, set())
    converted_cols: list[list[Any]] = []

    for col in df.columns:
        s = df[col]
        dtype_str = str(s.dtype)
        if pd.api.types.is_datetime64_any_dtype(s):
            fmt = "%Y-%m-%d" if col in date_cols else "%Y-%m-%d %H:%M:%S"
            vals = [None if pd.isna(v) else v.strftime(fmt) for v in s]
        elif dtype_str == "boolean":
            vals = [None if pd.isna(v) else int(bool(v)) for v in s]
        elif dtype_str == "Int64":
            vals = [None if pd.isna(v) else int(v) for v in s]
        elif dtype_str == "Float64":
            vals = [None if pd.isna(v) else float(v) for v in s]
        else:
            vals = [None if pd.isna(v) else v for v in s]
        converted_cols.append(vals)

    return list(zip(*converted_cols))


def validate_database(cursor: Any) -> dict[str, Any]:
    """Run Phase 5 validation checks against the loaded MySQL database."""
    manifest = pd.read_csv(PROJECT_ROOT / "data" / "metadata" / "processed_manifest.csv")
    expected_counts = (
        manifest.loc[manifest["format"] == "PARQUET", ["dataset", "rows"]]
        .set_index("dataset")["rows"]
        .to_dict()
    )

    row_counts: dict[str, int] = {}
    for table in LOAD_ORDER:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = int(cursor.fetchone()[0])
        row_counts[table] = cnt
        assert cnt == int(expected_counts[table]), (
            f"Row count mismatch for {table}: got {cnt}, expected {expected_counts[table]}"
        )

    # 8 required relationships
    fk_queries = {
        "orders->customers": "SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL",
        "order_items->orders": "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.order_id WHERE o.order_id IS NULL",
        "order_items->products": "SELECT COUNT(*) FROM order_items oi LEFT JOIN products p ON oi.product_id = p.product_id WHERE p.product_id IS NULL",
        "order_items->sellers": "SELECT COUNT(*) FROM order_items oi LEFT JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_id IS NULL",
        "payments->orders": "SELECT COUNT(*) FROM payments p LEFT JOIN orders o ON p.order_id = o.order_id WHERE o.order_id IS NULL",
        "reviews->orders": "SELECT COUNT(*) FROM reviews r LEFT JOIN orders o ON r.order_id = o.order_id WHERE o.order_id IS NULL",
        "products->category_translation": "SELECT COUNT(*) FROM products p LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name WHERE ct.product_category_name IS NULL",
        "closed_deals->marketing_leads": "SELECT COUNT(*) FROM closed_deals cd LEFT JOIN marketing_leads ml ON cd.mql_id = ml.mql_id WHERE ml.mql_id IS NULL",
    }
    orphan_counts: dict[str, int] = {}
    for rel, q in fk_queries.items():
        cursor.execute(q)
        orphans = int(cursor.fetchone()[0])
        orphan_counts[rel] = orphans
        assert orphans == 0, f"Required FK {rel} has {orphans} orphan rows"

    # 3 optional relationships
    gap_queries = {
        "customers->geolocation_lookup_unmatched": "SELECT COUNT(*) FROM customers c LEFT JOIN geolocation_lookup g ON c.customer_zip_code_prefix = g.zip_code_prefix WHERE g.zip_code_prefix IS NULL",
        "sellers->geolocation_lookup_unmatched": "SELECT COUNT(*) FROM sellers s LEFT JOIN geolocation_lookup g ON s.seller_zip_code_prefix = g.zip_code_prefix WHERE g.zip_code_prefix IS NULL",
        "closed_deals->sellers_unmatched": "SELECT COUNT(*) FROM closed_deals cd LEFT JOIN sellers s ON cd.seller_id = s.seller_id WHERE s.seller_id IS NULL",
    }
    optional_gaps: dict[str, int] = {}
    for gap_name, q in gap_queries.items():
        cursor.execute(q)
        unmatched = int(cursor.fetchone()[0])
        optional_gaps[gap_name] = unmatched
        assert unmatched == EXPECTED_OPTIONAL_GAPS[gap_name], (
            f"Optional gap mismatch for {gap_name}: got {unmatched}, expected {EXPECTED_OPTIONAL_GAPS[gap_name]}"
        )

    # Financial totals
    cursor.execute(
        """
        SELECT
            (SELECT SUM(price) FROM order_items),
            (SELECT SUM(freight_value) FROM order_items),
            (SELECT SUM(item_value_with_freight) FROM order_items),
            (SELECT SUM(payment_value) FROM payments),
            (SELECT SUM(declared_monthly_revenue) FROM closed_deals)
        """
    )
    fin_row = cursor.fetchone()
    financials = {
        "recorded_merchandise_brl": Decimal(str(fin_row[0])),
        "recorded_freight_brl": Decimal(str(fin_row[1])),
        "recorded_item_total_brl": Decimal(str(fin_row[2])),
        "recorded_payment_brl": Decimal(str(fin_row[3])),
        "declared_monthly_revenue_brl": Decimal(str(fin_row[4])),
    }
    for k, expected in EXPECTED_FINANCIALS.items():
        assert financials[k] == expected, f"Financial mismatch for {k}: {financials[k]} != {expected}"

    # Sanity checks (postal zeros, nullable booleans, utf8mb4 Portuguese text)
    cursor.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM customers WHERE CHAR_LENGTH(customer_zip_code_prefix) <> 5),
            (SELECT COUNT(*) FROM sellers WHERE CHAR_LENGTH(seller_zip_code_prefix) <> 5),
            (SELECT COUNT(*) FROM geolocation_lookup WHERE zip_code_prefix LIKE '0%'),
            (SELECT COUNT(*) FROM closed_deals WHERE has_company IS NULL),
            (SELECT COUNT(*) FROM reviews WHERE review_comment_message LIKE '%ã%' OR review_comment_message LIKE '%ç%')
        """
    )
    bad_cust_zip, bad_seller_zip, zero_zips, null_company, pt_reviews = [int(x) for x in cursor.fetchone()]
    assert bad_cust_zip == 0
    assert bad_seller_zip == 0
    assert zero_zips > 0
    assert null_company == 779
    assert pt_reviews > 0

    return {
        "row_counts": row_counts,
        "orphan_counts": orphan_counts,
        "optional_gaps": optional_gaps,
        "financials": financials,
        "sanity": {
            "bad_customer_zip_len": bad_cust_zip,
            "bad_seller_zip_len": bad_seller_zip,
            "zero_prefixed_zip_count": zero_zips,
            "null_has_company_deals": null_company,
            "portuguese_diacritic_reviews": pt_reviews,
        },
    }


def write_validation_report(
    load_summary_df: pd.DataFrame,
    validation: dict[str, Any],
    total_sec: float,
) -> None:
    """Write Phase 5 database validation report and metadata CSV."""
    meta_path = PROJECT_ROOT / "data" / "metadata" / "db_load_summary.csv"
    load_summary_df.to_csv(meta_path, index=False, encoding="utf-8")

    lines = [
        "# CommerceIQ — Operational Database Loading & Validation Report",
        "",
        f"**Execution Timestamp (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Target Database:** `{get_database_name()}` (MySQL 8.0, `utf8mb4` / `utf8mb4_unicode_ci`)",
        f"**Total Pipeline Duration:** {total_sec:.2f} seconds",
        f"**Total Records Loaded:** {int(load_summary_df['rows_loaded'].sum()):,}",
        "",
        "## 1. Table Load Reconciliation",
        "",
        "| Table | Rows Loaded | Duration (sec) | Status |",
        "|---|---:|---:|---|",
    ]
    for r in load_summary_df.itertuples(index=False):
        lines.append(f"| `{r.table_name}` | {r.rows_loaded:,} | {r.load_seconds:.2f} | {r.status} |")

    lines.extend([
        "",
        "## 2. Required Foreign-Key Integrity (8/8 Enforced)",
        "",
        "| Relationship | Orphan Rows | Status |",
        "|---|---:|---|",
    ])
    for rel, cnt in validation["orphan_counts"].items():
        lines.append(f"| `{rel}` | {cnt} | PASS |")

    lines.extend([
        "",
        "## 3. Preserved Optional Relationship Gaps",
        "",
        "| Optional Reference | Unmatched Rows | Status |",
        "|---|---:|---|",
    ])
    for gap, cnt in validation["optional_gaps"].items():
        lines.append(f"| `{gap}` | {cnt:,} | PRESERVED |")

    lines.extend([
        "",
        "## 4. Exact Financial Reconciliation (BRL)",
        "",
        "| Measure | MySQL Total (BRL) | Status |",
        "|---|---:|---|",
    ])
    for k, v in validation["financials"].items():
        lines.append(f"| `{k}` | {v:,.2f} | EXACT MATCH |")

    s = validation["sanity"]
    lines.extend([
        "",
        "## 5. Encoding, Postal Formatting & Null Preservation Checks",
        "",
        f"- Invalid customer postal prefix lengths (`<> 5`): **{s['bad_customer_zip_len']}**",
        f"- Invalid seller postal prefix lengths (`<> 5`): **{s['bad_seller_zip_len']}**",
        f"- Leading-zero postal prefixes preserved (`0%`): **{s['zero_prefixed_zip_count']:,}**",
        f"- Nullable boolean `NULL` preserved (`closed_deals.has_company IS NULL`): **{s['null_has_company_deals']:,}**",
        f"- UTF-8 Portuguese diacritic reviews preserved: **{s['portuguese_diacritic_reviews']:,}**",
        "",
    ])
    report_path = PROJECT_ROOT / "reports" / "database_validation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def load_operational_database(
    truncate_first: bool = True,
    batch_size: int = 5000,
) -> dict[str, Any]:
    """Create schema, load all 13 cleaned Parquet tables, and validate."""
    logger = configure_logger()
    overall_start = perf_counter()
    db_name = get_database_name()
    logger.info("Starting CommerceIQ operational database load into `%s`", db_name)

    schema_sql = PROJECT_ROOT / "sql" / "01_schema" / "01_create_database_and_tables.sql"
    index_sql = PROJECT_ROOT / "sql" / "01_schema" / "02_indexes_and_constraints.sql"
    parquet_dir = PROJECT_ROOT / "data" / "processed" / "parquet"

    conn = get_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    load_records: list[dict[str, Any]] = []
    try:
        # 1. Create database, tables, and indexes idempotently
        execute_sql_file(cursor, schema_sql)
        execute_sql_file(cursor, index_sql)
        conn.commit()
        logger.info("Schema and indexes verified/created.")

        cursor.execute(f"USE {db_name}")

        # 2. Safe idempotent reset in reverse dependency order
        if truncate_first:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in reversed(LOAD_ORDER):
                cursor.execute(f"TRUNCATE TABLE {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
            logger.info("Truncated existing tables in reverse dependency order.")

        # 3. Load each table in topological parent-first order with FK checks ON
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        for table in LOAD_ORDER:
            t0 = perf_counter()
            df = pd.read_parquet(parquet_dir / f"{table}.parquet")
            cols = ", ".join(df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            records = dataframe_to_records(df, table)

            try:
                for start in range(0, len(records), batch_size):
                    chunk = records[start : start + batch_size]
                    cursor.executemany(insert_sql, chunk)
                conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("Transaction rolled back while loading `%s`", table)
                raise

            elapsed = perf_counter() - t0
            load_records.append(
                {"table_name": table, "rows_loaded": len(records), "load_seconds": round(elapsed, 3), "status": "LOADED"}
            )
            logger.info("Loaded %-22s | %7d rows | %.2f sec", table, len(records), elapsed)

        # 4. Validate loaded operational database
        validation = validate_database(cursor)
        total_sec = perf_counter() - overall_start
        load_summary_df = pd.DataFrame(load_records)
        write_validation_report(load_summary_df, validation, total_sec)
        logger.info("Operational database validation PASSED in %.2f sec.", total_sec)
        return {"load_summary": load_summary_df, "validation": validation, "total_seconds": total_sec}

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    result = load_operational_database(truncate_first=True, batch_size=5000)
    print(result["load_summary"].to_string(index=False))
    print(f"\nTotal load & validation time: {result['total_seconds']:.2f} sec")
