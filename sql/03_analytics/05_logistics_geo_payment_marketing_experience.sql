-- ============================================================================
-- CommerceIQ SQL Analytics Library — 05. Logistics, Geography, Payments, Marketing & Experience
-- Covers: LOG-01..14, PAY-01..08, GEO-01..08, MKT-01..10, EXP-01..10
-- Limitations documented:
--   - GEO-08 (orders per population): external population dataset unavailable.
--   - EXP-09 (complaint themes): Portuguese text mining evaluated in Python (Phase 9).
--   - LOG-15 (late risk prediction): ML classification in Phase 12.
-- ============================================================================

USE commerceiq;

-- Q1 [LOG-01..LOG-10] Lifecycle Stage Durations & SLA Delivery Performance
SELECT
    COUNT(*) AS total_delivered_orders,
    SUM(is_valid_delivery_promise_comparison) AS eligible_sla_orders,
    SUM(CASE WHEN delivery_performance = 'early' THEN 1 ELSE 0 END) AS early_orders,
    SUM(CASE WHEN delivery_performance = 'on_time' THEN 1 ELSE 0 END) AS exact_on_time_orders,
    SUM(CASE WHEN delivery_performance = 'late' THEN 1 ELSE 0 END) AS late_orders,
    ROUND(SUM(is_on_time_delivery) * 100.0 / NULLIF(SUM(is_valid_delivery_promise_comparison), 0), 4) AS on_time_rate_pct,
    ROUND(AVG(approval_duration_hours), 2) AS mean_approval_hours,
    ROUND(AVG(processing_duration_days), 2) AS mean_processing_days,
    ROUND(AVG(transit_duration_days), 2) AS mean_transit_days,
    ROUND(AVG(delivery_duration_days), 2) AS mean_total_delivery_days,
    ROUND(AVG(estimated_delivery_days), 2) AS mean_estimated_days,
    ROUND(AVG(CASE WHEN delivery_deviation_days > 0 THEN delivery_deviation_days END), 2) AS mean_positive_delay_days
FROM fact_orders
WHERE is_delivered = 1;

-- Q2 [GEO-05, LOG-11] Intra-State vs Inter-State Delivery & Freight Comparison
SELECT
    CASE WHEN is_same_state_fulfillment = 1 THEN 'Intra-State' ELSE 'Inter-State' END AS fulfillment_scope,
    SUM(total_orders) AS orders,
    SUM(eligible_deliveries) AS eligible_deliveries,
    ROUND(SUM(on_time_deliveries) * 100.0 / NULLIF(SUM(eligible_deliveries), 0), 2) AS on_time_rate_pct,
    ROUND(AVG(mean_delivery_days), 2) AS avg_lane_delivery_days,
    SUM(total_freight_brl) AS freight_brl,
    SUM(total_merchandise_brl) AS merch_brl,
    ROUND(SUM(total_freight_brl) * 100.0 / NULLIF(SUM(total_merchandise_brl), 0), 2) AS freight_to_merch_pct
FROM mart_delivery_logistics
GROUP BY CASE WHEN is_same_state_fulfillment = 1 THEN 'Intra-State' ELSE 'Inter-State' END;

-- Q3 [LOG-12] Approximate Haversine Distance Band vs Delivery Duration (Delivered Single-Seller Orders)
WITH order_geo AS (
    SELECT
        fo.order_id,
        fo.delivery_duration_days,
        fo.is_on_time_delivery,
        MIN(dg_c.latitude) AS c_lat,
        MIN(dg_c.longitude) AS c_lng,
        MIN(dg_s.latitude) AS s_lat,
        MIN(dg_s.longitude) AS s_lng
    FROM fact_orders fo
    INNER JOIN fact_order_items foi ON fo.order_key = foi.order_key
    INNER JOIN dim_geography dg_c ON fo.customer_geo_key = dg_c.geo_key
    INNER JOIN dim_seller ds ON foi.seller_key = ds.seller_key
    INNER JOIN dim_geography dg_s ON ds.geo_key = dg_s.geo_key
    WHERE fo.is_delivered = 1
      AND fo.is_valid_delivery_promise_comparison = 1
      AND fo.distinct_sellers = 1
      AND dg_c.has_geolocation_match = 1
      AND dg_s.has_geolocation_match = 1
    GROUP BY fo.order_id, fo.delivery_duration_days, fo.is_on_time_delivery
),
dist AS (
    SELECT
        *,
        2 * 6371 * ASIN(SQRT(
            POWER(SIN(RADIANS(c_lat - s_lat) / 2), 2)
            + COS(RADIANS(s_lat)) * COS(RADIANS(c_lat)) * POWER(SIN(RADIANS(c_lng - s_lng) / 2), 2)
        )) AS approx_km
    FROM order_geo
)
SELECT
    CASE
        WHEN approx_km < 100 THEN '01: < 100 km'
        WHEN approx_km < 500 THEN '02: 100-499 km'
        WHEN approx_km < 1000 THEN '03: 500-999 km'
        WHEN approx_km < 2000 THEN '04: 1000-1999 km'
        ELSE '05: 2000+ km'
    END AS distance_band,
    COUNT(*) AS orders,
    ROUND(AVG(approx_km), 1) AS mean_km,
    ROUND(AVG(delivery_duration_days), 2) AS mean_delivery_days,
    ROUND(AVG(is_on_time_delivery) * 100.0, 2) AS on_time_rate_pct
