-- ============================================================================
-- CommerceIQ Analytical Data Warehouse ETL Load (MySQL 8.0)
-- Loads 7 dimensions first, then 5 fact tables in topological dependency order.
-- ============================================================================

USE commerceiq;

SET @@cte_max_recursion_depth = 2500;

-- ----------------------------------------------------------------------------
-- 1. dim_date (Unknown member -1 + calendar 2016-01-01 to 2020-12-31)
-- ----------------------------------------------------------------------------
INSERT INTO dim_date (
    date_key, full_date, year_num, quarter_num, year_quarter, month_num,
    month_name, year_month_str, day_of_month, day_of_week, day_name, is_weekend,
    is_core_reporting_period, is_brazil_national_holiday, is_brazil_any_holiday,
    holiday_name, holiday_local_name
) VALUES (
    -1, NULL, NULL, NULL, NULL, NULL,
    'Unknown', NULL, NULL, NULL, 'Unknown', 0,
    0, 0, 0, NULL, NULL
);

INSERT INTO dim_date (
    date_key, full_date, year_num, quarter_num, year_quarter, month_num,
    month_name, year_month_str, day_of_month, day_of_week, day_name, is_weekend,
    is_core_reporting_period, is_brazil_national_holiday, is_brazil_any_holiday,
    holiday_name, holiday_local_name
)
WITH RECURSIVE cal AS (
    SELECT DATE('2016-01-01') AS d
    UNION ALL
    SELECT DATE_ADD(d, INTERVAL 1 DAY) FROM cal WHERE d < DATE('2020-12-31')
)
SELECT
    CAST(DATE_FORMAT(c.d, '%Y%m%d') AS SIGNED) AS date_key,
    c.d AS full_date,
    YEAR(c.d) AS year_num,
    QUARTER(c.d) AS quarter_num,
    CONCAT(YEAR(c.d), '-Q', QUARTER(c.d)) AS year_quarter,
    MONTH(c.d) AS month_num,
    DATE_FORMAT(c.d, '%M') AS month_name,
    DATE_FORMAT(c.d, '%Y-%m') AS year_month_str,
    DAY(c.d) AS day_of_month,
    ((DAYOFWEEK(c.d) + 5) % 7) + 1 AS day_of_week,
    DATE_FORMAT(c.d, '%W') AS day_name,
    CASE WHEN DAYOFWEEK(c.d) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend,
    CASE WHEN c.d BETWEEN DATE('2017-01-01') AND DATE('2018-08-31') THEN 1 ELSE 0 END AS is_core_reporting_period,
    CASE WHEN bh.date IS NOT NULL AND bh.is_global = 1 THEN 1 ELSE 0 END AS is_brazil_national_holiday,
    CASE WHEN bh.date IS NOT NULL THEN 1 ELSE 0 END AS is_brazil_any_holiday,
    bh.name AS holiday_name,
    bh.local_name AS holiday_local_name
FROM cal c
LEFT JOIN brazil_holidays bh
    ON c.d = bh.date AND bh.country_code = 'BR';

-- ----------------------------------------------------------------------------
-- 2. dim_geography (Unknown member -1 + 19,011 cleaned postal prefixes)
-- ----------------------------------------------------------------------------
INSERT INTO dim_geography (
    geo_key, zip_code_prefix, city, state, region, latitude, longitude,
    is_ambiguous_zip, dominant_location_pct, has_geolocation_match
) VALUES (
    -1, '00000', 'unknown', 'NA', 'Unknown', NULL, NULL, 0, NULL, 0
);

INSERT INTO dim_geography (
    zip_code_prefix, city, state, region, latitude, longitude,
    is_ambiguous_zip, dominant_location_pct, has_geolocation_match
)
SELECT
    gl.zip_code_prefix,
    gl.city,
    gl.state,
    CASE
        WHEN gl.state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN gl.state IN ('PR', 'SC', 'RS') THEN 'South'
        WHEN gl.state IN ('BA', 'PE', 'CE', 'RN', 'PB', 'AL', 'SE', 'PI', 'MA') THEN 'Northeast'
        WHEN gl.state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West'
        WHEN gl.state IN ('AM', 'PA', 'RO', 'RR', 'AC', 'AP', 'TO') THEN 'North'
        ELSE 'Unknown'
    END AS region,
    gl.latitude,
    gl.longitude,
    gl.is_ambiguous_zip,
    gl.dominant_location_pct,
    1 AS has_geolocation_match
