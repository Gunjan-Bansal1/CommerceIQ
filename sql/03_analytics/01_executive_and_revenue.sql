-- ============================================================================
-- CommerceIQ SQL Analytics Library — 01. Executive & Commercial Performance
-- Covers: REV-01..REV-12 | KPIs: KPI-REV-01..KPI-REV-10
-- Engine: MySQL 8.0 (uses warehouse fact_orders, fact_order_items, dim_date)
-- ============================================================================

USE commerceiq;

-- Q1 [REV-01, REV-02, REV-06] Executive Commercial Baseline (All History vs Core 2017-01..2018-08)
-- Grain: Reporting scope (All vs Core) | Denominator: Eligible delivered orders with items for AOV
SELECT
    CASE WHEN is_core_reporting_period = 1 THEN 'Core (2017-01..2018-08)' ELSE 'Boundary Months' END AS period_scope,
    COUNT(*) AS total_orders,
    SUM(is_delivered) AS delivered_orders,
    SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN 1 ELSE 0 END) AS eligible_delivered_orders,
    SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN merchandise_value ELSE 0 END) AS delivered_merchandise_brl,
    SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN freight_value ELSE 0 END) AS delivered_freight_brl,
    SUM(merchandise_value) AS recorded_gmv_all_statuses_brl,
    SUM(total_payment_value) AS recorded_payment_all_statuses_brl,
    ROUND(
        SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN merchandise_value ELSE 0 END)
        / NULLIF(SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS avg_order_value_brl
FROM fact_orders
GROUP BY CASE WHEN is_core_reporting_period = 1 THEN 'Core (2017-01..2018-08)' ELSE 'Boundary Months' END;

-- Q2 [REV-03, REV-04, REV-07, REV-12] Monthly Sales Trend, MoM Growth, Running Total & Volume/AOV Decomposition
-- Grain: Calendar month (purchase_year_month) within Core Reporting Period
WITH monthly AS (
    SELECT
        purchase_year_month,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN 1 ELSE 0 END) AS delivered_orders,
        SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN item_count ELSE 0 END) AS delivered_items,
        SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN merchandise_value ELSE 0 END) AS delivered_merch_brl,
        ROUND(
            SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN merchandise_value ELSE 0 END)
            / NULLIF(SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN 1 ELSE 0 END), 0),
            2
        ) AS aov_brl
    FROM fact_orders
    WHERE is_core_reporting_period = 1
    GROUP BY purchase_year_month
),
with_lag AS (
    SELECT
        *,
        LAG(delivered_merch_brl) OVER (ORDER BY purchase_year_month) AS prev_merch_brl,
        LAG(delivered_orders) OVER (ORDER BY purchase_year_month) AS prev_orders,
        LAG(aov_brl) OVER (ORDER BY purchase_year_month) AS prev_aov_brl,
        SUM(delivered_merch_brl) OVER (ORDER BY purchase_year_month) AS cumulative_merch_brl,
        ROUND(AVG(delivered_merch_brl) OVER (ORDER BY purchase_year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3m_avg_merch_brl,
        DENSE_RANK() OVER (ORDER BY delivered_merch_brl DESC) AS sales_month_rank
    FROM monthly
)
SELECT
    purchase_year_month,
    total_orders,
    delivered_orders,
    delivered_items,
    delivered_merch_brl,
    aov_brl,
    ROUND((delivered_merch_brl - prev_merch_brl) * 100.0 / NULLIF(prev_merch_brl, 0), 2) AS mom_sales_growth_pct,
    ROUND((delivered_orders - prev_orders) * 100.0 / NULLIF(prev_orders, 0), 2) AS mom_volume_growth_pct,
    ROUND((aov_brl - prev_aov_brl) * 100.0 / NULLIF(prev_aov_brl, 0), 2) AS mom_aov_growth_pct,
    cumulative_merch_brl,
    rolling_3m_avg_merch_brl,
    sales_month_rank
FROM with_lag
ORDER BY purchase_year_month;

-- Q3 [REV-05] Comparable Year-over-Year Growth (Jan-Aug 2017 vs Jan-Aug 2018)
-- Grain: Calendar month (1..8) comparing full comparable months in 2017 vs 2018
WITH ym AS (
    SELECT
        dd.year_num,
        dd.month_num,
        dd.month_name,
        SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN 1 ELSE 0 END) AS delivered_orders,
        SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END) AS delivered_merch_brl
    FROM fact_orders fo
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE dd.year_num IN (2017, 2018) AND dd.month_num BETWEEN 1 AND 8
    GROUP BY dd.year_num, dd.month_num, dd.month_name
)
SELECT
    y17.month_num,
    y17.month_name,
    y17.delivered_orders AS orders_2017,
    y18.delivered_orders AS orders_2018,
    ROUND((y18.delivered_orders - y17.delivered_orders) * 100.0 / NULLIF(y17.delivered_orders, 0), 2) AS yoy_order_growth_pct,
    y17.delivered_merch_brl AS merch_2017_brl,
    y18.delivered_merch_brl AS merch_2018_brl,
    ROUND((y18.delivered_merch_brl - y17.delivered_merch_brl) * 100.0 / NULLIF(y17.delivered_merch_brl, 0), 2) AS yoy_merch_growth_pct
