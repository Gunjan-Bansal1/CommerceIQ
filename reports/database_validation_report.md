# CommerceIQ — Operational Database Loading & Validation Report

**Execution Timestamp (UTC):** 2026-11-27 16:50:02
**Target Database:** `commerceiq` (MySQL 8.0, `utf8mb4` / `utf8mb4_unicode_ci`)
**Total Pipeline Duration:** 148.70 seconds
**Total Records Loaded:** 1,299,152

## 1. Table Load Reconciliation

| Table | Rows Loaded | Duration (sec) | Status |
|---|---:|---:|---|
| `category_translation` | 74 | 0.15 | LOADED |
| `geolocation_lookup` | 19,011 | 1.43 | LOADED |
| `geolocation` | 720,495 | 40.09 | LOADED |
| `brazil_holidays` | 42 | 0.26 | LOADED |
| `marketing_leads` | 8,000 | 0.53 | LOADED |
| `sellers` | 3,095 | 0.19 | LOADED |
| `customers` | 99,441 | 10.83 | LOADED |
| `products` | 32,951 | 4.42 | LOADED |
| `orders` | 99,441 | 34.70 | LOADED |
| `order_items` | 112,650 | 21.83 | LOADED |
| `payments` | 103,886 | 9.04 | LOADED |
| `reviews` | 99,224 | 16.82 | LOADED |
| `closed_deals` | 842 | 0.17 | LOADED |

## 2. Required Foreign-Key Integrity (8/8 Enforced)

| Relationship | Orphan Rows | Status |
|---|---:|---|
| `orders->customers` | 0 | PASS |
| `order_items->orders` | 0 | PASS |
| `order_items->products` | 0 | PASS |
| `order_items->sellers` | 0 | PASS |
| `payments->orders` | 0 | PASS |
| `reviews->orders` | 0 | PASS |
| `products->category_translation` | 0 | PASS |
| `closed_deals->marketing_leads` | 0 | PASS |

## 3. Preserved Optional Relationship Gaps

| Optional Reference | Unmatched Rows | Status |
|---|---:|---|
| `customers->geolocation_lookup_unmatched` | 279 | PRESERVED |
| `sellers->geolocation_lookup_unmatched` | 7 | PRESERVED |
| `closed_deals->sellers_unmatched` | 462 | PRESERVED |

## 4. Exact Financial Reconciliation (BRL)

| Measure | MySQL Total (BRL) | Status |
|---|---:|---|
| `recorded_merchandise_brl` | 13,591,643.70 | EXACT MATCH |
| `recorded_freight_brl` | 2,251,909.54 | EXACT MATCH |
| `recorded_item_total_brl` | 15,843,553.24 | EXACT MATCH |
| `recorded_payment_brl` | 16,008,872.12 | EXACT MATCH |
| `declared_monthly_revenue_brl` | 61,784,006.00 | EXACT MATCH |

## 5. Encoding, Postal Formatting & Null Preservation Checks

- Invalid customer postal prefix lengths (`<> 5`): **0**
- Invalid seller postal prefix lengths (`<> 5`): **0**
- Leading-zero postal prefixes preserved (`0%`): **4,354**
- Nullable boolean `NULL` preserved (`closed_deals.has_company IS NULL`): **779**
- UTF-8 Portuguese diacritic reviews preserved: **37,592**
