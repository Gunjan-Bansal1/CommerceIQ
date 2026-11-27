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
