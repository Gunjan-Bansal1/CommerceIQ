# CommerceIQ — SQL Business Analytics Execution Report (Phase 8)

**Execution Timestamp (UTC):** 2026-11-27 17:28:30
**Target Database:** `commerceiq` (MySQL 8.0)
**Queries Executed:** 41 (All PASS)
**Total Execution Time:** 98.27 seconds

## 1. Headline Findings From Executed SQL

- **Order & Merchandise Baseline:** 99,441 placed orders (96,478 delivered), **BRL 13,221,498.11** delivered merchandise value, **BRL 13,591,643.70** total recorded GMV across all statuses.
- **Customer Repeat Behavior (`customer_unique_id`):** 93,358 unique delivered customers, **2,801** repeat customers (**3.00%** repeat rate), average spend **BRL 141.62**.
- **Product & Seller Concentration:** **8,351** of 32,216 sold products (**25.92%**) drive 80% of delivered sales; Top 10% of sellers generate **67.11%** of delivered sales.
- **Logistics SLA:** 96,470 eligible SLA deliveries with **93.2269%** on-time rate (6,534 late orders; mean delivery **12.56** days; mean positive delay **10.62** days).
- **Marketing Funnel:** 8,000 qualified leads, **842** recorded closed deals.

## 2. Query Execution Log

| Script | Query Tag | Rows | Elapsed (s) | Status |
|---|---|---:|---:|---|
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q01` | 2 | 0.678 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q02` | 20 | 0.731 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q03` | 8 | 0.868 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q04` | 7 | 0.982 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q05` | 24 | 0.281 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q06` | 15 | 0.784 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q07` | 8 | 0.607 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q01` | 8 | 0.513 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q02` | 20 | 0.536 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q03` | 15 | 1.504 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q04` | 15 | 7.924 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q05` | 27 | 1.199 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q06` | 6 | 0.465 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q07` | 1 | 0.842 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q01` | 1 | 1.885 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q02` | 20 | 5.296 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q03` | 10 | 1.748 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q04` | 1 | 3.934 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q05` | 20 | 5.904 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q06` | 6 | 2.726 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q07` | 3 | 5.388 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q01` | 20 | 5.088 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q02` | 1 | 1.809 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q03` | 15 | 1.340 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q04` | 15 | 3.724 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q05` | 100 | 5.546 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q06` | 1 | 2.726 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q07` | 25 | 7.822 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q01` | 1 | 0.314 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q02` | 2 | 5.346 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q03` | 5 | 4.920 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q04` | 27 | 2.198 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q05` | 5 | 1.148 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q06` | 2 | 0.388 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q07` | 11 | 0.116 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q08` | 11 | 0.112 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q09` | 5 | 0.387 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q10` | 3 | 1.768 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q01` | 1 | 0.008 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q02` | 2 | 0.017 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q03` | 10 | 0.011 | PASS |
