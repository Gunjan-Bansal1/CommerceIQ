# CommerceIQ — Exploratory Data Analysis Findings Report (Phase 9)

## 1. Commercial & Seasonality Findings
- Delivered orders with items: **96,478** totaling **BRL 13,221,498.11** merchandise value (mean AOV **BRL 137.04**, median **BRL 86.57**).
- Removing upper-IQR outliers (> BRL 305.90) yields **88,819** orders with mean AOV **BRL 94.34**.
- Peak core month was **2017-11** (Black Friday); weekday-hour traffic peaks Monday–Thursday 10:00–22:00.

## 2. Category & Seller Concentration
- Top category by delivered merchandise value: **health_beauty** (**BRL 1,233,131.72**).
- Top 10% of active sellers generate **67.11%** of delivered merchandise value.

## 3. Logistics & Regional Performance
- Carrier transit averages **9.33 days**, representing the dominant share of total delivery lead time vs. seller processing (**2.85 days**) and approval (**0.43 days**).
- Northeast/North states (e.g., BA, CE, PE, PA) exhibit substantially lower on-time delivery rates and higher freight ratios than SP/Southeast.

## 4. Customer Satisfaction & Portuguese Complaint Themes
- Early deliveries average **4.29** stars vs. **2.27** stars for late deliveries.
- Among 10,889 negative written reviews, **29.5%** cite non-delivery/waiting and **15.0%** cite delivery delays.

## 5. Payment & Marketing Funnel
- Credit cards account for **78.34%** of payment value (mean **3.51** installments).
- Overall sampled marketing conversion is **842/8,000 (10.53%)**, led in volume by `organic_search` and `paid_search`.

## 6. Exported Figures
- `reports/figures/eda_01_monthly_trends_and_seasonality.png`
- `reports/figures/eda_02_category_and_seller_concentration.png`
- `reports/figures/eda_03_logistics_stages_and_state_sla.png`
- `reports/figures/eda_04_satisfaction_and_complaint_themes.png`
- `reports/figures/eda_05_payments_and_marketing_funnel.png`
