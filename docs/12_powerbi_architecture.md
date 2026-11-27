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

## 4. Validation Status & Exact Manual GUI Procedure

- **Source Assets Status:** **CREATED & VERIFIED** (`PBIP`, `TMDL`, `DAX`, `M`, `Theme JSON`, and SQL-backed KPI reconciliation).
- **Native Desktop Rendering Status:** **PENDING INTERACTIVE GUI OPEN** (`PBIDesktopStore.exe` is an interactive Microsoft Store GUI application that requires opening the `.pbip` interactively and signing into MySQL Connector/Net if prompted).
- **Shortest Manual Steps in Power BI Desktop:**
  1. Double-click `powerbi/CommerceIQ.pbip` (or open via `File -> Open` in Power BI Desktop).
  2. When prompted for MySQL credentials on `localhost / commerceiq`, enter your local MySQL user/password (Database/Windows auth) and approve Privacy Levels (`Organizational`).
  3. Click **Refresh** on the Home ribbon to load all warehouse tables and downstream CSVs, then **File -> Save as** `.pbix` and export screenshots to `powerbi/screenshots/` if desired.
