-- ============================================================================
-- CommerceIQ SQL Analytics Library — 04. Product & Seller Performance
-- Covers: PRD-01..PRD-10, SEL-01..SEL-12 | KPIs: KPI-PRD-01..04, KPI-SEL-01..06
-- ============================================================================

USE commerceiq;

-- Q1 [PRD-01, PRD-03, PRD-04, PRD-08, PRD-09] Top Product Categories by Delivered Merchandise Value
SELECT
    product_category_name_english AS category_en,
    catalog_products,
    total_orders,
    delivered_items,
    delivered_merchandise_brl,
    delivered_freight_brl,
    avg_delivered_item_price_brl,
    avg_freight_to_price_pct,
    avg_order_review_score
FROM mart_product_category_performance
ORDER BY delivered_merchandise_brl DESC
LIMIT 20;

-- Q2 [PRD-02, PRD-06] Top Products & 80% Pareto Concentration Analysis
WITH prod_sales AS (
    SELECT
        dp.product_id,
        dp.product_category_name_english AS category_en,
        COUNT(*) AS delivered_items,
        SUM(foi.price) AS delivered_merch_brl
    FROM fact_order_items foi
    INNER JOIN dim_product dp ON foi.product_key = dp.product_key
    WHERE foi.is_delivered = 1
    GROUP BY dp.product_id, dp.product_category_name_english
),
pareto AS (
    SELECT
        *,
        SUM(delivered_merch_brl) OVER (ORDER BY delivered_merch_brl DESC, product_id) AS cum_merch_brl,
        SUM(delivered_merch_brl) OVER () AS total_merch_brl,
        ROW_NUMBER() OVER (ORDER BY delivered_merch_brl DESC, product_id) AS prod_rank
    FROM prod_sales
)
SELECT
    COUNT(*) AS total_sold_products,
    SUM(CASE WHEN cum_merch_brl <= 0.80 * total_merch_brl THEN 1 ELSE 0 END) AS products_contributing_80pct,
    ROUND(SUM(CASE WHEN cum_merch_brl <= 0.80 * total_merch_brl THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_of_products_for_80pct_sales
FROM pareto;

-- Q3 [PRD-05] Comparable YoY Category Growth (Jan-Aug 2017 vs Jan-Aug 2018, Top 15 by 2018 Sales)
WITH cat_yoy AS (
    SELECT
        dp.product_category_name_english AS category_en,
        SUM(CASE WHEN dd.year_num = 2017 AND dd.month_num BETWEEN 1 AND 8 THEN foi.price ELSE 0 END) AS sales_2017_brl,
        SUM(CASE WHEN dd.year_num = 2018 AND dd.month_num BETWEEN 1 AND 8 THEN foi.price ELSE 0 END) AS sales_2018_brl
    FROM fact_order_items foi
    INNER JOIN dim_product dp ON foi.product_key = dp.product_key
    INNER JOIN dim_date dd ON foi.purchase_date_key = dd.date_key
    WHERE foi.is_delivered = 1 AND dd.year_num IN (2017, 2018) AND dd.month_num BETWEEN 1 AND 8
    GROUP BY dp.product_category_name_english
)
SELECT
    category_en,
    sales_2017_brl,
    sales_2018_brl,
    ROUND((sales_2018_brl - sales_2017_brl) * 100.0 / NULLIF(sales_2017_brl, 0), 2) AS yoy_growth_pct
FROM cat_yoy
WHERE sales_2017_brl >= 5000
ORDER BY sales_2018_brl DESC
LIMIT 15;

-- Q4 [PRD-07] Cross-Category Co-Purchase Basket Affinity (Self-Join on Multi-Category Orders)
WITH order_cats AS (
    SELECT DISTINCT
        foi.order_id,
        dp.product_category_name_english AS category_en
    FROM fact_order_items foi
    INNER JOIN dim_product dp ON foi.product_key = dp.product_key
    WHERE foi.is_delivered = 1
),
total_baskets AS (
    SELECT COUNT(DISTINCT order_id) AS n_baskets FROM order_cats
),
cat_counts AS (
    SELECT category_en, COUNT(*) AS baskets_with_cat FROM order_cats GROUP BY category_en
)
SELECT
    a.category_en AS category_a,
    b.category_en AS category_b,
    COUNT(*) AS joint_baskets,
    ROUND(COUNT(*) * 100.0 / tb.n_baskets, 4) AS support_pct,
    ROUND(
        (COUNT(*) * 1.0 / tb.n_baskets)
        / ((ca.baskets_with_cat * 1.0 / tb.n_baskets) * (cb.baskets_with_cat * 1.0 / tb.n_baskets)),
        2
    ) AS lift
FROM order_cats a
INNER JOIN order_cats b ON a.order_id = b.order_id AND a.category_en < b.category_en
CROSS JOIN total_baskets tb
INNER JOIN cat_counts ca ON a.category_en = ca.category_en
INNER JOIN cat_counts cb ON b.category_en = cb.category_en
GROUP BY a.category_en, b.category_en, tb.n_baskets, ca.baskets_with_cat, cb.baskets_with_cat
HAVING joint_baskets >= 10
ORDER BY joint_baskets DESC
LIMIT 15;

-- Q5 [PRD-10] Top 5 Categories Monthly Seasonality (Core Period)
WITH top5 AS (
    SELECT product_category_name_english
    FROM mart_product_category_performance
    ORDER BY delivered_merchandise_brl DESC
    LIMIT 5
)
SELECT
    dd.year_month_str,
    dp.product_category_name_english AS category_en,
    SUM(foi.price) AS delivered_merch_brl
FROM fact_order_items foi
INNER JOIN dim_product dp ON foi.product_key = dp.product_key
INNER JOIN dim_date dd ON foi.purchase_date_key = dd.date_key
INNER JOIN top5 t ON dp.product_category_name_english = t.product_category_name_english
WHERE foi.is_delivered = 1 AND foi.is_core_reporting_period = 1
GROUP BY dd.year_month_str, dp.product_category_name_english
ORDER BY dd.year_month_str, delivered_merch_brl DESC;

-- Q6 [SEL-01..SEL-03] Active Sellers & Seller Sales Concentration (Top 10, Top 50, Top 10%)
WITH seller_ranked AS (
    SELECT
        seller_id,
        seller_state,
        delivered_orders,
        delivered_merchandise_brl,
        ROW_NUMBER() OVER (ORDER BY delivered_merchandise_brl DESC, seller_id) AS seller_rank,
        COUNT(*) OVER () AS total_sellers,
        SUM(delivered_merchandise_brl) OVER () AS total_market_brl
    FROM mart_seller_performance
    WHERE delivered_orders > 0
)
SELECT
    COUNT(*) AS active_delivered_sellers,
    SUM(CASE WHEN seller_rank <= 10 THEN delivered_merchandise_brl ELSE 0 END) AS top10_sellers_brl,
    ROUND(SUM(CASE WHEN seller_rank <= 10 THEN delivered_merchandise_brl ELSE 0 END) * 100.0 / MAX(total_market_brl), 2) AS top10_share_pct,
    SUM(CASE WHEN seller_rank <= 50 THEN delivered_merchandise_brl ELSE 0 END) AS top50_sellers_brl,
    ROUND(SUM(CASE WHEN seller_rank <= 50 THEN delivered_merchandise_brl ELSE 0 END) * 100.0 / MAX(total_market_brl), 2) AS top50_share_pct,
    ROUND(SUM(CASE WHEN seller_rank <= CEIL(total_sellers * 0.10) THEN delivered_merchandise_brl ELSE 0 END) * 100.0 / MAX(total_market_brl), 2) AS top10pct_share_pct
FROM seller_ranked;

-- Q7 [SEL-06..SEL-08, SEL-11, SEL-12] Composite Seller Scorecard & Intervention Tiers (Min 30 Delivered Orders)
WITH base AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY delivered_merchandise_brl ASC) AS sales_pct_rank,
        1.0 - COALESCE(late_exposure_pct, 0) / 100.0 AS on_time_reliability_proxy,
        COALESCE(avg_associated_review_score, 0) / 5.0 AS rating_norm
    FROM mart_seller_performance
    WHERE delivered_orders >= 30
)
SELECT
    seller_id,
    seller_state,
    delivered_orders,
    delivered_merchandise_brl,
    canceled_orders,
    late_exposure_pct,
    avg_associated_review_score,
    ROUND((0.40 * sales_pct_rank + 0.35 * on_time_reliability_proxy + 0.25 * rating_norm) * 100, 2) AS composite_seller_score,
    CASE
        WHEN late_exposure_pct >= 15 OR avg_associated_review_score < 3.5 THEN 'Priority Intervention'
        WHEN late_exposure_pct >= 8  OR avg_associated_review_score < 4.0 THEN 'Watchlist'
        ELSE 'High Performing'
    END AS seller_tier
FROM base
ORDER BY delivered_merchandise_brl DESC
LIMIT 25;
