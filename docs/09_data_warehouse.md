# CommerceIQ — Analytical Data Warehouse (Phase 6)

## 1. Architecture Overview

CommerceIQ implements a Kimball **Fact Constellation (Galaxy Schema)** inside MySQL 8.0 (`commerceiq`) composed of **7 conformed dimensions**, **5 fact tables**, and **9 business domain data marts** (`mart_*` views).

## 2. Dimensions

| Dimension | Grain | Surrogate Key | Unknown Member | Notes |
|---|---|---|---|---|
| `dim_date` | 1 row per calendar day (2016–2020) | `date_key` (`YYYYMMDD`) | `-1` | Includes Brazilian holidays (`brazil_holidays`) and `is_core_reporting_period` |
| `dim_geography` | 1 row per eligible postal prefix | `geo_key` | `-1` (`00000`) | Maps Brazilian states to 5 macro-regions (`Southeast`, `South`, `Northeast`, `Central-West`, `North`) |
| `dim_customer` | 1 row per `customer_id` | `customer_key` | — | Retains persistent `customer_unique_id`, order sequence, lifetime order count, and repeat flag |
| `dim_seller` | 1 row per marketplace `seller_id` | `seller_key` | `-1` (`UNKNOWN`) | Enriched with marketing funnel origin/segment where matched |
| `dim_product` | 1 row per `product_id` | `product_key` | — | Denormalized with English category translations |
| `dim_payment_type` | 1 row per payment method | `payment_type_key` | — | Groups card, bank slip (`boleto`), voucher, and undefined |
| `dim_marketing_channel` | 1 row per acquisition origin | `channel_key` | — | Groups organic/direct, paid/social, referral/other, and unrecorded |

## 3. Fact Tables & Grain Protection

| Fact Table | Grain | Rows | Anti-Fan-Out Design |
|---|---|---:|---|
| `fact_orders` | 1 row per `order_id` | 99,441 | Pre-aggregates `order_items`, `payments`, and `reviews` by `order_id` in CTEs before joining |
| `fact_order_items` | 1 row per `(order_id, order_item_id)` | 112,650 | Item-level price, freight, and intra-state fulfillment flag |
| `fact_payments` | 1 row per `(order_id, payment_sequential)` | 103,886 | Payment method, installments, and multi-payment indicator |
| `fact_reviews` | 1 row per `(review_id, order_id)` | 99,224 | Review rating, written flag, response time, and order delivery performance context |
| `fact_marketing_funnel` | 1 row per `mql_id` | 8,000 | Lead contact, won deal attributes, conversion duration, and optional seller linkage |

## 4. Analytical Data Marts

- `mart_executive_monthly`
- `mart_customer_intelligence`
- `mart_product_category_performance`
- `mart_seller_performance`
- `mart_delivery_logistics`
- `mart_customer_satisfaction`
- `mart_marketing_funnel`
- `mart_geographic_performance`
- `mart_payment_reconciliation`

## 5. Execution

```powershell
python src/warehouse/build_warehouse.py
```
