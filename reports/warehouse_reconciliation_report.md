# CommerceIQ — Data Warehouse Reconciliation Report

**Execution Timestamp (UTC):** 2026-11-27 16:59:05
**Warehouse Schema:** `commerceiq`
**Build Duration:** 138.96 seconds

## 1. Dimension & Fact Table Counts

| Table | Role | Row Count |
|---|---|---:|
| `dim_date` | Dimension | 1,828 |
| `dim_geography` | Dimension | 19,012 |
| `dim_customer` | Dimension | 99,441 |
| `dim_seller` | Dimension | 3,096 |
| `dim_product` | Dimension | 32,951 |
| `dim_payment_type` | Dimension | 5 |
| `dim_marketing_channel` | Dimension | 11 |
| `fact_orders` | Fact | 99,441 |
| `fact_order_items` | Fact | 112,650 |
| `fact_payments` | Fact | 103,886 |
| `fact_reviews` | Fact | 99,224 |
| `fact_marketing_funnel` | Fact | 8,000 |

## 2. Analytical Data Mart Views

| View | Row Count |
|---|---:|
| `mart_executive_monthly` | 25 |
| `mart_customer_intelligence` | 96,096 |
| `mart_product_category_performance` | 74 |
| `mart_seller_performance` | 3,095 |
| `mart_delivery_logistics` | 417 |
| `mart_customer_satisfaction` | 253 |
| `mart_marketing_funnel` | 11 |
| `mart_geographic_performance` | 27 |
| `mart_payment_reconciliation` | 5 |

## 3. Financial & Grain Fan-Out Reconciliation

| Check | Warehouse Total (BRL) | Status |
|---|---:|---|
| `fact_orders_merch_brl` | 13,591,643.70 | EXACT MATCH |
| `fact_order_items_merch_brl` | 13,591,643.70 | EXACT MATCH |
| `fact_orders_freight_brl` | 2,251,909.54 | EXACT MATCH |
| `fact_orders_payment_brl` | 16,008,872.12 | EXACT MATCH |
| `fact_payments_brl` | 16,008,872.12 | EXACT MATCH |
| `fact_marketing_declared_rev_brl` | 61,784,006.00 | EXACT MATCH |

- `fact_orders` pre-aggregates `order_items`, `payments`, and `reviews` at `order_id` grain prior to joining, preventing fan-out across 99,441 orders.
- Unknown dimension members (`date_key = -1`, `geo_key = -1`, `seller_key = -1`) preserve unmatched optional references cleanly.
