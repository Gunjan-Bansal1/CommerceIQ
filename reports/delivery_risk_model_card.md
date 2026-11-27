# CommerceIQ — Model Card: Purchase-Time Delivery Delay Risk Classification

## 1. Intended Use & Anti-Leakage Controls
- **Prediction Moment:** Order checkout (`order_purchase_timestamp`).
- **Target:** `is_late` (`delivery_deviation_days > 0`) among eligible delivered orders.
- **Zero-Leakage Guarantee:** Excludes actual delivery, carrier handover, approval timestamps, review scores, and future seller outcomes. Seller historical late rate uses strictly prior orders already delivered before the current purchase timestamp.
- **Temporal Splits:** Train (< 2018-03-01: n=57,317, late=6.60%) | Validation (2018-03..2018-05: n=20,550, late=10.11%) | Test (>= 2018-06-01: n=18,603, late=3.61%).

## 2. Unseen Test Model Comparison
| model | val_roc_auc | val_pr_auc | test_roc_auc | test_pr_auc | val_opt_threshold | test_precision | test_recall | test_f1 | test_brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hist_Gradient_Boosting | 0.698 | 0.1966 | 0.7325 | 0.0771 | 0.4709 | 0.0854 | 0.5923 | 0.1492 | 0.1629 |
| Logistic_Regression | 0.723 | 0.2241 | 0.6581 | 0.0629 | 0.6344 | 0.0661 | 0.2411 | 0.1038 | 0.2154 |
| Decision_Tree | 0.6595 | 0.1617 | 0.6169 | 0.0559 | 0.4751 | 0.0633 | 0.3839 | 0.1087 | 0.1707 |
| Random_Forest | 0.7035 | 0.2082 | 0.6354 | 0.0519 | 0.4923 | 0.052 | 0.1399 | 0.0758 | 0.1595 |
| Dummy_Stratified | 0.4967 | 0.1005 | 0.5039 | 0.0364 | 0.0 | 0.0361 | 1.0 | 0.0697 | 0.0963 |

## 3. Selected Model Confusion Matrix (`Hist_Gradient_Boosting`, threshold=0.4709)
- True Negatives: **13,666** | False Positives: **4,265**
- False Negatives: **274** | True Positives: **398**

## 4. Top Purchase-Time Drivers (Permutation Importance)
| feature | importance_mean | importance_std |
| --- | --- | --- |
| estimated_delivery_days | 0.04688 | 0.00033 |
| approx_distance_km | 0.0139 | 0.00276 |
| is_same_state | 0.00614 | 0.00524 |
| category_grouped | 0.00287 | 0.00043 |
| primary_payment_type | 0.0017 | 0.00072 |
| distinct_sellers | 0.00136 | 0.00117 |
| customer_region | 0.00107 | 0.00447 |
| item_count | 0.00096 | 0.0006 |
| purchase_hour | 0.00083 | 0.00122 |
| seller_prior_late_rate | 0.00058 | 0.00196 |

## 5. Limitations
- Trained on historical 2017–2018 delivered orders; non-delivered/canceled orders are excluded from target evaluation.
- Offline experimental evaluation only; not deployed into live production checkout.
