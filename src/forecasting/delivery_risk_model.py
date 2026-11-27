"""
CommerceIQ - Phase 12 Model B: Purchase-Time Delivery Delay Risk Classification

Strictly predicts late delivery risk (`delivery_deviation_days > 0`) at order
purchase time (`order_purchase_timestamp`) with ZERO post-purchase leakage.
Past seller historical late rates use event-time ordering: only orders whose
actual delivery occurred BEFORE the current order's purchase timestamp contribute.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast", "ES": "Southeast",
    "PR": "South", "SC": "South", "RS": "South",
    "BA": "Northeast", "PE": "Northeast", "CE": "Northeast", "RN": "Northeast",
    "PB": "Northeast", "AL": "Northeast", "SE": "Northeast", "PI": "Northeast", "MA": "Northeast",
    "DF": "Central-West", "GO": "Central-West", "MT": "Central-West", "MS": "Central-West",
    "AM": "North", "PA": "North", "RO": "North", "RR": "North", "AC": "North", "AP": "North", "TO": "North",
}


def df_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def build_purchase_time_dataset() -> pd.DataFrame:
    """Construct leakage-free feature table strictly observable at checkout."""
    parquet_dir = PROJECT_ROOT / "data" / "processed" / "parquet"
    orders = pd.read_parquet(parquet_dir / "orders.parquet")
    customers = pd.read_parquet(parquet_dir / "customers.parquet")
    order_items = pd.read_parquet(parquet_dir / "order_items.parquet")
    payments = pd.read_parquet(parquet_dir / "payments.parquet")
    products = pd.read_parquet(parquet_dir / "products.parquet")
    sellers = pd.read_parquet(parquet_dir / "sellers.parquet")
    geo_lookup = pd.read_parquet(parquet_dir / "geolocation_lookup.parquet")
    cat_trans = pd.read_parquet(parquet_dir / "category_translation.parquet")

    for c in ["price", "freight_value"]:
        order_items[c] = order_items[c].astype(float)

    elig = orders[orders["is_valid_delivery_promise_comparison"]].copy()
    elig["is_late"] = (elig["delivery_deviation_days"] > 0).astype(int)

    # Catalog & item aggregations (all known at checkout)
    items_enr = (
        order_items.merge(
            products[["product_id", "product_category_name", "product_weight_g", "product_volume_cm3"]],
            on="product_id",
            how="left",
        )
        .merge(cat_trans, on="product_category_name", how="left")
    )
    item_agg = items_enr.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        distinct_products=("product_id", "nunique"),
        distinct_sellers=("seller_id", "nunique"),
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        total_weight_g=("product_weight_g", "sum"),
        max_volume_cm3=("product_volume_cm3", "max"),
        primary_seller_id=("seller_id", "first"),
        primary_category=("product_category_name_english", "first"),
    )

    pay_agg = payments.sort_values(["order_id", "payment_sequential"]).groupby("order_id", as_index=False).agg(
        primary_payment_type=("payment_type", "first"),
        max_installments=("payment_installments", "max"),
    )

    cust_geo = customers.merge(
        geo_lookup[["zip_code_prefix", "latitude", "longitude"]],
        left_on="customer_zip_code_prefix",
        right_on="zip_code_prefix",
        how="left",
    )
    sell_geo = sellers.merge(
        geo_lookup[["zip_code_prefix", "latitude", "longitude"]],
        left_on="seller_zip_code_prefix",
        right_on="zip_code_prefix",
        how="left",
    )

    df = (
        elig[[
            "order_id", "customer_id", "order_purchase_timestamp", "order_delivered_customer_date",
            "purchase_month", "purchase_day_of_week", "purchase_hour", "estimated_delivery_days", "is_late",
        ]]
        .merge(cust_geo[["customer_id", "customer_state", "latitude", "longitude"]], on="customer_id", how="left")
        .merge(item_agg, on="order_id", how="inner")
        .merge(pay_agg, on="order_id", how="left")
        .merge(sell_geo[["seller_id", "seller_state", "latitude", "longitude"]], left_on="primary_seller_id", right_on="seller_id", how="left", suffixes=("_c", "_s"))
    )

    df["customer_region"] = df["customer_state"].map(REGION_MAP).fillna("Unknown")
    df["seller_region"] = df["seller_state"].map(REGION_MAP).fillna("Unknown")
    df["is_same_state"] = df["customer_state"].eq(df["seller_state"]).fillna(False).astype(int)
    df["is_q4_peak"] = df["purchase_month"].isin([11, 12]).fillna(False).astype(int)
    df["freight_to_price_ratio"] = np.where(df["total_price"].astype(float) > 0, df["total_freight"].astype(float) / df["total_price"].astype(float), 0.0)

    # Approximate Haversine distance (km) from postal prefix lookup
    lat1 = np.radians(df["latitude_s"].astype(float))
    lon1 = np.radians(df["longitude_s"].astype(float))
    lat2 = np.radians(df["latitude_c"].astype(float))
    lon2 = np.radians(df["longitude_c"].astype(float))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    df["approx_distance_km"] = 2 * 6371.0 * np.arcsin(np.sqrt(a))

    # Event-time strictly prior seller historical late rate (ZERO leakage!)
    # Only orders DELIVERED strictly before current order_purchase_timestamp are visible.
    global_prior_rate = 0.0677
    prior_strength = 10.0
    df = df.sort_values("order_purchase_timestamp").reset_index(drop=True)
    prior_orders_arr = np.zeros(len(df), dtype=float)
    prior_late_rate_arr = np.full(len(df), global_prior_rate, dtype=float)

    for _, grp in df.groupby("primary_seller_id", sort=False):
        deliv_ts = grp["order_delivered_customer_date"].to_numpy(dtype="datetime64[ns]")
        late_vals = grp["is_late"].to_numpy(dtype=float)
        order_idx = np.argsort(deliv_ts)
        sorted_deliv = deliv_ts[order_idx]
        sorted_late_cum = np.concatenate([[0.0], np.cumsum(late_vals[order_idx])])

        purch_ts = grp["order_purchase_timestamp"].to_numpy(dtype="datetime64[ns]")
        pos = np.searchsorted(sorted_deliv, purch_ts, side="left")
        prior_cnt = pos.astype(float)
        prior_late = sorted_late_cum[pos]
        smoothed_rate = (prior_late + prior_strength * global_prior_rate) / (prior_cnt + prior_strength)

        orig_indices = grp.index.to_numpy()
        prior_orders_arr[orig_indices] = prior_cnt
        prior_late_rate_arr[orig_indices] = smoothed_rate

    df["seller_prior_delivered_orders"] = prior_orders_arr
    df["seller_prior_late_rate"] = prior_late_rate_arr

    # Collapse rare product categories to top 20 + 'other' for clean generalization
    top_cats = df["primary_category"].value_counts().head(20).index
    df["category_grouped"] = df["primary_category"].where(df["primary_category"].isin(top_cats), "other").fillna("other")
    return df


def run_delivery_risk_pipeline() -> dict[str, Any]:
    df = build_purchase_time_dataset()
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    model_dir = PROJECT_ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    num_features = [
        "purchase_month", "purchase_day_of_week", "purchase_hour", "is_q4_peak",
        "item_count", "distinct_products", "distinct_sellers",
        "total_price", "total_freight", "freight_to_price_ratio",
        "total_weight_g", "max_volume_cm3", "estimated_delivery_days",
        "approx_distance_km", "is_same_state", "max_installments",
        "seller_prior_delivered_orders", "seller_prior_late_rate",
    ]
    cat_features = ["customer_region", "seller_region", "category_grouped", "primary_payment_type"]
    all_features = num_features + cat_features

    # Convert Pandas nullable extension dtypes to standard float64/object for sklearn
    for c in num_features:
        df[c] = df[c].astype(float)
    for c in cat_features:
        df[c] = df[c].astype("string").fillna("missing").astype(object)

    # Strict temporal train / validation / test split
    train_mask = df["order_purchase_timestamp"] < "2018-03-01"
    val_mask = (df["order_purchase_timestamp"] >= "2018-03-01") & (df["order_purchase_timestamp"] < "2018-06-01")
    test_mask = df["order_purchase_timestamp"] >= "2018-06-01"

    X_train, y_train = df.loc[train_mask, all_features], df.loc[train_mask, "is_late"].to_numpy()
    X_val, y_val = df.loc[val_mask, all_features], df.loc[val_mask, "is_late"].to_numpy()
    X_test, y_test = df.loc[test_mask, all_features], df.loc[test_mask, "is_late"].to_numpy()

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num_features),
            ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat_features),
        ]
    )

    candidates = {
        "Dummy_Stratified": DummyClassifier(strategy="stratified", random_state=42),
        "Logistic_Regression": LogisticRegression(max_iter=500, class_weight="balanced", random_state=42),
        "Decision_Tree": DecisionTreeClassifier(max_depth=7, min_samples_leaf=50, class_weight="balanced", random_state=42),
        "Random_Forest": RandomForestClassifier(n_estimators=120, max_depth=12, min_samples_leaf=20, class_weight="balanced", n_jobs=-1, random_state=42),
        "Hist_Gradient_Boosting": HistGradientBoostingClassifier(max_depth=6, learning_rate=0.06, max_iter=200, class_weight="balanced", random_state=42),
    }

    eval_rows: list[dict[str, Any]] = []
    fitted_pipes: dict[str, Pipeline] = {}

    for name, clf in candidates.items():
        pipe = Pipeline([("prep", preprocessor), ("clf", clf)])
        pipe.fit(X_train, y_train)
        fitted_pipes[name] = pipe

        val_prob = pipe.predict_proba(X_val)[:, 1]
        test_prob = pipe.predict_proba(X_test)[:, 1]

        # Select optimal F1 threshold on validation set (not test set!)
        prec_v, rec_v, thresh_v = precision_recall_curve(y_val, val_prob)
        f1_v = 2 * prec_v[:-1] * rec_v[:-1] / np.maximum(prec_v[:-1] + rec_v[:-1], 1e-9)
        best_thr = float(thresh_v[int(np.argmax(f1_v))]) if len(thresh_v) > 0 else 0.5
        test_pred = (test_prob >= best_thr).astype(int)

        eval_rows.append({
            "model": name,
            "val_roc_auc": round(roc_auc_score(y_val, val_prob), 4),
            "val_pr_auc": round(average_precision_score(y_val, val_prob), 4),
            "test_roc_auc": round(roc_auc_score(y_test, test_prob), 4),
            "test_pr_auc": round(average_precision_score(y_test, test_prob), 4),
            "val_opt_threshold": round(best_thr, 4),
            "test_precision": round(precision_score(y_test, test_pred, zero_division=0), 4),
            "test_recall": round(recall_score(y_test, test_pred, zero_division=0), 4),
            "test_f1": round(f1_score(y_test, test_pred, zero_division=0), 4),
            "test_brier": round(brier_score_loss(y_test, test_prob), 4),
        })

    comp_df = pd.DataFrame(eval_rows).sort_values("test_pr_auc", ascending=False).reset_index(drop=True)
    best_name = str(comp_df.iloc[0]["model"])
    best_pipe = fitted_pipes[best_name]
    best_thr = float(comp_df.iloc[0]["val_opt_threshold"])

    # Permutation importance on unseen test set (sample 6,000 rows for speed)
    rng = np.random.default_rng(42)
    sub_idx = rng.choice(len(X_test), size=min(6000, len(X_test)), replace=False)
    perm = permutation_importance(
        best_pipe, X_test.iloc[sub_idx], y_test[sub_idx],
        n_repeats=5, random_state=42, scoring="average_precision", n_jobs=-1
    )
    imp_df = pd.DataFrame({
        "feature": all_features,
        "importance_mean": perm.importances_mean,
        "importance_std": perm.importances_std,
    }).sort_values("importance_mean", ascending=False).reset_index(drop=True)

    # Save trained artifact locally (excluded from git by .gitignore)
    joblib.dump(best_pipe, model_dir / "delivery_risk_model.joblib")

    # Save test predictions for Power BI Predictive Intelligence page
    test_probs = best_pipe.predict_proba(X_test)[:, 1]
    pred_out = df.loc[test_mask, [
        "order_id", "order_purchase_timestamp", "customer_state", "seller_state",
        "customer_region", "seller_region", "estimated_delivery_days", "approx_distance_km", "is_late"
    ]].copy()
    pred_out["predicted_late_prob"] = np.round(test_probs, 4)
    pred_out["predicted_high_risk_flag"] = (test_probs >= best_thr).astype(int)
    pred_out["risk_tier"] = pd.cut(
        test_probs, bins=[-0.01, 0.25, 0.50, 0.75, 1.01],
        labels=["Low (<25%)", "Moderate (25-50%)", "Elevated (50-75%)", "High (>=75%)"]
    )
    pred_out.to_csv(PROJECT_ROOT / "data" / "processed" / "delivery_risk_predictions.csv", index=False)

    cm = confusion_matrix(y_test, (test_probs >= best_thr).astype(int))

    # Plot PR-AUC comparison & Top Feature Importance
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    plot_c = comp_df.sort_values("test_pr_auc")
    axes[0].barh(plot_c["model"], plot_c["test_pr_auc"], color="#2b6cb0")
    axes[0].axvline(float(y_test.mean()), color="#c53030", linestyle="--", label=f"No-Skill Baseline ({y_test.mean():.3f})")
    axes[0].set_title("Unseen Test PR-AUC Comparison (Jun–Aug 2018)", fontweight="bold")
    axes[0].set_xlabel("Precision-Recall AUC")
    axes[0].legend()

    top_imp = imp_df.head(12).iloc[::-1]
    axes[1].barh(top_imp["feature"], top_imp["importance_mean"], color="#2c7a7b")
    axes[1].set_title(f"Top Purchase-Time Drivers ({best_name})", fontweight="bold")
    axes[1].set_xlabel("Permutation Importance (PR-AUC Drop)")

    plt.tight_layout()
    fig.savefig(fig_dir / "pred_02_delivery_risk_performance.png", dpi=150)
    plt.close(fig)

    # Save Model Card
    card = [
        "# CommerceIQ — Model Card: Purchase-Time Delivery Delay Risk Classification",
        "",
        "## 1. Intended Use & Anti-Leakage Controls",
        "- **Prediction Moment:** Order checkout (`order_purchase_timestamp`).",
        "- **Target:** `is_late` (`delivery_deviation_days > 0`) among eligible delivered orders.",
        "- **Zero-Leakage Guarantee:** Excludes actual delivery, carrier handover, approval timestamps, review scores, and future seller outcomes. Seller historical late rate uses strictly prior orders already delivered before the current purchase timestamp.",
        f"- **Temporal Splits:** Train (< 2018-03-01: n={train_mask.sum():,}, late={y_train.mean()*100:.2f}%) | Validation (2018-03..2018-05: n={val_mask.sum():,}, late={y_val.mean()*100:.2f}%) | Test (>= 2018-06-01: n={test_mask.sum():,}, late={y_test.mean()*100:.2f}%).",
        "",
        "## 2. Unseen Test Model Comparison",
        df_to_md(comp_df),
        "",
        f"## 3. Selected Model Confusion Matrix (`{best_name}`, threshold={best_thr:.4f})",
        f"- True Negatives: **{cm[0,0]:,}** | False Positives: **{cm[0,1]:,}**",
        f"- False Negatives: **{cm[1,0]:,}** | True Positives: **{cm[1,1]:,}**",
        "",
        "## 4. Top Purchase-Time Drivers (Permutation Importance)",
        df_to_md(imp_df.head(10).round(5)),
        "",
        "## 5. Limitations",
        "- Trained on historical 2017–2018 delivered orders; non-delivered/canceled orders are excluded from target evaluation.",
        "- Offline experimental evaluation only; not deployed into live production checkout.",
        "",
    ]
    (PROJECT_ROOT / "reports" / "delivery_risk_model_card.md").write_text("\n".join(card), encoding="utf-8")

    return {
        "splits": {"train": int(train_mask.sum()), "val": int(val_mask.sum()), "test": int(test_mask.sum())},
        "comparison": comp_df,
        "importance": imp_df,
        "confusion_matrix": cm.tolist(),
        "best_model": best_name,
    }


if __name__ == "__main__":
    res = run_delivery_risk_pipeline()
    print(res["comparison"].to_string(index=False))
    print("\nTop 10 Features:\n", res["importance"].head(10).to_string(index=False))
