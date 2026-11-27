# CommerceIQ — Technical & Business Interview Preparation Guide

## 1. 30-Second Elevator Pitch
> "I built **CommerceIQ**, an end-to-end e-commerce analytics, business intelligence, and predictive decision platform using 1.56 million historical Brazilian marketplace records from Olist. I engineered a SHA-256 verified Python ETL pipeline, a MySQL 8.0 operational database and Kimball star-schema warehouse, 41 domain SQL queries, an Excel COM workbook, a Power BI PBIP semantic model with 39 DAX measures, statistical hypothesis tests, RFM/cohort customer analytics, and a leakage-free checkout delivery-risk model—all reconciled to the exact cent across tools and backed by automated pytest suites and GitHub Actions CI."

## 2. Two-Minute Project Explanation
- **Context & Scope:** An e-commerce marketplace generates disconnected order, item, payment, review, seller, geolocation, and marketing funnel logs. I started with business requirements—defining 72 KPIs and 120 business questions—before writing ETL code.
- **Engineering & Data Modeling:** Raw ingestion (`src/ingestion/extract.py`) validates SHA-256 checksums and keeps strings/leading zeros intact. Cleaning (`src/transformation/clean.py`) deduplicates 279,668 geolocation rows into a unique 19,011-prefix `geolocation_lookup`, flags 43 quality observations, and exports 13 typed Parquet/CSV datasets (1,299,152 rows). I loaded them into MySQL 8.0 enforcing 8 required foreign keys while preserving 3 optional linkage gaps, then built a 7-dimension, 5-fact constellation warehouse where `fact_orders` pre-aggregates items, payments, and reviews at `order_id` grain so multi-item/multi-payment joins never inflate revenue.
- **Analytics, ML & Insights:** Across 96,478 delivered orders (BRL 13.22M merchandise value), statistical testing confirmed late deliveries impose a **2.02-star** rating drop (Cohen *d* = 1.71, Holm adj. *p* < 1e-100), carrier transit accounts for 74% of delivery duration, and only **3.00%** of persistent customers (`customer_unique_id`) make repeat purchases. I trained a zero-leakage checkout delay-risk classifier (`HistGradientBoosting`, **0.7325 ROC-AUC** on unseen temporal test orders) and built an illustrative Low/Base/High decision simulator plus end-to-end CLI automation (`pipelines/run_pipeline.py`).

## 3. Detailed Architecture Walkthrough
`Raw CSVs (12)` → `extract.py (SHA-256)` → `clean.py (13 Parquet/CSV)` → `load_database.py (MySQL 8.0 Operational)` → `build_warehouse.py (7 Dims, 5 Facts, 9 Marts)` → `SQL Analytics (41 Queries) / Excel COM / Power BI PBIP / Python EDA-Stats-RFM-ML-Decision` → `pipelines/run_pipeline.py + pytest + GitHub Actions CI`.

## 4. Core Interview Questions & Implementation-Grounded Answers

### Business Understanding & Governance
- **Q: Why can't you call `SUM(price)` "marketplace revenue" or "profit"?**  
  **A:** Olist datasets record item merchandise prices (`BRL 13,591,643.70` total, `BRL 13,221,498.11` delivered) and freight charged (`BRL 2,251,909.54`), not Olist's commission rate, COGS, or refund settlements. Calling GMV "profit" would mislead executives, so CommerceIQ separates delivered merchandise value, freight, payment value, unsuccessful order exposure, and illustrative simulation assumptions.
- **Q: Which business question could NOT be answered and why?**  
  **A:** `GEO-08` (orders relative to state/city population) because external IBGE demographic data was outside the 12 validated source datasets. Documented in `docs/10_kpi_and_question_traceability.md` instead of fabricating denominators.

### SQL, Database Design & Data Warehousing
- **Q: How did you prevent join fan-out when combining orders, items, payments, and reviews?**  
  **A:** An order can have multiple items (`112,650` rows for `99,441` orders), multiple payment records (`103,886` rows), and multiple reviews. Joining them directly multiplies monetary totals. In `sql/02_warehouse/02_build_warehouse_tables.sql`, `fact_orders` aggregates `order_items`, `payments`, and `reviews` independently in CTEs (`agg_items`, `agg_payments`, `agg_reviews`) at `order_id` grain *before* `LEFT JOIN`ing to `orders`.
- **Q: Why didn't you put foreign keys on `customers.customer_zip_code_prefix` or `closed_deals.seller_id`?**  
  **A:** Phase 3/4 profiling proved 279 customer zip prefixes, 7 seller zip prefixes, and 462 closed-deal seller IDs do not exist in the parent tables. Enforcing hard FKs would force us to drop valid business records or invent dummy keys. Instead, we preserved all rows, added boolean match flags (`has_geolocation_match`, `has_marketplace_seller_match`), and used `-1` unknown dimension members (`dim_geography`, `dim_seller`) in the warehouse.
