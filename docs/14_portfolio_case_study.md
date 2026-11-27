# CommerceIQ — End-to-End E-Commerce Analytics Portfolio Case Study

> **Project Classification:** Independent historical data analytics, BI, and predictive modeling portfolio case study built using public Olist Brazilian e-commerce and marketing datasets (`2016–2018`). Not commissioned by or deployed into Olist's production environment.

## 1. Business Problem
An online marketplace coordinates customers, sellers, payments, logistics carriers, and marketing acquisition channels across fragmented operational logs. Without unified grain control and reliable data governance, analysts risk double-counting multi-item/multi-payment orders, inflating customer counts by treating order-specific `customer_id`s as lifetime users, joining non-unique postal tables (causing row explosion), and building predictive models contaminated by post-purchase data leakage.

## 2. Analytical & Engineering Approach
CommerceIQ follows a structured 18-phase lifecycle (Phases 0–17):
1. **Business Alignment & Governance:** Translated 15 business problems into 72 KPIs and 120 business questions, enforcing strict metric rules (recorded BRL merchandise value ≠ profit; `customer_unique_id` for retention; `geolocation_lookup` for safe postal joins).
2. **Reproducible Ingestion & Cleaning:** Built SHA-256 verified ingestion (`src/ingestion/extract.py`) and deterministic cleaning (`src/transformation/clean.py`) transforming 12 raw datasets (1,559,806 rows) into 13 typed Parquet/CSV datasets (1,299,152 rows, 165 fields, 27 engineered features, 20/20 validation checks).
3. **Operational DB & Kimball Data Warehouse:** Modeled a MySQL 8.0 operational schema enforcing 8 required foreign keys while preserving 3 documented optional relationship gaps (`279` unmatched customer zips, `7` seller zips, `462` closed deals without marketplace sellers), followed by a 7-dimension, 5-fact constellation schema (`fact_orders` pre-aggregated at `order_id` grain to prevent fan-out) and 9 business data marts.
4. **Multi-Tool Analytics & BI:** Executed 41 domain SQL queries, automated a native Excel workbook (`XLOOKUP`, `SUMIFS`, PivotTable, PivotChart, 3 Slicers via Excel COM), and authored a Power BI PBIP semantic model (`39` explicit DAX measures across 10 pages).
5. **Statistical Inference, Customer Intelligence & Predictive ML:** Tested 5 formal business hypotheses with Holm-Bonferroni correction, segmented 93,358 unique delivered customers via RFM/cohorts/K-Means, backtested weekly demand forecasts, and trained a checkout-time delivery delay risk classifier with strict event-time zero-leakage seller features.

## 3. Key Analytical Findings
- **Commercial Scale & Skew:** 99,441 placed orders (96,478 delivered) generated **BRL 13,221,498.11** in delivered merchandise value (**BRL 13,591,643.70** recorded GMV across all statuses). Mean AOV is **BRL 137.04** vs. median **BRL 86.57**, with top 10% of sellers driving **67.11%** of delivered sales.
- **Delivery Reliability Drives Satisfaction:** On-time delivery rate is **93.23%** (89,936 / 96,470 eligible). Late orders (6,534) average **2.27 stars** vs. **4.29 stars** for early deliveries—a massive **2.02-star drop** (Mann-Whitney p < 1e-100, Cohen *d* = **1.71**, 95% CI [1.98, 2.06]), with negative review rates jumping from **9.23%** to **62.36%**.
- **Carrier Transit & Regional Disparities:** Carrier transit averages **9.33 days** (vs. 2.85 days seller processing). Haversine distance correlates strongly with delivery duration (Spearman ρ = **0.543**) and freight (ρ = **0.593**), leaving North/Northeast regions with higher freight burden and lower SLA compliance.
- **Extreme First-Order Retention Drop-Off:** Only **3.00%** (2,801 / 93,358) of delivered customers placed a repeat order across the observed window, underscoring the urgency of post-delivery 14–30 day cross-sell triggers.
- **Predictive Capability Without Leakage:** `Hist_Gradient_Boosting` scored **0.7325 ROC-AUC** and **0.0771 PR-AUC** (>2.1x baseline) on unseen Jun–Aug 2018 orders using strictly checkout-time features (`estimated_delivery_days`, `approx_distance_km`, `is_same_state`, event-time `seller_prior_late_rate`).

## 4. Recommendations & Validation
- Prioritize low-effort **Unsuccessful Order Recovery** (BRL 97,242.96 known canceled/unavailable exposure) and **14-day Retention Triggers** for Recent Single Buyers (~39% of customer base), paired with **Checkout Delay-Risk Flagging** on long-haul inter-state lanes.
- Reconciled 100% of headline KPIs (`99,441` orders, `96,478` delivered, `BRL 13,591,643.70` GMV, `93.2269%` on-time rate) across Python, MySQL Operational DB, Warehouse, SQL Analytics, Excel, and Power BI DAX definitions.
