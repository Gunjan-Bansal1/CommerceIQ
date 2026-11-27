# CommerceIQ — Operational Relational Database (Phase 5)

## 1. Overview

The operational database `commerceiq` (MySQL 8.0, `utf8mb4` / `utf8mb4_unicode_ci`) stores all 13 cleaned analytical datasets (1,299,152 total rows across 165 fields) produced by Phase 4.

## 2. Schema & Scripts

- `sql/01_schema/01_create_database_and_tables.sql`: Idempotent database and InnoDB table DDL in parent-first dependency order.
- `sql/01_schema/02_indexes_and_constraints.sql`: Analytical indexes for customer, seller, order date/status, payment, review, marketing, and zip lookup queries.
- `sql/01_schema/03_validation_checks.sql`: SQL reconciliation checks for row counts, required FK orphans, optional relationship gaps, financial totals, and UTF-8 / postal formatting.
- `src/database/connection.py`: Environment-driven `mysql.connector` and SQLAlchemy engine helpers.
- `src/database/load_database.py`: Transaction-aware, idempotent batch loader (`load_operational_database()`).
- `docs/diagrams/operational_erd.mmd`: Mermaid entity-relationship diagram.

## 3. Table Granularity & Primary Keys

| Table | Grain | Primary Key | Rows |
|---|---|---|---:|
| `category_translation` | One record per Portuguese category | `(product_category_name)` | 74 |
| `geolocation_lookup` | One representative record per eligible postal prefix | `(zip_code_prefix)` | 19,011 |
| `geolocation` | One cleaned geographic observation | `(geolocation_id)` | 720,495 |
| `brazil_holidays` | One holiday record per date and country | `(date, country_code)` | 42 |
| `marketing_leads` | One record per marketing-qualified lead | `(mql_id)` | 8,000 |
| `sellers` | One record per marketplace seller | `(seller_id)` | 3,095 |
| `customers` | One record per order-specific customer ID | `(customer_id)` | 99,441 |
| `products` | One record per product | `(product_id)` | 32,951 |
| `orders` | One record per order | `(order_id)` | 99,441 |
| `order_items` | One record per item within an order | `(order_id, order_item_id)` | 112,650 |
| `payments` | One record per payment sequence within an order | `(order_id, payment_sequential)` | 103,886 |
| `reviews` | One record per review ID and order ID | `(review_id, order_id)` | 99,224 |
| `closed_deals` | One record per won marketing deal | `(mql_id)` | 842 |

## 4. Constraint Design: Required vs. Optional Relationships

- **8 Required Foreign Keys Enforced (`ON UPDATE RESTRICT ON DELETE RESTRICT`)**:
  - `orders.customer_id -> customers.customer_id`
  - `order_items.order_id -> orders.order_id`
  - `order_items.product_id -> products.product_id`
  - `order_items.seller_id -> sellers.seller_id`
  - `payments.order_id -> orders.order_id`
  - `reviews.order_id -> orders.order_id`
  - `products.product_category_name -> category_translation.product_category_name`
  - `closed_deals.mql_id -> marketing_leads.mql_id`
- **3 Optional Relationships Preserved Without FK Constraints**:
  - `customers.customer_zip_code_prefix -> geolocation_lookup.zip_code_prefix` (279 unmatched rows preserved; flagged by `has_geolocation_match`)
  - `sellers.seller_zip_code_prefix -> geolocation_lookup.zip_code_prefix` (7 unmatched rows preserved; flagged by `has_geolocation_match`)
  - `closed_deals.seller_id -> sellers.seller_id` (462 unmatched rows preserved; flagged by `has_marketplace_seller_match`)

## 5. Type Precision & Representation Decisions

- **Monetary fields** (`order_items.price`, `freight_value`, `item_value_with_freight`, `payments.payment_value`) use `DECIMAL(12,2)`; `closed_deals.declared_monthly_revenue` uses `DECIMAL(14,2)` to preserve exact BRL cents.
- **Postal prefixes** use fixed `CHAR(5)` so leading zeros (e.g., `01001`) are never stripped.
- **Nullable Booleans** (`closed_deals.has_company`, `has_gtin`, `orders.is_on_time_delivery`, product outlier flags) use nullable `TINYINT(1)` so unknown `NULL` values remain distinct from `0` (`False`).
- **Timestamps** use `DATETIME(0)` and dates use `DATE`.

## 6. Execution

```powershell
python src/database/load_database.py
```

Running the loader is idempotent: it verifies DDL/indexes, resets tables safely, reloads all 13 tables inside per-table transactions with `FOREIGN_KEY_CHECKS = 1`, validates all counts and BRL totals, and writes `reports/database_validation_report.md` and `data/metadata/db_load_summary.csv`.
