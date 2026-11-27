-- ============================================================================
-- CommerceIQ SQL Analytics Library — 03. Customer Intelligence & Cohorts
-- Covers: CUS-01..CUS-14 | KPIs: KPI-CUS-01..KPI-CUS-10
-- Rule: Uses persistent `customer_unique_id` for all customer-level metrics.
-- ============================================================================

USE commerceiq;

-- Q1 [CUS-01..CUS-06] Persistent Customer Summary & Repeat Purchase Rate (Eligible Delivered Orders)
-- Grain: Marketplace customer population (customer_unique_id)
WITH cust_delivered AS (
    SELECT
        dc.customer_unique_id,
        COUNT(*) AS delivered_orders,
        SUM(fo.merchandise_value) AS delivered_merch_brl,
        MIN(dd.full_date) AS first_purchase_date,
        MAX(dd.full_date) AS last_purchase_date
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
    GROUP BY dc.customer_unique_id
)
SELECT
    COUNT(*) AS unique_delivered_customers,
    SUM(delivered_orders) AS total_delivered_orders,
    SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 4) AS repeat_purchase_rate_pct,
    ROUND(SUM(delivered_orders) * 1.0 / COUNT(*), 4) AS avg_purchase_frequency,
    ROUND(AVG(delivered_merch_brl), 2) AS avg_observed_spend_brl,
    ROUND(MAX(delivered_merch_brl), 2) AS max_observed_spend_brl
FROM cust_delivered;

-- Q2 [CUS-04] Monthly First-Time Observed Purchasers vs Repeat Purchasers (Core Period)
WITH first_buy AS (
    SELECT
        dc.customer_unique_id,
        MIN(dd.full_date) AS first_date
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
    GROUP BY dc.customer_unique_id
)
SELECT
    fo.purchase_year_month,
    COUNT(DISTINCT dc.customer_unique_id) AS active_customers,
    COUNT(DISTINCT CASE WHEN dd.full_date = fb.first_date THEN dc.customer_unique_id END) AS new_observed_customers,
    COUNT(DISTINCT CASE WHEN dd.full_date > fb.first_date THEN dc.customer_unique_id END) AS returning_customers
FROM fact_orders fo
INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
INNER JOIN first_buy fb ON dc.customer_unique_id = fb.customer_unique_id
WHERE fo.is_core_reporting_period = 1 AND fo.is_delivered = 1 AND fo.has_order_items = 1
GROUP BY fo.purchase_year_month
ORDER BY fo.purchase_year_month;

-- Q3 [CUS-07, CUS-08] Top 10% Customer Sales Concentration (NTILE(10) Pareto)
WITH cust_spend AS (
    SELECT
        dc.customer_unique_id,
        SUM(fo.merchandise_value) AS total_spend_brl,
        COUNT(*) AS delivered_orders
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
    GROUP BY dc.customer_unique_id
),
deciles AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY total_spend_brl DESC) AS spend_decile
    FROM cust_spend
)
SELECT
    spend_decile,
    COUNT(*) AS customers,
    SUM(delivered_orders) AS orders,
    SUM(total_spend_brl) AS segment_spend_brl,
    ROUND(SUM(total_spend_brl) * 100.0 / SUM(SUM(total_spend_brl)) OVER (), 2) AS share_of_sales_pct
FROM deciles
GROUP BY spend_decile
ORDER BY spend_decile;

-- Q4 [CUS-09] Interpurchase Duration Among Repeat Customers (LAG)
WITH ordered_buys AS (
    SELECT
        dc.customer_unique_id,
        dd.full_date AS purchase_date,
        LAG(dd.full_date) OVER (PARTITION BY dc.customer_unique_id ORDER BY dd.full_date, fo.order_id) AS prev_purchase_date
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
)
SELECT
    COUNT(*) AS repeat_purchase_intervals,
    ROUND(AVG(DATEDIFF(purchase_date, prev_purchase_date)), 2) AS mean_interpurchase_days,
    MIN(DATEDIFF(purchase_date, prev_purchase_date)) AS min_days,
    MAX(DATEDIFF(purchase_date, prev_purchase_date)) AS max_days
FROM ordered_buys
WHERE prev_purchase_date IS NOT NULL;

