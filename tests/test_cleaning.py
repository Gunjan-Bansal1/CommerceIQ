"""
CommerceIQ - Automated Data Cleaning Regression Tests

Uses a session-scoped fixture so the cleaning pipeline runs once
across the test module (`export=False`, preserving existing processed files).
"""

import hashlib
import json
from decimal import Decimal

import openpyxl
import pandas as pd
import pytest

from src.transformation.clean import PROJECT_ROOT, run_cleaning


@pytest.fixture(scope="session")
def cleaning_result():
    """Execute the cleaning pipeline once in-memory for all cleaning tests."""
    return run_cleaning(export=False)


@pytest.fixture(scope="session")
def cleaned_datasets(cleaning_result):
    return cleaning_result["datasets"]


def test_dataset_count(cleaned_datasets):
    expected_names = {
        "orders",
        "customers",
        "order_items",
        "payments",
        "reviews",
        "products",
        "sellers",
        "geolocation",
        "category_translation",
        "marketing_leads",
        "closed_deals",
        "brazil_holidays",
        "geolocation_lookup",
    }
    assert len(cleaned_datasets) == 13
    assert set(cleaned_datasets.keys()) == expected_names


def test_record_reconciliation(cleaning_result, cleaned_datasets):
    summary = cleaning_result["cleaning_summary"].set_index("metric")["value"].to_dict()
    assert int(summary["Original datasets"]) == 12
    assert int(summary["Final datasets"]) == 13
    assert int(summary["Original records"]) == 1_559_806
    assert int(summary["Records removed"]) == 279_668
    assert int(summary["Records added"]) == 19_014
    assert int(summary["Final records"]) == 1_299_152
    assert sum(len(df) for df in cleaned_datasets.values()) == 1_299_152

    expected_rows = {
        "orders": 99_441,
        "customers": 99_441,
        "order_items": 112_650,
        "payments": 103_886,
        "reviews": 99_224,
        "products": 32_951,
        "sellers": 3_095,
        "geolocation": 720_495,
        "category_translation": 74,
        "marketing_leads": 8_000,
        "closed_deals": 842,
        "brazil_holidays": 42,
        "geolocation_lookup": 19_011,
    }
    for name, rows in expected_rows.items():
        assert len(cleaned_datasets[name]) == rows, f"Row count mismatch for {name}"


def test_schema_and_data_dictionary(cleaning_result, cleaned_datasets):
    dictionary = cleaning_result["data_dictionary"]
    total_cols = sum(len(df.columns) for df in cleaned_datasets.values())
    assert total_cols == 165
    assert len(dictionary) == 165
    assert not dictionary.duplicated(subset=["dataset", "column"]).any()

    expected_dtype_mapping = {
        "STRING": "string",
        "TEXT": "string",
        "JSON": "string",
        "INTEGER": "Int64",
        "FLOAT": "Float64",
        "DECIMAL": "object",
        "DATE": "datetime64[ns]",
        "DATETIME": "datetime64[ns]",
        "BOOLEAN": "boolean",
    }
    for row in dictionary.itertuples(index=False):
        expected = expected_dtype_mapping[row.recommended_dtype]
        assert str(cleaned_datasets[row.dataset][row.column].dtype) == expected


def test_primary_keys(cleaning_result, cleaned_datasets):
    dictionary = cleaning_result["data_dictionary"]
    for dataset_name, df in cleaned_datasets.items():
        key_fields = dictionary.loc[
            dictionary["dataset"].eq(dataset_name)
            & dictionary["primary_key_component"].eq(True),
            "column",
        ].tolist()
        assert key_fields, f"Missing primary key definition for {dataset_name}"
        assert df[key_fields].notna().all().all()
        assert not df.duplicated(subset=key_fields).any()


def test_geographic_lookup_and_join_safety(cleaned_datasets):
    lookup = cleaned_datasets["geolocation_lookup"]
    geo = cleaned_datasets["geolocation"]
    customers = cleaned_datasets["customers"]
    sellers = cleaned_datasets["sellers"]

    assert len(geo) == 720_495
    assert int((~geo["is_valid_geo_observation"]).sum()) == 27
    assert len(lookup) == 19_011
    assert lookup["zip_code_prefix"].is_unique
    assert lookup["zip_code_prefix"].notna().all()
    assert int(lookup["is_ambiguous_zip"].sum()) == 552

    cust_joined = customers.merge(
        lookup, left_on="customer_zip_code_prefix", right_on="zip_code_prefix", how="left"
    )
    seller_joined = sellers.merge(
        lookup, left_on="seller_zip_code_prefix", right_on="zip_code_prefix", how="left"
    )
    assert len(cust_joined) == len(customers)
    assert len(seller_joined) == len(sellers)
    assert int((~customers["has_geolocation_match"]).sum()) == 279
    assert int((~sellers["has_geolocation_match"]).sum()) == 7


def test_product_category_coverage(cleaned_datasets):
    products = cleaned_datasets["products"]
    translations = cleaned_datasets["category_translation"]

    assert len(translations) == 74
    assert translations["product_category_name"].is_unique
    assert products["product_category_name"].notna().all()
    assert products["product_category_name"].isin(translations["product_category_name"]).all()
    assert int(products["product_category_name"].eq("unknown").sum()) == 610


