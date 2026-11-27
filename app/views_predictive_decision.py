"""
CommerceIQ Analytics Studio — Pages 9 & 10 (Predictive Analytics & Decision Simulator)
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
import streamlit as st

from app.data_access import load_delivery_risk_model, load_predictive_and_decision_data
from app.theme import BLUE, COLOR_PALETTE, GREEN, NAVY, RED, TEAL, format_brl, kpi_card, render_banner, style_plotly
from src.optimization.decision_simulator import build_scenarios, compute_observed_baselines

STATE_APPROX_COORDS = {
    "SP": (-23.55, -46.63), "RJ": (-22.91, -43.17), "MG": (-19.92, -43.94), "ES": (-20.32, -40.34),
    "PR": (-25.43, -49.27), "SC": (-27.59, -48.55), "RS": (-30.03, -51.23),
    "BA": (-12.97, -38.50), "PE": (-8.05, -34.88), "CE": (-3.73, -38.52),
    "DF": (-15.79, -47.88), "GO": (-16.69, -49.26), "AM": (-3.12, -60.02), "PA": (-1.46, -48.50),
}
REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast", "ES": "Southeast",
    "PR": "South", "SC": "South", "RS": "South",
    "BA": "Northeast", "PE": "Northeast", "CE": "Northeast",
    "DF": "Central-West", "GO": "Central-West", "AM": "North", "PA": "North",
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, l1, p2, l2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def render_predictive_analytics() -> None:
    render_banner(
        "Predictive Analytics Studio",
        "Historical weekly demand backtests and zero-leakage purchase-time delivery delay risk scoring.",
    )
    data = load_predictive_and_decision_data()
    fc = data["forecast"]
    risk = data["risk"]

    tab_fc, tab_risk, tab_form = st.tabs([
        "Demand Forecasting (Model A)",
        "Delay Risk Evaluation (Model B)",
        "Interactive Checkout Risk Scorer",
    ])

    with tab_fc:
        target = st.radio("Select Forecast Target", ["merch_brl", "delivered_orders"], horizontal=True, format_func=lambda x: "Weekly Merchandise Value (BRL)" if x == "merch_brl" else "Weekly Delivered Orders")
        sub_fc = fc[fc["target"] == target].copy()
        bt = sub_fc[sub_fc["record_type"] == "holdout_backtest"]
        fu = sub_fc[sub_fc["record_type"] == "illustrative_historical_projection"]

        wape = float(np.sum(np.abs(bt["actual_value"] - bt["predicted_value"])) / np.sum(np.abs(bt["actual_value"])) * 100.0)
        mae = float(np.mean(np.abs(bt["actual_value"] - bt["predicted_value"])))

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("Selected Model", str(bt["model"].iloc[0]), "Best on 12-wk unseen holdout")
        with c2:
            kpi_card("Holdout WAPE", f"{wape:.2f}%", "Jun–Aug 2018 backtest", "teal")
        with c3:
            kpi_card("Holdout MAE", format_brl(mae) if target == "merch_brl" else f"{mae:,.1f} orders", "Mean absolute weekly error")

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=bt["week_start"], y=bt["actual_value"], name="Actual (Holdout)", mode="lines+markers", line={"color": NAVY, "width": 2.5}))
        fig_fc.add_trace(go.Scatter(x=bt["week_start"], y=bt["predicted_value"], name="Holdout Forecast", mode="lines+markers", line={"color": BLUE, "dash": "dash"}))
        fig_fc.add_trace(go.Scatter(x=fu["week_start"], y=fu["predicted_value"], name="Illustrative 8w Continuation", mode="lines+markers", line={"color": TEAL, "dash": "dot"}))
        fig_fc.add_trace(go.Scatter(
            x=list(fu["week_start"]) + list(fu["week_start"])[::-1],
            y=list(fu["ci_upper_95"]) + list(fu["ci_lower_95"])[::-1],
            fill="toself",
            fillcolor="rgba(13, 148, 136, 0.15)",
            line={"color": "rgba(255,255,255,0)"},
            name="Illustrative 95% Band",
        ))
        style_plotly(fig_fc, "Historical Backtest & Illustrative Post-August 2018 Continuation", height=420)
        st.plotly_chart(fig_fc, use_container_width=True)
        st.markdown(
            '<div class="ciq-disclaimer"><strong>Historical Forecast Framing:</strong> Source records end in August 2018. Continuation projections are illustrative historical benchmarks, not live marketplace forecasts.</div>',
            unsafe_allow_html=True,
        )

    with tab_risk:
        y_true = risk["is_late"].to_numpy()
        y_prob = risk["predicted_late_prob"].to_numpy()
        y_pred = risk["predicted_high_risk_flag"].to_numpy()

        roc_auc = roc_auc_score(y_true, y_prob)
        pr_auc = average_precision_score(y_true, y_prob)
        cm = confusion_matrix(y_true, y_pred)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("Test Orders (>=2018-06)", f"{len(risk):,}", f"Late Base Rate: {y_true.mean()*100:.2f}%")
        with c2:
            kpi_card("Test ROC-AUC", f"{roc_auc:.4f}", "HistGradientBoosting", "good")
        with c3:
            kpi_card("Test PR-AUC", f"{pr_auc:.4f}", ">2.1x no-skill baseline", "teal")
        with c4:
            kpi_card("Flagged High-Risk", f"{int(y_pred.sum()):,}", f"True Positives caught: {int(cm[1,1]):,}")

        fpr, tpr, _ = roc_curve(y_true, y_prob)
        prec, rec, _ = precision_recall_curve(y_true, y_prob)

        col_l, col_r = st.columns(2)
        with col_l:
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, name=f"HGB (AUC={roc_auc:.3f})", line={"color": BLUE, "width": 2.5}))
            fig_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Random Baseline", line={"color": "gray", "dash": "dash"}))
            style_plotly(fig_roc, "Unseen Test ROC Curve", height=380)
            fig_roc.update_xaxes(title_text="False Positive Rate")
            fig_roc.update_yaxes(title_text="True Positive Rate")
            st.plotly_chart(fig_roc, use_container_width=True)

        with col_r:
            fig_pr = go.Figure()
            fig_pr.add_trace(go.Scatter(x=rec, y=prec, name=f"HGB (PR-AUC={pr_auc:.3f})", line={"color": TEAL, "width": 2.5}))
            fig_pr.add_hline(y=float(y_true.mean()), line_dash="dash", line_color="gray", annotation_text="Baseline")
            style_plotly(fig_pr, "Unseen Test Precision-Recall Curve", height=380)
            fig_pr.update_xaxes(title_text="Recall")
            fig_pr.update_yaxes(title_text="Precision")
            st.plotly_chart(fig_pr, use_container_width=True)

        col_cm, col_tier = st.columns(2)
        with col_cm:
            fig_cm = px.imshow(
                cm,
                x=["Pred On-Time", "Pred High-Risk"],
                y=["Actual On-Time", "Actual Late"],
                text_auto=True,
                color_continuous_scale="Blues",
            )
            style_plotly(fig_cm, "Test Confusion Matrix (Threshold = 0.4709)", height=340)
            st.plotly_chart(fig_cm, use_container_width=True)
        with col_tier:
            tier_df = risk.groupby("risk_tier", as_index=False).agg(orders=("order_id", "count"), observed_late_pct=("is_late", lambda s: round(s.mean() * 100, 2)))
            fig_t = px.bar(tier_df, x="risk_tier", y="observed_late_pct", text="orders", color="observed_late_pct", color_continuous_scale="RdYlGn_r")
            style_plotly(fig_t, "Observed Late Rate (%) by Predicted Risk Tier", height=340)
            st.plotly_chart(fig_t, use_container_width=True)

    with tab_form:
        st.subheader("Live Purchase-Time Delivery Risk Predictor (Zero Leakage)")
        st.caption("Uses ONLY features observable at checkout and the persisted `models/delivery_risk_model.joblib` pipeline.")
        model = load_delivery_risk_model()
        if model is None:
            st.error("Trained model file `models/delivery_risk_model.joblib` was not found.")
            return

        with st.form("checkout_risk_form"):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                c_state = st.selectbox("Customer State", sorted(STATE_APPROX_COORDS.keys()), index=sorted(STATE_APPROX_COORDS.keys()).index("BA"))
                s_state = st.selectbox("Seller State", sorted(STATE_APPROX_COORDS.keys()), index=sorted(STATE_APPROX_COORDS.keys()).index("SP"))
                cat = st.selectbox("Product Category", ["health_beauty", "bed_bath_table", "watches_gifts", "sports_leisure", "computers_accessories", "furniture_decor", "housewares", "other"])
                pay_type = st.selectbox("Payment Type", ["credit_card", "boleto", "voucher", "debit_card"])
            with fc2:
                est_days = st.slider("Promised Delivery Lead Time (Days)", 3, 60, 18)
                item_price = st.number_input("Merchandise Price (BRL)", min_value=10.0, max_value=5000.0, value=140.0, step=10.0)
                freight_val = st.number_input("Freight Charge (BRL)", min_value=0.0, max_value=1000.0, value=28.0, step=2.0)
                weight_g = st.number_input("Package Weight (grams)", min_value=50, max_value=30000, value=950, step=100)
            with fc3:
                p_month = st.slider("Purchase Month", 1, 12, 11)
                p_hour = st.slider("Purchase Hour", 0, 23, 14)
                seller_hist_orders = st.number_input("Seller Prior Delivered Orders", min_value=0, max_value=2000, value=45, step=5)
                seller_hist_late = st.slider("Seller Historical Late Rate (%)", 0.0, 40.0, 7.5, step=0.5) / 100.0

            submitted = st.form_submit_button("Predict Checkout Delay Risk", type="primary")

        if submitted:
            c_lat, c_lon = STATE_APPROX_COORDS[c_state]
            s_lat, s_lon = STATE_APPROX_COORDS[s_state]
            dist_km = _haversine_km(s_lat, s_lon, c_lat, c_lon)
            input_row = pd.DataFrame([{
                "purchase_month": float(p_month),
                "purchase_day_of_week": 3.0,
                "purchase_hour": float(p_hour),
                "is_q4_peak": 1.0 if p_month in (11, 12) else 0.0,
                "item_count": 1.0,
                "distinct_products": 1.0,
                "distinct_sellers": 1.0,
                "total_price": float(item_price),
                "total_freight": float(freight_val),
                "freight_to_price_ratio": float(freight_val / max(item_price, 1.0)),
                "total_weight_g": float(weight_g),
                "max_volume_cm3": 6000.0,
                "estimated_delivery_days": float(est_days),
                "approx_distance_km": float(dist_km),
                "is_same_state": 1.0 if c_state == s_state else 0.0,
                "max_installments": 3.0,
                "seller_prior_delivered_orders": float(seller_hist_orders),
                "seller_prior_late_rate": float(seller_hist_late),
                "customer_region": REGION_MAP[c_state],
                "seller_region": REGION_MAP[s_state],
                "category_grouped": cat,
                "primary_payment_type": pay_type,
            }])
            prob = float(model.predict_proba(input_row)[0, 1])
            risk_label = "High Risk (>= 0.4709)" if prob >= 0.4709 else "Lower Risk (< 0.4709)"
            r1, r2, r3 = st.columns(3)
            with r1:
                kpi_card("Predicted Late Probability", f"{prob*100:.2f}%", risk_label, "warn" if prob >= 0.4709 else "good")
            with r2:
                kpi_card("Estimated Route Distance", f"{dist_km:,.0f} km", f"{s_state} -> {c_state}")
            with r3:
                kpi_card("Freight-to-Price Ratio", f"{freight_val / max(item_price, 1.0) * 100:.1f}%", f"Lead Time: {est_days} days")


def render_decision_simulator() -> None:
    render_banner(
        "Decision Intelligence Simulator",
        "Interactive what-if scenario modeling separating observed 2016–2018 baselines from illustrative sensitivity assumptions.",
    )
    st.markdown(
        '<div class="ciq-disclaimer"><strong>Important Simulation Disclaimer:</strong> Actual marketplace commissions, profit margins, CAC, and operating costs are unavailable in source data. The margin and intervention cost sliders below are <strong>illustrative sensitivity parameters</strong>, not guaranteed financial returns.</div>',
        unsafe_allow_html=True,
    )

    base = compute_observed_baselines()
    _, prio_default = build_scenarios(base)

    col_ctrl, col_viz = st.columns([1, 2])
    with col_ctrl:
        st.subheader("Adjustable Scenario Inputs")
        margin_pct = st.slider("Illustrative Contribution Margin (%)", 5.0, 30.0, 15.0, step=1.0) / 100.0
        ret_lift_pp = st.slider("SIM-01: Repeat Rate Lift (+pp)", 0.2, 3.0, 1.0, step=0.1) / 100.0
        late_red_pct = st.slider("SIM-02: Late Orders Shifted On-Time (%)", 5.0, 50.0, 20.0, step=5.0) / 100.0
        unsucc_rec_pct = st.slider("SIM-03: Known Canceled Value Recovered (%)", 5.0, 50.0, 25.0, step=5.0) / 100.0
        mkt_lift_pp = st.slider("SIM-04: MQL Conversion Lift (+pp)", 0.5, 6.0, 3.0, step=0.5) / 100.0
        frt_red_pct = st.slider("SIM-05: North/NE Freight Friction Reduction (%)", 1.0, 15.0, 6.0, step=1.0) / 100.0

    # Compute dynamic Low / Base / High around user's chosen central parameters
    inputs = [
        ("SIM-01: Retention & Repeat Lift", ret_lift_pp * base["unique_delivered_customers"] * base["delivered_aov_brl"], 120000.0),
        ("SIM-02: Late Delivery Reduction", (late_red_pct * base["late_deliveries"]) * 0.03 * base["delivered_aov_brl"], 95000.0),
        ("SIM-03: Unsuccessful Order Recovery", unsucc_rec_pct * base["known_unsuccessful_merch_brl"], 35000.0),
        ("SIM-04: Marketing Funnel Lift", (mkt_lift_pp * base["qualified_leads"]) * 0.45 * 4200.0, 65000.0),
        ("SIM-05: North/NE Freight Reduction", frt_red_pct * base["ne_n_freight_brl"], 150000.0),
    ]
    sim_rows = []
    for name, base_gmv, cost in inputs:
        for tier, mult in [("Low (0.6x)", 0.6), ("Selected Base (1.0x)", 1.0), ("High (1.5x)", 1.5)]:
            gmv = round(base_gmv * mult, 2)
            contrib = round(gmv * margin_pct, 2)
            sim_rows.append({
                "Initiative": name,
                "Scenario Tier": tier,
                "Simulated Impact (BRL, Illustrative)": gmv,
                "Illustrative Contribution (BRL)": contrib,
                "Illustrative Cost (BRL)": cost,
                "Illustrative Net Benefit (BRL)": round(contrib - cost, 2),
            })
    sim_df = pd.DataFrame(sim_rows)
    base_only = sim_df[sim_df["Scenario Tier"] == "Selected Base (1.0x)"]

    with col_viz:
        k1, k2, k3 = st.columns(3)
        with k1:
            kpi_card("Selected Gross Impact", format_brl(base_only["Simulated Impact (BRL, Illustrative)"].sum()), "Illustrative GMV + savings", "teal")
        with k2:
            kpi_card("Illustrative Contribution", format_brl(base_only["Illustrative Contribution (BRL)"].sum()), f"At {margin_pct*100:.0f}% margin assumption", "good")
        with k3:
            net_tot = base_only["Illustrative Net Benefit (BRL)"].sum()
            kpi_card("Illustrative Net Benefit", format_brl(net_tot), "Contribution minus assumed costs", "good" if net_tot >= 0 else "warn")

        fig_sim = px.bar(
            sim_df,
            x="Simulated Impact (BRL, Illustrative)",
            y="Initiative",
            color="Scenario Tier",
            barmode="group",
            orientation="h",
            color_discrete_sequence=["#93C5FD", BLUE, NAVY],
        )
        style_plotly(fig_sim, "Low / Selected Base / High Sensitivity Comparison (Illustrative BRL)", height=390)
        st.plotly_chart(fig_sim, use_container_width=True)

    st.subheader("Opportunity Prioritization Matrix (Observed Baseline Driven)")
    st.dataframe(prio_default, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Custom Scenario Sensitivity Table (CSV)",
        sim_df.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_custom_decision_scenarios.csv",
        mime="text/csv",
    )