FROM geolocation_lookup gl
ORDER BY gl.zip_code_prefix;

-- ----------------------------------------------------------------------------
-- 3. dim_customer (99,441 rows; preserves customer_unique_id & order seq)
-- ----------------------------------------------------------------------------
INSERT INTO dim_customer (
    customer_id, customer_unique_id, customer_zip_code_prefix, customer_city,
    customer_state, customer_region, geo_key, has_geolocation_match,
    customer_order_seq, customer_lifetime_orders, is_repeat_customer
)
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    CASE
        WHEN c.customer_state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN c.customer_state IN ('PR', 'SC', 'RS') THEN 'South'
        WHEN c.customer_state IN ('BA', 'PE', 'CE', 'RN', 'PB', 'AL', 'SE', 'PI', 'MA') THEN 'Northeast'
        WHEN c.customer_state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West'
        WHEN c.customer_state IN ('AM', 'PA', 'RO', 'RR', 'AC', 'AP', 'TO') THEN 'North'
        ELSE 'Unknown'
    END AS customer_region,
    COALESCE(dg.geo_key, -1) AS geo_key,
    c.has_geolocation_match,
    ROW_NUMBER() OVER (
        PARTITION BY c.customer_unique_id
        ORDER BY o.order_purchase_timestamp, c.customer_id
    ) AS customer_order_seq,
    COUNT(*) OVER (PARTITION BY c.customer_unique_id) AS customer_lifetime_orders,
    CASE WHEN COUNT(*) OVER (PARTITION BY c.customer_unique_id) >= 2 THEN 1 ELSE 0 END AS is_repeat_customer
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN dim_geography dg ON c.customer_zip_code_prefix = dg.zip_code_prefix;

-- ----------------------------------------------------------------------------
-- 4. dim_seller (Unknown member -1 + 3,095 sellers)
-- ----------------------------------------------------------------------------
INSERT INTO dim_seller (
    seller_key, seller_id, seller_zip_code_prefix, seller_city, seller_state,
    seller_region, geo_key, has_geolocation_match, has_recorded_marketing_deal,
    marketing_origin, business_segment, lead_type, business_type
) VALUES (
    -1, 'UNKNOWN', '00000', 'unknown', 'NA',
    'Unknown', -1, 0, 0, NULL, NULL, NULL, NULL
);

INSERT INTO dim_seller (
    seller_id, seller_zip_code_prefix, seller_city, seller_state,
    seller_region, geo_key, has_geolocation_match, has_recorded_marketing_deal,
    marketing_origin, business_segment, lead_type, business_type
)
SELECT
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    CASE
        WHEN s.seller_state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN s.seller_state IN ('PR', 'SC', 'RS') THEN 'South'
        WHEN s.seller_state IN ('BA', 'PE', 'CE', 'RN', 'PB', 'AL', 'SE', 'PI', 'MA') THEN 'Northeast'
        WHEN s.seller_state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West'
        WHEN s.seller_state IN ('AM', 'PA', 'RO', 'RR', 'AC', 'AP', 'TO') THEN 'North'
        ELSE 'Unknown'
    END AS seller_region,
    COALESCE(dg.geo_key, -1) AS geo_key,
    s.has_geolocation_match,
    s.has_recorded_marketing_deal,
    cd_mkt.origin AS marketing_origin,
    cd_mkt.business_segment,
    cd_mkt.lead_type,
    cd_mkt.business_type
FROM sellers s
LEFT JOIN dim_geography dg ON s.seller_zip_code_prefix = dg.zip_code_prefix
LEFT JOIN (
    SELECT
        cd.seller_id,
        MIN(ml.origin) AS origin,
        MIN(cd.business_segment) AS business_segment,
        MIN(cd.lead_type) AS lead_type,
        MIN(cd.business_type) AS business_type
    FROM closed_deals cd
    INNER JOIN marketing_leads ml ON cd.mql_id = ml.mql_id
    WHERE cd.has_marketplace_seller_match = 1
    GROUP BY cd.seller_id
) cd_mkt ON s.seller_id = cd_mkt.seller_id;