FROM dist
GROUP BY distance_band
ORDER BY distance_band;

-- Q4 [GEO-01..GEO-04, GEO-06, GEO-07] Customer State Performance Summary
SELECT
    customer_state,
    customer_region,
    total_orders,
    unique_customers,
    delivered_orders,
    delivered_merchandise_brl,
    ROUND(delivered_merchandise_brl / NULLIF(delivered_orders, 0), 2) AS aov_brl,
    delivered_freight_brl,
    freight_to_merchandise_pct,
    on_time_rate_pct,
    mean_delivery_days,
    mean_review_score
FROM mart_geographic_performance
ORDER BY delivered_merchandise_brl DESC;

-- Q5 [PAY-01..PAY-06, PAY-08] Payment Method Shares, Multi-Payment & Instalments
SELECT
    payment_type,
    payment_group,
    payment_records,
    distinct_orders,
    total_payment_value_brl,
    ROUND(total_payment_value_brl * 100.0 / SUM(total_payment_value_brl) OVER (), 2) AS payment_value_share_pct,
    mean_payment_value_brl,
    mean_installments,
    max_installments,
    multi_payment_records,
    zero_payment_records
FROM mart_payment_reconciliation
ORDER BY total_payment_value_brl DESC;

SELECT
    CASE WHEN payment_record_count > 1 THEN 'Multiple Payments' ELSE 'Single Payment' END AS payment_pattern,
    COUNT(*) AS orders,
    ROUND(AVG(total_payment_value), 2) AS avg_payment_brl,
    SUM(CASE WHEN ABS(payment_discrepancy_brl) > 0.05 THEN 1 ELSE 0 END) AS discrepancy_orders
FROM fact_orders
WHERE has_payment_records = 1
GROUP BY CASE WHEN payment_record_count > 1 THEN 'Multiple Payments' ELSE 'Single Payment' END;

-- Q6 [MKT-01..MKT-09] Marketing Funnel Conversion, Sales Cycle & Matched Seller Sales
SELECT
    origin,
    channel_group,
    qualified_leads,
    closed_deals,
    conversion_rate_pct,
    matched_marketplace_sellers,
    mean_conversion_days,
    total_declared_monthly_revenue_brl
FROM mart_marketing_funnel
ORDER BY qualified_leads DESC;

SELECT
    dmc.origin,
    COUNT(DISTINCT fm.seller_key) AS matched_sellers_in_funnel,
    COUNT(DISTINCT foi.order_id) AS subsequent_orders,
    SUM(CASE WHEN foi.is_delivered = 1 THEN foi.price ELSE 0 END) AS subsequent_delivered_merch_brl
FROM fact_marketing_funnel fm
INNER JOIN dim_marketing_channel dmc ON fm.channel_key = dmc.channel_key
LEFT JOIN fact_order_items foi ON fm.seller_key = foi.seller_key AND fm.seller_key <> -1
WHERE fm.has_closed_deal = 1
GROUP BY dmc.origin
ORDER BY subsequent_delivered_merch_brl DESC;

-- Q7 [EXP-01..EXP-07] Review Score Distribution & Delivery Experience Relationship
SELECT
    review_score,
    rating_classification,
    COUNT(*) AS review_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct,
    SUM(has_written_review) AS with_written_comment
FROM fact_reviews
GROUP BY review_score, rating_classification
ORDER BY review_score DESC;

SELECT
    fo.delivery_performance,
    COUNT(*) AS review_count,
    ROUND(AVG(fr.review_score), 4) AS mean_review_score,
    ROUND(SUM(CASE WHEN fr.rating_classification = 'positive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS positive_pct,
    ROUND(SUM(CASE WHEN fr.rating_classification = 'negative' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS negative_pct
FROM fact_reviews fr
INNER JOIN fact_orders fo ON fr.order_key = fo.order_key
WHERE fo.delivery_performance IS NOT NULL
GROUP BY fo.delivery_performance
ORDER BY mean_review_score DESC;
