"""
CommerceIQ - Public CI-Safe Unit Tests (Synthetic Fixtures Only)

Does NOT depend on uncommitted raw/processed data or local Windows MySQL.
"""

import numpy as np
import pandas as pd
import pytest

from pipelines.run_pipeline import parse_args, resolve_stages
from src.forecasting.demand_forecasting import compute_metrics
from src.ingestion.extract import (
    DataIngestionError,
    calculate_file_hash,
    load_config,
    safe_load_csv,
)
from src.optimization.decision_simulator import build_scenarios


def test_config_loads():
    cfg = load_config()
    assert cfg["project"]["name"] == "CommerceIQ"
    assert cfg["database"]["name"] == "commerceiq"


def test_synthetic_ingestion_validations(tmp_path):
    good = tmp_path / "sample.csv"
    good.write_text("zip,val\n01001,NA\n", encoding="utf-8")
    digest = calculate_file_hash(good)
    df = safe_load_csv("sample", good, expected_hash=digest)
    assert df.loc[0, "zip"] == "01001"
    assert df.loc[0, "val"] == "NA"

    with pytest.raises(DataIngestionError):
        safe_load_csv("sample", good, expected_hash="0" * 64)


def test_forecast_metrics_calculation():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 300.0])
    m = compute_metrics(y_true, y_pred)
    assert m["MAE"] == round(20.0 / 3.0, 2)
    assert m["WAPE_pct"] == round(20.0 / 600.0 * 100.0, 2)


def test_decision_simulator_synthetic_baseline():
    synth_base = {
        "delivered_orders": 1000.0,
        "delivered_merch_brl": 150000.0,
        "delivered_aov_brl": 150.0,
        "unique_delivered_customers": 950.0,
        "repeat_purchase_rate": 0.03,
        "late_deliveries": 60.0,
        "late_merch_brl": 9000.0,
        "late_neg_review_rate": 0.50,
        "ontime_neg_review_rate": 0.08,
        "known_unsuccessful_merch_brl": 5000.0,
        "qualified_leads": 200.0,
        "closed_deals": 20.0,
        "ne_n_freight_brl": 10000.0,
        "ne_n_merch_brl": 40000.0,
    }
    scen_df, prio_df = build_scenarios(synth_base)
    assert len(scen_df) == 15
    assert set(scen_df["tier"]) == {"Low", "Base", "High"}
    assert scen_df["is_illustrative_simulation"].all()
    assert len(prio_df) == 5


def test_pipeline_cli_resolution():
    args = parse_args(["--stages", "all", "--skip-cleaning", "--train-models", "--dry-run"])
    stages = resolve_stages(args)
    assert "clean" not in stages
    assert "models" in stages
    assert stages[0] == "validate_sources"
    assert stages[-1] == "validate"
