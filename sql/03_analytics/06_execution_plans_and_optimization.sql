-- ============================================================================
-- CommerceIQ SQL Analytics Library — 06. Execution Plans & Optimization
-- Demonstrates EXPLAIN plan inspection, temporary tables, and index utilization.
-- ============================================================================

USE commerceiq;

-- 1. Verify index usage on core reporting period monthly aggregation
EXPLAIN
SELECT
    purchase_year_month,
    COUNT(*) AS orders,
    SUM(merchandise_value) AS merch_brl
FROM fact_orders
WHERE is_core_reporting_period = 1
GROUP BY purchase_year_month;

-- 2. Verify index usage on customer_unique_id lookup
EXPLAIN
SELECT
    dc.customer_unique_id,
    COUNT(*) AS orders,
    SUM(fo.merchandise_value) AS spend_brl
FROM dim_customer dc
INNER JOIN fact_orders fo ON dc.customer_key = fo.customer_key
WHERE dc.customer_state = 'SP'
GROUP BY dc.customer_unique_id;

-- 3. Practical Temporary Table pattern for multi-step seller scorecard filtering
DROP TEMPORARY TABLE IF EXISTS tmp_active_seller_base;
CREATE TEMPORARY TABLE tmp_active_seller_base AS
SELECT
    seller_id,
    seller_state,
    delivered_orders,
    delivered_merchandise_brl,
    late_exposure_pct,
    avg_associated_review_score
FROM mart_seller_performance
WHERE delivered_orders >= 20;

SELECT
    seller_state,
    COUNT(*) AS qualifying_sellers,
    SUM(delivered_merchandise_brl) AS total_merch_brl,
    ROUND(AVG(late_exposure_pct), 2) AS avg_late_pct,
    ROUND(AVG(avg_associated_review_score), 3) AS avg_review_score
FROM tmp_active_seller_base
GROUP BY seller_state
ORDER BY total_merch_brl DESC
LIMIT 10;

DROP TEMPORARY TABLE IF EXISTS tmp_active_seller_base;
