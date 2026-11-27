# CommerceIQ — Model Card: Historical Demand & Merchandise Forecasting

## 1. Model Overview & Intended Use
- **Scope:** Weekly delivered merchandise value (`merch_brl`) and delivered order volume (`delivered_orders`) across 86 complete weeks (`2017-01-02` to `2018-08-26`).
- **Important Limitation:** Source data ends in August 2018. Forecasts are **historical backtests and illustrative 2018 continuations**, not predictions of current market conditions.

## 2. Holdout Test Performance (Final 12 Weeks)

### Merchandise Value (BRL)
| target | model | MAE | RMSE | WAPE_pct | MAPE_pct |
| --- | --- | --- | --- | --- | --- |
| merch_brl | Holt_Winters_Trend | 36933.64 | 44108.81 | 17.97 | 19.74 |
| merch_brl | Moving_Avg_4w | 37447.95 | 45420.54 | 18.22 | 21.02 |
| merch_brl | ARIMA_111 | 37718.76 | 44527.02 | 18.35 | 20.42 |
| merch_brl | Naive | 42718.59 | 50691.96 | 20.78 | 20.42 |
| merch_brl | Lag_Ridge | 44854.64 | 54724.38 | 21.82 | 20.68 |
| merch_brl | Seasonal_Naive_4w | 63302.66 | 74802.84 | 30.8 | 34.11 |

### Order Volume
| target | model | MAE | RMSE | WAPE_pct | MAPE_pct |
| --- | --- | --- | --- | --- | --- |
| delivered_orders | Moving_Avg_4w | 256.75 | 320.28 | 17.14 | 17.91 |
| delivered_orders | ARIMA_111 | 287.91 | 334.7 | 19.22 | 19.63 |
| delivered_orders | Lag_Ridge | 367.28 | 439.98 | 24.51 | 22.59 |
| delivered_orders | Holt_Winters_Trend | 393.05 | 448.95 | 26.23 | 24.55 |
| delivered_orders | Naive | 443.92 | 527.67 | 29.63 | 26.82 |
| delivered_orders | Seasonal_Naive_4w | 465.25 | 548.13 | 31.05 | 33.44 |

## 3. Expanding-Window Cross-Validation (4 Folds x 4 Weeks)
| target | model | MAE | RMSE | WAPE_pct | MAPE_pct |
| --- | --- | --- | --- | --- | --- |
| delivered_orders | Moving_Avg_4w | 176.44 | 199.64 | 11.87 | 13.85 |
| delivered_orders | ARIMA_111 | 176.96 | 203.86 | 12.0 | 14.02 |
| delivered_orders | Lag_Ridge | 234.5 | 251.98 | 15.74 | 17.06 |
| delivered_orders | Naive | 243.94 | 274.65 | 16.65 | 19.14 |
| delivered_orders | Holt_Winters_Trend | 249.03 | 287.36 | 16.99 | 19.86 |
| delivered_orders | Seasonal_Naive_4w | 287.44 | 327.67 | 19.57 | 21.65 |
| merch_brl | Naive | 23437.48 | 28017.42 | 11.0 | 12.74 |
| merch_brl | ARIMA_111 | 24380.54 | 26457.92 | 11.37 | 12.84 |
| merch_brl | Moving_Avg_4w | 25743.51 | 28625.1 | 12.02 | 13.66 |
| merch_brl | Holt_Winters_Trend | 26136.19 | 30307.63 | 12.28 | 14.32 |
| merch_brl | Lag_Ridge | 30257.61 | 33470.86 | 13.96 | 14.7 |
| merch_brl | Seasonal_Naive_4w | 37383.44 | 43643.92 | 17.7 | 19.25 |

**Selected Merchandise Model:** `Holt_Winters_Trend` (Holdout WAPE **17.97%**, MAE **BRL 36,933.64**).
**Selected Order Volume Model:** `Moving_Avg_4w` (Holdout WAPE **17.14%**, MAE **256.8** orders).