-- ----------------------------------------------------------------------------
-- 5. dim_product (32,951 products)
-- ----------------------------------------------------------------------------
INSERT INTO dim_product (
    product_id, product_category_name, product_category_name_english,
    product_name_length, product_description_length, product_photos_qty,
    product_weight_g, product_length_cm, product_height_cm, product_width_cm,
    product_volume_cm3, product_density_g_cm3
)
SELECT
    p.product_id,
    p.product_category_name,
    ct.product_category_name_english,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    p.product_volume_cm3,
    p.product_density_g_cm3
FROM products p
INNER JOIN category_translation ct
    ON p.product_category_name = ct.product_category_name;

-- ----------------------------------------------------------------------------
-- 6. dim_payment_type
-- ----------------------------------------------------------------------------
INSERT INTO dim_payment_type (payment_type, payment_group, is_defined_payment_type)
SELECT DISTINCT
    p.payment_type,
    CASE
        WHEN p.payment_type = 'credit_card' THEN 'Card'
        WHEN p.payment_type = 'debit_card'  THEN 'Card'
        WHEN p.payment_type = 'boleto'      THEN 'Bank Slip'
        WHEN p.payment_type = 'voucher'     THEN 'Voucher'
        ELSE 'Other / Undefined'
    END AS payment_group,
    CASE WHEN p.payment_type = 'not_defined' THEN 0 ELSE 1 END AS is_defined_payment_type
FROM payments p
ORDER BY p.payment_type;

-- ----------------------------------------------------------------------------
-- 7. dim_marketing_channel
-- ----------------------------------------------------------------------------
INSERT INTO dim_marketing_channel (origin, channel_group, is_recorded_origin)
SELECT DISTINCT
    ml.origin,
    CASE
        WHEN ml.origin IN ('organic_search', 'direct_traffic') THEN 'Organic / Direct'
        WHEN ml.origin IN ('paid_search', 'display', 'social') THEN 'Paid / Social'
        WHEN ml.origin IN ('referral', 'email', 'other_publicities', 'other') THEN 'Referral / Other'
        WHEN ml.origin = 'not_recorded' THEN 'Unrecorded'
        ELSE 'Other'
    END AS channel_group,
    CASE WHEN ml.origin = 'not_recorded' THEN 0 ELSE 1 END AS is_recorded_origin
FROM marketing_leads ml
ORDER BY ml.origin;

