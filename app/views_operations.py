"""
CommerceIQ Analytics Studio — Pages 5 to 8 (Logistics, Satisfaction, Marketing, Geography)
"""

from __future__ import annotations

import datetime as dt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.data_access import (
    query_logistics_and_geo,
    query_marketing_funnel,
    query_satisfaction,
)
from app.theme import BLUE, COLOR_PALETTE, GREEN, NAVY, RED, TEAL, format_brl, kpi_card, render_banner, style_plotly


def render_logistics_analytics(start_dt: dt.date, end_dt: dt.date, states: tuple[str, ...]) -> None:
    render_banner(
        "Logistics & Delivery Analytics",
        "SLA compliance, order lifecycle stage bottlenecks, freight burden, and state-to-state shipping lanes.",
    )
    with st.spinner("Loading logistics and SLA metrics..."):
        data = query_logistics_and_geo(start_dt, end_dt, states)

    st_df = data["states"]
    sla_df = data["sla"]
    lanes = data["lanes"]
    if st_df.empty or int(st_df["delivered_orders"].sum()) == 0:
        st.warning("No delivered orders match the selected filters.")
        return

    tot_deliv = int(st_df["delivered_orders"].sum())
    w_ontime = float((st_df["on_time_rate_pct"].fillna(0) * st_df["delivered_orders"]).sum() / tot_deliv)
    w_days = float((st_df["mean_delivery_days"].fillna(0) * st_df["delivered_orders"]).sum() / tot_deliv)
    w_transit = float((st_df["mean_transit_days"].fillna(0) * st_df["delivered_orders"]).sum() / tot_deliv)
    freight_ratio = float(st_df["delivered_freight_brl"].sum() / max(st_df["delivered_merch_brl"].sum(), 1.0) * 100.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("On-Time Rate", f"{w_ontime:.2f}%", "Promised vs. actual calendar date", "good" if w_ontime >= 90 else "warn")
    with c2:
        kpi_card("Mean Delivery Time", f"{w_days:.2f} days", f"Transit share: {w_transit:.2f} days", "teal")
    with c3:
        kpi_card("Delivered Freight", format_brl(st_df["delivered_freight_brl"].sum()), f"Freight-to-Merch: {freight_ratio:.2f}%")
    with c4:
        late_cnt = int(sla_df.loc[sla_df["delivery_performance"] == "late", "orders"].sum())
        kpi_card("Late Deliveries", f"{late_cnt:,}", "Actual > Estimated date", "warn")

    col_l, col_r = st.columns(2)
    with col_l:
        stages = pd.DataFrame({
            "Stage": ["Approval", "Seller Processing", "Carrier Transit"],
            "Mean Days": [
                float((st_df["mean_approval_days"].fillna(0) * st_df["delivered_orders"]).sum() / tot_deliv),
                float((st_df["mean_processing_days"].fillna(0) * st_df["delivered_orders"]).sum() / tot_deliv),
                w_transit,
            ],
        })
        fig_st = px.bar(stages, x="Stage", y="Mean Days", color="Stage", color_discrete_sequence=[NAVY, "#DD6B20", BLUE])
        style_plotly(fig_st, "Fulfillment Lifecycle Stage Breakdown (Mean Days)", height=400)
        st.plotly_chart(fig_st, use_container_width=True)

    with col_r:
        sla_elig = sla_df[sla_df["delivery_performance"].isin(["early", "on_time", "late"])]
        fig_sla = px.pie(
            sla_elig, names="delivery_performance", values="orders", hole=0.52,
            color="delivery_performance",
            color_discrete_map={"early": GREEN, "on_time": BLUE, "late": RED},
        )
        style_plotly(fig_sla, "Delivery Promise Compliance Split", height=400)
        st.plotly_chart(fig_sla, use_container_width=True)

    fig_state = px.bar(
        st_df.head(15).sort_values("on_time_rate_pct"),
        x="on_time_rate_pct",
        y="customer_state",
        orientation="h",
        color="mean_delivery_days",
        color_continuous_scale="RdYlGn_r",
        labels={"on_time_rate_pct": "On-Time Rate (%)", "customer_state": "State", "mean_delivery_days": "Mean Days"},
    )
    style_plotly(fig_state, "On-Time SLA & Mean Delivery Duration Across Top 15 States", height=430)
    st.plotly_chart(fig_state, use_container_width=True)

    st.subheader("Top State-to-State Shipping Lanes")
    st.dataframe(lanes.head(30), use_container_width=True, hide_index=True)
    st.download_button(
        "Download State Logistics Summary (CSV)",
        st_df.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_logistics_by_state.csv",
        mime="text/csv",
    )


def render_customer_satisfaction(start_dt: dt.date, end_dt: dt.date, states: tuple[str, ...]) -> None:
    render_banner(
        "Customer Satisfaction & Statistical Evidence",
        "Rating distributions, SLA delivery impact on review stars, and Holm-Bonferroni hypothesis findings.",
    )
    with st.spinner("Loading review and satisfaction data..."):
        data = query_satisfaction(start_dt, end_dt, states)

    dist = data["dist"]
    sla_rev = data["sla_rev"]
    if dist.empty:
        st.warning("No review records match the selected filters.")
        return

    tot_rev = int(dist["reviews"].sum())
    mean_score = float((dist["review_score"] * dist["reviews"]).sum() / tot_rev)
    pos_pct = float(dist.loc[dist["rating_classification"] == "positive", "reviews"].sum() / tot_rev * 100.0)
    neg_pct = float(dist.loc[dist["rating_classification"] == "negative", "reviews"].sum() / tot_rev * 100.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Reviews", f"{tot_rev:,}", "Rule-based star classifications")
    with c2:
        kpi_card("Mean Review Score", f"{mean_score:.2f} / 5", "Validated 1–5 ratings", "good" if mean_score >= 4.0 else "warn")
    with c3:
        kpi_card("Positive Share (4-5 Stars)", f"{pos_pct:.2f}%", "Rating-based class", "good")
    with c4:
        kpi_card("Negative Share (1-2 Stars)", f"{neg_pct:.2f}%", "Rating-based class", "warn")

    col_l, col_r = st.columns(2)
    with col_l:
        fig_d = px.bar(
            dist.sort_values("review_score"),
            x="review_score",
            y="reviews",
            color="rating_classification",
            color_discrete_map={"positive": GREEN, "neutral": "#D97706", "negative": RED},
            labels={"review_score": "Star Rating", "reviews": "Review Count"},
        )
        style_plotly(fig_d, "Review Rating Distribution (1–5 Stars)", height=400)
        st.plotly_chart(fig_d, use_container_width=True)

    with col_r:
        sla_clean = sla_rev[sla_rev["delivery_performance"].isin(["early", "on_time", "late"])]
        fig_sr = px.bar(
            sla_clean,
            x="delivery_performance",
            y="mean_score",
            color="negative_pct",
            color_continuous_scale="RdYlGn_r",
            text="mean_score",
            labels={"delivery_performance": "Delivery SLA Outcome", "mean_score": "Mean Star Score", "negative_pct": "Negative %"},
        )
        style_plotly(fig_sr, "Mean Review Score by Delivery SLA Outcome", height=400)
        fig_sr.update_yaxes(range=[0, 5.2])
        st.plotly_chart(fig_sr, use_container_width=True)

    st.markdown(
        '<div class="ciq-note"><strong>Phase 10 Statistical Evidence:</strong> Late deliveries reduce mean review scores by <strong>2.02 stars</strong> overall (4.29 early/on-time vs. 2.27 late; Mann-Whitney <em>p</em> &lt; 1e-100, Cohen <em>d</em> = <strong>1.71</strong>, 95% CI [1.98, 2.06]). Among negative written Portuguese comments, <strong>29.5%</strong> cite non-delivery/waiting and <strong>15.0%</strong> cite delays.</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download Satisfaction Breakdown (CSV)",
        sla_rev.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_satisfaction_by_sla.csv",
        mime="text/csv",
    )


def render_marketing_intelligence() -> None:
    render_banner(
        "Marketing Seller Acquisition Intelligence",
        "Qualified lead volume, observed closed-deal conversion rates, channel performance, and seller linkage coverage.",
    )
    with st.spinner("Loading marketing funnel metrics..."):
        data = query_marketing_funnel()

    funnel = data["funnel"]
    monthly = data["monthly"]
    segments = data["segments"]

    mqls = int(funnel["qualified_leads"].sum())
    deals = int(funnel["closed_deals"].sum())
    matched = int(funnel["matched_marketplace_sellers"].sum())
    conv = deals / mqls * 100.0 if mqls else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Qualified Leads (MQL)", f"{mqls:,}", "Jun 2017 – May 2018 sample")
    with c2:
        kpi_card("Recorded Closed Deals", f"{deals:,}", f"Conversion: {conv:.2f}%", "good")
    with c3:
        kpi_card("Matched Marketplace Sellers", f"{matched:,}", f"{matched/deals*100:.1f}% linked in sellers table", "teal")
    with c4:
        kpi_card("Unmatched Closed Deals", f"{deals - matched:,}", "Documented cross-dataset gap")

    col_l, col_r = st.columns(2)
    with col_l:
        funnel_stages = pd.DataFrame({
            "Stage": ["1. Qualified Leads (MQL)", "2. Won Closed Deals", "3. Matched in Marketplace Sellers"],
            "Count": [mqls, deals, matched],
        })
        fig_fn = px.funnel(funnel_stages, x="Count", y="Stage", color_discrete_sequence=[NAVY])
        style_plotly(fig_fn, "Seller Acquisition Funnel Stages", height=400)
        st.plotly_chart(fig_fn, use_container_width=True)

    with col_r:
        fig_ch = px.bar(
            funnel.sort_values("conversion_rate_pct"),
            x="conversion_rate_pct",
            y="origin",
            orientation="h",
            color="qualified_leads",
            color_continuous_scale="Blues",
            labels={"conversion_rate_pct": "Conversion Rate (%)", "origin": "Origin Channel", "qualified_leads": "MQL Volume"},
        )
        style_plotly(fig_ch, "Conversion Rate (%) & Lead Volume by Origin Channel", height=400)
        st.plotly_chart(fig_ch, use_container_width=True)

    fig_m = px.line(monthly, x="contact_month", y=["leads", "deals"], markers=True, color_discrete_sequence=[BLUE, TEAL])
    style_plotly(fig_m, "Monthly Lead Acquisition & Closed Deal Trajectory", height=360)
    st.plotly_chart(fig_m, use_container_width=True)

    st.subheader("Top Converted Seller Business Segments")
    st.dataframe(segments, use_container_width=True, hide_index=True)
    st.markdown(
        '<div class="ciq-note"><strong>Analytical Limitation:</strong> Ad-spend/CAC data is unavailable. A closed-deal seller absent from `sellers` (462 deals) reflects incomplete cross-dataset linkage rather than verified seller inactivity.</div>',
        unsafe_allow_html=True,
    )


def render_geographic_analytics(start_dt: dt.date, end_dt: dt.date, states: tuple[str, ...]) -> None:
    render_banner(
        "Geographic Analytics (Brazil)",
        "State-level merchandise distribution, representative postal-prefix coordinates, freight ratios, and delivery SLA.",
    )
    with st.spinner("Loading geographic performance..."):
        data = query_logistics_and_geo(start_dt, end_dt, states)

    st_df = data["states"].merge(data["coords"], left_on="customer_state", right_on="state", how="left")
    if st_df.empty:
        st.warning("No geographic records match the selected filters.")
        return

    st_df["freight_ratio_pct"] = st_df["delivered_freight_brl"] / st_df["delivered_merch_brl"].clip(lower=1.0) * 100.0
    reg_df = st_df.groupby("customer_region", as_index=False).agg(
        orders=("total_orders", "sum"),
        merch_brl=("delivered_merch_brl", "sum"),
        freight_brl=("delivered_freight_brl", "sum"),
    ).sort_values("merch_brl", ascending=False)

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        map_df = st_df.dropna(subset=["lat", "lon"]).copy()
        fig_map = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            size="delivered_merch_brl",
            color="on_time_rate_pct",
            hover_name="customer_state",
            hover_data={"delivered_orders": True, "delivered_merch_brl": ":,.2f", "freight_ratio_pct": ":.2f", "lat": False, "lon": False},
            scope="south america",
            color_continuous_scale="RdYlGn",
            size_max=45,
        )
        fig_map.update_geos(center={"lat": -14.2, "lon": -51.9}, projection_scale=2.2, showcountries=True, countrycolor="#CBD5E1")
        style_plotly(fig_map, "Brazil State Merchandise Scale & On-Time SLA Map", height=460)
        st.plotly_chart(fig_map, use_container_width=True)

    with col_r:
        fig_reg = px.bar(
            reg_df, x="customer_region", y="merch_brl", color="customer_region", color_discrete_sequence=COLOR_PALETTE,
            labels={"customer_region": "Brazilian Macro-Region", "merch_brl": "Delivered Merch (BRL)"},
        )
        style_plotly(fig_reg, "Delivered Merchandise by Brazilian Macro-Region", height=460)
        st.plotly_chart(fig_reg, use_container_width=True)

    st.dataframe(st_df[["customer_state", "customer_region", "total_orders", "delivered_orders", "delivered_merch_brl", "delivered_freight_brl", "freight_ratio_pct", "on_time_rate_pct", "mean_delivery_days", "mean_review_score"]], use_container_width=True, hide_index=True)
    st.download_button(
        "Download Geographic State Performance (CSV)",
        st_df.to_csv(index=False).encode("utf-8"),
        file_name="commerceiq_geographic_performance.csv",
        mime="text/csv",
    )