FROM ym y17
INNER JOIN ym y18 ON y17.month_num = y18.month_num AND y17.year_num = 2017 AND y18.year_num = 2018
ORDER BY y17.month_num;

-- Q4 [REV-08, REV-09] Demand by Weekday and Hour of Day
-- Grain: Weekday (Mon=1..Sun=7) and Hour (0..23)
SELECT
    dd.day_of_week,
    dd.day_name,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN fo.is_delivered = 1 AND fo.has_order_items = 1 THEN fo.merchandise_value ELSE 0 END) AS delivered_merch_brl,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_of_orders_pct
FROM fact_orders fo
INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
GROUP BY dd.day_of_week, dd.day_name
ORDER BY dd.day_of_week;

SELECT
    purchase_hour,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN is_delivered = 1 AND has_order_items = 1 THEN merchandise_value ELSE 0 END) AS delivered_merch_brl,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_of_orders_pct
FROM fact_orders
GROUP BY purchase_hour
ORDER BY purchase_hour;

-- Q5 [REV-10] Top Category Sales Concentration
-- Grain: English product category | Denominator: Total delivered merchandise value
WITH cat AS (
    SELECT
        dp.product_category_name_english AS category_en,
        COUNT(*) AS delivered_items,
        SUM(foi.price) AS delivered_merch_brl
    FROM fact_order_items foi
    INNER JOIN dim_product dp ON foi.product_key = dp.product_key
    WHERE foi.is_delivered = 1
    GROUP BY dp.product_category_name_english
)
SELECT
    category_en,
    delivered_items,
    delivered_merch_brl,
    ROUND(delivered_merch_brl * 100.0 / SUM(delivered_merch_brl) OVER (), 2) AS share_pct,
    ROUND(SUM(delivered_merch_brl) OVER (ORDER BY delivered_merch_brl DESC) * 100.0 / SUM(delivered_merch_brl) OVER (), 2) AS cumulative_share_pct
FROM cat
ORDER BY delivered_merch_brl DESC
LIMIT 15;

-- Q6 [REV-11] Order-Level Merchandise+Freight vs Payment Reconciliation by Order Status
-- Grain: Order status
SELECT
    order_status,
    COUNT(*) AS order_count,
    SUM(merchandise_value) AS merch_brl,
    SUM(freight_value) AS freight_brl,
    SUM(item_total_value) AS item_plus_freight_brl,
    SUM(total_payment_value) AS recorded_payment_brl,
    SUM(payment_discrepancy_brl) AS net_payment_minus_item_brl,
    SUM(CASE WHEN ABS(payment_discrepancy_brl) > 0.05 THEN 1 ELSE 0 END) AS orders_with_diff_gt_5cents
FROM fact_orders
GROUP BY order_status
ORDER BY order_count DESC;