-- Q5 [CUS-10, CUS-11, CUS-12] Observable 30-Day & 90-Day Cohort Retention (Capped at 2018-08-31 Max Observation Date)
-- Note: Only cohorts with >= 90 days of follow-up (first purchase <= 2018-06-02) are eligible for 90-day retention!
WITH cust_orders AS (
    SELECT
        dc.customer_unique_id,
        dd.full_date AS purchase_date,
        DATE_FORMAT(dd.full_date, '%Y-%m') AS purchase_ym
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
),
first_order AS (
    SELECT
        customer_unique_id,
        MIN(purchase_date) AS cohort_first_date,
        DATE_FORMAT(MIN(purchase_date), '%Y-%m') AS cohort_ym
    FROM cust_orders
    GROUP BY customer_unique_id
),
cohort_activity AS (
    SELECT
        fo.customer_unique_id,
        fo.cohort_ym,
        fo.cohort_first_date,
        MAX(CASE WHEN DATEDIFF(co.purchase_date, fo.cohort_first_date) BETWEEN 1 AND 30 THEN 1 ELSE 0 END) AS retained_30d,
        MAX(CASE WHEN DATEDIFF(co.purchase_date, fo.cohort_first_date) BETWEEN 1 AND 90 THEN 1 ELSE 0 END) AS retained_90d
    FROM first_order fo
    INNER JOIN cust_orders co ON fo.customer_unique_id = co.customer_unique_id
    GROUP BY fo.customer_unique_id, fo.cohort_ym, fo.cohort_first_date
)
SELECT
    cohort_ym,
    COUNT(*) AS cohort_size,
    SUM(CASE WHEN cohort_first_date <= DATE('2018-08-01') THEN 1 ELSE 0 END) AS eligible_30d_window,
    SUM(CASE WHEN cohort_first_date <= DATE('2018-08-01') THEN retained_30d ELSE 0 END) AS retained_30d_customers,
    ROUND(
        SUM(CASE WHEN cohort_first_date <= DATE('2018-08-01') THEN retained_30d ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN cohort_first_date <= DATE('2018-08-01') THEN 1 ELSE 0 END), 0),
        2
    ) AS retention_30d_pct,
    SUM(CASE WHEN cohort_first_date <= DATE('2018-06-02') THEN 1 ELSE 0 END) AS eligible_90d_window,
    SUM(CASE WHEN cohort_first_date <= DATE('2018-06-02') THEN retained_90d ELSE 0 END) AS retained_90d_customers,
    ROUND(
        SUM(CASE WHEN cohort_first_date <= DATE('2018-06-02') THEN retained_90d ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN cohort_first_date <= DATE('2018-06-02') THEN 1 ELSE 0 END), 0),
        2
    ) AS retention_90d_pct
FROM cohort_activity
WHERE cohort_ym BETWEEN '2017-01' AND '2018-08'
GROUP BY cohort_ym
ORDER BY cohort_ym;

-- Q6 [CUS-13] SQL RFM Segmentation Baseline (Reference Date = 2018-09-01)
WITH rfm_raw AS (
    SELECT
        dc.customer_unique_id,
        DATEDIFF(DATE('2018-09-01'), MAX(dd.full_date)) AS recency_days,
        COUNT(*) AS frequency_orders,
        SUM(fo.merchandise_value) AS monetary_brl
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1
    GROUP BY dc.customer_unique_id
),
rfm_scores AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        CASE WHEN frequency_orders >= 3 THEN 5 WHEN frequency_orders = 2 THEN 3 ELSE 1 END AS f_score,
        NTILE(5) OVER (ORDER BY monetary_brl ASC) AS m_score
    FROM rfm_raw
),
rfm_segments AS (
    SELECT
        *,
        CASE
            WHEN f_score >= 3 AND r_score >= 4 AND m_score >= 4 THEN 'Champions (Repeat High-Value)'
            WHEN f_score >= 3 THEN 'Loyal Repeat Buyers'
            WHEN r_score >= 4 AND m_score >= 4 THEN 'Recent High-Spend Single Buyers'
            WHEN r_score >= 4 THEN 'Recent Single Buyers'
            WHEN r_score <= 2 AND m_score >= 4 THEN 'At-Risk High-Spend'
            ELSE 'Dormant / Low-Engagement'
        END AS rfm_segment
    FROM rfm_scores
)
SELECT
    rfm_segment,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency_orders), 3) AS avg_frequency,
    ROUND(AVG(monetary_brl), 2) AS avg_monetary_brl,
    SUM(monetary_brl) AS total_monetary_brl
FROM rfm_segments
GROUP BY rfm_segment
ORDER BY total_monetary_brl DESC;

-- Q7 [CUS-14] First-Order Delivery Experience vs Subsequent Repeat Buying
WITH first_orders AS (
    SELECT
        dc.customer_unique_id,
        fo.delivery_performance,
        ROW_NUMBER() OVER (PARTITION BY dc.customer_unique_id ORDER BY dd.full_date, fo.order_id) AS rn,
        COUNT(*) OVER (PARTITION BY dc.customer_unique_id) AS lifetime_delivered_orders
    FROM fact_orders fo
    INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
    INNER JOIN dim_date dd ON fo.purchase_date_key = dd.date_key
    WHERE fo.is_delivered = 1 AND fo.has_order_items = 1 AND fo.is_valid_delivery_promise_comparison = 1
)
SELECT
    delivery_performance AS first_order_delivery_outcome,
    COUNT(*) AS customers,
    SUM(CASE WHEN lifetime_delivered_orders >= 2 THEN 1 ELSE 0 END) AS went_on_to_repeat,
    ROUND(SUM(CASE WHEN lifetime_delivered_orders >= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 3) AS subsequent_repeat_rate_pct
FROM first_orders
WHERE rn = 1
GROUP BY delivery_performance
ORDER BY customers DESC;
