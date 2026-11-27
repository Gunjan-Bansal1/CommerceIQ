# CommerceIQ — End-to-End E-Commerce Analytics, BI & Predictive Decision Platform

[![CommerceIQ CI](https://github.com/Gunjan-Bansal1/CommerceIQ/actions/workflows/ci.yml/badge.svg)](https://github.com/Gunjan-Bansal1/CommerceIQ/actions/workflows/ci.yml)

**CommerceIQ** is an independent, end-to-end Data Analytics, Data Engineering, Business Intelligence, Statistical Inference, and Predictive Modeling portfolio project built on historical Brazilian e-commerce and marketing funnel datasets (`2016–2018`).

> **Disclaimer:** CommerceIQ is an independent educational portfolio case study. It is not commissioned by, affiliated with, or deployed in Olist's production environment. Recorded merchandise values (BRL) are not marketplace revenue or profit, and decision simulations use clearly labeled illustrative assumptions.

---

## Key Verified Results & Business Findings

| Domain | Verified Metric / Finding | Source |
|---|---|---|
| **Data Scale** | **1,559,806** raw rows (`12` files) → **1,299,152** cleaned rows (`13` tables, `165` fields, `27` engineered features) | [`clean.py`](file:///c:/Users/bgunj/Desktop/commerceIQ/src/transformation/clean.py) |
| **Commercial Baseline** | **99,441** placed orders (**96,478** delivered) \| **BRL 13,221,498.11** delivered merchandise \| **BRL 13,591,643.70** recorded GMV \| **BRL 16,008,872.12** recorded payments | [`sql_analytics_report.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/sql_analytics_report.md) |
| **Unsuccessful Exposure** | **1,234** canceled/unavailable orders (**1.24%**) \| **BRL 97,242.96** known item exposure (missing item rows flagged cleanly) | [`02_revenue_leakage_and_exceptions.sql`](file:///c:/Users/bgunj/Desktop/commerceIQ/sql/03_analytics/02_revenue_leakage_and_exceptions.sql) |
| **Customer Retention** | **93,358** unique delivered customers (`customer_unique_id`) \| **2,801** repeat buyers (**3.00%** repeat rate) \| **BRL 141.62** mean spend | [`customer_intelligence_report.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/customer_intelligence_report.md) |
| **Logistics & SLA** | **93.2269%** on-time rate (`89,936 / 96,470` eligible) \| **12.56 days** mean delivery (**9.33 days** carrier transit) | [`eda_findings_report.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/eda_findings_report.md) |
| **Statistical Impact** | Late deliveries drop mean rating by **2.02 stars** (`4.29` on-time vs. `2.27` late; Mann-Whitney *p* < 1e-100, Cohen *d* = **1.71**) | [`statistical_findings_report.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/statistical_findings_report.md) |
| **Marketing Funnel** | **8,000** qualified leads → **842** closed deals (**10.53%** conversion; **380** matched to marketplace `sellers`) | [`05_logistics_geo_payment_marketing_experience.sql`](file:///c:/Users/bgunj/Desktop/commerceIQ/sql/03_analytics/05_logistics_geo_payment_marketing_experience.sql) |
| **Demand Forecasting** | 12-week holdout: Holt-Winters **17.97% WAPE** (merch BRL); 4-week Moving Avg **17.14% WAPE** (order volume) | [`forecasting_model_card.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/forecasting_model_card.md) |
| **Checkout Delay Risk** | Zero-leakage `HistGradientBoosting` on unseen Jun–Aug 2018 orders: **0.7325 ROC-AUC**, **0.0771 PR-AUC** (>2.1x baseline) | [`delivery_risk_model_card.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/delivery_risk_model_card.md) |

---

## System Architecture & Pipeline Flow

```text
Raw CSVs (12) ─▶ Ingestion (SHA-256) ─▶ Cleaning (13 Parquet/CSV) ─▶ MySQL 8.0 Operational DB (13 Tables)
                                                                              │
                                                                              ▼
Power BI PBIP (39 DAX, 10 Pages) ◀─ Warehouse Star Schema (7 Dims, 5 Facts, 9 Marts) ─▶ 41 Domain SQL Queries
        ▲                                     │                                                  │
        │                                     ▼                                                  ▼
  ML & Decision CSVs ◀── Python EDA, Stats, RFM/Cohorts, Forecasting, Risk ML ──▶ Excel COM Workbook (Pivot/Slicers)
```

Diagram sources in [`docs/diagrams/`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/diagrams/):
- [`system_architecture.mmd`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/diagrams/system_architecture.mmd)
- [`operational_erd.mmd`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/diagrams/operational_erd.mmd)
- [`warehouse_star_schema.mmd`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/diagrams/warehouse_star_schema.mmd)
- [`ml_and_bi_workflow.mmd`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/diagrams/ml_and_bi_workflow.mmd)

---

## Technology Stack

- **Data Engineering & Testing:** Python 3.13.3, Pandas 3.1.1, NumPy 2.5.5, PyArrow 26.0, Pytest 9.2, GitHub Actions
- **Database & Warehouse:** MySQL 8.0.44, SQLAlchemy 2.1.9, `mysql-connector-python`
- **Business Intelligence:** Microsoft Excel (OpenPyXL + Excel 16.0 COM PivotTables/Slicers + Power Query `.pq`), Power BI (PBIP, TMDL Semantic Model, DAX, PBIR)
- **Analytics & ML:** Matplotlib, Seaborn, SciPy, Statsmodels, Scikit-Learn, Python-PPTX

---

## Project Structure

- `config.yaml`, `.env.example`, `requirements.txt` — Configuration & pinned environment dependencies
- `src/ingestion/extract.py` — SHA-256 verified raw CSV ingestion
- `src/transformation/clean.py` — Deterministic cleaning, deduplication, lookup & feature pipeline
- `src/database/` & `sql/01_schema/` — MySQL 8.0 operational DDL, indexes, loader, and validation SQL
- `src/warehouse/` & `sql/02_warehouse/` — Star schema (7 dims, 5 facts) & 9 business data marts
- `sql/03_analytics/` & `src/analytics/run_sql_analytics.py` — 41 executed SQL queries tracing 120 business questions
- `excel/` & `src/analytics/build_excel_workbook.py` — Executive Excel workbook, Decision Simulator, and Power Query `.pq` scripts
- `powerbi/` — Native Power BI Project (`CommerceIQ.pbip`), TMDL semantic model, 39 DAX measures, and theme JSON
- `notebooks/` — 8 executed Jupyter notebooks (`00_data_ingestion` through `07_delivery_risk_classification`) with outputs preserved
- `src/forecasting/` & `src/optimization/` — Forecasting, zero-leakage delivery risk classification, and decision simulator
- `pipelines/run_pipeline.py` & `.github/workflows/ci.yml` — End-to-end automated CLI runner and CI workflow
- `docs/`, `reports/`, `presentation/` — Business requirements, KPI/question traceability, technical docs, executive PPTX, case study, and interview prep
- `tests/` — Ingestion, cleaning, CI-synthetic, cross-tool reconciliation, and security test suites

---

## Reproduction Instructions

1. **Setup Environment & Datasets**
   - Obtain the public [Olist E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and [Marketing Funnel](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) CSVs and place them under `data/raw/` per [`docs/data_sources.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/docs/data_sources.md).
   - Copy `.env.example` to `.env` and set local MySQL credentials (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME=commerceiq`).
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **Run the Full Automated Pipeline**
   ```powershell
   python pipelines/run_pipeline.py --stages all --train-models
   ```
3. **Run Tests**
   ```powershell
   python -m pytest tests/ -v
   ```
4. **Open Power BI Project**
   - Open `powerbi/CommerceIQ.pbip` in Power BI Desktop, enter local MySQL credentials for `commerceiq`, and click **Refresh**.

---

## Known Limitations & Licensing

- **Historical Snapshot:** Covers 2016–2018 (core period Jan 2017–Aug 2018); forecasts are backtests/illustrative continuations.
- **Unrecorded Financials:** Marketplace commissions, COGS, profit margins, CAC, ROAS, and refunds are absent from source data.
- **Cross-Dataset Linkage:** 462 of 842 closed marketing deals have no matching marketplace `seller_id`; `GEO-08` (per-capita orders) is infeasible without external population data.
- **Licensing:** Olist datasets are used under CC BY-NC-SA 4.0 (educational/non-commercial); raw and processed datasets are excluded from version control via `.gitignore`.
