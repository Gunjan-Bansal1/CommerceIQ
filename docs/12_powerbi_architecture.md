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
  2. **MySQL Connection Error (`MySql.Data.MySqlClient`):** Confirmed via Windows `.NET DbProviderFactories`, GAC, and `MySQL Installer` inspection that **MySQL Connector/NET** is NOT installed on the host Windows system (only MySQL Server/Shell/Workbench 8.0.44 and Installer 1.6.16.0 are present), and installing it writes to `.NET GAC / machine.config` requiring Windows Administrator UAC elevation.
- **Native Desktop Rendering & Refresh Status:** **BLOCKED BY SYSTEM CONNECTOR PREREQUISITE** (`PBIDesktopStore.exe` v2.160.1151.0 x64 cannot refresh `MySQL.Database("localhost", "commerceiq")` until 64-bit MySQL Connector/NET 8.0.x is installed with Administrator privileges).
- **Exact Steps to Complete Live Refresh in Power BI Desktop:**
  1. Close Power BI Desktop (`PBIDesktop.exe`).
  2. Download **64-bit MySQL Connector/NET 8.0.x** (e.g., `8.0.36`, **not `9.x`** which Power BI Desktop does not natively recognize) from the official Oracle archive: https://dev.mysql.com/downloads/connector/net/ (select Archives -> `8.0.36` -> Microsoft Windows x64 MSI) and run the installer as **Administrator**.
  3. Verify registration in PowerShell: `[System.Data.Common.DbProviderFactories]::GetFactoryClasses()` lists `MySql.Data.MySqlClient`.
  4. Re-open [`powerbi/CommerceIQ.pbip`](file:///c:/Users/bgunj/Desktop/commerceIQ/powerbi/CommerceIQ.pbip), supply local MySQL credentials for `localhost / commerceiq`, approve **Organizational** privacy levels if prompted, and click **Refresh** on the Home ribbon.
  5. Save via **File -> Save** (or **Save as `.pbix`**) and optionally capture screenshots into `powerbi/screenshots/`.
