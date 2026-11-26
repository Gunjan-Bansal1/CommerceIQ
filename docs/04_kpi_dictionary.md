# CommerceIQ — Preliminary KPI Dictionary

Version 1.0. All definitions are candidates pending Phase 3 profiling. No actual KPI results or targets are asserted.

## Shared calculation rules
- BRL; use fixed-precision monetary values. Ratios displayed as percentages where appropriate. Zero denominator = NULL/not applicable. Missing amounts are unknown.
- Eligible sales = delivered orders with valid item prices; order value denominators must match the numerator coverage. Report coverage and exclusions. Unsuccessful statuses = canceled/unavailable, pending verification. In-progress orders are not automatically unsuccessful.
- Use distinct order IDs and persistent customer IDs. Pre-aggregate payment, item and review grains before combining. Review-event policy and geographic mapping to be verified.
- Purchase date is the default reporting date; review and lead trends use appropriate event dates. Compare complete equivalent periods. Retention and activation require observable fixed follow-up windows; choose and document them during analysis.
- SLA compares calendar dates; elapsed duration uses valid timestamp differences. Negative or inconsistent durations flagged. Seller and category exposure does not prove responsibility.
- Merchandise value is not marketplace revenue; scenarios are not realized savings. Forecast and risk metrics use unseen data and baseline comparison.
- Reporting grain, filters, owner, refresh cadence and exception rules will be finalized in the relevant data marts before BI implementation.

## REV

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-REV-01 | Total orders | Distinct order_id | Orders |
| KPI-REV-02 | Delivered orders | Distinct delivered order_id | Orders |
| KPI-REV-03 | Merchandise sales | Sum eligible delivered item price | Orders + items |
| KPI-REV-04 | Recorded gross merchandise value | Sum recorded valid item price across statuses | Items |
| KPI-REV-05 | Payment value | Sum valid payment records | Payments |
| KPI-REV-06 | Average order value | Delivered merchandise value / eligible delivered orders with known item values | Orders + items |
| KPI-REV-07 | Item volume | Count eligible delivered item rows | Items + orders |
| KPI-REV-08 | Average item price | Delivered merchandise value / eligible item rows | Items + orders |
| KPI-REV-09 | MoM growth | Current / prior comparable month - 1 | Orders + items |
| KPI-REV-10 | YoY growth | Current / same prior-year period - 1 | Orders + items |

## LEK

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-LEK-01 | Cancellation rate | Canceled distinct orders / placed orders | Orders |
| KPI-LEK-02 | Unavailable rate | Unavailable orders / placed orders | Orders |
| KPI-LEK-03 | Unsuccessful rate | Canceled or unavailable orders / placed orders | Orders |
| KPI-LEK-04 | Recorded lost order value | Sum known item prices for unsuccessful orders | Orders + items |
| KPI-LEK-05 | Recorded leakage ratio | Recorded unsuccessful value / recorded gross merchandise value | Orders + items |
| KPI-LEK-06 | Value coverage | Unsuccessful orders with known item value / unsuccessful orders | Orders + items |

## CUS

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-CUS-01 | Unique purchasing customers | Distinct persistent IDs with eligible purchases | Customers + orders |
| KPI-CUS-02 | New observed customers | First observed eligible purchase in period | Customers + orders |
| KPI-CUS-03 | Repeat customers | Persistent IDs with at least two eligible purchases | Customers + orders |
| KPI-CUS-04 | Repeat purchase rate | Repeat customers / eligible purchasing customers | Customers + orders |
| KPI-CUS-05 | Purchase frequency | Eligible orders / purchasing customers | Customers + orders |
| KPI-CUS-06 | Observed spending | Sum eligible merchandise value per persistent ID | Customers + orders + items |
| KPI-CUS-07 | Recency | Reference date minus last eligible purchase | Customers + orders |
| KPI-CUS-08 | Interpurchase duration | Days between consecutive eligible purchases | Customers + orders |
| KPI-CUS-09 | Cohort retention | Active cohort members / eligible original cohort | Customers + orders |
| KPI-CUS-10 | RFM segment | Validated recency, frequency and monetary scoring | Customer mart |

## PRD

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-PRD-01 | Category contribution | Category eligible value / total eligible value | Products + items + orders |
| KPI-PRD-02 | Category growth | Current / prior comparable category value - 1 | Products + items + orders |
| KPI-PRD-03 | Basket support | Baskets containing itemset / eligible baskets | Items + orders |
| KPI-PRD-04 | Basket lift | Joint support / product of individual supports | Items + orders |

