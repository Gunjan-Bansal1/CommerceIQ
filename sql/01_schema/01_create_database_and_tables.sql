-- ============================================================================
-- CommerceIQ Operational Relational Database Schema (MySQL 8.0)
-- Phase 5: 13 cleaned tables in topological parent-first dependency order.
-- Preserves exact monetary precision (DECIMAL), UTF-8 (utf8mb4), postal prefix
-- leading zeros (CHAR(5)), nullable booleans (TINYINT(1)), and optional
-- relationship gaps (no artificial FK on unmatched optional references).
-- ============================================================================

CREATE DATABASE IF NOT EXISTS commerceiq
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE commerceiq;

-- 1. category_translation (parent of products)
CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name         VARCHAR(64) NOT NULL,
    product_category_name_english VARCHAR(64) NOT NULL,
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. geolocation_lookup (optional lookup parent for customers & sellers)
CREATE TABLE IF NOT EXISTS geolocation_lookup (
    zip_code_prefix                  CHAR(5)     NOT NULL,
    city                             VARCHAR(64) NOT NULL,
    state                            CHAR(2)     NOT NULL,
    latitude                         DOUBLE      NOT NULL,
    longitude                        DOUBLE      NOT NULL,
    selected_observation_count       INT         NOT NULL,
    total_observations               INT         NOT NULL,
    distinct_city_state_combinations INT         NOT NULL,
    is_ambiguous_zip                 TINYINT(1)  NOT NULL,
    dominant_location_pct            DOUBLE      NOT NULL,
    PRIMARY KEY (zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. geolocation (cleaned individual geographic observations)
CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_id              BIGINT      NOT NULL,
    geolocation_zip_code_prefix CHAR(5)     NOT NULL,
    geolocation_lat             DOUBLE      NOT NULL,
    geolocation_lng             DOUBLE      NOT NULL,
    geolocation_city            VARCHAR(64) NOT NULL,
    geolocation_state           CHAR(2)     NOT NULL,
    is_valid_brazil_coordinate  TINYINT(1)  NOT NULL,
    is_valid_zip_prefix         TINYINT(1)  NOT NULL,
    is_valid_state              TINYINT(1)  NOT NULL,
    is_valid_geo_observation    TINYINT(1)  NOT NULL,
    PRIMARY KEY (geolocation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. brazil_holidays (calendar enrichment snapshot)
CREATE TABLE IF NOT EXISTS brazil_holidays (
    date         DATE         NOT NULL,
    local_name   VARCHAR(64)  NOT NULL,
    name         VARCHAR(64)  NOT NULL,
    country_code CHAR(2)      NOT NULL,
    is_fixed     TINYINT(1)   NOT NULL,
    is_global    TINYINT(1)   NOT NULL,
    counties     TEXT         NULL,
    types        TEXT         NOT NULL,
    source_year  SMALLINT     NOT NULL,
    source_url   VARCHAR(128) NOT NULL,
    PRIMARY KEY (date, country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. marketing_leads (parent of closed_deals)
CREATE TABLE IF NOT EXISTS marketing_leads (
    mql_id                   CHAR(32)    NOT NULL,
    first_contact_date       DATE        NOT NULL,
    landing_page_id          CHAR(32)    NOT NULL,
    origin                   VARCHAR(32) NOT NULL,
    has_closed_deal          TINYINT(1)  NOT NULL,
    first_contact_year_month CHAR(7)     NOT NULL,
    PRIMARY KEY (mql_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. sellers (parent of order_items; optional zip match to geolocation_lookup)
CREATE TABLE IF NOT EXISTS sellers (
    seller_id                   CHAR(32)    NOT NULL,
    seller_zip_code_prefix      CHAR(5)     NOT NULL,
    seller_city                 VARCHAR(64) NOT NULL,
    seller_state                CHAR(2)     NOT NULL,
    has_geolocation_match       TINYINT(1)  NOT NULL,
    has_recorded_marketing_deal TINYINT(1)  NOT NULL,
    PRIMARY KEY (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. customers (parent of orders; optional zip match to geolocation_lookup)
CREATE TABLE IF NOT EXISTS customers (
    customer_id              CHAR(32)    NOT NULL,
    customer_unique_id       CHAR(32)    NOT NULL,
    customer_zip_code_prefix CHAR(5)     NOT NULL,
    customer_city            VARCHAR(64) NOT NULL,
    customer_state           CHAR(2)     NOT NULL,
    has_geolocation_match    TINYINT(1)  NOT NULL,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. products (FK -> category_translation)
CREATE TABLE IF NOT EXISTS products (
    product_id                             CHAR(32)    NOT NULL,
    product_category_name                  VARCHAR(64) NOT NULL,
    product_name_length                    INT         NULL,
    product_description_length             INT         NULL,
    product_photos_qty                     INT         NULL,
    product_weight_g                       DOUBLE      NULL,
    product_length_cm                      DOUBLE      NULL,
    product_height_cm                      DOUBLE      NULL,
    product_width_cm                       DOUBLE      NULL,
    is_zero_weight_source                  TINYINT(1)  NULL,
    is_product_name_length_outlier         TINYINT(1)  NULL,
    is_product_description_length_outlier  TINYINT(1)  NULL,
    is_product_photos_qty_outlier          TINYINT(1)  NULL,
    is_product_weight_g_outlier            TINYINT(1)  NULL,
    is_product_length_cm_outlier           TINYINT(1)  NULL,
    is_product_height_cm_outlier           TINYINT(1)  NULL,
    is_product_width_cm_outlier            TINYINT(1)  NULL,
    product_volume_cm3                     DOUBLE      NULL,
    product_density_g_cm3                  DOUBLE      NULL,
    PRIMARY KEY (product_id),
    CONSTRAINT fk_products_category
        FOREIGN KEY (product_category_name)
        REFERENCES category_translation (product_category_name)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. orders (FK -> customers)
CREATE TABLE IF NOT EXISTS orders (
    order_id                             CHAR(32)    NOT NULL,
    customer_id                          CHAR(32)    NOT NULL,
    order_status                         VARCHAR(20) NOT NULL,
    order_purchase_timestamp             DATETIME(0) NOT NULL,
    order_approved_at                    DATETIME(0) NULL,
    order_delivered_carrier_date         DATETIME(0) NULL,
    order_delivered_customer_date        DATETIME(0) NULL,
    order_estimated_delivery_date        DATE        NOT NULL,
    is_delivered_missing_approval        TINYINT(1)  NOT NULL,
    is_delivered_missing_carrier         TINYINT(1)  NOT NULL,
    is_delivered_missing_delivery        TINYINT(1)  NOT NULL,
    is_carrier_before_purchase           TINYINT(1)  NULL,
    is_carrier_before_approval           TINYINT(1)  NULL,
    is_delivery_before_approval          TINYINT(1)  NULL,
    is_delivery_before_carrier           TINYINT(1)  NULL,
    is_valid_approval_duration           TINYINT(1)  NOT NULL,
    is_valid_processing_duration         TINYINT(1)  NOT NULL,
    is_valid_transit_duration            TINYINT(1)  NOT NULL,
    is_valid_delivery_duration           TINYINT(1)  NOT NULL,
    is_valid_estimated_delivery_duration TINYINT(1)  NOT NULL,
    is_valid_delivery_promise_comparison TINYINT(1)  NOT NULL,
    is_core_reporting_period             TINYINT(1)  NOT NULL,
    has_order_items                      TINYINT(1)  NOT NULL,
    has_payment_records                  TINYINT(1)  NOT NULL,
    has_review_records                   TINYINT(1)  NOT NULL,
    purchase_date                        DATE        NOT NULL,
    purchase_year                        SMALLINT    NOT NULL,
    purchase_month                       TINYINT     NOT NULL,
    purchase_year_month                  CHAR(7)     NOT NULL,
    purchase_quarter                     TINYINT     NOT NULL,
    purchase_day_of_week                 TINYINT     NOT NULL,
    purchase_hour                        TINYINT     NOT NULL,
    approval_duration_hours              DOUBLE      NULL,
    processing_duration_days             DOUBLE      NULL,
    transit_duration_days                DOUBLE      NULL,
    delivery_duration_days               DOUBLE      NULL,
    estimated_delivery_days              DOUBLE      NOT NULL,
    delivery_deviation_days              INT         NULL,
    is_on_time_delivery                  TINYINT(1)  NULL,
    delivery_performance                 VARCHAR(16) NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. order_items (FKs -> orders, products, sellers)
CREATE TABLE IF NOT EXISTS order_items (
    order_id                        CHAR(32)      NOT NULL,
    order_item_id                   INT           NOT NULL,
    product_id                      CHAR(32)      NOT NULL,
    seller_id                       CHAR(32)      NOT NULL,
    shipping_limit_date             DATETIME(0)   NOT NULL,
    price                           DECIMAL(12,2) NOT NULL,
    freight_value                   DECIMAL(12,2) NOT NULL,
    is_zero_freight                 TINYINT(1)    NOT NULL,
    is_price_outlier                TINYINT(1)    NOT NULL,
    is_freight_value_outlier        TINYINT(1)    NOT NULL,
    is_distant_shipping_deadline    TINYINT(1)    NOT NULL,
    item_value_with_freight         DECIMAL(12,2) NOT NULL,
    freight_to_price_pct            DOUBLE        NOT NULL,
    freight_share_of_item_total_pct DOUBLE        NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_order_items_seller
        FOREIGN KEY (seller_id) REFERENCES sellers (seller_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. payments (FK -> orders)
CREATE TABLE IF NOT EXISTS payments (
    order_id                  CHAR(32)      NOT NULL,
    payment_sequential        INT           NOT NULL,
    payment_type              VARCHAR(20)   NOT NULL,
    payment_installments      INT           NOT NULL,
    payment_value             DECIMAL(12,2) NOT NULL,
    is_zero_installment       TINYINT(1)    NOT NULL,
    is_zero_payment           TINYINT(1)    NOT NULL,
    is_undefined_payment_type TINYINT(1)    NOT NULL,
    is_payment_value_outlier  TINYINT(1)    NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. reviews (FK -> orders)
CREATE TABLE IF NOT EXISTS reviews (
    review_id              CHAR(32)    NOT NULL,
    order_id               CHAR(32)    NOT NULL,
    review_score           TINYINT     NOT NULL,
    review_comment_title   TEXT        NULL,
    review_comment_message TEXT        NULL,
    review_creation_date   DATE        NOT NULL,
    review_answer_timestamp DATETIME(0) NOT NULL,
    review_response_hours  DOUBLE      NOT NULL,
    has_written_review     TINYINT(1)  NOT NULL,
    has_review_title       TINYINT(1)  NOT NULL,
    rating_classification  VARCHAR(16) NOT NULL,
    PRIMARY KEY (review_id, order_id),
    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. closed_deals (FK -> marketing_leads; seller_id intentionally unconstrained due to 462 unmatched records)
CREATE TABLE IF NOT EXISTS closed_deals (
    mql_id                                   CHAR(32)      NOT NULL,
    seller_id                                CHAR(32)      NOT NULL,
    sdr_id                                   CHAR(32)      NOT NULL,
    sr_id                                    CHAR(32)      NOT NULL,
    won_date                                 DATETIME(0)   NOT NULL,
    business_segment                         VARCHAR(64)   NULL,
    lead_type                                VARCHAR(32)   NULL,
    lead_behaviour_profile                   VARCHAR(32)   NULL,
    has_company                              TINYINT(1)    NULL,
    has_gtin                                 TINYINT(1)    NULL,
    average_stock                            VARCHAR(16)   NULL,
    business_type                            VARCHAR(32)   NULL,
    declared_product_catalog_size            INT           NULL,
    declared_monthly_revenue                 DECIMAL(14,2) NOT NULL,
    is_zero_declared_revenue                 TINYINT(1)    NOT NULL,
    is_extreme_declared_revenue              TINYINT(1)    NOT NULL,
    is_declared_product_catalog_size_outlier TINYINT(1)    NULL,
    is_won_before_first_contact              TINYINT(1)    NOT NULL,
    is_valid_conversion_duration             TINYINT(1)    NOT NULL,
    has_marketplace_seller_match             TINYINT(1)    NOT NULL,
    conversion_duration_days                 DOUBLE        NULL,
    won_year_month                           CHAR(7)       NOT NULL,
    PRIMARY KEY (mql_id),
    CONSTRAINT fk_closed_deals_mql
        FOREIGN KEY (mql_id) REFERENCES marketing_leads (mql_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
