"""
CommerceIQ Analytics Studio — Main Streamlit Application Entry Point

Launch from project root:
    python -m streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.data_access import get_filter_options
from app.theme import inject_custom_css
from app.views_commercial import (
    render_customer_intelligence,
    render_executive_overview,
    render_sales_and_products,
    render_seller_intelligence,
)
from app.views_operations import (
    render_customer_satisfaction,
    render_geographic_analytics,
    render_logistics_analytics,
    render_marketing_intelligence,
)
from app.views_predictive_decision import (
    render_decision_simulator,
    render_predictive_analytics,
)

PAGES = [
    "Executive Overview",
    "Sales and Product Analytics",
    "Customer Intelligence",
    "Seller Intelligence",
    "Logistics Analytics",
    "Customer Satisfaction",
    "Marketing Intelligence",
    "Geographic Analytics",
    "Predictive Analytics",
    "Decision Simulator",
]


def main() -> None:
    st.set_page_config(
        page_title="CommerceIQ Analytics Studio",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

    try:
        opts = get_filter_options()
    except Exception as exc:
        st.error(f"Unable to connect to MySQL warehouse (`commerceiq`). Check `.env` and MySQL server status.\nDetails: {exc}")
        return

    with st.sidebar:
        st.markdown("## CommerceIQ Studio")
        st.caption("MySQL Warehouse + ML + Decision Intelligence")
        qp_page = st.query_params.get("page", PAGES[0])
        default_idx = PAGES.index(qp_page) if qp_page in PAGES else 0
        page = st.radio("Navigation", PAGES, index=default_idx)
        st.divider()
        st.markdown("### Global Filters")
        date_range = st.date_input(
            "Purchase Date Range",
            value=(opts["min_date"], opts["max_date"]),
            min_value=opts["min_date"],
            max_value=opts["max_date"],
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_dt, end_dt = date_range
        else:
            start_dt, end_dt = opts["min_date"], opts["max_date"]

        selected_states = tuple(st.multiselect("Customer / Seller State", opts["states"], default=[]))
        selected_cats = tuple(st.multiselect("Product Category", opts["categories"], default=[]))
        st.divider()
        st.caption("Historical Olist Brazil Data (2016–2018) | Currency: BRL")

    if page == "Executive Overview":
        render_executive_overview(start_dt, end_dt, selected_states, selected_cats)
    elif page == "Sales and Product Analytics":
        render_sales_and_products(start_dt, end_dt, selected_states, selected_cats)
    elif page == "Customer Intelligence":
        render_customer_intelligence()
    elif page == "Seller Intelligence":
        render_seller_intelligence(selected_states, opts["top_sellers"])
    elif page == "Logistics Analytics":
        render_logistics_analytics(start_dt, end_dt, selected_states)
    elif page == "Customer Satisfaction":
        render_customer_satisfaction(start_dt, end_dt, selected_states)
    elif page == "Marketing Intelligence":
        render_marketing_intelligence()
    elif page == "Geographic Analytics":
        render_geographic_analytics(start_dt, end_dt, selected_states)
    elif page == "Predictive Analytics":
        render_predictive_analytics()
    elif page == "Decision Simulator":
        render_decision_simulator()


if __name__ == "__main__":
    main()
