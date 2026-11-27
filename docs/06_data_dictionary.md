# CommerceIQ - Data Dictionary

## Overview

This document describes the 12 registered source datasets.
Recommended data types and keys are proposed analytical designs.
Raw source files remain unchanged.

## orders

**Grain:** One record per order

**Proposed primary key:** order_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| order_id | Unique order identifier | STRING | 0.00% |
| customer_id | Order-specific customer identifier | STRING | 0.00% |
| order_status | Current recorded order lifecycle status | STRING | 0.00% |
| order_purchase_timestamp | Date and time of order purchase | DATETIME | 0.00% |
| order_approved_at | Date and time of order approval | DATETIME | 0.16% |
| order_delivered_carrier_date | Date and time of carrier handover | DATETIME | 1.79% |
| order_delivered_customer_date | Date and time of customer delivery | DATETIME | 2.98% |
| order_estimated_delivery_date | Estimated customer delivery date | DATE | 0.00% |

## customers

**Grain:** One record per order-specific customer ID

**Proposed primary key:** customer_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| customer_id | Unique order-specific customer identifier | STRING | 0.00% |
| customer_unique_id | Persistent anonymized customer identifier | STRING | 0.00% |
| customer_zip_code_prefix | Customer postal code prefix | STRING | 0.00% |
| customer_city | Customer city | STRING | 0.00% |
| customer_state | Customer state abbreviation | STRING | 0.00% |

## order_items

**Grain:** One record per item within an order

**Proposed primary key:** order_id, order_item_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| order_id | Associated order identifier | STRING | 0.00% |
| order_item_id | Sequential item identifier within an order | INTEGER | 0.00% |
| product_id | Associated product identifier | STRING | 0.00% |
| seller_id | Associated seller identifier | STRING | 0.00% |
| shipping_limit_date | Deadline for seller shipment | DATETIME | 0.00% |
| price | Item merchandise price in BRL | DECIMAL | 0.00% |
| freight_value | Item freight value in BRL | DECIMAL | 0.00% |

## payments

**Grain:** One record per payment sequence within an order

**Proposed primary key:** order_id, payment_sequential

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| order_id | Associated order identifier | STRING | 0.00% |
| payment_sequential | Payment sequence within an order | INTEGER | 0.00% |
| payment_type | Payment method | STRING | 0.00% |
| payment_installments | Number of payment installments | INTEGER | 0.00% |
| payment_value | Recorded payment amount in BRL | DECIMAL | 0.00% |

## reviews

**Grain:** One record per review and order combination

**Proposed primary key:** review_id, order_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| review_id | Anonymized review identifier | STRING | 0.00% |
| order_id | Associated order identifier | STRING | 0.00% |
| review_score | Customer rating from 1 to 5 | INTEGER | 0.00% |
| review_comment_title | Optional review title | TEXT | 88.34% |
| review_comment_message | Optional written customer feedback | TEXT | 58.73% |
| review_creation_date | Review creation date | DATE | 0.00% |
| review_answer_timestamp | Date and time of review response | DATETIME | 0.00% |

## products

**Grain:** One record per product

**Proposed primary key:** product_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| product_id | Unique product identifier | STRING | 0.00% |
| product_category_name | Portuguese product category | STRING | 1.85% |
| product_name_lenght | Product name character length | INTEGER | 1.85% |
| product_description_lenght | Product description character length | INTEGER | 1.85% |
| product_photos_qty | Number of product photos | INTEGER | 1.85% |
| product_weight_g | Product weight in grams | FLOAT | 0.01% |
| product_length_cm | Product length in centimeters | FLOAT | 0.01% |
| product_height_cm | Product height in centimeters | FLOAT | 0.01% |
| product_width_cm | Product width in centimeters | FLOAT | 0.01% |

## sellers

**Grain:** One record per seller

**Proposed primary key:** seller_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| seller_id | Unique seller identifier | STRING | 0.00% |
| seller_zip_code_prefix | Seller postal code prefix | STRING | 0.00% |
| seller_city | Seller city | STRING | 0.00% |
| seller_state | Seller state abbreviation | STRING | 0.00% |

