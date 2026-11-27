-- ============================================================================
-- CommerceIQ SQL Analytics Library — 02. Revenue Leakage & Data Quality Audits
-- Covers: LEK-01..LEK-09, DQ-01..DQ-10 | KPIs: KPI-LEK-01..KPI-LEK-06
-- Note: LEK-10 (scenario benefit) is modeled in Phase 14 decision simulator.
-- ============================================================================

USE commerceiq;

-- Q1 [LEK-01..LEK-05] Unsuccessful Order Rates, Recorded Lost Value & Coverage
-- Grain: Order status among placed orders (99,441)
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 4) AS pct_of_all_orders,
    SUM(has_order_items) AS orders_with_item_values,
    COUNT(*) - SUM(has_order_items) AS orders_missing_item_values,
    ROUND(SUM(has_order_items) * 100.0 / COUNT(*), 2) AS value_coverage_pct,
    SUM(merchandise_value) AS recorded_merch_value_brl,
    SUM(total_payment_value) AS recorded_payment_value_brl
FROM fact_orders
GROUP BY order_status
ORDER BY order_count DESC;

-- Q2 [LEK-03] Monthly Cancellation & Unsuccessful Rate Trend (Core Period)
-- Grain: purchase_year_month
SELECT
    purchase_year_month,
    COUNT(*) AS total_orders,
    SUM(is_canceled) AS canceled_orders,
    SUM(is_unavailable) AS unavailable_orders,
    SUM(is_unsuccessful) AS unsuccessful_orders,
    ROUND(SUM(is_canceled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
    ROUND(SUM(is_unsuccessful) * 100.0 / COUNT(*), 2) AS unsuccessful_rate_pct,
    SUM(CASE WHEN is_unsuccessful = 1 THEN merchandise_value ELSE 0 END) AS known_unsuccessful_merch_brl
FROM fact_orders
WHERE is_core_reporting_period = 1
GROUP BY purchase_year_month
ORDER BY purchase_year_month;

-- Q3 [LEK-06] Category Unsuccessful Order Exposure (where item rows exist)
-- Grain: Product category (English)
SELECT
    dp.product_category_name_english AS category_en,
    COUNT(DISTINCT CASE WHEN foi.order_status IN ('canceled', 'unavailable') THEN foi.order_id END) AS unsuccessful_orders,
    SUM(CASE WHEN foi.order_status IN ('canceled', 'unavailable') THEN foi.price ELSE 0 END) AS unsuccessful_merch_brl,
    COUNT(DISTINCT foi.order_id) AS total_category_orders,
    ROUND(
        SUM(CASE WHEN foi.order_status IN ('canceled', 'unavailable') THEN foi.price ELSE 0 END) * 100.0
        / NULLIF(SUM(foi.price), 0),
        2
    ) AS category_unsuccessful_value_pct
FROM fact_order_items foi
INNER JOIN dim_product dp ON foi.product_key = dp.product_key
GROUP BY dp.product_category_name_english
HAVING unsuccessful_orders > 0
ORDER BY unsuccessful_merch_brl DESC
LIMIT 15;

-- Q4 [LEK-07] Seller Unsuccessful Order Value Exposure (Top 15)
SELECT
    seller_id,
    seller_state,
    total_orders,
    canceled_orders,
    unsuccessful_exposure_brl,
    recorded_merchandise_brl,
    ROUND(unsuccessful_exposure_brl * 100.0 / NULLIF(recorded_merchandise_brl, 0), 2) AS exposure_pct
FROM mart_seller_performance
WHERE unsuccessful_exposure_brl > 0
ORDER BY unsuccessful_exposure_brl DESC
LIMIT 15;

-- Q5 [LEK-08] Regional Cancellation Rates
-- Grain: Customer state
SELECT
    dc.customer_state,
    dc.customer_region,
    COUNT(*) AS placed_orders,
    SUM(fo.is_canceled) AS canceled_orders,
    SUM(fo.is_unavailable) AS unavailable_orders,
    ROUND(SUM(fo.is_canceled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
    ROUND(SUM(fo.is_unsuccessful) * 100.0 / COUNT(*), 2) AS unsuccessful_rate_pct
FROM fact_orders fo
INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
GROUP BY dc.customer_state, dc.customer_region
ORDER BY placed_orders DESC;

-- Q6 [LEK-09] Payment Method & Unsuccessful Status Association
-- Grain: Primary payment method on order
SELECT
    COALESCE(primary_payment_type, 'no_payment_record') AS primary_payment_type,
    COUNT(*) AS orders,
    SUM(is_canceled) AS canceled_orders,
    SUM(is_unavailable) AS unavailable_orders,
    ROUND(SUM(is_canceled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
    ROUND(SUM(is_unsuccessful) * 100.0 / COUNT(*), 2) AS unsuccessful_rate_pct
FROM fact_orders
GROUP BY COALESCE(primary_payment_type, 'no_payment_record')
ORDER BY orders DESC;

-- Q7 [DQ-05, DQ-08] Operational Exception & Join Fan-Out Audit Summary
SELECT
    COUNT(*) AS total_orders,
    SUM(COALESCE(is_carrier_before_purchase, 0)) AS carrier_before_purchase,
    SUM(COALESCE(is_carrier_before_approval, 0)) AS carrier_before_approval,
    SUM(COALESCE(is_delivery_before_approval, 0)) AS delivery_before_approval,
    SUM(COALESCE(is_delivery_before_carrier, 0)) AS delivery_before_carrier,
    SUM(CASE WHEN has_order_items = 0 THEN 1 ELSE 0 END) AS orders_without_items,
    SUM(CASE WHEN has_payment_records = 0 THEN 1 ELSE 0 END) AS orders_without_payments,
    SUM(CASE WHEN has_review_records = 0 THEN 1 ELSE 0 END) AS orders_without_reviews
FROM orders;
