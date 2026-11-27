# CommerceIQ — Customer Intelligence Report (Phase 11)

**Analysis Reference Date:** `2018-09-01` | **Persistent ID:** `customer_unique_id`
- **Unique Delivered Customers:** 93,358
- **Repeat Customers (>= 2 delivered orders):** 2,801 (**3.00%**)
- **Observed Mean / Median Historical Spend:** BRL 141.62 / BRL 89.73
- **K-Means Clustering Quality:** Best k=3 achieved Silhouette Score = **0.3983** (separating repeat buyers, recent single buyers, high-value single buyers, and dormant cohorts).

## RFM Segment Breakdown

| Segment | Customers | Share % | Avg Recency (d) | Avg Freq | Avg Spend (BRL) | Total Value (BRL) |
|---|---:|---:|---:|---:|---:|---:|
| Recent High-Spend Single | 14,575 | 15.61% | 94.8 | 1.000 | 267.09 | 3,892,776.88 |
| At-Risk High-Spend | 13,679 | 14.65% | 398.1 | 1.000 | 277.09 | 3,790,330.98 |
| Dormant / Low-Engagement | 40,533 | 43.42% | 320.3 | 1.000 | 88.84 | 3,601,080.67 |
| Recent Single Buyers | 21,770 | 23.32% | 92.6 | 1.000 | 55.53 | 1,208,900.83 |
| Loyal Repeat Buyers | 1,860 | 1.99% | 288.9 | 2.075 | 226.27 | 420,865.64 |
| Champions (Repeat High-Value) | 941 | 1.01% | 92.2 | 2.190 | 326.83 | 307,543.11 |

## Targeted Retention Recommendations
1. **Recent Single Buyers & Recent High-Spend Single (~39% of customers):** Trigger post-delivery 14–30 day cross-category replenishment offers (`bed_bath_table`, `health_beauty`, `housewares`) before the critical first-90-day drop-off.
2. **Champions & Loyal Repeat Buyers (3.0% of customers):** Protect SLA reliability (prioritize fast carrier lanes) and offer loyalty bundles; repeat buyers spend nearly 2x single-order buyers.
3. **At-Risk High-Spend:** Run targeted win-back campaigns paired with delivery guarantee messaging.
