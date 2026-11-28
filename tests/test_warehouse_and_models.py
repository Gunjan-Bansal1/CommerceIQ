"""
CommerceIQ - Phase 16 Local Integration, Cross-Tool KPI Reconciliation & Model Validation Tests

Validates end-to-end consistency across:
  - Python cleaned Parquet baseline
  - MySQL operational database
  - MySQL analytical warehouse & marts
  - Executed SQL analytics outputs
  - Excel business analytics workbook
  - Power BI DAX reconciliation
  - Predictive model leakage prevention & evaluation artifacts
"""

from decimal import Decimal
import json
import os
from pathlib import Path
import re

import openpyxl
import pandas as pd
import pytest

from src.database.connection import get_connection, get_database_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _mysql_available() -> bool:
    try:
        conn = get_connection(database=get_database_name())
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _mysql_available(), reason="Local MySQL commerceiq database unreachable in this environment")
def test_mysql_operational_and_warehouse_reconciliation():
    conn = get_connection(database=get_database_name())
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM orders),
                (SELECT COUNT(*) FROM fact_orders),
                (SELECT SUM(total_orders) FROM mart_executive_monthly),
                (SELECT SUM(price) FROM order_items),
                (SELECT SUM(merchandise_value) FROM fact_orders),
                (SELECT SUM(price) FROM fact_order_items),
                (SELECT SUM(recorded_gmv_brl) FROM mart_executive_monthly),
                (SELECT SUM(payment_value) FROM payments),
                (SELECT SUM(total_payment_value) FROM fact_orders),
                (SELECT SUM(payment_value) FROM fact_payments)
            """
        )
        row = cur.fetchone()
        assert int(row[0]) == int(row[1]) == int(row[2]) == 99441
        assert Decimal(str(row[3])) == Decimal(str(row[4])) == Decimal(str(row[5])) == Decimal(str(row[6])) == Decimal("13591643.70")
        assert Decimal(str(row[7])) == Decimal(str(row[8])) == Decimal(str(row[9])) == Decimal("16008872.12")
    finally:
        cur.close()
        conn.close()


def test_cross_tool_kpi_reconciliation_python_sql_excel_powerbi():
    pq_dir = PROJECT_ROOT / "data" / "processed" / "parquet"
    if not (pq_dir / "orders.parquet").is_file():
        pytest.skip("Processed parquet datasets unavailable")

    orders = pd.read_parquet(pq_dir / "orders.parquet")
    items = pd.read_parquet(pq_dir / "order_items.parquet")
    py_orders = len(orders)
    py_deliv = int(orders["order_status"].eq("delivered").sum())
    py_gmv = sum(items["price"], Decimal("0"))
    py_ontime = int(orders["is_on_time_delivery"].sum())
    py_elig_sla = int(orders["is_valid_delivery_promise_comparison"].sum())

    # SQL analytics CSV reconciliation
    sql_exec = pd.read_csv(PROJECT_ROOT / "reports" / "sql_analytics_results" / "01_executive_and_revenue__q01.csv")
    assert int(sql_exec["total_orders"].sum()) == py_orders == 99441
    assert int(sql_exec["delivered_orders"].sum()) == py_deliv == 96478
    assert round(float(sql_exec["recorded_gmv_all_statuses_brl"].sum()), 2) == float(py_gmv)

    # Excel calculated cached values reconciliation
    wb = openpyxl.load_workbook(PROJECT_ROOT / "excel" / "commerceiq_business_analytics.xlsx", data_only=True)
    ws_dash = wb["Executive Dashboard"]
    assert int(round(ws_dash["B6"].value)) == py_orders
    assert int(round(ws_dash["D6"].value)) == py_deliv
    assert abs(float(ws_dash["H6"].value) - float(py_gmv)) < 0.05
    assert abs(float(ws_dash["B10"].value) * 100.0 - (py_ontime / py_elig_sla * 100.0)) < 0.01
    wb.close()

    # Power BI DAX reconciliation doc + PBIP presence
    assert (PROJECT_ROOT / "powerbi" / "CommerceIQ.pbip").is_file()
    pbi_rec = (PROJECT_ROOT / "reports" / "powerbi_kpi_reconciliation.md").read_text(encoding="utf-8")
    assert "99,441" in pbi_rec
    assert "13,591,643.70" in pbi_rec


def test_predictive_model_outputs_and_no_leakage():
    fc_path = PROJECT_ROOT / "data" / "processed" / "forecast_outputs.csv"
    risk_path = PROJECT_ROOT / "data" / "processed" / "delivery_risk_predictions.csv"
    if not (fc_path.is_file() and risk_path.is_file()):
        pytest.skip("Model prediction outputs unavailable")

    fc = pd.read_csv(fc_path)
    assert set(fc["target"]) == {"merch_brl", "delivered_orders"}
    assert set(fc["record_type"]) == {"holdout_backtest", "illustrative_historical_projection"}
    assert (fc["predicted_value"] >= 0).all()

    risk = pd.read_csv(risk_path)
    assert len(risk) > 10000
    assert risk["predicted_late_prob"].between(0.0, 1.0).all()
    assert pd.to_datetime(risk["order_purchase_timestamp"]).min() >= pd.Timestamp("2018-06-01")

    # Verify forbidden post-purchase leakage columns are absent from delivery_risk_model feature lists
    model_src = (PROJECT_ROOT / "src" / "forecasting" / "delivery_risk_model.py").read_text(encoding="utf-8")
    feature_block = model_src.split("num_features = [")[1].split("all_features =")[0]
    for forbidden in ["delivery_duration", "carrier", "review_score", "delivery_deviation", "transit_duration"]:
        assert forbidden not in feature_block, f"Leakage feature found: {forbidden}"


def test_pipeline_execution_metadata_exists():
    summary_path = PROJECT_ROOT / "data" / "metadata" / "pipeline_execution_summary.json"
    if not summary_path.is_file():
        pytest.skip("Pipeline automation has not been executed yet")
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["status"] == "SUCCESS"


def test_powerbi_pbir_and_tmdl_bindings():
    tables_dir = PROJECT_ROOT / "powerbi" / "CommerceIQ.SemanticModel" / "definition" / "tables"
    model_cols = {}
    measures = set()
    for p in tables_dir.glob("*.tmdl"):
        txt = p.read_text(encoding="utf-8")
        model_cols[p.stem] = set(re.findall(r"^\tcolumn\s+([^\s=]+)", txt, flags=re.M))
        if p.stem == "_Measures":
            measures = set(re.findall(r"^\tmeasure\s+'([^']+)'", txt, flags=re.M))
        elif p.stem in {"customer_rfm_segments", "forecast_outputs", "delivery_risk_predictions", "decision_scenarios"}:
            assert "Table.TransformColumnTypes" in txt
            assert '"en-US"' in txt
        elif p.stem == "dim_date":
            assert "[date_key] > 0 and [full_date] <> null" in txt
            assert "\tisKey" in txt
            assert "Int64.From" in txt

    assert len(model_cols) == 17
    assert len(measures) >= 60

    rep = json.loads((PROJECT_ROOT / "powerbi" / "CommerceIQ.Report" / "report.json").read_text(encoding="utf-8"))
    assert len(rep["sections"]) == 10
    total_vis = 0
    for sec in rep["sections"]:
        for vc in sec["visualContainers"]:
            total_vis += 1
            sv = json.loads(vc["config"])["singleVisual"]
            if sv["visualType"] == "pageNavigator":
                continue
            pq = sv["prototypeQuery"]
            assert pq["Version"] == 2 and len(pq["Select"]) >= 1
            sel_names = {s["Name"] for s in pq["Select"]}
            for items in sv["projections"].values():
                for it in items:
                    ref = it["queryRef"]
                    assert ref in sel_names
                    ent, prop = ref.split(".", 1)
                    if ent == "_Measures":
                        assert prop in measures
                    else:
                        assert prop in model_cols[ent]
                        assert it.get("active") is True
    assert total_vis == 84


@pytest.mark.skipif(not _mysql_available(), reason="Local MySQL commerceiq database unreachable in this environment")
def test_powerbi_source_data_relationship_and_date_compatibility():
    """Verify MySQL & CSV source keys satisfy VertiPaq 1:N, isKey, and tinyint(1) rules."""
    tables_dir = PROJECT_ROOT / "powerbi" / "CommerceIQ.SemanticModel" / "definition" / "tables"

    conn = get_connection(database=get_database_name())
    cur = conn.cursor()
    try:
        # 1. Filtered dim_date calendar must have 0 NULLs, 0 duplicates, and 0 missing days
        cur.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN full_date IS NULL THEN 1 ELSE 0 END),
                   COUNT(full_date) - COUNT(DISTINCT full_date),
                   DATEDIFF(MAX(full_date), MIN(full_date)) + 1
            FROM dim_date
            WHERE date_key > 0 AND full_date IS NOT NULL
            """
        )
        valid_rows, nulls, dups, span_days = cur.fetchone()
        assert int(nulls) == 0 and int(dups) == 0
        assert int(valid_rows) == int(span_days) == 1827

        # 2. Active date foreign keys must never hit unknown -1 or NULL
        for tbl, col in [
            ("fact_orders", "purchase_date_key"),
            ("fact_orders", "estimated_date_key"),
            ("fact_marketing_funnel", "first_contact_date_key"),
        ]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL OR {col} <= 0")
            assert int(cur.fetchone()[0]) == 0, f"Invalid active date FK in {tbl}.{col}"

        # 3. Every 1-side relationship target key must be unique and non-null
        one_side_targets = [
            ("dim_customer", "customer_key"),
            ("dim_geography", "geo_key"),
            ("dim_seller", "seller_key"),
            ("dim_product", "product_key"),
            ("dim_payment_type", "payment_type_key"),
            ("dim_marketing_channel", "channel_key"),
            ("fact_orders", "order_key"),
            ("fact_orders", "order_id"),
        ]
        for tbl, col in one_side_targets:
            cur.execute(f"SELECT COUNT(*), SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END), COUNT(DISTINCT {col}) FROM {tbl}")
            tot, nulls_cnt, uniq_cnt = cur.fetchone()
            assert int(nulls_cnt) == 0 and int(tot) == int(uniq_cnt), f"Invalid 1-side key {tbl}.{col}"

        # 4. Every warehouse table with tinyint(1) columns must normalize flags in TMDL M partition
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND (table_name LIKE 'dim\\_%' OR table_name LIKE 'fact\\_%')
              AND LOWER(column_type) LIKE 'tinyint(1)%'
            """,
            (get_database_name(),),
        )
        for tname, cname in cur.fetchall():
            tmdl_txt = (tables_dir / f"{tname}.tmdl").read_text(encoding="utf-8")
            assert f'"{cname}"' in tmdl_txt and "Int64.From" in tmdl_txt, (
                f"Missing tinyint(1) -> Int64.From normalization for {tname}.{cname}"
            )

        cur.execute("SELECT order_id FROM fact_orders")
        valid_order_ids = {r[0] for r in cur.fetchall()}
    finally:
        cur.close()
        conn.close()

    # 5. CSV partitions exist cleanly and delivery_risk_predictions aligns 100% with fact_orders
    for csv_name in ["customer_rfm_segments", "forecast_outputs", "delivery_risk_predictions", "decision_scenarios"]:
        csv_path = PROJECT_ROOT / "data" / "processed" / f"{csv_name}.csv"
        assert csv_path.is_file()
        tmdl_txt = (tables_dir / f"{csv_name}.tmdl").read_text(encoding="utf-8")
        assert str(csv_path.resolve()) in tmdl_txt
        if csv_name == "delivery_risk_predictions":
            risk_df = pd.read_csv(csv_path, usecols=["order_id"])
            assert risk_df["order_id"].notna().all()
            assert risk_df["order_id"].is_unique
            assert set(risk_df["order_id"]).issubset(valid_order_ids)
