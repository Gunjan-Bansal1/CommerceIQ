"""
CommerceIQ - Phase 12 Predictive Analytics Notebook Generator & Runner

Builds and executes:
  1. `notebooks/06_demand_forecasting.ipynb`
  2. `notebooks/07_delivery_risk_classification.ipynb`
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.notebook_executor import build_and_execute_notebook, code_cell, md_cell


def build_forecasting_nb() -> None:
    cells = [
        md_cell(
            """# CommerceIQ — Phase 12 (Model A): Historical Demand & Merchandise Forecasting

**Objective:** Evaluate weekly delivered merchandise value (`merch_brl`) and delivered order volume (`delivered_orders`) forecasting models against classical baselines using chronological train/test splits and expanding-window cross-validation.  
**Historical Framing:** Source records span `2016–2018` (`2017-01-02` to `2018-08-26` for 86 complete Monday-aligned weeks). Results represent **historical backtests and illustrative 8-week continuations**, not current marketplace predictions."""
        ),
        code_cell(
            """import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PROJECT_ROOT = Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.demand_forecasting import run_forecasting_pipeline

res = run_forecasting_pipeline()
print(f"Complete Core Weekly Observations: {res['weekly_rows']} weeks")"""
        ),
        md_cell("## 1. Holdout Evaluation (Final 12 Weeks: Jun–Aug 2018)"),
        code_cell(
            """print("Merchandise Value (BRL) Model Comparison:")
display(res["merch_comparison"])
print("\\nOrder Volume Model Comparison:")
display(res["orders_comparison"])"""
        ),
        md_cell("## 2. Expanding-Window Cross-Validation (4 Folds × 4 Weeks) & Forecast Visualization"),
        code_cell(
            """display(res["expanding_cv"])

img = mpimg.imread(PROJECT_ROOT / "reports" / "figures" / "pred_01_demand_forecast_backtest.png")
fig, ax = plt.subplots(figsize=(13, 8))
ax.imshow(img)
ax.axis("off")
plt.show()
print("Saved forecast outputs to data/processed/forecast_outputs.csv and model card to reports/forecasting_model_card.md")"""
        ),
    ]
    build_and_execute_notebook(cells, PROJECT_ROOT / "notebooks" / "06_demand_forecasting.ipynb", PROJECT_ROOT)


def build_delivery_risk_nb() -> None:
    cells = [
        md_cell(
            """# CommerceIQ — Phase 12 (Model B): Purchase-Time Delivery Delay Risk Classification

**Prediction Moment:** Order checkout (`order_purchase_timestamp`).  
**Leakage Prevention:** Strictly excludes actual delivery dates, carrier handover dates, actual durations, review scores, and future seller outcomes. Seller historical late rates are computed in event-time using only orders already delivered prior to the current purchase timestamp."""
        ),
        code_cell(
            """import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd

PROJECT_ROOT = Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.delivery_risk_model import run_delivery_risk_pipeline

res = run_delivery_risk_pipeline()
print("Temporal Splits:", res["splits"])
print("Selected Best Model (by Test PR-AUC):", res["best_model"])"""
        ),
        md_cell("## 1. Model Comparison on Unseen Temporal Test Split (>= 2018-06-01)"),
        code_cell(
            """display(res["comparison"])
print("Confusion Matrix [TN, FP; FN, TP]:", res["confusion_matrix"])"""
        ),
        md_cell("## 2. Purchase-Time Drivers (Permutation Importance) & Diagnostic Plot"),
        code_cell(
            """display(res["importance"].head(15).round(5))

img = mpimg.imread(PROJECT_ROOT / "reports" / "figures" / "pred_02_delivery_risk_performance.png")
fig, ax = plt.subplots(figsize=(13, 5))
ax.imshow(img)
ax.axis("off")
plt.show()
print("Saved model to models/delivery_risk_model.joblib, test predictions to data/processed/delivery_risk_predictions.csv, and model card to reports/delivery_risk_model_card.md")"""
        ),
    ]
    build_and_execute_notebook(cells, PROJECT_ROOT / "notebooks" / "07_delivery_risk_classification.ipynb", PROJECT_ROOT)


if __name__ == "__main__":
    build_forecasting_nb()
    print("Completed 06_demand_forecasting.ipynb")
    build_delivery_risk_nb()
    print("Completed 07_delivery_risk_classification.ipynb")
