"""
CommerceIQ Analytics Studio — Pages 1 to 4 (Executive, Sales/Product, Customer, Seller)
"""

from __future__ import annotations

import datetime as dt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app.data_access import (
    query_customer_intelligence,
    query_executive_summary,
    query_sales_and_products,
    query_sellers,
)
from app.theme import BLUE, COLOR_PALETTE, GREEN, NAVY, RED, TEAL, format_brl, kpi_card, render_banner, style_plotly


def render_executive_overview(start_dt: dt.date, end_dt: dt.date, states: tuple[str, ...], categories: tuple[str, ...]) -> None:
    render_banner(
        "Executive Overview",
        "Commercial scale, order fulfillment outcomes, delivery reliability, and customer satisfaction across the filtered slice.",
    )
    with st.spinner("Loading executive warehouse metrics..."):
        data = query_executive_summary(start_dt, end_dt, states, categories)

    kpi = data["kpi"]
    total_orders = int(kpi["total_orders"] or 0)
    if total_orders == 0:
        st.warning("No orders match the current sidebar filter selection. Widen your date range, state, or category filter.")
        return

    deliv_orders = int(kpi["delivered_orders"] or 0)
    deliv_merch = float(kpi["delivered_merch_brl"] or 0.0)
    recorded_gmv = float(kpi["recorded_gmv_brl"] or 0.0)
    aov = deliv_merch / deliv_orders if deliv_orders else 0.0
    uniq_cust = int(kpi["unique_delivered_customers"] or 0)
    ontime_pct = (int(kpi["ontime_orders"] or 0) / int(kpi["elig_sla_orders"] or 1)) * 100.0 if int(kpi["elig_sla_orders"] or 0) > 0 else 0.0
    mean_rev = float(kpi["mean_review_score"] or 0.0)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        kpi_card("Delivered Merch", format_brl(deliv_merch), f"Total GMV: {format_brl(recorded_gmv)}", "good")
    with c2:
        kpi_card("Placed Orders", f"{total_orders:,}", f"Delivered: {deliv_orders:,}")
    with c3:
        kpi_card("Average Order Value", format_brl(aov), "Delivered orders w/ items", "teal")
    with c4:
        kpi_card("Unique Customers", f"{uniq_cust:,}", "Persistent customer_unique_id")
    with c5:
        kpi_card("On-Time Rate", f"{ontime_pct:.2f}%", "SLA eligible deliveries", "good" if ontime_pct >= 90 else "warn")
    with c6:
        kpi_card("Mean Review Score", f"{mean_rev:.2f} / 5", "Validated order average", "good" if mean_rev >= 4.0 else "warn")

    monthly = data["monthly"].copy()
    monthly["ontime_rate_pct"] = np.where(monthly["elig_sla_orders"] > 0, monthly["ontime_orders"] / monthly["elig_sla_orders"] * 100.0, np.nan)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=monthly["purchase_ym"], y=monthly["delivered_merch_brl"], name="Delivered Merch (BRL)", marker_color=BLUE),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=monthly["purchase_ym"], y=monthly["delivered_orders"], name="Delivered Orders", mode="lines+markers", line={"color": TEAL, "width": 2.5}),
            secondary_y=True,
        )
        style_plotly(fig, "Monthly Delivered Merchandise Value (BRL) & Order Volume", height=410)
        fig.update_yaxes(title_text="Merchandise (BRL)", secondary_y=False)
        fig.update_yaxes(title_text="Orders", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        status_df = data["status"]
        fig_st = px.pie(status_df, names="order_status", values="orders", hole=0.52, color_discrete_sequence=COLOR_PALETTE)
        fig_st.update_traces(textposition="inside", textinfo="percent")
        style_plotly(fig_st, "Order Lifecycle Status Mix", height=410)
        fig_st.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
        st.plotly_chart(fig_st, use_container_width=True)

    st.markdown(
        '<div class="ciq-note"><strong>Business Governance Note:</strong> Merchandise values reflect recorded BRL item prices, not marketplace commission or profit. Partial boundary months (2016-09–2016-12 and 2018-09–2018-10) are retained; the core reporting period is Jan 2017–Aug 2018.</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download Monthly Executive Summary (CSV)",
        monthly.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_executive_monthly.csv",
        mime="text/csv",
    )


def render_sales_and_products(start_dt: dt.date, end_dt: dt.date, states: tuple[str, ...], categories: tuple[str, ...]) -> None:
    render_banner(
        "Sales and Product Analytics",
        "Category revenue rankings, Pareto product concentration, monthly growth, and payment mix.",
    )
    with st.spinner("Loading category and product performance..."):
        data = query_sales_and_products(start_dt, end_dt, states, categories)
        exec_data = query_executive_summary(start_dt, end_dt, states, categories)

    cat_df = data["categories"]
    if cat_df.empty:
        st.warning("No delivered product items match the current filters.")
        return

    cat_df["sales_share_pct"] = cat_df["delivered_merch_brl"] / cat_df["delivered_merch_brl"].sum() * 100.0
    cat_df["cum_share_pct"] = cat_df["sales_share_pct"].cumsum()

    top1_cat = cat_df.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Active Categories", f"{len(cat_df):,}", "With delivered items")
    with c2:
        kpi_card("Top Category", str(top1_cat["category_en"]), format_brl(top1_cat["delivered_merch_brl"]), "good")
    with c3:
        kpi_card("Delivered Items", f"{int(cat_df['delivered_items'].sum()):,}", "Order item rows")
    with c4:
        avg_item = cat_df["delivered_merch_brl"].sum() / cat_df["delivered_items"].sum()
        kpi_card("Avg Item Price", format_brl(avg_item), "Across filtered categories", "teal")

    col_l, col_r = st.columns(2)
    with col_l:
        top15 = cat_df.head(15).iloc[::-1]
        fig_c = px.bar(
            top15, x="delivered_merch_brl", y="category_en", orientation="h",
            color="avg_review_score", color_continuous_scale="Teal",
            labels={"delivered_merch_brl": "Delivered Merch (BRL)", "category_en": "Category", "avg_review_score": "Avg Rating"},
        )
        style_plotly(fig_c, "Top 15 Categories by Delivered Merchandise Value (BRL)", height=450)
        st.plotly_chart(fig_c, use_container_width=True)

    with col_r:
        monthly = exec_data["monthly"].copy()
        monthly["mom_growth_pct"] = monthly["delivered_merch_brl"].pct_change() * 100.0
        fig_g = px.bar(
            monthly.dropna(subset=["mom_growth_pct"]),
            x="purchase_ym",
            y="mom_growth_pct",
            color=np.where(monthly.dropna(subset=["mom_growth_pct"])["mom_growth_pct"] >= 0, "Positive", "Negative"),
            color_discrete_map={"Positive": GREEN, "Negative": RED},
            labels={"purchase_ym": "Month", "mom_growth_pct": "MoM Growth (%)"},
        )
        style_plotly(fig_g, "Month-over-Month Merchandise Growth (%)", height=450)
        st.plotly_chart(fig_g, use_container_width=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        fig_par = go.Figure()
        top25 = cat_df.head(25)
        fig_par.add_trace(go.Bar(x=top25["category_en"], y=top25["sales_share_pct"], name="Category Share %", marker_color=BLUE))
        fig_par.add_trace(go.Scatter(x=top25["category_en"], y=top25["cum_share_pct"], name="Cumulative %", line={"color": RED, "width": 2.5}))
        style_plotly(fig_par, "Category Sales Pareto Concentration (Top 25)", height=390)
        fig_par.update_xaxes(tickangle=-40)
        st.plotly_chart(fig_par, use_container_width=True)

    with col_b2:
        pay_df = data["payments"]
        fig_pay = px.pie(pay_df, names="payment_type", values="total_payment_brl", hole=0.5, color_discrete_sequence=COLOR_PALETTE)
        style_plotly(fig_pay, "Recorded Payment Value by Method (BRL)", height=390)
        st.plotly_chart(fig_pay, use_container_width=True)

    st.subheader("Top 25 Individual Products (Anonymized Product IDs)")
    st.dataframe(data["top_products"], use_container_width=True, hide_index=True)
    st.download_button(
        "Download Category Performance (CSV)",
        cat_df.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_category_performance.csv",
        mime="text/csv",
    )


def render_customer_intelligence() -> None:
    render_banner(
        "Customer Intelligence",
        "Persistent customer_unique_id RFM segmentation, K-Means clusters, and maturity-aware cohort retention.",
    )
    with st.spinner("Loading customer intelligence and cohort matrix..."):
        cust = query_customer_intelligence()
    rfm = cust["rfm"]
    coh_mat = cust["cohort_matrix"]

    uniq = len(rfm)
    rep_cnt = int(rfm["is_repeat"].sum())
    rep_rate = rep_cnt / uniq * 100.0
    mean_val = float(rfm["monetary_brl"].mean())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Unique Delivered Customers", f"{uniq:,}", "Reference Date: 2018-09-01")
    with c2:
        kpi_card("Repeat Customers (>=2 Orders)", f"{rep_cnt:,}", f"Repeat Rate: {rep_rate:.2f}%", "warn")
    with c3:
        kpi_card("Mean Observed Spend", format_brl(mean_val), f"Median: {format_brl(rfm['monetary_brl'].median())}", "teal")
    with c4:
        kpi_card("K-Means Clusters", "k = 3 (Sil = 0.3983)", "Log-scaled RFM features", "good")

    seg_df = (
        rfm.groupby("rfm_segment", as_index=False)
        .agg(
            customers=("customer_unique_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary_brl=("monetary_brl", "mean"),
            total_monetary_brl=("monetary_brl", "sum"),
        )
        .sort_values("total_monetary_brl", ascending=False)
    )
    seg_df["customer_share_pct"] = (seg_df["customers"] / uniq * 100.0).round(2)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_rfm = px.bar(
            seg_df.sort_values("total_monetary_brl"),
            x="total_monetary_brl",
            y="rfm_segment",
            orientation="h",
            color="avg_monetary_brl",
            color_continuous_scale="Blues",
            labels={"total_monetary_brl": "Observed Value (BRL)", "rfm_segment": "RFM Segment", "avg_monetary_brl": "Avg Spend"},
        )
        style_plotly(fig_rfm, "Observed Historical Value by RFM Segment (BRL)", height=420)
        st.plotly_chart(fig_rfm, use_container_width=True)

    with col_r:
        fig_coh = px.imshow(
            coh_mat,
            text_auto=".2f",
            color_continuous_scale="YlGnBu",
            aspect="auto",
            labels={"x": "Months After First Purchase", "y": "Acquisition Cohort", "color": "Retention %"},
        )
        style_plotly(fig_coh, "Monthly Cohort Repeat Retention Matrix (%)", height=420)
        st.plotly_chart(fig_coh, use_container_width=True)

    st.subheader("RFM Segment Summary & Retention Recommendations")
    st.dataframe(seg_df.round(2), use_container_width=True, hide_index=True)
    st.markdown(
        """
        <div class="ciq-note">
        <strong>Segment Recommendations:</strong>
        (1) <em>Recent Single & High-Spend Single (~39% of customers)</em>: Trigger 14–30 day post-delivery cross-category offers before the first-90-day churn window.
        (2) <em>Champions & Loyal Repeat (3.0%)</em>: Prioritize reliable carrier lanes and loyalty bundles; repeat customers spend nearly 2x single-order buyers.
        (3) <em>At-Risk High-Spend</em>: Target with win-back incentives paired with guaranteed delivery estimates.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download RFM Segment Summary (CSV)",
        seg_df.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_rfm_segment_summary.csv",
        mime="text/csv",
    )


def render_seller_intelligence(states: tuple[str, ...], top_sellers: list[str]) -> None:
    render_banner(
        "Seller Intelligence",
        "Seller revenue concentration, origin state distribution, late-delivery exposure, and seller scorecard.",
    )
    seller_sel = st.selectbox("Focus Specific Top Seller (Optional)", ["All Sellers"] + top_sellers)
    with st.spinner("Loading seller warehouse scorecard..."):
        df = query_sellers(states, seller_sel)

    if df.empty:
        st.warning("No sellers match the selected state/seller filter.")
        return

    df_sorted = df.sort_values("delivered_merchandise_brl", ascending=False).reset_index(drop=True)
    df_sorted["cum_sales_pct"] = df_sorted["delivered_merchandise_brl"].cumsum() / df_sorted["delivered_merchandise_brl"].sum() * 100.0
    df_sorted["seller_pct"] = (np.arange(len(df_sorted)) + 1) / len(df_sorted) * 100.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Active Delivered Sellers", f"{len(df_sorted):,}", "Filtered marketplace sellers")
    with c2:
        kpi_card("Delivered Seller Sales", format_brl(df_sorted["delivered_merchandise_brl"].sum()), "Item price attribution", "good")
    with c3:
        top10_share = float(df_sorted.loc[df_sorted["seller_pct"] <= 10.0, "cum_sales_pct"].max()) if len(df_sorted) >= 10 else 100.0
        kpi_card("Top 10% Seller Share", f"{top10_share:.2f}%", "Sales concentration", "teal")
    with c4:
        kpi_card("Mean Late Exposure", f"{df_sorted['late_exposure_pct'].mean():.2f}%", "Unweighted seller avg", "warn")

    col_l, col_r = st.columns(2)
    with col_l:
        top15_s = df_sorted.head(15).copy()
        top15_s["seller_short"] = top15_s["seller_id"].str[:8] + " (" + top15_s["seller_state"] + ")"
        fig_s = px.bar(
            top15_s.iloc[::-1],
            x="delivered_merchandise_brl",
            y="seller_short",
            orientation="h",
            color="late_exposure_pct",
            color_continuous_scale="RdYlGn_r",
            labels={"delivered_merchandise_brl": "Delivered Merch (BRL)", "seller_short": "Seller", "late_exposure_pct": "Late %"},
        )
        style_plotly(fig_s, "Top 15 Sellers by Delivered Merchandise Value", height=430)
        st.plotly_chart(fig_s, use_container_width=True)

    with col_r:
        fig_sc = px.scatter(
            df_sorted[df_sorted["delivered_orders"] >= 10],
            x="delivered_orders",
            y="late_exposure_pct",
            size="delivered_merchandise_brl",
            color="seller_region",
            hover_data=["seller_state", "avg_associated_review_score"],
            color_discrete_sequence=COLOR_PALETTE,
            labels={"delivered_orders": "Delivered Orders", "late_exposure_pct": "Late Exposure (%)"},
        )
        style_plotly(fig_sc, "Seller Order Volume vs. Late Delivery Exposure (>=10 Orders)", height=430)
        st.plotly_chart(fig_sc, use_container_width=True)

    st.subheader("Seller Scorecard (Top 100 Filtered)")
    st.dataframe(df_sorted.head(100).drop(columns=["cum_sales_pct", "seller_pct"]), use_container_width=True, hide_index=True)
    st.download_button(
        "Download Seller Scorecard (CSV)",
        df_sorted.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_seller_scorecard.csv",
        mime="text/csv",
    )