- **Q: Why use `customer_unique_id` instead of `customer_id`?**  
  **A:** In Olist's schema, `customer_id` is 1:1 with `order_id` (`99,441` unique values). Treating `customer_id` as a person would make repeat-purchase rate 0%. Grouping by `customer_unique_id` reveals `93,358` unique delivered customers and `2,801` repeat customers (`3.00%`).

### Python, Pandas & Data Quality
- **Q: How did you preserve leading zeros in Brazilian postal codes and exact monetary precision?**  
  **A:** Ingestion reads CSVs with `dtype=str, keep_default_na=False`. Cleaning stores zip prefixes as 5-char strings (`CHAR(5)` in MySQL) and monetary fields as Python `Decimal` in Parquet (`decimal128(18, 2)`) and `DECIMAL(12,2)` in MySQL.
- **Q: How did you resolve geographic many-to-many joins?**  
  **A:** Raw geolocation had 1,000,163 rows with 279,668 duplicates and 552 ambiguous prefixes mapping to multiple city/state labels. I built `geolocation_lookup` (19,011 unique `zip_code_prefix` rows) using the dominant city-state combination and median coordinates after excluding 27 out-of-envelope coordinates.

### Excel & Power BI / DAX
- **Q: Why did `XLOOKUP` written by OpenPyXL initially evaluate to `0` in Excel COM?**  
  **A:** Modern dynamic Excel functions like `XLOOKUP` require the `_xlfn.XLOOKUP` namespace prefix in OpenXML formulas when generated outside Excel; otherwise Excel returns `#NAME?` (caught by `IFERROR`). Prefixing `_xlfn.XLOOKUP` resolved it cleanly (`health_beauty` reconciled to `BRL 1,233,131.72`).
- **Q: Why does Power BI have both `fact_orders` and `fact_order_items`?**  
  **A:** `fact_orders` answers order-grain SLA, payment reconciliation, and AOV measures cleanly, while `fact_order_items` enables category/product/seller slicing without distorting order-level counts. Explicit DAX measures in `_Measures` (`powerbi/dax/commerceiq_measures.dax`) enforce consistent filters (`is_delivered = 1`).

### Statistics & Machine Learning
- **Q: Why use Mann-Whitney U and Kruskal-Wallis alongside Welch's t-test, plus Holm-Bonferroni correction?**  
  **A:** Review ratings (1–5 discrete skewed scale) and delivery durations (right-skewed) violate normality, and Levene's test confirmed unequal variance. Running 5+ tests inflates Type I error, so Holm-Bonferroni keeps family-wise error controlled, while Cohen's *d* (1.71 for late deliveries) and $\epsilon^2$ (0.0092 for category duration) distinguish practical importance from mere sample-size significance.
- **Q: How did you guarantee ZERO data leakage in the delivery delay risk classifier?**  
  **A:** Prediction happens at checkout (`order_purchase_timestamp`). We excluded all post-checkout timestamps (`order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`), actual durations, and reviews. Even the historical `seller_prior_late_rate` was computed via `np.searchsorted` on `order_delivered_customer_date`, so an order's lateness only enters a seller's history *after* it was actually delivered! And we used a strict chronological train/validation/test split (`<2018-03` / `2018-03..05` / `>=2018-06`).

### Hard Implementation Challenges Solved
1. **MySQL 8.0 Reserved Word (`YEAR_MONTH`):** `CREATE TABLE dim_date` failed with syntax error 1064 because `YEAR_MONTH` is a MySQL interval keyword; renamed to `year_month_str`.
2. **Pandas 3.1 Nullable Dtypes in Scikit-Learn:** `Float64`/`Int64`/`string` columns containing `pd.NA` triggered `boolean value of NA is ambiguous` inside `SimpleImputer`/`np.where`; resolved by casting numeric features to `float64` and categoricals to `object` before the `ColumnTransformer`.
3. **Notebook Cell `Step 4.14A` `_IncompleteInputError`:** Repaired the truncated triple-quoted docstring in `notebooks/02_data_cleaning.ipynb` in-place while preserving all prior cells' outputs and metadata.
4. **Public CI Without Restricted Data:** Separated CI-safe synthetic tests (`tests/test_ci_synthetic.py`, `tests/test_security.py`) plus a disposable `mysql:8.0` schema container in `.github/workflows/ci.yml` from full local integration tests (`tests/test_cleaning.py`, `tests/test_warehouse_and_models.py`).
