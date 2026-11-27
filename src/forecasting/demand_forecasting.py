"""
CommerceIQ - Phase 12 Model A: Historical Demand & Merchandise Forecasting

Evaluates weekly delivered merchandise value and order-volume forecasting models
using chronological train/test splits and expanding-window validation against
naive, seasonal naive, moving-average, Holt-Winters, SARIMA, and lag-Ridge models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def df_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    denom = float(np.sum(np.abs(y_true)))
    wape = float(np.sum(np.abs(err)) / denom * 100.0) if denom > 0 else np.nan
    nonzero = y_true > 0
    mape = float(np.mean(np.abs(err[nonzero]) / y_true[nonzero]) * 100.0) if nonzero.any() else np.nan
    return {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "WAPE_pct": round(wape, 2), "MAPE_pct": round(mape, 2)}


def prepare_weekly_series() -> pd.DataFrame:
    parquet_dir = PROJECT_ROOT / "data" / "processed" / "parquet"
    orders = pd.read_parquet(parquet_dir / "orders.parquet")
    orders["purchase_date"] = pd.to_datetime(orders["purchase_date"])
    order_items = pd.read_parquet(parquet_dir / "order_items.parquet")
    order_items["price"] = order_items["price"].astype(float)
    agg = order_items.groupby("order_id", as_index=False)["price"].sum().rename(columns={"price": "merch_brl"})
    deliv = orders[orders["order_status"].eq("delivered") & orders["has_order_items"]].merge(agg, on="order_id", how="inner")

    # Core complete Monday-Sunday weeks: 2017-01-02 through 2018-08-26 (86 full weeks)
    mask = (deliv["purchase_date"] >= "2017-01-02") & (deliv["purchase_date"] <= "2018-08-26")
    core = deliv.loc[mask].copy()
    core["week_start"] = core["purchase_date"] - pd.to_timedelta(core["purchase_date"].dt.weekday, unit="D")
    weekly = (
        core.groupby("week_start", as_index=False)
        .agg(delivered_orders=("order_id", "count"), merch_brl=("merch_brl", "sum"))
        .sort_values("week_start")
        .reset_index(drop=True)
    )
    return weekly


def _predict_models(train_y: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    preds: dict[str, np.ndarray] = {}
    preds["Naive"] = np.repeat(train_y[-1], horizon)
    preds["Seasonal_Naive_4w"] = np.array([train_y[-4 + (i % 4)] for i in range(horizon)])
    preds["Moving_Avg_4w"] = np.repeat(np.mean(train_y[-4:]), horizon)

    try:
        hw = ExponentialSmoothing(train_y, trend="add", seasonal=None, initialization_method="estimated").fit(optimized=True)
        preds["Holt_Winters_Trend"] = np.maximum(0.0, hw.forecast(horizon))
    except Exception:
        preds["Holt_Winters_Trend"] = preds["Moving_Avg_4w"].copy()

    try:
        sarima = SARIMAX(train_y, order=(1, 1, 1), seasonal_order=(0, 0, 0, 0), enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        preds["ARIMA_111"] = np.maximum(0.0, sarima.forecast(horizon))
    except Exception:
        preds["ARIMA_111"] = preds["Moving_Avg_4w"].copy()

    # Leakage-free recursive lag Ridge model (lags 1, 2, 4, rolling_mean_4)
    if len(train_y) >= 12:
        X_rows, y_rows = [], []
        for idx in range(4, len(train_y)):
            X_rows.append([train_y[idx - 1], train_y[idx - 2], train_y[idx - 4], np.mean(train_y[idx - 4 : idx])])
            y_rows.append(train_y[idx])
        pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        pipe.fit(np.array(X_rows), np.array(y_rows))
        hist = list(train_y)
        ridge_fc = []
        for _ in range(horizon):
            feats = np.array([[hist[-1], hist[-2], hist[-4], np.mean(hist[-4:])]])
            yhat = max(0.0, float(pipe.predict(feats)[0]))
            ridge_fc.append(yhat)
            hist.append(yhat)
        preds["Lag_Ridge"] = np.array(ridge_fc)
    else:
        preds["Lag_Ridge"] = preds["Moving_Avg_4w"].copy()
    return preds


def run_forecasting_pipeline() -> dict[str, Any]:
    weekly = prepare_weekly_series()
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    horizon = 12  # Last 12 weeks holdout (~3 months: Jun-Aug 2018)
    train_df = weekly.iloc[:-horizon].copy()
    test_df = weekly.iloc[-horizon:].copy()

    results_by_target: dict[str, pd.DataFrame] = {}
    expanding_rows: list[dict[str, Any]] = []
    export_frames: list[pd.DataFrame] = []

    for target_col, label in [("merch_brl", "Weekly Delivered Merchandise (BRL)"), ("delivered_orders", "Weekly Delivered Orders")]:
        y_train = train_df[target_col].to_numpy(dtype=float)
        y_test = test_df[target_col].to_numpy(dtype=float)
        fc_dict = _predict_models(y_train, horizon)

        comp_rows = []
        for model_name, y_hat in fc_dict.items():
            m = compute_metrics(y_test, y_hat)
            comp_rows.append({"target": target_col, "model": model_name, **m})
        comp_df = pd.DataFrame(comp_rows).sort_values("WAPE_pct").reset_index(drop=True)
        results_by_target[target_col] = comp_df

        # Expanding-window CV (4 folds x 4-week horizon)
        cv_cutoffs = [len(weekly) - 24, len(weekly) - 20, len(weekly) - 16, len(weekly) - 12]
        for fold_idx, cut in enumerate(cv_cutoffs, start=1):
            tr_y = weekly[target_col].iloc[:cut].to_numpy(dtype=float)
            va_y = weekly[target_col].iloc[cut : cut + 4].to_numpy(dtype=float)
            fc_cv = _predict_models(tr_y, 4)
            for mname, yhat_cv in fc_cv.items():
                met = compute_metrics(va_y, yhat_cv)
                expanding_rows.append({"target": target_col, "fold": fold_idx, "model": mname, **met})

        best_model = comp_df.iloc[0]["model"]
        best_pred = fc_dict[best_model]
        resid_std = float(np.std(y_test - best_pred, ddof=1))

        # Backtest export frame
        bt = test_df[["week_start", target_col]].copy().rename(columns={target_col: "actual_value"})
        bt["target"] = target_col
        bt["record_type"] = "holdout_backtest"
        bt["model"] = best_model
        bt["predicted_value"] = np.round(best_pred, 2)
        bt["ci_lower_95"] = np.round(np.maximum(0.0, best_pred - 1.96 * resid_std), 2)
        bt["ci_upper_95"] = np.round(best_pred + 1.96 * resid_std, 2)
        export_frames.append(bt)

        # 8-week illustrative continuation beyond 2018-08-26 (clearly labeled!)
        full_y = weekly[target_col].to_numpy(dtype=float)
        fut_pred = _predict_models(full_y, 8)[best_model]
        last_wk = weekly["week_start"].iloc[-1]
        fut_weeks = [last_wk + pd.Timedelta(weeks=i) for i in range(1, 9)]
        steps = np.sqrt(np.arange(1, 9))
        fut_df = pd.DataFrame({
            "week_start": fut_weeks,
            "actual_value": np.nan,
            "target": target_col,
            "record_type": "illustrative_historical_projection",
            "model": best_model,
            "predicted_value": np.round(fut_pred, 2),
            "ci_lower_95": np.round(np.maximum(0.0, fut_pred - 1.96 * resid_std * steps), 2),
            "ci_upper_95": np.round(fut_pred + 1.96 * resid_std * steps, 2),
        })
        export_frames.append(fut_df)

    expanding_df = pd.DataFrame(expanding_rows)
    expanding_summary = (
        expanding_df.groupby(["target", "model"], as_index=False)[["MAE", "RMSE", "WAPE_pct", "MAPE_pct"]]
        .mean()
        .round(2)
        .sort_values(["target", "WAPE_pct"])
    )

    forecast_out_df = pd.concat(export_frames, ignore_index=True)
    forecast_out_df.to_csv(PROJECT_ROOT / "data" / "processed" / "forecast_outputs.csv", index=False)

    # Visualization
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for ax, target_col, ylabel, scale in [
        (axes[0], "merch_brl", "Delivered Merch (k BRL)", 1e3),
        (axes[1], "delivered_orders", "Delivered Orders", 1.0),
    ]:
        sub_bt = forecast_out_df[(forecast_out_df["target"] == target_col) & (forecast_out_df["record_type"] == "holdout_backtest")]
        sub_fu = forecast_out_df[(forecast_out_df["target"] == target_col) & (forecast_out_df["record_type"] == "illustrative_historical_projection")]
        ax.plot(weekly["week_start"], weekly[target_col] / scale, color="#1a365d", linewidth=2, label="Observed Weekly Actual")
        ax.plot(sub_bt["week_start"], sub_bt["predicted_value"] / scale, color="#dd6b20", linestyle="--", linewidth=2, label=f"Holdout Forecast ({sub_bt['model'].iloc[0]})")
        ax.plot(sub_fu["week_start"], sub_fu["predicted_value"] / scale, color="#2f855a", linestyle=":", linewidth=2, label="Illustrative 8w Continuation (Post-Aug 2018)")
        ax.fill_between(sub_fu["week_start"], sub_fu["ci_lower_95"] / scale, sub_fu["ci_upper_95"] / scale, color="#2f855a", alpha=0.15, label="Illustrative 95% Uncertainty Band")
        ax.axvline(test_df["week_start"].iloc[0], color="gray", linestyle="-.", alpha=0.7)
        ax.set_ylabel(ylabel)
        ax.set_title(f"Historical Backtest & Illustrative Continuation: {ylabel}", fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    fig.savefig(fig_dir / "pred_01_demand_forecast_backtest.png", dpi=150)
    plt.close(fig)

    # Save Model Card
    best_merch = results_by_target["merch_brl"].iloc[0]
    best_ord = results_by_target["delivered_orders"].iloc[0]
    card_lines = [
        "# CommerceIQ — Model Card: Historical Demand & Merchandise Forecasting",
        "",
        "## 1. Model Overview & Intended Use",
        "- **Scope:** Weekly delivered merchandise value (`merch_brl`) and delivered order volume (`delivered_orders`) across 86 complete weeks (`2017-01-02` to `2018-08-26`).",
        "- **Important Limitation:** Source data ends in August 2018. Forecasts are **historical backtests and illustrative 2018 continuations**, not predictions of current market conditions.",
        "",
        "## 2. Holdout Test Performance (Final 12 Weeks)",
        "",
        "### Merchandise Value (BRL)",
        df_to_md(results_by_target["merch_brl"]),
        "",
        "### Order Volume",
        df_to_md(results_by_target["delivered_orders"]),
        "",
        "## 3. Expanding-Window Cross-Validation (4 Folds x 4 Weeks)",
        df_to_md(expanding_summary),
        "",
        f"**Selected Merchandise Model:** `{best_merch['model']}` (Holdout WAPE **{best_merch['WAPE_pct']:.2f}%**, MAE **BRL {best_merch['MAE']:,.2f}**).",
        f"**Selected Order Volume Model:** `{best_ord['model']}` (Holdout WAPE **{best_ord['WAPE_pct']:.2f}%**, MAE **{best_ord['MAE']:,.1f}** orders).",
        "",
    ]
    (PROJECT_ROOT / "reports" / "forecasting_model_card.md").write_text("\n".join(card_lines), encoding="utf-8")

    return {
        "weekly_rows": len(weekly),
        "merch_comparison": results_by_target["merch_brl"],
        "orders_comparison": results_by_target["delivered_orders"],
        "expanding_cv": expanding_summary,
        "forecast_outputs": forecast_out_df,
    }


if __name__ == "__main__":
    res = run_forecasting_pipeline()
    print(res["merch_comparison"].to_string(index=False))
    print(res["orders_comparison"].to_string(index=False))