-- ----------------------------------------------------------------------------
-- 8. fact_orders (99,441 rows — pre-aggregated items, payments, reviews)
-- ----------------------------------------------------------------------------
INSERT INTO fact_orders (
    order_id, customer_key, customer_geo_key, purchase_date_key, delivered_date_key,
    estimated_date_key, order_status, is_delivered, is_canceled, is_unavailable,
    is_unsuccessful, is_core_reporting_period, purchase_year_month, purchase_hour,
    has_order_items, has_payment_records, has_review_records,
    item_count, distinct_products, distinct_sellers,
    merchandise_value, freight_value, item_total_value,
    payment_record_count, total_payment_value, max_installments, primary_payment_type,
    payment_discrepancy_brl,
    review_count, avg_review_score, min_review_score, has_written_review,
    approval_duration_hours, processing_duration_days, transit_duration_days,
    delivery_duration_days, estimated_delivery_days, delivery_deviation_days,
    is_valid_delivery_promise_comparison, is_on_time_delivery, delivery_performance
)
WITH agg_items AS (
    SELECT
        oi.order_id,
        COUNT(*) AS item_count,
        COUNT(DISTINCT oi.product_id) AS distinct_products,
        COUNT(DISTINCT oi.seller_id) AS distinct_sellers,
        SUM(oi.price) AS merchandise_value,
        SUM(oi.freight_value) AS freight_value,
        SUM(oi.item_value_with_freight) AS item_total_value
    FROM order_items oi
    GROUP BY oi.order_id
),
agg_payments AS (
    SELECT
        p.order_id,
        COUNT(*) AS payment_record_count,
        SUM(p.payment_value) AS total_payment_value,
        MAX(p.payment_installments) AS max_installments,
        COALESCE(
            MIN(CASE WHEN p.payment_sequential = 1 THEN p.payment_type END),
            MAX(p.payment_type)
        ) AS primary_payment_type
    FROM payments p
    GROUP BY p.order_id
),
agg_reviews AS (
    SELECT
        r.order_id,
        COUNT(*) AS review_count,
        AVG(r.review_score) AS avg_review_score,
        MIN(r.review_score) AS min_review_score,
        MAX(r.has_written_review) AS has_written_review
    FROM reviews r
    GROUP BY r.order_id
)
SELECT
    o.order_id,
    dc.customer_key,
    dc.geo_key AS customer_geo_key,
    CAST(DATE_FORMAT(o.purchase_date, '%Y%m%d') AS SIGNED) AS purchase_date_key,
    COALESCE(CAST(DATE_FORMAT(o.order_delivered_customer_date, '%Y%m%d') AS SIGNED), -1) AS delivered_date_key,
    CAST(DATE_FORMAT(o.order_estimated_delivery_date, '%Y%m%d') AS SIGNED) AS estimated_date_key,
    o.order_status,
    CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END AS is_delivered,
    CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END AS is_canceled,
    CASE WHEN o.order_status = 'unavailable' THEN 1 ELSE 0 END AS is_unavailable,
    CASE WHEN o.order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS is_unsuccessful,
    o.is_core_reporting_period,
    o.purchase_year_month,
    o.purchase_hour,
    o.has_order_items,
    o.has_payment_records,
    o.has_review_records,
    COALESCE(ai.item_count, 0) AS item_count,
    COALESCE(ai.distinct_products, 0) AS distinct_products,
    COALESCE(ai.distinct_sellers, 0) AS distinct_sellers,
    COALESCE(ai.merchandise_value, 0.00) AS merchandise_value,
    COALESCE(ai.freight_value, 0.00) AS freight_value,
    COALESCE(ai.item_total_value, 0.00) AS item_total_value,
    COALESCE(ap.payment_record_count, 0) AS payment_record_count,
    COALESCE(ap.total_payment_value, 0.00) AS total_payment_value,
    COALESCE(ap.max_installments, 0) AS max_installments,
    ap.primary_payment_type,
    COALESCE(ap.total_payment_value, 0.00) - COALESCE(ai.item_total_value, 0.00) AS payment_discrepancy_brl,
    COALESCE(ar.review_count, 0) AS review_count,
    ar.avg_review_score,
    ar.min_review_score,
    COALESCE(ar.has_written_review, 0) AS has_written_review,
    o.approval_duration_hours,
    o.processing_duration_days,
    o.transit_duration_days,
    o.delivery_duration_days,
    o.estimated_delivery_days,
    o.delivery_deviation_days,
    o.is_valid_delivery_promise_comparison,
    o.is_on_time_delivery,
    o.delivery_performance
FROM orders o
INNER JOIN dim_customer dc ON o.customer_id = dc.customer_id
LEFT JOIN agg_items ai ON o.order_id = ai.order_id
LEFT JOIN agg_payments ap ON o.order_id = ap.order_id
LEFT JOIN agg_reviews ar ON o.order_id = ar.order_id;

-- ----------------------------------------------------------------------------
-- 9. fact_order_items (112,650 rows)
-- ----------------------------------------------------------------------------
INSERT INTO fact_order_items (
    order_id, order_item_id, order_key, customer_key, product_key, seller_key,
    purchase_date_key, shipping_limit_date, order_status, is_delivered,
    is_core_reporting_period, price, freight_value, item_value_with_freight,
    freight_to_price_pct, freight_share_of_item_total_pct, is_same_state_fulfillment
)
SELECT
    oi.order_id,
    oi.order_item_id,
    fo.order_key,
    fo.customer_key,
    dp.product_key,
    ds.seller_key,
    fo.purchase_date_key,
    oi.shipping_limit_date,
    fo.order_status,
    fo.is_delivered,
    fo.is_core_reporting_period,
    oi.price,
    oi.freight_value,
    oi.item_value_with_freight,
    oi.freight_to_price_pct,
    oi.freight_share_of_item_total_pct,
    CASE WHEN dc.customer_state = ds.seller_state THEN 1 ELSE 0 END AS is_same_state_fulfillment
