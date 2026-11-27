"""
CommerceIQ Analytics Studio — Parameterized MySQL Warehouse & Artifact Data Layer

All SQL queries bind user-controlled filters via SQLAlchemy `text()` parameters.
Caches read-only analytical frames and the trained Scikit-Learn pipeline.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy import text
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_database_name, get_sqlalchemy_engine


@st.cache_resource
def get_db_engine():
    return get_sqlalchemy_engine(get_database_name())


@st.cache_resource
def load_delivery_risk_model():
    model_path = PROJECT_ROOT / "models" / "delivery_risk_model.joblib"
    if not model_path.is_file():
        return None
    return joblib.load(model_path)


@st.cache_data(ttl=3600)
def get_filter_options() -> dict[str, Any]:
    engine = get_db_engine()
    with engine.connect() as conn:
        bounds = conn.execute(
            text("SELECT MIN(full_date), MAX(full_date) FROM dim_date dd INNER JOIN fact_orders fo ON dd.date_key = fo.purchase_date_key")
        ).fetchone()
        states = [r[0] for r in conn.execute(text("SELECT DISTINCT customer_state FROM dim_customer ORDER BY customer_state")).fetchall()]
        cats = [r[0] for r in conn.execute(text("SELECT DISTINCT product_category_name_english FROM dim_product ORDER BY product_category_name_english")).fetchall()]
        sellers = [r[0] for r in conn.execute(text("SELECT seller_id FROM mart_seller_performance ORDER BY delivered_merchandise_brl DESC LIMIT 100")).fetchall()]
    return {
        "min_date": bounds[0] if bounds and bounds[0] else dt.date(2016, 9, 4),
        "max_date": bounds[1] if bounds and bounds[1] else dt.date(2018, 10, 17),
        "states": states,
        "categories": cats,
        "top_sellers": sellers,
    }


def _build_order_where(
    start_date: dt.date,
    end_date: dt.date,
    states: tuple[str, ...],
) -> tuple[str, dict[str, Any]]:
    clauses = ["dd.full_date BETWEEN :start_dt AND :end_dt"]
    params: dict[str, Any] = {"start_dt": start_date, "end_dt": end_date}
    if states:
        placeholders = ", ".join(f":st_{i}" for i in range(len(states)))
        clauses.append(f"dc.customer_state IN ({placeholders})")
        for i, st_code in enumerate(states):
            params[f"st_{i}"] = st_code
    return " AND ".join(clauses), params


@st.cache_data(ttl=1800)
def query_executive_summary(
    start_date: dt.date,
    end_date: dt.date,
    states: tuple[str, ...],
    categories: tuple[str, ...],
) -> dict[str, Any]:
    engine = get_db_engine()
    where_sql, params = _build_order_where(start_date, end_date, states)
    cat_filter = ""
    if categories:
        cat_ph = ", ".join(f":cat_{i}" for i in range(len(categories)))
        cat_filter = f" AND fo.order_key IN (SELECT foi2.order_key FROM fact_order_items foi2 INNER JOIN dim_product dp2 ON foi2.product_key = dp2.product_key WHERE dp2.product_category_name_english IN ({cat_ph}))"
        for i, c in enumerate(categories):
            params[f"cat_{i}"] = c

    kpi_sql = text(
        f"""
        SELECT
            COUNT(*) AS total_orders,
            SUM(fo.is_delivered) AS delivered_orders,
            SUM(fo.is_unsuccessful) AS unsuccessful_orders,
            COUNT(DISTINCT CASE WHEN fo.is_delivered = 1 THEN dc.customer_unique_id END) AS unique_delivered_customers,
            CAST(SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END) AS DOUBLE) AS delivered_merch_brl,
            CAST(SUM(fo.merchandise_value) AS DOUBLE) AS recorded_gmv_brl,
            CAST(SUM(fo.total_payment_value) AS DOUBLE) AS recorded_payment_brl,
            SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) AS ontime_orders,
            SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END) AS elig_sla_orders,
            CAST(AVG(fo.avg_review_score) AS DOUBLE) AS mean_review_score
        FROM fact_orders fo
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql} {cat_filter}
        """
    )
    monthly_sql = text(
        f"""
        SELECT
            dd.year_month_str AS purchase_ym,
            COUNT(*) AS total_orders,
            SUM(fo.is_delivered) AS delivered_orders,
            CAST(SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END) AS DOUBLE) AS delivered_merch_brl,
            SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) AS ontime_orders,
            SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END) AS elig_sla_orders
        FROM fact_orders fo
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql} {cat_filter}
        GROUP BY dd.year_month_str
        ORDER BY dd.year_month_str
        """
    )
    status_sql = text(
        f"""
        SELECT fo.order_status, COUNT(*) AS orders, CAST(SUM(fo.merchandise_value) AS DOUBLE) AS merch_brl
        FROM fact_orders fo
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql} {cat_filter}
        GROUP BY fo.order_status
        ORDER BY orders DESC
        """
    )
    with engine.connect() as conn:
        kpi_df = pd.read_sql(kpi_sql, conn, params=params)
        monthly_df = pd.read_sql(monthly_sql, conn, params=params)
        status_df = pd.read_sql(status_sql, conn, params=params)
    return {"kpi": kpi_df.iloc[0].to_dict(), "monthly": monthly_df, "status": status_df}


@st.cache_data(ttl=1800)
def query_sales_and_products(
    start_date: dt.date,
    end_date: dt.date,
    states: tuple[str, ...],
    categories: tuple[str, ...],
) -> dict[str, pd.DataFrame]:
    engine = get_db_engine()
    where_sql, params = _build_order_where(start_date, end_date, states)
    cat_clause = ""
    if categories:
        cat_ph = ", ".join(f":cat_{i}" for i in range(len(categories)))
        cat_clause = f" AND dp.product_category_name_english IN ({cat_ph})"
        for i, c in enumerate(categories):
            params[f"cat_{i}"] = c

    cat_sql = text(
        f"""
        SELECT
            dp.product_category_name_english AS category_en,
            COUNT(DISTINCT foi.order_id) AS orders,
            COUNT(*) AS delivered_items,
            CAST(SUM(foi.price) AS DOUBLE) AS delivered_merch_brl,
            CAST(SUM(foi.freight_value) AS DOUBLE) AS delivered_freight_brl,
            ROUND(AVG(foi.price), 2) AS avg_item_price_brl,
            ROUND(AVG(fo.avg_review_score), 3) AS avg_review_score
        FROM fact_order_items foi
        INNER JOIN fact_orders fo ON foi.order_key = fo.order_key
        INNER JOIN dim_customer dc ON foi.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON foi.purchase_date_key = dd.date_key
        INNER JOIN dim_product dp ON foi.product_key = dp.product_key
        WHERE foi.is_delivered = 1 AND {where_sql} {cat_clause}
        GROUP BY dp.product_category_name_english
        ORDER BY delivered_merch_brl DESC
        """
    )
    prod_sql = text(
        f"""
        SELECT
            dp.product_id,
            dp.product_category_name_english AS category_en,
            COUNT(*) AS items_sold,
            CAST(SUM(foi.price) AS DOUBLE) AS delivered_merch_brl
        FROM fact_order_items foi
        INNER JOIN fact_orders fo ON foi.order_key = fo.order_key
        INNER JOIN dim_customer dc ON foi.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON foi.purchase_date_key = dd.date_key
        INNER JOIN dim_product dp ON foi.product_key = dp.product_key
        WHERE foi.is_delivered = 1 AND {where_sql} {cat_clause}
        GROUP BY dp.product_id, dp.product_category_name_english
        ORDER BY delivered_merch_brl DESC
        LIMIT 25
        """
    )
    pay_sql = text(
        f"""
        SELECT
            dpt.payment_type,
            COUNT(*) AS payment_records,
            CAST(SUM(fp.payment_value) AS DOUBLE) AS total_payment_brl,
            ROUND(AVG(fp.payment_installments), 2) AS avg_installments
        FROM fact_payments fp
        INNER JOIN fact_orders fo ON fp.order_key = fo.order_key
        INNER JOIN dim_customer dc ON fp.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fp.purchase_date_key = dd.date_key
        INNER JOIN dim_payment_type dpt ON fp.payment_type_key = dpt.payment_type_key
        WHERE {where_sql}
        GROUP BY dpt.payment_type
        ORDER BY total_payment_brl DESC
        """
    )
    with engine.connect() as conn:
        return {
            "categories": pd.read_sql(cat_sql, conn, params=params),
            "top_products": pd.read_sql(prod_sql, conn, params=params),
            "payments": pd.read_sql(pay_sql, conn, params=params),
        }


@st.cache_data(ttl=1800)
def query_customer_intelligence() -> dict[str, pd.DataFrame]:
    rfm = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "customer_rfm_segments.csv")
    cohort_sql = pd.read_csv(PROJECT_ROOT / "reports" / "sql_analytics_results" / "03_customer_analytics__q05.csv")

    # Build cohort retention heatmap from cleaned parquet (aggregated, no individual IDs shown)
    orders = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "parquet" / "orders.parquet", columns=["order_id", "customer_id", "order_status", "has_order_items", "purchase_date"])
    orders["purchase_date"] = pd.to_datetime(orders["purchase_date"])
    customers = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "parquet" / "customers.parquet", columns=["customer_id", "customer_unique_id"])
    deliv = orders[orders["order_status"].eq("delivered") & orders["has_order_items"]].merge(customers, on="customer_id", how="inner")
    first = deliv.groupby("customer_unique_id", as_index=False)["purchase_date"].min().rename(columns={"purchase_date": "first_date"})
    first["cohort_ym"] = first["first_date"].dt.to_period("M")
    deliv = deliv.merge(first, on="customer_unique_id", how="inner")
    deliv["order_ym"] = deliv["purchase_date"].dt.to_period("M")
    deliv["cohort_index"] = (deliv["order_ym"] - deliv["cohort_ym"]).apply(lambda p: p.n)
    core = deliv[(deliv["cohort_ym"] >= "2017-01") & (deliv["cohort_ym"] <= "2018-08")]
    counts = core.groupby(["cohort_ym", "cohort_index"])["customer_unique_id"].nunique().unstack(fill_value=0)
    max_p = pd.Period("2018-08", freq="M")
    for idx_c in counts.index:
        max_off = (max_p - idx_c).n
        for c_off in counts.columns:
            if c_off > max_off:
                counts.loc[idx_c, c_off] = float("nan")
    ret_pct = counts.divide(counts[0], axis=0) * 100.0
    ret_pct.index = ret_pct.index.astype(str)
    return {"rfm": rfm, "cohort_sql": cohort_sql, "cohort_matrix": ret_pct.loc[:, 1:12]}


@st.cache_data(ttl=1800)
def query_sellers(states: tuple[str, ...], seller_filter: str | None = None) -> pd.DataFrame:
    engine = get_db_engine()
    clauses = ["delivered_orders > 0"]
    params: dict[str, Any] = {}
    if states:
        ph = ", ".join(f":st_{i}" for i in range(len(states)))
        clauses.append(f"seller_state IN ({ph})")
        for i, s in enumerate(states):
            params[f"st_{i}"] = s
    if seller_filter and seller_filter != "All Sellers":
        clauses.append("seller_id = :sid")
        params["sid"] = seller_filter
    sql = text(
        f"""
        SELECT
            seller_id, seller_city, seller_state, seller_region,
            has_recorded_marketing_deal, total_orders, delivered_orders, canceled_orders,
            total_items, distinct_products,
            CAST(delivered_merchandise_brl AS DOUBLE) AS delivered_merchandise_brl,
            CAST(unsuccessful_exposure_brl AS DOUBLE) AS unsuccessful_exposure_brl,
            CAST(COALESCE(late_exposure_pct, 0) AS DOUBLE) AS late_exposure_pct,
            CAST(COALESCE(avg_associated_review_score, 0) AS DOUBLE) AS avg_associated_review_score
        FROM mart_seller_performance
        WHERE {' AND '.join(clauses)}
        ORDER BY delivered_merchandise_brl DESC
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=1800)
def query_logistics_and_geo(
    start_date: dt.date,
    end_date: dt.date,
    states: tuple[str, ...],
) -> dict[str, pd.DataFrame]:
    engine = get_db_engine()
    where_sql, params = _build_order_where(start_date, end_date, states)
    state_sql = text(
        f"""
        SELECT
            dc.customer_state,
            dc.customer_region,
            COUNT(*) AS total_orders,
            SUM(fo.is_delivered) AS delivered_orders,
            CAST(SUM(CASE WHEN fo.is_delivered = 1 THEN fo.merchandise_value ELSE 0 END) AS DOUBLE) AS delivered_merch_brl,
            CAST(SUM(CASE WHEN fo.is_delivered = 1 THEN fo.freight_value ELSE 0 END) AS DOUBLE) AS delivered_freight_brl,
            ROUND(AVG(fo.delivery_duration_days), 2) AS mean_delivery_days,
            ROUND(AVG(fo.processing_duration_days), 2) AS mean_processing_days,
            ROUND(AVG(fo.transit_duration_days), 2) AS mean_transit_days,
            ROUND(AVG(fo.approval_duration_hours) / 24.0, 2) AS mean_approval_days,
            ROUND(SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END), 0), 2) AS on_time_rate_pct,
            ROUND(AVG(fo.avg_review_score), 3) AS mean_review_score
        FROM fact_orders fo
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql}
        GROUP BY dc.customer_state, dc.customer_region
        ORDER BY delivered_merch_brl DESC
        """
    )
    lanes_sql = text("SELECT * FROM mart_delivery_logistics ORDER BY total_orders DESC LIMIT 200")
    sla_sql = text(
        f"""
        SELECT
            COALESCE(fo.delivery_performance, 'not_delivered') AS delivery_performance,
            COUNT(*) AS orders,
            ROUND(AVG(fo.delivery_duration_days), 2) AS mean_delivery_days,
            ROUND(AVG(fo.delivery_deviation_days), 2) AS mean_deviation_days,
            ROUND(AVG(fo.avg_review_score), 3) AS mean_review_score
        FROM fact_orders fo
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql}
        GROUP BY COALESCE(fo.delivery_performance, 'not_delivered')
        """
    )
    geo_coords_sql = text(
        """
        SELECT
            dg.state,
            dg.region,
            ROUND(AVG(dg.latitude), 4) AS lat,
            ROUND(AVG(dg.longitude), 4) AS lon
        FROM dim_geography dg
        WHERE dg.has_geolocation_match = 1
        GROUP BY dg.state, dg.region
        """
    )
    with engine.connect() as conn:
        return {
            "states": pd.read_sql(state_sql, conn, params=params),
            "lanes": pd.read_sql(lanes_sql, conn),
            "sla": pd.read_sql(sla_sql, conn, params=params),
            "coords": pd.read_sql(geo_coords_sql, conn),
        }


