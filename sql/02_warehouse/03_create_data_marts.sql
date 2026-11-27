-- ============================================================================
-- CommerceIQ Analytical Data Marts (Views on Star Schema)
-- Phase 6: 9 Business Domain Data Marts
-- ============================================================================

USE commerceiq;

-- 1. Executive Commercial Performance (Monthly)
CREATE OR REPLACE VIEW mart_executive_monthly AS
SELECT
    fo.purchase_year_month AS year_month_str,
    MIN(fo.is_core_reporting_period) AS is_core_reporting_period,
    COUNT(*) AS total_orders,
    SUM(fo.is_delivered) AS delivered_orders,
    SUM(fo.is_canceled) AS canceled_orders,
    SUM(fo.is_unavailable) AS unavailable_orders,
    SUM(fo.is_unsuccessful) AS unsuccessful_orders,
    SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.freight_value ELSE 0 END) AS delivered_freight_brl,
    SUM(fo.merchandise_value) AS recorded_gmv_brl,
    SUM(fo.total_payment_value) AS recorded_payment_brl,
    ROUND(
        SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS avg_delivered_order_value_brl,
    SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END) AS eligible_delivery_orders,
    SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) AS on_time_orders,
    ROUND(
        SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END), 0),
        4
    ) AS on_time_delivery_pct,
    ROUND(AVG(fo.avg_review_score), 4) AS mean_order_review_score
FROM fact_orders fo
GROUP BY fo.purchase_year_month
ORDER BY fo.purchase_year_month;

-- 2. Customer Intelligence (Persistent customer_unique_id grain)
CREATE OR REPLACE VIEW mart_customer_intelligence AS
SELECT
    dc.customer_unique_id,
    MIN(dc.customer_state) AS primary_state,
    MIN(dc.customer_region) AS primary_region,
    COUNT(*) AS total_orders,
    SUM(fo.is_delivered) AS delivered_orders,
    SUM(fo.is_unsuccessful) AS unsuccessful_orders,
    CASE WHEN SUM(fo.is_delivered) >= 2 THEN 1 ELSE 0 END AS is_repeat_delivered_customer,
    MIN(dd.full_date) AS first_purchase_date,
    MAX(dd.full_date) AS last_purchase_date,
    SUM(CASE WHEN fo.is_delivered = 1 THEN fo.merchandise_value ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN fo.is_delivered = 1 THEN fo.freight_value ELSE 0 END) AS delivered_freight_brl,
    SUM(fo.merchandise_value) AS recorded_merchandise_brl,
    SUM(fo.item_count) AS total_items,
    AVG(fo.avg_review_score) AS mean_review_score,
    SUM(CASE WHEN fo.delivery_performance = 'late' THEN 1 ELSE 0 END) AS late_deliveries
FROM fact_orders fo
INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
GROUP BY dc.customer_unique_id;