FROM order_items oi
INNER JOIN fact_orders fo ON oi.order_id = fo.order_id
INNER JOIN dim_customer dc ON fo.customer_key = dc.customer_key
INNER JOIN dim_product dp ON oi.product_id = dp.product_id
INNER JOIN dim_seller ds ON oi.seller_id = ds.seller_id;

-- ----------------------------------------------------------------------------
-- 10. fact_payments (103,886 rows)
-- ----------------------------------------------------------------------------
INSERT INTO fact_payments (
    order_id, payment_sequential, order_key, customer_key, payment_type_key,
    purchase_date_key, order_status, payment_installments, payment_value,
    is_zero_installment, is_zero_payment, is_multi_payment_order
)
SELECT
    p.order_id,
    p.payment_sequential,
    fo.order_key,
    fo.customer_key,
    dpt.payment_type_key,
    fo.purchase_date_key,
    fo.order_status,
    p.payment_installments,
    p.payment_value,
    p.is_zero_installment,
    p.is_zero_payment,
    CASE WHEN fo.payment_record_count > 1 THEN 1 ELSE 0 END AS is_multi_payment_order
FROM payments p
INNER JOIN fact_orders fo ON p.order_id = fo.order_id
INNER JOIN dim_payment_type dpt ON p.payment_type = dpt.payment_type;

-- ----------------------------------------------------------------------------
-- 11. fact_reviews (99,224 rows)
-- ----------------------------------------------------------------------------
INSERT INTO fact_reviews (
    review_id, order_id, order_key, customer_key, review_date_key,
    purchase_date_key, review_score, rating_classification, review_response_hours,
    has_written_review, has_review_title, order_status,
    is_on_time_delivery, delivery_deviation_days
)
SELECT
    r.review_id,
    r.order_id,
    fo.order_key,
    fo.customer_key,
    CAST(DATE_FORMAT(r.review_creation_date, '%Y%m%d') AS SIGNED) AS review_date_key,
    fo.purchase_date_key,
    r.review_score,
    r.rating_classification,
    r.review_response_hours,
    r.has_written_review,
    r.has_review_title,
    fo.order_status,
    fo.is_on_time_delivery,
    fo.delivery_deviation_days
FROM reviews r
INNER JOIN fact_orders fo ON r.order_id = fo.order_id;

-- ----------------------------------------------------------------------------
-- 12. fact_marketing_funnel (8,000 rows)
-- ----------------------------------------------------------------------------
INSERT INTO fact_marketing_funnel (
    mql_id, channel_key, first_contact_date_key, won_date_key, seller_key,
    has_closed_deal, has_marketplace_seller_match, conversion_duration_days,
    is_valid_conversion_duration, declared_monthly_revenue,
    declared_product_catalog_size, business_segment, lead_type, business_type,
    sdr_id, sr_id
)
SELECT
    ml.mql_id,
    dmc.channel_key,
    CAST(DATE_FORMAT(ml.first_contact_date, '%Y%m%d') AS SIGNED) AS first_contact_date_key,
    COALESCE(CAST(DATE_FORMAT(cd.won_date, '%Y%m%d') AS SIGNED), -1) AS won_date_key,
    COALESCE(ds.seller_key, -1) AS seller_key,
    ml.has_closed_deal,
    COALESCE(cd.has_marketplace_seller_match, 0) AS has_marketplace_seller_match,
    cd.conversion_duration_days,
    cd.is_valid_conversion_duration,
    cd.declared_monthly_revenue,
    cd.declared_product_catalog_size,
    cd.business_segment,
    cd.lead_type,
    cd.business_type,
    cd.sdr_id,
    cd.sr_id
FROM marketing_leads ml
INNER JOIN dim_marketing_channel dmc ON ml.origin = dmc.origin
LEFT JOIN closed_deals cd ON ml.mql_id = cd.mql_id
LEFT JOIN dim_seller ds ON cd.seller_id = ds.seller_id AND cd.has_marketplace_seller_match = 1;