## SEL

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-SEL-01 | Active sellers | Distinct sellers with eligible sales | Items + orders |
| KPI-SEL-02 | Seller sales | Sum eligible item prices attributed to seller | Items + orders |
| KPI-SEL-03 | Seller concentration | Top seller value / total eligible value | Items + orders |
| KPI-SEL-04 | Cancellation exposure | Distinct canceled seller-associated orders / seller-associated placed orders | Items + orders |
| KPI-SEL-05 | Late exposure | Late eligible seller-associated orders / eligible seller-associated delivered orders | Items + orders |
| KPI-SEL-06 | Seller score | Documented weighted score, minimum volume and sensitivity checks | Seller mart |

## LOG

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-LOG-01 | Mean delivery time | Mean elapsed purchase-to-delivery duration | Orders |
| KPI-LOG-02 | Median delivery time | Median elapsed purchase-to-delivery duration | Orders |
| KPI-LOG-03 | P90 delivery time | 90th percentile elapsed purchase-to-delivery duration | Orders |
| KPI-LOG-04 | On-time rate | Delivered on or before promised calendar date / eligible delivered orders | Orders |
| KPI-LOG-05 | Late rate | Delivered after promised calendar date / eligible delivered orders | Orders |
| KPI-LOG-06 | Mean delay | Mean positive calendar days after promise among late deliveries | Orders |
| KPI-LOG-07 | Approval time | Elapsed approval minus purchase timestamp | Orders |
| KPI-LOG-08 | Processing time | Elapsed carrier handover minus approval timestamp | Orders |
| KPI-LOG-09 | Transit time | Elapsed delivery minus carrier handover timestamp | Orders |
| KPI-LOG-10 | Freight per order | Eligible freight charges / eligible orders | Items + orders |
| KPI-LOG-11 | Freight ratio | Eligible freight charges / eligible merchandise value | Items + orders |
| KPI-LOG-12 | SLA coverage | Delivered orders with valid actual and promised dates / delivered orders | Orders |

## PAY

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-PAY-01 | Payment method value share | Method payment value / total payment value | Payments |
| KPI-PAY-02 | Multiple payment rate | Orders with multiple valid payment records / orders with payment records | Payments |
| KPI-PAY-03 | Instalment distribution | Count payment records by instalment number | Payments |
| KPI-PAY-04 | Payment reconciliation difference | Order payment sum minus item price and freight sum | Payments + items |

## MKT

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-MKT-01 | Qualified leads | Distinct mql_id | Leads |
| KPI-MKT-02 | Converted leads | Distinct qualified leads with closed deal | Leads + deals |
| KPI-MKT-03 | Lead conversion | Converted / eligible qualified leads | Leads + deals |
| KPI-MKT-04 | Sales cycle | Won date minus first contact date | Leads + deals |
| KPI-MKT-05 | Seller activation | Converted sellers with subsequent eligible recorded sales / converted sellers with observable follow-up | Deals + orders + items |
| KPI-MKT-06 | Channel conversion | Converted / eligible leads within channel | Leads + deals |

## EXP

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-EXP-01 | Mean review score | Mean validated review rating | Reviews |
| KPI-EXP-02 | Negative review rate | Valid scores 1–2 / valid reviews | Reviews |
| KPI-EXP-03 | Positive review rate | Valid scores 4–5 / valid reviews | Reviews |
| KPI-EXP-04 | Review coverage | Eligible orders with review / eligible orders | Reviews + orders |
| KPI-EXP-05 | Complaint theme frequency | Validated theme occurrences / eligible text reviews | Reviews |

## DEC

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-DEC-01 | Recoverable sales | Scenario eligible exposure times assumed recoverable fraction | Scenario inputs |
| KPI-DEC-02 | Contribution recovery | Estimated recovered sales times assumed incremental margin | Scenario inputs |
| KPI-DEC-03 | Net benefit | Estimated contribution recovery minus intervention cost | Scenario inputs |

## PRED

| ID | Metric | Calculation | Logical sources |
|---|---|---|---|
| KPI-PRED-01 | MAE | Mean absolute forecast error | Holdout predictions |
| KPI-PRED-02 | RMSE | Square root of mean squared forecast error | Holdout predictions |
| KPI-PRED-03 | WAPE | Sum absolute errors / sum absolute actuals | Holdout predictions |
| KPI-PRED-04 | Precision | True positives / predicted positives | Holdout predictions |
| KPI-PRED-05 | Recall | True positives / actual positives | Holdout predictions |
| KPI-PRED-06 | PR-AUC | Area under precision-recall curve using documented method | Holdout predictions |
