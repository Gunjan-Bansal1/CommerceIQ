-- ============================================================================
-- CommerceIQ Operational Database Indexes
-- Idempotent analytical index creation (safe to execute repeatedly on MySQL 8.0).
-- ============================================================================

USE commerceiq;

DROP PROCEDURE IF EXISTS sp_create_index_if_missing;

DELIMITER $$
CREATE PROCEDURE sp_create_index_if_missing(
    IN p_table VARCHAR(64),
    IN p_index VARCHAR(64),
    IN p_cols  VARCHAR(255)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;
    SELECT COUNT(*)
      INTO v_exists
      FROM information_schema.statistics
     WHERE table_schema = DATABASE()
       AND table_name = p_table
       AND index_name = p_index;
    IF v_exists = 0 THEN
        SET @ddl = CONCAT('CREATE INDEX ', p_index, ' ON ', p_table, ' (', p_cols, ')');
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

CALL sp_create_index_if_missing('customers', 'idx_customers_unique_id', 'customer_unique_id');
CALL sp_create_index_if_missing('customers', 'idx_customers_zip', 'customer_zip_code_prefix');
CALL sp_create_index_if_missing('customers', 'idx_customers_state', 'customer_state');

CALL sp_create_index_if_missing('sellers', 'idx_sellers_zip', 'seller_zip_code_prefix');
CALL sp_create_index_if_missing('sellers', 'idx_sellers_state', 'seller_state');

CALL sp_create_index_if_missing('geolocation', 'idx_geo_zip', 'geolocation_zip_code_prefix');

CALL sp_create_index_if_missing('orders', 'idx_orders_status', 'order_status');
CALL sp_create_index_if_missing('orders', 'idx_orders_purchase_ts', 'order_purchase_timestamp');
CALL sp_create_index_if_missing('orders', 'idx_orders_purchase_ym', 'purchase_year_month');
CALL sp_create_index_if_missing('orders', 'idx_orders_core_period', 'is_core_reporting_period');

CALL sp_create_index_if_missing('payments', 'idx_payments_type', 'payment_type');

CALL sp_create_index_if_missing('reviews', 'idx_reviews_order_id', 'order_id');
CALL sp_create_index_if_missing('reviews', 'idx_reviews_score', 'review_score');
CALL sp_create_index_if_missing('reviews', 'idx_reviews_rating_cls', 'rating_classification');

CALL sp_create_index_if_missing('marketing_leads', 'idx_mql_origin_date', 'origin, first_contact_date');
CALL sp_create_index_if_missing('closed_deals', 'idx_closed_deals_seller', 'seller_id');

DROP PROCEDURE IF EXISTS sp_create_index_if_missing;
