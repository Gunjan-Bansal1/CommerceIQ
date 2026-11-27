# CommerceIQ — SQL Business Analytics Execution Report (Phase 8)

**Execution Timestamp (UTC):** 2026-11-27 17:11:18
**Target Database:** `commerceiq` (MySQL 8.0)
**Queries Executed:** 41 (All PASS)
**Total Execution Time:** 86.32 seconds

## 1. Headline Findings From Executed SQL

- **Order & Merchandise Baseline:** 99,441 placed orders (96,478 delivered), **BRL 13,221,498.11** delivered merchandise value, **BRL 13,591,643.70** total recorded GMV across all statuses.
- **Customer Repeat Behavior (`customer_unique_id`):** 93,358 unique delivered customers, **2,801** repeat customers (**3.00%** repeat rate), average spend **BRL 141.62**.
- **Product & Seller Concentration:** **8,351** of 32,216 sold products (**25.92%**) drive 80% of delivered sales; Top 10% of sellers generate **67.11%** of delivered sales.
- **Logistics SLA:** 96,470 eligible SLA deliveries with **93.2269%** on-time rate (6,534 late orders; mean delivery **12.56** days; mean positive delay **10.62** days).
- **Marketing Funnel:** 8,000 qualified leads, **842** recorded closed deals.

## 2. Query Execution Log

| Script | Query Tag | Rows | Elapsed (s) | Status |
|---|---|---:|---:|---|
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q01` | 2 | 0.872 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q02` | 20 | 0.597 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q03` | 8 | 0.786 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q04` | 7 | 0.898 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q05` | 24 | 0.203 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q06` | 15 | 0.889 | PASS |
| `01_executive_and_revenue.sql` | `01_executive_and_revenue__q07` | 8 | 0.528 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q01` | 8 | 0.432 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q02` | 20 | 0.472 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q03` | 15 | 1.334 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q04` | 15 | 2.620 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q05` | 27 | 2.216 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q06` | 6 | 0.367 | PASS |
| `02_revenue_leakage_and_exceptions.sql` | `02_revenue_leakage_and_exceptions__q07` | 1 | 1.039 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q01` | 1 | 1.595 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q02` | 20 | 4.919 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q03` | 10 | 1.524 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q04` | 1 | 3.682 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q05` | 20 | 5.440 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q06` | 6 | 2.545 | PASS |
| `03_customer_analytics.sql` | `03_customer_analytics__q07` | 3 | 5.391 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q01` | 20 | 2.770 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q02` | 1 | 1.790 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q03` | 15 | 1.292 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q04` | 15 | 3.039 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q05` | 100 | 5.416 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q06` | 1 | 2.804 | PASS |
| `04_product_and_seller_analytics.sql` | `04_product_and_seller_analytics__q07` | 25 | 6.815 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q01` | 1 | 0.322 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q02` | 2 | 5.126 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q03` | 5 | 4.007 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q04` | 27 | 2.278 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q05` | 5 | 1.273 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q06` | 2 | 0.373 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q07` | 11 | 0.173 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q08` | 11 | 0.110 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q09` | 5 | 0.550 | PASS |
| `05_logistics_geo_payment_marketing_experience.sql` | `05_logistics_geo_payment_marketing_experience__q10` | 3 | 2.005 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q01` | 1 | 0.008 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q02` | 2 | 0.019 | PASS |
| `06_execution_plans_and_optimization.sql` | `06_execution_plans_and_optimization__q03` | 10 | 0.009 | PASS |
