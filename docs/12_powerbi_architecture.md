# CommerceIQ — Power BI Architecture & Manual Refresh Guide (Phase 13)

## 1. Delivered Native Assets

- **Power BI Project (PBIP):** [`powerbi/CommerceIQ.pbip`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/CommerceIQ.pbip)
  - [`CommerceIQ.SemanticModel/`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/CommerceIQ.SemanticModel/) — TMDL star/constellation semantic model, single-direction relationships, hidden surrogate keys, and explicit DAX measures.
  - [`CommerceIQ.Report/`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/CommerceIQ.Report/) — 10-page report structure and visual theme binding.
- **DAX Measure Library:** [`powerbi/dax/commerceiq_measures.dax`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/dax/commerceiq_measures.dax)
- **Power Query M Scripts:** [`powerbi/power_query/warehouse_queries.pq`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/power_query/warehouse_queries.pq)
- **Visual Theme JSON:** [`powerbi/theme/commerceiq_theme.json`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/theme/commerceiq_theme.json)
- **KPI Reconciliation:** [`reports/powerbi_kpi_reconciliation.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/powerbi_kpi_reconciliation.md)

## 2. Star Schema & Relationship Rules

- **Fact Tables:** `fact_orders`, `fact_order_items`, `fact_payments`, `fact_reviews`, `fact_marketing_funnel`
- **Conformed Dimensions:** `dim_date` (marked as Date table), `dim_customer`, `dim_seller`, `dim_product`, `dim_geography`, `dim_payment_type`, `dim_marketing_channel`
- **Analytical Extensions:** `customer_rfm_segments`, `forecast_outputs`, `delivery_risk_predictions`, `decision_scenarios`
- **Cardinality & Filtering:** Strict many-to-one (`*:1`) single-direction filtering from dimensions to facts; inactive role-playing date relationships (`delivered_date_key`, `estimated_date_key`, `won_date_key`) activated explicitly via `USERELATIONSHIP` when needed; surrogate keys (`*_key`, `*_sk`) hidden in report view.

## 3. Ten-Page Report Specification

1. **Executive Overview:** Delivered Merchandise Value, Placed/Delivered Orders, Unique Customers, AOV, On-Time Rate, Mean Review Score, Monthly Trend, Status Funnel.
2. **Sales & Product Intelligence:** Category Pareto, YoY Growth (Jan–Aug 2017 vs 2018), Product Concentration, Payment Mix.
3. **Customer Intelligence:** Persistent `customer_unique_id` RFM Segments, K-Means Clusters, Repeat Purchase Rate, Cohort Retention Matrix, Observed Customer Spend.
4. **Seller Intelligence:** Seller Concentration, Active Sellers, Scorecard Tiers, Late & Cancellation Exposure Drill-Through.
5. **Logistics & Delivery:** On-Time / Late Split, Approval/Processing/Transit Stage Durations, State-to-State Lane Matrix, Freight-to-Price Ratio.
6. **Customer Satisfaction:** Rating Distribution, Positive/Negative Rates, Delivery Performance Impact on Stars, Complaint Themes.
7. **Marketing Intelligence:** Qualified Leads, Closed Deals, Conversion Rate by Channel, Sales Cycle Duration, Seller Match Coverage.
8. **Geographic Intelligence:** State/Region Sales & Order Distribution, Intra-State vs Inter-State Delivery & Freight Comparison.
9. **Predictive Intelligence:** Historical Weekly Backtest & 8-Week Illustrative Continuation (`forecast_outputs`), Checkout Delay Risk Tiers & Top Drivers (`delivery_risk_predictions`).
10. **Decision Intelligence:** Low/Base/High Illustrative Scenarios & Opportunity Prioritization Matrix (`decision_scenarios`).

## 4. Audit Findings, Fixes Applied & Exact Connector/GUI Steps

- **Source Assets & Schema Status:** **REPAIRED & VALIDATED** (`17` TMDL tables, `15` relationships, `61` formatted DAX measures, `10` PBIR pages, `84` visuals with explicit `prototypeQuery` + `active` projections + explicit measure bindings, strongly typed CSV M partitions, and `dim_geography[state_brazil]` geo disambiguation).
- **Root Causes Diagnosed & Resolved:**
  1. **Empty Visuals ("Select or drag fields to populate this visual."):** Original `report.json` visuals omitted `prototypeQuery` (`Version: 2`) and `"active": true` on categorical/slicer projections, and Pages 3, 9, and 10 referenced raw columns despite `discourageImplicitMeasures`. All 84 visuals now bind explicit `prototypeQuery` queries and explicit `_Measures.*` metrics, plus cross-grain `fact_order_items` / `fact_payments` measures for product, seller, and payment slicing.
  2. **MySQL Connection Error (`MySql.Data.MySqlClient`):** Resolved by installing MySQL Connector/NET (`MySQL Data Provider` registered cleanly in Windows `.NET DbProviderFactories`).
  3. **`dim_date[full_date]` Blank Primary Key Error & Cascading `0x80040E4E` Aborts + `tinyint(1)` Flag Typing:** MySQL `dim_date` stores an unknown member (`date_key = -1`, `full_date = NULL`) for undelivered orders (`delivered_date_key = -1` on `2,965` rows), while `dim_date.tmdl` declared `full_date` as `isKey` (`dataCategory: Time`), causing VertiPaq to reject the NULL primary key and abort parallel partition loads (`HRESULT: 0x80040E4E`). Fixed `dim_date` M import to filter `each [date_key] > 0 and [full_date] <> null` (yielding `1,827` continuous, non-null calendar days `2016-01-01`..`2020-12-31` without altering any `fact_orders` rows), normalized all MySQL `tinyint(1)` flags cleanly via `Int64.From` against Connector/NET's `TreatTinyAsBoolean` default, and set `"en-US"` culture on all CSV `Table.TransformColumnTypes` steps.
- **Native Desktop Rendering & Refresh Status:** **COMPLETED & CONFIRMED**
  - **User Manual Confirmation (2026-11-28):** Installed MySQL Connector/NET (`MySql.Data.MySqlClient`), verified MySQL database connection to `localhost / commerceiq`, and confirmed the semantic model refreshes cleanly in Power BI Desktop (`CommerceIQ.pbip`).
  - **Agent Automated Verification:** Validated schema consistency, `0` unbound visuals across all `10` pages / `84` visuals, `61` explicit DAX measures, `17` TMDL tables (`dim_date` `-1` filter + `TINYINT(1)` normalization + `"en-US"` CSV typing), and MySQL/CSV source-key integrity via automated pytest checks (`tests/test_warehouse_and_models.py`).
- **Optional Screenshot Export:** No PNG files currently exist in `powerbi/screenshots/`; if screenshots are exported later from Power BI Desktop, save them to `powerbi/screenshots/` and add them to `README.md`.
