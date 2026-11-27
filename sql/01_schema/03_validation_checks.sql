-- ============================================================================
-- CommerceIQ Operational Database Validation Checks (MySQL 8.0)
-- ============================================================================

USE commerceiq;

-- 1. Row count reconciliation across all 13 tables
SELECT 'category_translation' AS table_name, COUNT(*) AS row_count FROM category_translation
UNION ALL SELECT 'geolocation_lookup', COUNT(*) FROM geolocation_lookup
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'brazil_holidays', COUNT(*) FROM brazil_holidays
UNION ALL SELECT 'marketing_leads', COUNT(*) FROM marketing_leads
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'closed_deals', COUNT(*) FROM closed_deals;

-- 2. Required relationship integrity (all 8 must return 0 orphan rows)
SELECT 'orders->customers' AS relationship, COUNT(*) AS orphan_rows
FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL
UNION ALL
SELECT 'order_items->orders', COUNT(*)
FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'order_items->products', COUNT(*)
FROM order_items oi LEFT JOIN products p ON oi.product_id = p.product_id WHERE p.product_id IS NULL
UNION ALL
SELECT 'order_items->sellers', COUNT(*)
FROM order_items oi LEFT JOIN sellers s ON oi.seller_id = s.seller_id WHERE s.seller_id IS NULL
UNION ALL
SELECT 'payments->orders', COUNT(*)
FROM payments p LEFT JOIN orders o ON p.order_id = o.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'reviews->orders', COUNT(*)
FROM reviews r LEFT JOIN orders o ON r.order_id = o.order_id WHERE o.order_id IS NULL
UNION ALL
SELECT 'products->category_translation', COUNT(*)
FROM products p LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name WHERE ct.product_category_name IS NULL
UNION ALL
SELECT 'closed_deals->marketing_leads', COUNT(*)
FROM closed_deals cd LEFT JOIN marketing_leads ml ON cd.mql_id = ml.mql_id WHERE ml.mql_id IS NULL;

-- 3. Optional relationship gap preservation check
SELECT 'customers->geolocation_lookup_unmatched' AS gap_check, COUNT(*) AS unmatched_rows
FROM customers c LEFT JOIN geolocation_lookup g ON c.customer_zip_code_prefix = g.zip_code_prefix WHERE g.zip_code_prefix IS NULL
UNION ALL
SELECT 'sellers->geolocation_lookup_unmatched', COUNT(*)
FROM sellers s LEFT JOIN geolocation_lookup g ON s.seller_zip_code_prefix = g.zip_code_prefix WHERE g.zip_code_prefix IS NULL
UNION ALL
SELECT 'closed_deals->sellers_unmatched', COUNT(*)
FROM closed_deals cd LEFT JOIN sellers s ON cd.seller_id = s.seller_id WHERE s.seller_id IS NULL;

-- 4. Financial totals reconciliation (exact DECIMAL precision)
SELECT
    (SELECT SUM(price) FROM order_items) AS recorded_merchandise_brl,
    (SELECT SUM(freight_value) FROM order_items) AS recorded_freight_brl,
    (SELECT SUM(item_value_with_freight) FROM order_items) AS recorded_item_total_brl,
    (SELECT SUM(payment_value) FROM payments) AS recorded_payment_brl,
    (SELECT SUM(declared_monthly_revenue) FROM closed_deals) AS declared_monthly_revenue_brl;

-- 5. Postal code leading-zero & nullable boolean / UTF-8 sanity checks
SELECT
    (SELECT COUNT(*) FROM customers WHERE CHAR_LENGTH(customer_zip_code_prefix) <> 5) AS bad_cust_zip_len,
    (SELECT COUNT(*) FROM sellers WHERE CHAR_LENGTH(seller_zip_code_prefix) <> 5) AS bad_seller_zip_len,
    (SELECT COUNT(*) FROM geolocation_lookup WHERE zip_code_prefix LIKE '0%') AS zero_prefixed_zips,
    (SELECT COUNT(*) FROM closed_deals WHERE has_company IS NULL) AS null_has_company_deals,
    (SELECT COUNT(*) FROM reviews WHERE review_comment_message LIKE '%ã%' OR review_comment_message LIKE '%ç%') AS portuguese_diacritic_reviews;