def test_financial_integrity(cleaned_datasets):
    items = cleaned_datasets["order_items"]
    payments = cleaned_datasets["payments"]
    deals = cleaned_datasets["closed_deals"]

    merch = sum(items["price"], Decimal("0"))
    freight = sum(items["freight_value"], Decimal("0"))
    item_total = sum(items["item_value_with_freight"], Decimal("0"))
    pay_total = sum(payments["payment_value"], Decimal("0"))
    declared_rev = sum(deals["declared_monthly_revenue"], Decimal("0"))

    assert merch == Decimal("13591643.70")
    assert freight == Decimal("2251909.54")
    assert item_total == Decimal("15843553.24")
    assert item_total == merch + freight
    assert pay_total == Decimal("16008872.12")
    assert declared_rev == Decimal("61784006.00")


def test_delivery_features(cleaned_datasets):
    orders = cleaned_datasets["orders"]
    for col in [
        "approval_duration_hours",
        "processing_duration_days",
        "transit_duration_days",
        "delivery_duration_days",
        "estimated_delivery_days",
    ]:
        assert not orders[col].dropna().lt(0).any(), f"Negative duration in {col}"

    eligible = int(orders["is_valid_delivery_promise_comparison"].sum())
    assert eligible == 96_470
    perf = orders["delivery_performance"].value_counts().to_dict()
    assert perf["early"] == 88_644
    assert perf["on_time"] == 1_292
    assert perf["late"] == 6_534
    assert int(orders["is_on_time_delivery"].sum()) == 89_936
    assert round(89_936 / 96_470 * 100, 4) == 93.2269
    assert round(float(orders["delivery_duration_days"].mean()), 4) == 12.5582


def test_missing_value_treatment(cleaning_result, cleaned_datasets):
    assert int(cleaned_datasets["products"]["product_category_name"].eq("unknown").sum()) == 610
    assert int(cleaned_datasets["marketing_leads"]["origin"].eq("not_recorded").sum()) == 60
    assert "launch_year" not in cleaned_datasets["brazil_holidays"].columns

    total_missing = sum(int(df.isna().sum().sum()) for df in cleaned_datasets.values())
    assert total_missing == 186_367
    summary_missing = int(
        cleaning_result["cleaning_summary"].set_index("metric").loc["Final missing cells", "value"]
    )
    assert summary_missing == 186_367


def test_relationships(cleaned_datasets):
    orders = cleaned_datasets["orders"]
    customers = cleaned_datasets["customers"]
    items = cleaned_datasets["order_items"]
    payments = cleaned_datasets["payments"]
    reviews = cleaned_datasets["reviews"]
    products = cleaned_datasets["products"]
    sellers = cleaned_datasets["sellers"]
    translations = cleaned_datasets["category_translation"]
    leads = cleaned_datasets["marketing_leads"]
    deals = cleaned_datasets["closed_deals"]

    assert orders["customer_id"].isin(customers["customer_id"]).all()
    assert items["order_id"].isin(orders["order_id"]).all()
    assert items["product_id"].isin(products["product_id"]).all()
    assert items["seller_id"].isin(sellers["seller_id"]).all()
    assert payments["order_id"].isin(orders["order_id"]).all()
    assert reviews["order_id"].isin(orders["order_id"]).all()
    assert products["product_category_name"].isin(translations["product_category_name"]).all()
    assert deals["mql_id"].isin(leads["mql_id"]).all()

    assert int((~orders["has_order_items"]).sum()) == 775
    assert int((~orders["has_payment_records"]).sum()) == 1
    assert int((~orders["has_review_records"]).sum()) == 768
    assert int(deals["has_marketplace_seller_match"].sum()) == 380
    assert int((~deals["has_marketplace_seller_match"]).sum()) == 462
    assert int((~leads["has_closed_deal"]).sum()) == 7_158


def test_quality_reconciliation(cleaning_result):
    q_reg = cleaning_result["quality_register"]
    assert len(q_reg) == 43
    counts = q_reg["treatment_status"].value_counts().to_dict()
    assert counts == {
        "CONTROLLED": 26,
        "ACCEPTED LIMITATION": 10,
        "RESOLVED": 7,
    }


def test_final_validation(cleaning_result):
    val_df = cleaning_result["validation_results"]
    audit_df = cleaning_result["cleaning_audit"]
    assert len(val_df) == 20
    assert val_df["status"].eq("PASS").all()
    assert len(audit_df) == 107


def test_processed_file_integrity():
    manifest_path = PROJECT_ROOT / "data" / "metadata" / "processed_manifest.csv"
    schema_path = PROJECT_ROOT / "data" / "processed" / "processed_schema.json"
    summary_path = PROJECT_ROOT / "data" / "metadata" / "cleaning_summary.csv"
    report_path = PROJECT_ROOT / "reports" / "data_cleaning_report.xlsx"
    doc_path = PROJECT_ROOT / "docs" / "07_data_cleaning.md"

    assert manifest_path.is_file()
    assert schema_path.is_file()
    assert summary_path.is_file()
    assert report_path.is_file()
    assert doc_path.is_file()

    manifest = pd.read_csv(manifest_path)
    assert len(manifest) == 26
    assert manifest["validation_status"].eq("PASS").all()

    for row in manifest.itertuples(index=False):
        fpath = PROJECT_ROOT / row.relative_path
        assert fpath.is_file(), f"Missing processed file: {row.relative_path}"
        sha256 = hashlib.sha256()
        with fpath.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256.update(chunk)
        assert sha256.hexdigest() == row.sha256, f"Checksum mismatch: {row.relative_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert len(schema) == 13
    assert sum(int(info["columns"]) for info in schema.values()) == 165
    assert sum(len(info["fields"]) for info in schema.values()) == 165

    wb = openpyxl.load_workbook(report_path, read_only=True)
    assert len(wb.sheetnames) == 35
    wb.close()
