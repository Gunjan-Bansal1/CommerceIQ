-- ============================================================================
-- CommerceIQ Analytical Data Warehouse Schema (MySQL 8.0)
-- Phase 6: Fact Constellation (Star Schema) — 7 Dimensions & 5 Fact Tables
-- ============================================================================

USE commerceiq;

-- Drop facts first, then dimensions (idempotent rebuild)
DROP TABLE IF EXISTS fact_marketing_funnel;
DROP TABLE IF EXISTS fact_reviews;
DROP TABLE IF EXISTS fact_payments;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;

DROP TABLE IF EXISTS dim_marketing_channel;
DROP TABLE IF EXISTS dim_payment_type;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_date;

-- 1. dim_date (date_key YYYYMMDD, unknown member = -1)
CREATE TABLE dim_date (
    date_key                   INT          NOT NULL,
    full_date                  DATE         NULL,
    year_num                   SMALLINT     NULL,
    quarter_num                TINYINT      NULL,
    year_quarter               CHAR(7)      NULL,
    month_num                  TINYINT      NULL,
    month_name                 VARCHAR(16)  NOT NULL,
    year_month_str             CHAR(7)      NULL,
    day_of_month               TINYINT      NULL,
    day_of_week                TINYINT      NULL,
    day_name                   VARCHAR(16)  NOT NULL,
    is_weekend                 TINYINT(1)   NOT NULL,
    is_core_reporting_period   TINYINT(1)   NOT NULL,
    is_brazil_national_holiday TINYINT(1)   NOT NULL,
    is_brazil_any_holiday      TINYINT(1)   NOT NULL,
    holiday_name               VARCHAR(64)  NULL,
    holiday_local_name         VARCHAR(64)  NULL,
    PRIMARY KEY (date_key),
    UNIQUE KEY uq_dim_date_full (full_date),
    KEY idx_dim_date_ym (year_month_str)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. dim_geography (geo_key SK, unknown member = -1)
CREATE TABLE dim_geography (
    geo_key                          INT         NOT NULL AUTO_INCREMENT,
    zip_code_prefix                  CHAR(5)     NOT NULL,
    city                             VARCHAR(64) NOT NULL,
    state                            CHAR(2)     NOT NULL,
    region                           VARCHAR(16) NOT NULL,
    latitude                         DOUBLE      NULL,
    longitude                        DOUBLE      NULL,
    is_ambiguous_zip                 TINYINT(1)  NOT NULL,
    dominant_location_pct            DOUBLE      NULL,
    has_geolocation_match            TINYINT(1)  NOT NULL,
    PRIMARY KEY (geo_key),
    UNIQUE KEY uq_dim_geo_zip (zip_code_prefix),
    KEY idx_dim_geo_state_region (state, region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. dim_customer (grain: customer_id; preserves persistent customer_unique_id)
CREATE TABLE dim_customer (
    customer_key             BIGINT      NOT NULL AUTO_INCREMENT,
    customer_id              CHAR(32)    NOT NULL,
    customer_unique_id       CHAR(32)    NOT NULL,
    customer_zip_code_prefix CHAR(5)     NOT NULL,
    customer_city            VARCHAR(64) NOT NULL,
    customer_state           CHAR(2)     NOT NULL,
    customer_region          VARCHAR(16) NOT NULL,
    geo_key                  INT         NOT NULL,
    has_geolocation_match    TINYINT(1)  NOT NULL,
    customer_order_seq       INT         NOT NULL,
    customer_lifetime_orders INT         NOT NULL,
    is_repeat_customer       TINYINT(1)  NOT NULL,
    PRIMARY KEY (customer_key),
    UNIQUE KEY uq_dim_cust_id (customer_id),
    KEY idx_dim_cust_unique (customer_unique_id),
    KEY idx_dim_cust_state (customer_state),
    CONSTRAINT fk_dim_cust_geo FOREIGN KEY (geo_key) REFERENCES dim_geography (geo_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. dim_seller (unknown member = -1 for unmatched closed deals)
CREATE TABLE dim_seller (
    seller_key                  INT         NOT NULL AUTO_INCREMENT,
    seller_id                   CHAR(32)    NOT NULL,
    seller_zip_code_prefix      CHAR(5)     NOT NULL,
    seller_city                 VARCHAR(64) NOT NULL,
    seller_state                CHAR(2)     NOT NULL,
    seller_region               VARCHAR(16) NOT NULL,
    geo_key                     INT         NOT NULL,
    has_geolocation_match       TINYINT(1)  NOT NULL,
    has_recorded_marketing_deal TINYINT(1)  NOT NULL,
    marketing_origin            VARCHAR(32) NULL,
    business_segment            VARCHAR(64) NULL,
    lead_type                   VARCHAR(32) NULL,
    business_type               VARCHAR(32) NULL,
    PRIMARY KEY (seller_key),
    UNIQUE KEY uq_dim_seller_id (seller_id),
    KEY idx_dim_seller_state (seller_state),
    CONSTRAINT fk_dim_seller_geo FOREIGN KEY (geo_key) REFERENCES dim_geography (geo_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. dim_product (denormalized with English category translation)
CREATE TABLE dim_product (
    product_key                   INT         NOT NULL AUTO_INCREMENT,
    product_id                    CHAR(32)    NOT NULL,
    product_category_name         VARCHAR(64) NOT NULL,
    product_category_name_english VARCHAR(64) NOT NULL,
    product_name_length           INT         NULL,
    product_description_length    INT         NULL,
    product_photos_qty            INT         NULL,
    product_weight_g              DOUBLE      NULL,
    product_length_cm             DOUBLE      NULL,
    product_height_cm             DOUBLE      NULL,
    product_width_cm              DOUBLE      NULL,
    product_volume_cm3            DOUBLE      NULL,
    product_density_g_cm3         DOUBLE      NULL,
    PRIMARY KEY (product_key),
    UNIQUE KEY uq_dim_product_id (product_id),
    KEY idx_dim_prod_cat_en (product_category_name_english)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. dim_payment_type
CREATE TABLE dim_payment_type (
    payment_type_key        INT         NOT NULL AUTO_INCREMENT,
    payment_type            VARCHAR(20) NOT NULL,
    payment_group           VARCHAR(32) NOT NULL,
    is_defined_payment_type TINYINT(1)  NOT NULL,
    PRIMARY KEY (payment_type_key),
    UNIQUE KEY uq_dim_pay_type (payment_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. dim_marketing_channel
CREATE TABLE dim_marketing_channel (
    channel_key        INT         NOT NULL AUTO_INCREMENT,
    origin             VARCHAR(32) NOT NULL,
    channel_group      VARCHAR(32) NOT NULL,
    is_recorded_origin TINYINT(1)  NOT NULL,
    PRIMARY KEY (channel_key),
    UNIQUE KEY uq_dim_mkt_origin (origin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. fact_orders (Grain: 1 row per order_id, pre-aggregated child measures)
CREATE TABLE fact_orders (
    order_key                            BIGINT        NOT NULL AUTO_INCREMENT,
    order_id                             CHAR(32)      NOT NULL,
    customer_key                         BIGINT        NOT NULL,
    customer_geo_key                     INT           NOT NULL,
    purchase_date_key                    INT           NOT NULL,
    delivered_date_key                   INT           NOT NULL,
    estimated_date_key                   INT           NOT NULL,
    order_status                         VARCHAR(20)   NOT NULL,
    is_delivered                         TINYINT(1)    NOT NULL,
    is_canceled                          TINYINT(1)    NOT NULL,
    is_unavailable                       TINYINT(1)    NOT NULL,
    is_unsuccessful                      TINYINT(1)    NOT NULL,
    is_core_reporting_period             TINYINT(1)    NOT NULL,
    purchase_year_month                  CHAR(7)       NOT NULL,
    purchase_hour                        TINYINT       NOT NULL,
    has_order_items                      TINYINT(1)    NOT NULL,
    has_payment_records                  TINYINT(1)    NOT NULL,
    has_review_records                   TINYINT(1)    NOT NULL,
    item_count                           INT           NOT NULL,
    distinct_products                    INT           NOT NULL,
    distinct_sellers                     INT           NOT NULL,
    merchandise_value                    DECIMAL(12,2) NOT NULL,
    freight_value                        DECIMAL(12,2) NOT NULL,
    item_total_value                     DECIMAL(12,2) NOT NULL,
    payment_record_count                 INT           NOT NULL,
    total_payment_value                  DECIMAL(12,2) NOT NULL,
    max_installments                     INT           NOT NULL,
    primary_payment_type                 VARCHAR(20)   NULL,
    payment_discrepancy_brl              DECIMAL(12,2) NOT NULL,
    review_count                         INT           NOT NULL,
    avg_review_score                     DOUBLE        NULL,
    min_review_score                     TINYINT       NULL,
    has_written_review                   TINYINT(1)    NOT NULL,
    approval_duration_hours              DOUBLE        NULL,
    processing_duration_days             DOUBLE        NULL,
    transit_duration_days                DOUBLE        NULL,
    delivery_duration_days               DOUBLE        NULL,
    estimated_delivery_days              DOUBLE        NOT NULL,
    delivery_deviation_days              INT           NULL,
    is_valid_delivery_promise_comparison TINYINT(1)    NOT NULL,
    is_on_time_delivery                  TINYINT(1)    NULL,
    delivery_performance                 VARCHAR(16)   NULL,
    PRIMARY KEY (order_key),
    UNIQUE KEY uq_fact_orders_id (order_id),
    KEY idx_fact_orders_status_core (order_status, is_core_reporting_period),
    KEY idx_fact_orders_ym (purchase_year_month),
    CONSTRAINT fk_fo_customer  FOREIGN KEY (customer_key)       REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fo_geo       FOREIGN KEY (customer_geo_key)   REFERENCES dim_geography (geo_key),
    CONSTRAINT fk_fo_pdate     FOREIGN KEY (purchase_date_key)  REFERENCES dim_date (date_key),
    CONSTRAINT fk_fo_ddate     FOREIGN KEY (delivered_date_key) REFERENCES dim_date (date_key),
    CONSTRAINT fk_fo_edate     FOREIGN KEY (estimated_date_key) REFERENCES dim_date (date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. fact_order_items (Grain: 1 row per order_id + order_item_id)
CREATE TABLE fact_order_items (
    order_item_sk                   BIGINT        NOT NULL AUTO_INCREMENT,
    order_id                        CHAR(32)      NOT NULL,
    order_item_id                   INT           NOT NULL,
    order_key                       BIGINT        NOT NULL,
    customer_key                    BIGINT        NOT NULL,
    product_key                     INT           NOT NULL,
    seller_key                      INT           NOT NULL,
    purchase_date_key               INT           NOT NULL,
    shipping_limit_date             DATETIME(0)   NOT NULL,
    order_status                    VARCHAR(20)   NOT NULL,
    is_delivered                    TINYINT(1)    NOT NULL,
    is_core_reporting_period        TINYINT(1)    NOT NULL,
    price                           DECIMAL(12,2) NOT NULL,
    freight_value                   DECIMAL(12,2) NOT NULL,
    item_value_with_freight         DECIMAL(12,2) NOT NULL,
    freight_to_price_pct            DOUBLE        NOT NULL,
    freight_share_of_item_total_pct DOUBLE        NOT NULL,
    is_same_state_fulfillment       TINYINT(1)    NOT NULL,
    PRIMARY KEY (order_item_sk),
    UNIQUE KEY uq_fact_oi_nk (order_id, order_item_id),
    CONSTRAINT fk_foi_order    FOREIGN KEY (order_key)         REFERENCES fact_orders (order_key),
    CONSTRAINT fk_foi_customer FOREIGN KEY (customer_key)      REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_foi_product  FOREIGN KEY (product_key)       REFERENCES dim_product (product_key),
    CONSTRAINT fk_foi_seller   FOREIGN KEY (seller_key)        REFERENCES dim_seller (seller_key),
    CONSTRAINT fk_foi_pdate    FOREIGN KEY (purchase_date_key) REFERENCES dim_date (date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. fact_payments (Grain: 1 row per order_id + payment_sequential)
CREATE TABLE fact_payments (
    payment_sk             BIGINT        NOT NULL AUTO_INCREMENT,
    order_id               CHAR(32)      NOT NULL,
    payment_sequential     INT           NOT NULL,
    order_key              BIGINT        NOT NULL,
    customer_key           BIGINT        NOT NULL,
    payment_type_key       INT           NOT NULL,
    purchase_date_key      INT           NOT NULL,
    order_status           VARCHAR(20)   NOT NULL,
    payment_installments   INT           NOT NULL,
    payment_value          DECIMAL(12,2) NOT NULL,
    is_zero_installment    TINYINT(1)    NOT NULL,
    is_zero_payment        TINYINT(1)    NOT NULL,
    is_multi_payment_order TINYINT(1)    NOT NULL,
    PRIMARY KEY (payment_sk),
    UNIQUE KEY uq_fact_pay_nk (order_id, payment_sequential),
    CONSTRAINT fk_fp_order    FOREIGN KEY (order_key)         REFERENCES fact_orders (order_key),
    CONSTRAINT fk_fp_customer FOREIGN KEY (customer_key)      REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fp_ptype    FOREIGN KEY (payment_type_key)  REFERENCES dim_payment_type (payment_type_key),
    CONSTRAINT fk_fp_pdate    FOREIGN KEY (purchase_date_key) REFERENCES dim_date (date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. fact_reviews (Grain: 1 row per review_id + order_id)
CREATE TABLE fact_reviews (
    review_sk               BIGINT      NOT NULL AUTO_INCREMENT,
    review_id               CHAR(32)    NOT NULL,
    order_id                CHAR(32)    NOT NULL,
    order_key               BIGINT      NOT NULL,
    customer_key            BIGINT      NOT NULL,
    review_date_key         INT         NOT NULL,
    purchase_date_key       INT         NOT NULL,
    review_score            TINYINT     NOT NULL,
    rating_classification   VARCHAR(16) NOT NULL,
    review_response_hours   DOUBLE      NOT NULL,
    has_written_review      TINYINT(1)  NOT NULL,
    has_review_title        TINYINT(1)  NOT NULL,
    order_status            VARCHAR(20) NOT NULL,
    is_on_time_delivery     TINYINT(1)  NULL,
    delivery_deviation_days INT         NULL,
    PRIMARY KEY (review_sk),
    UNIQUE KEY uq_fact_rev_nk (review_id, order_id),
    CONSTRAINT fk_fr_order    FOREIGN KEY (order_key)         REFERENCES fact_orders (order_key),
    CONSTRAINT fk_fr_customer FOREIGN KEY (customer_key)      REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fr_rdate    FOREIGN KEY (review_date_key)   REFERENCES dim_date (date_key),
    CONSTRAINT fk_fr_pdate    FOREIGN KEY (purchase_date_key) REFERENCES dim_date (date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. fact_marketing_funnel (Grain: 1 row per mql_id)
CREATE TABLE fact_marketing_funnel (
    mql_sk                       BIGINT        NOT NULL AUTO_INCREMENT,
    mql_id                       CHAR(32)      NOT NULL,
    channel_key                  INT           NOT NULL,
    first_contact_date_key       INT           NOT NULL,
    won_date_key                 INT           NOT NULL,
    seller_key                   INT           NOT NULL,
    has_closed_deal              TINYINT(1)    NOT NULL,
    has_marketplace_seller_match TINYINT(1)    NOT NULL,
    conversion_duration_days     DOUBLE        NULL,
    is_valid_conversion_duration TINYINT(1)    NULL,
    declared_monthly_revenue     DECIMAL(14,2) NULL,
    declared_product_catalog_size INT          NULL,
    business_segment             VARCHAR(64)   NULL,
    lead_type                    VARCHAR(32)   NULL,
    business_type                VARCHAR(32)   NULL,
    sdr_id                       CHAR(32)      NULL,
    sr_id                        CHAR(32)      NULL,
    PRIMARY KEY (mql_sk),
    UNIQUE KEY uq_fact_mkt_mql (mql_id),
    CONSTRAINT fk_fm_channel FOREIGN KEY (channel_key)            REFERENCES dim_marketing_channel (channel_key),
    CONSTRAINT fk_fm_fdate   FOREIGN KEY (first_contact_date_key) REFERENCES dim_date (date_key),
    CONSTRAINT fk_fm_wdate   FOREIGN KEY (won_date_key)           REFERENCES dim_date (date_key),
    CONSTRAINT fk_fm_seller  FOREIGN KEY (seller_key)             REFERENCES dim_seller (seller_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