@st.cache_data(ttl=1800)
def query_satisfaction(
    start_date: dt.date,
    end_date: dt.date,
    states: tuple[str, ...],
) -> dict[str, pd.DataFrame]:
    engine = get_db_engine()
    where_sql, params = _build_order_where(start_date, end_date, states)
    dist_sql = text(
        f"""
        SELECT fr.review_score, fr.rating_classification, COUNT(*) AS reviews
        FROM fact_reviews fr
        INNER JOIN fact_orders fo ON fr.order_key = fo.order_key
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql}
        GROUP BY fr.review_score, fr.rating_classification
        ORDER BY fr.review_score DESC
        """
    )
    sla_rev_sql = text(
        f"""
        SELECT
            COALESCE(fo.delivery_performance, 'not_delivered') AS delivery_performance,
            COUNT(*) AS reviews,
            ROUND(AVG(fr.review_score), 3) AS mean_score,
            ROUND(SUM(CASE WHEN fr.rating_classification = 'negative' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS negative_pct,
            ROUND(SUM(CASE WHEN fr.rating_classification = 'positive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS positive_pct
        FROM fact_reviews fr
        INNER JOIN fact_orders fo ON fr.order_key = fo.order_key
        INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
        INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
        WHERE {where_sql}
        GROUP BY COALESCE(fo.delivery_performance, 'not_delivered')
        """
    )
    with engine.connect() as conn:
        return {
            "dist": pd.read_sql(dist_sql, conn, params=params),
            "sla_rev": pd.read_sql(sla_rev_sql, conn, params=params),
        }