## geolocation

**Grain:** One geographic observation per source row

**Proposed primary key:** Requires design

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| geolocation_zip_code_prefix | Geographic postal code prefix | STRING | 0.00% |
| geolocation_lat | Geographic latitude | FLOAT | 0.00% |
| geolocation_lng | Geographic longitude | FLOAT | 0.00% |
| geolocation_city | Geographic city name | STRING | 0.00% |
| geolocation_state | Geographic state abbreviation | STRING | 0.00% |

## category_translation

**Grain:** One record per Portuguese product category

**Proposed primary key:** product_category_name

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| product_category_name | Original Portuguese category | STRING | 0.00% |
| product_category_name_english | English category translation | STRING | 0.00% |

## marketing_leads

**Grain:** One record per marketing-qualified lead

**Proposed primary key:** mql_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| mql_id | Marketing-qualified lead identifier | STRING | 0.00% |
| first_contact_date | Date of initial lead contact | DATE | 0.00% |
| landing_page_id | Lead landing page identifier | STRING | 0.00% |
| origin | Recorded marketing acquisition channel | STRING | 0.75% |

## closed_deals

**Grain:** One record per closed marketing lead

**Proposed primary key:** mql_id

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| mql_id | Associated marketing-qualified lead identifier | STRING | 0.00% |
| seller_id | Seller identifier associated with the closed deal | STRING | 0.00% |
| sdr_id | Sales development representative identifier | STRING | 0.00% |
| sr_id | Sales representative identifier | STRING | 0.00% |
| won_date | Date and time when the deal was won | DATETIME | 0.00% |
| business_segment | Declared seller business segment | STRING | 0.12% |
| lead_type | Recorded lead classification | STRING | 0.71% |
| lead_behaviour_profile | Recorded lead behaviour classification | STRING | 21.02% |
| has_company | Recorded company-registration indicator | BOOLEAN | 92.52% |
| has_gtin | Recorded global trade item number indicator | BOOLEAN | 92.40% |
| average_stock | Declared average stock range | STRING | 92.16% |
| business_type | Recorded seller business type | STRING | 1.19% |
| declared_product_catalog_size | Seller-declared catalog size | INTEGER | 91.81% |
| declared_monthly_revenue | Seller-declared monthly revenue | DECIMAL | 0.00% |

## brazil_holidays

**Grain:** One holiday record per date in the current snapshot

**Proposed primary key:** date, countryCode

| Column | Description | Recommended type | Missing % |
|---|---|---|---:|
| date | Holiday calendar date | DATE | 0.00% |
| localName | Holiday name in the local language | STRING | 0.00% |
| name | English holiday name | STRING | 0.00% |
| countryCode | Holiday country code | STRING | 0.00% |
| fixed | Provider-reported fixed-date indicator | BOOLEAN | 0.00% |
| global | Provider-reported nationwide applicability indicator | BOOLEAN | 0.00% |
| counties | Applicable regional subdivision codes | JSON | 92.86% |
| launchYear | Provider-reported holiday introduction year | INTEGER | 100.00% |
| types | Provider-reported holiday classifications | JSON | 0.00% |
| source_year | Year requested from the holiday API | INTEGER | 0.00% |
| source_url | API endpoint used to acquire the record | STRING | 0.00% |

## Important Analytical Considerations

- Preserve identifiers and postal codes as strings.
- Merchandise value is not actual marketplace revenue.
- Aggregate transactional tables at the appropriate grain.
- Retain legitimate repeated customer identifiers.
- Preserve optional review text and unknown Boolean values.
- Geographic lookups require deduplication.
- Statistical outliers are not automatically invalid.
- Core monthly reporting period: January 2017 to August 2018 (proposed).
- Distinguish missing seller matches from seller inactivity.
- Proposed data types will be finalized during transformation.
- Declared seller revenue is not verified marketplace revenue.