-- 3. Product & Category Performance
CREATE OR REPLACE VIEW mart_product_category_performance AS
SELECT
    dp.product_category_name,
    dp.product_category_name_english,
    COUNT(DISTINCT dp.product_id) AS catalog_products,
    COUNT(DISTINCT foi.order_id) AS total_orders,
    COUNT(*) AS total_items,
    SUM(CASE WHEN foi.is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_items,
    SUM(CASE WHEN foi.is_delivered = 1 THEN foi.price ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN foi.is_delivered = 1 THEN foi.freight_value ELSE 0 END) AS delivered_freight_brl,
    SUM(foi.price) AS recorded_merchandise_brl,
    ROUND(
        SUM(CASE WHEN foi.is_delivered = 1 THEN foi.price ELSE 0 END)
        / NULLIF(SUM(CASE WHEN foi.is_delivered = 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS avg_delivered_item_price_brl,
    ROUND(AVG(foi.freight_to_price_pct), 2) AS avg_freight_to_price_pct,
    ROUND(AVG(fo.avg_review_score), 4) AS avg_order_review_score
FROM fact_order_items foi
INNER JOIN dim_product dp ON foi.product_key = dp.product_key
INNER JOIN fact_orders fo ON foi.order_key = fo.order_key
GROUP BY dp.product_category_name, dp.product_category_name_english;

-- 4. Seller Performance Scorecard
CREATE OR REPLACE VIEW mart_seller_performance AS
SELECT
    ds.seller_id,
    ds.seller_city,
    ds.seller_state,
    ds.seller_region,
    ds.has_recorded_marketing_deal,
    ds.marketing_origin,
    COUNT(DISTINCT foi.order_id) AS total_orders,
    COUNT(DISTINCT CASE WHEN fo.is_delivered = 1 THEN foi.order_id END) AS delivered_orders,
    COUNT(DISTINCT CASE WHEN fo.is_canceled = 1 THEN foi.order_id END) AS canceled_orders,
    COUNT(*) AS total_items,
    COUNT(DISTINCT foi.product_key) AS distinct_products,
    SUM(CASE WHEN fo.is_delivered = 1 THEN foi.price ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN fo.is_unsuccessful = 1 THEN foi.price ELSE 0 END) AS unsuccessful_exposure_brl,
    SUM(foi.price) AS recorded_merchandise_brl,
    COUNT(DISTINCT CASE WHEN fo.delivery_performance = 'late' THEN foi.order_id END) AS late_delivered_orders,
    COUNT(DISTINCT CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN foi.order_id END) AS eligible_delivery_orders,
    ROUND(
        COUNT(DISTINCT CASE WHEN fo.delivery_performance = 'late' THEN foi.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN foi.order_id END), 0),
        2
    ) AS late_exposure_pct,
    ROUND(AVG(fo.avg_review_score), 4) AS avg_associated_review_score
FROM fact_order_items foi
INNER JOIN dim_seller ds ON foi.seller_key = ds.seller_key
INNER JOIN fact_orders fo ON foi.order_key = fo.order_key
GROUP BY
    ds.seller_id, ds.seller_city, ds.seller_state, ds.seller_region,
    ds.has_recorded_marketing_deal, ds.marketing_origin;

-- 5. Delivery & Logistics Lane Performance
CREATE OR REPLACE VIEW mart_delivery_logistics AS
SELECT
    dc.customer_state,
    dc.customer_region,
    ds.seller_state,
    ds.seller_region,
    foi.is_same_state_fulfillment,
    COUNT(DISTINCT foi.order_id) AS total_orders,
    COUNT(DISTINCT CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN foi.order_id END) AS eligible_deliveries,
    COUNT(DISTINCT CASE WHEN fo.is_on_time_delivery = 1 THEN foi.order_id END) AS on_time_deliveries,
    COUNT(DISTINCT CASE WHEN fo.delivery_performance = 'late' THEN foi.order_id END) AS late_deliveries,
    ROUND(
        COUNT(DISTINCT CASE WHEN fo.is_on_time_delivery = 1 THEN foi.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN foi.order_id END), 0),
        2
    ) AS on_time_rate_pct,
    ROUND(AVG(fo.delivery_duration_days), 2) AS mean_delivery_days,
    ROUND(AVG(fo.processing_duration_days), 2) AS mean_processing_days,
    ROUND(AVG(fo.transit_duration_days), 2) AS mean_transit_days,
    ROUND(AVG(CASE WHEN fo.delivery_deviation_days > 0 THEN fo.delivery_deviation_days END), 2) AS mean_delay_days_when_late,
    SUM(foi.freight_value) AS total_freight_brl,
    SUM(foi.price) AS total_merchandise_brl
FROM fact_order_items foi
INNER JOIN fact_orders fo ON foi.order_key = fo.order_key
INNER JOIN dim_customer dc ON foi.customer_key = dc.customer_key
INNER JOIN dim_seller ds ON foi.seller_key = ds.seller_key
GROUP BY
    dc.customer_state, dc.customer_region,
    ds.seller_state, ds.seller_region,
    foi.is_same_state_fulfillment;

-- 6. Customer Satisfaction (Review x Delivery Performance)
CREATE OR REPLACE VIEW mart_customer_satisfaction AS
SELECT
    dd.year_month_str AS purchase_year_month,
    COALESCE(fr.delivery_performance_bucket, 'not_delivered_or_ineligible') AS delivery_bucket,
    fr.rating_classification,
    COUNT(*) AS review_count,
    ROUND(AVG(fr.review_score), 4) AS mean_review_score,
    ROUND(AVG(fr.review_response_hours), 2) AS mean_response_hours,
    SUM(fr.has_written_review) AS written_reviews
FROM (
    SELECT
        r.*,
        fo.delivery_performance AS delivery_performance_bucket
    FROM fact_reviews r
    INNER JOIN fact_orders fo ON r.order_key = fo.order_key
) fr
INNER JOIN dim_date dd ON fr.purchase_date_key = dd.date_key
GROUP BY
    dd.year_month_str,
    COALESCE(fr.delivery_performance_bucket, 'not_delivered_or_ineligible'),
    fr.rating_classification;

-- 7. Marketing Funnel Performance
CREATE OR REPLACE VIEW mart_marketing_funnel AS
SELECT
    dmc.origin,
    dmc.channel_group,
    COUNT(*) AS qualified_leads,
    SUM(fm.has_closed_deal) AS closed_deals,
    ROUND(SUM(fm.has_closed_deal) * 100.0 / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct,
    SUM(fm.has_marketplace_seller_match) AS matched_marketplace_sellers,
    ROUND(AVG(CASE WHEN fm.is_valid_conversion_duration = 1 THEN fm.conversion_duration_days END), 2) AS mean_conversion_days,
    SUM(COALESCE(fm.declared_monthly_revenue, 0.00)) AS total_declared_monthly_revenue_brl
FROM fact_marketing_funnel fm
INNER JOIN dim_marketing_channel dmc ON fm.channel_key = dmc.channel_key
GROUP BY dmc.origin, dmc.channel_group;

-- 8. Geographic Performance (Customer State & Region)
CREATE OR REPLACE VIEW mart_geographic_performance AS
SELECT
    dc.customer_state,
    dc.customer_region,
    COUNT(*) AS total_orders,
    COUNT(DISTINCT dc.customer_unique_id) AS unique_customers,
    SUM(fo.is_delivered) AS delivered_orders,
    SUM(CASE WHEN fo.is_delivered = 1 THEN fo.merchandise_value ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN fo.is_delivered = 1 THEN fo.freight_value ELSE 0 END) AS delivered_freight_brl,
    ROUND(
        SUM(CASE WHEN fo.is_delivered = 1 THEN fo.freight_value ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN fo.is_delivered = 1 THEN fo.merchandise_value ELSE 0 END), 0),
        2
    ) AS freight_to_merchandise_pct,
    ROUND(
        SUM(CASE WHEN fo.is_on_time_delivery = 1 THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN fo.is_valid_delivery_promise_comparison = 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS on_time_rate_pct,
    ROUND(AVG(fo.delivery_duration_days), 2) AS mean_delivery_days,
    ROUND(AVG(fo.avg_review_score), 4) AS mean_review_score
FROM fact_orders fo
INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
GROUP BY dc.customer_state, dc.customer_region;

-- 9. Payment Reconciliation & Method Behaviour
CREATE OR REPLACE VIEW mart_payment_reconciliation AS
SELECT
    dpt.payment_type,
    dpt.payment_group,
    COUNT(*) AS payment_records,
    COUNT(DISTINCT fp.order_id) AS distinct_orders,
    SUM(fp.payment_value) AS total_payment_value_brl,
    ROUND(AVG(fp.payment_value), 2) AS mean_payment_value_brl,
    ROUND(AVG(fp.payment_installments), 2) AS mean_installments,
    MAX(fp.payment_installments) AS max_installments,
    SUM(fp.is_multi_payment_order) AS multi_payment_records,
    SUM(fp.is_zero_payment) AS zero_payment_records
FROM fact_payments fp
INNER JOIN dim_payment_type dpt ON fp.payment_type_key = dpt.payment_type_key
GROUP BY dpt.payment_type, dpt.payment_group;
