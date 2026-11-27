-- ============================================================================
-- CommerceIQ Data Warehouse Reconciliation Queries
-- ============================================================================

USE commerceiq;

-- 1. Dimension and Fact row counts
SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
UNION ALL SELECT 'dim_geography', COUNT(*) FROM dim_geography
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_seller', COUNT(*) FROM dim_seller
UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL SELECT 'dim_payment_type', COUNT(*) FROM dim_payment_type
UNION ALL SELECT 'dim_marketing_channel', COUNT(*) FROM dim_marketing_channel
UNION ALL SELECT 'fact_orders', COUNT(*) FROM fact_orders
UNION ALL SELECT 'fact_order_items', COUNT(*) FROM fact_order_items
UNION ALL SELECT 'fact_payments', COUNT(*) FROM fact_payments
UNION ALL SELECT 'fact_reviews', COUNT(*) FROM fact_reviews
UNION ALL SELECT 'fact_marketing_funnel', COUNT(*) FROM fact_marketing_funnel;

-- 2. Exact financial & KPI reconciliation between operational DB and warehouse
SELECT
    (SELECT SUM(merchandise_value) FROM fact_orders) AS fact_orders_merch_brl,
    (SELECT SUM(price) FROM fact_order_items) AS fact_items_merch_brl,
    (SELECT SUM(price) FROM order_items) AS ops_items_merch_brl,
    (SELECT SUM(freight_value) FROM fact_orders) AS fact_orders_freight_brl,
    (SELECT SUM(freight_value) FROM fact_order_items) AS fact_items_freight_brl,
    (SELECT SUM(total_payment_value) FROM fact_orders) AS fact_orders_payment_brl,
    (SELECT SUM(payment_value) FROM fact_payments) AS fact_payments_brl,
    (SELECT SUM(payment_value) FROM payments) AS ops_payments_brl,
    (SELECT SUM(declared_monthly_revenue) FROM fact_marketing_funnel) AS fact_mkt_declared_rev_brl;

-- 3. Mart cross-check (mart_executive_monthly vs fact_orders)
SELECT
    (SELECT SUM(total_orders) FROM mart_executive_monthly) AS mart_total_orders,
    (SELECT COUNT(*) FROM fact_orders) AS fact_total_orders,
    (SELECT SUM(recorded_gmv_brl) FROM mart_executive_monthly) AS mart_gmv_brl,
    (SELECT SUM(merchandise_value) FROM fact_orders) AS fact_gmv_brl;