@st.cache_data(ttl=1800)
def query_marketing_funnel() -> dict[str, pd.DataFrame]:
    engine = get_db_engine()
    with engine.connect() as conn:
        funnel = pd.read_sql("SELECT * FROM mart_marketing_funnel ORDER BY qualified_leads DESC", conn)
        monthly = pd.read_sql(
            """
            SELECT dd.year_month_str AS contact_month, COUNT(*) AS leads, SUM(fm.has_closed_deal) AS deals
            FROM fact_marketing_funnel fm
            INNER JOIN dim_date dd ON fm.first_contact_date_key = dd.date_key
            GROUP BY dd.year_month_str
            ORDER BY dd.year_month_str
            """,
            conn,
        )
        segments = pd.read_sql(
            """
            SELECT COALESCE(business_segment, 'unrecorded') AS business_segment, COUNT(*) AS closed_deals,
                   SUM(has_marketplace_seller_match) AS matched_sellers,
                   ROUND(AVG(conversion_duration_days), 1) AS avg_cycle_days
            FROM fact_marketing_funnel
            WHERE has_closed_deal = 1
            GROUP BY COALESCE(business_segment, 'unrecorded')
            ORDER BY closed_deals DESC
            LIMIT 15
            """,
            conn,
        )
    return {"funnel": funnel, "monthly": monthly, "segments": segments}


@st.cache_data(ttl=1800)
def load_predictive_and_decision_data() -> dict[str, Any]:
    fc = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "forecast_outputs.csv")
    risk = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "delivery_risk_predictions.csv")
    scen = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "decision_scenarios.csv")
    return {"forecast": fc, "risk": risk, "scenarios": scen}
