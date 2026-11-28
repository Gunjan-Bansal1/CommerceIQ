# CommerceIQ — Quality Assurance, Cross-Tool KPI Reconciliation & Limitations Register (Phase 16)

## 1. Cross-Tool KPI Reconciliation Matrix

| KPI / Measure | Python (Parquet) | MySQL Operational DB | MySQL Data Warehouse | SQL Analytics (`01_exec`) | Excel Workbook (COM Cached) | Power BI DAX Spec | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Total Placed Orders | 99,441 | 99,441 | 99,441 | 99,441 | 99,441 | 99,441 | EXACT MATCH |
| Delivered Orders | 96,478 | 96,478 | 96,478 | 96,478 | 96,478 | 96,478 | EXACT MATCH |
| Recorded GMV All Statuses (BRL) | 13,591,643.70 | 13,591,643.70 | 13,591,643.70 | 13,591,643.70 | 13,591,643.70 | 13,591,643.70 | EXACT MATCH |
| Delivered Merchandise Value (BRL) | 13,221,498.11 | 13,221,498.11 | 13,221,498.11 | 13,221,498.11 | 13,221,498.11 | 13,221,498.11 | EXACT MATCH |
| Recorded Freight Value (BRL) | 2,251,909.54 | 2,251,909.54 | 2,251,909.54 | 2,251,909.54 | 2,251,909.54 | 2,251,909.54 | EXACT MATCH |
| Recorded Payment Value (BRL) | 16,008,872.12 | 16,008,872.12 | 16,008,872.12 | 16,008,872.12 | 16,008,872.12 | 16,008,872.12 | EXACT MATCH |
| Declared Monthly Revenue (BRL) | 61,784,006.00 | 61,784,006.00 | 61,784,006.00 | — | — | — | EXACT MATCH |
| Eligible Delivery SLA Orders | 96,470 | 96,470 | 96,470 | 96,470 | 96,470 | 96,470 | EXACT MATCH |
| On-Time Delivery Rate (%) | 93.2269% | 93.2269% | 93.2269% | 93.2269% | 93.2269% | 93.2269% | EXACT MATCH |

## 2. Automated Test Execution Summary (`pytest tests/ -v`)

- **Total Tests Executed:** **43** | **Passed:** **43** | **Failed:** **0** | **Skipped:** **0**
  - `tests/test_ingestion.py`: **14 / 14 PASSED**
  - `tests/test_cleaning.py`: **13 / 13 PASSED**
  - `tests/test_ci_synthetic.py`: **5 / 5 PASSED**
  - `tests/test_security.py`: **3 / 3 PASSED**
  - `tests/test_streamlit_app.py`: **2 / 2 PASSED** (all 10 pages + interactive checkout delay-risk prediction form)
  - `tests/test_warehouse_and_models.py`: **6 / 6 PASSED** (MySQL/warehouse reconciliation, cross-tool KPI reconciliation, ML leakage guard, pipeline metadata, PBIR/TMDL bindings, and source-data relationship & `dim_date` compatibility)
- **Pipeline Automation Execution:** `pipelines/run_pipeline.py --stages validate_sources,sql_analytics,analytics,validate` succeeded in **126.61s** (`data/metadata/pipeline_execution_summary.json`).

## 3. Security & Repository Integrity Audit

- `.env`, `.venv/`, `data/raw/`, `data/processed/`, `logs/`, and `models/*.joblib` remain excluded by `.gitignore`.
- `git ls-files` verified zero tracked credentials, raw/processed datasets, or binary models.
- No hardcoded database passwords exist in `src/`, `pipelines/`, `app/`, or `sql/`.

## 4. Closure Notes & Known Scope Boundaries

1. **`GEO-08` (Orders Relative to Population):** Marked infeasible because external Brazilian population data was outside the 12 source datasets.
2. **Profit, Commission, CAC, ROAS, Refunds:** Excluded from source Olist datasets; monetary values represent recorded BRL merchandise/freight/payment amounts, and Phase 14 scenario financials are explicitly labeled illustrative.
3. **Marketing Seller Activation (`MKT-08`):** 462 of 842 closed deals lack matching `seller_id` in `sellers` (preserved as expected linkage gap).
4. **Power BI Desktop Validation (`powerbi/CommerceIQ.pbip`):** Agent-automated checks verified 17 TMDL tables, 15 relationships, 61 DAX measures, 10 pages / 84 bound visuals (`0` unbound), `dim_date` filtering, `TINYINT(1)` integer normalization, and live MySQL/CSV key compatibility; user manually confirmed MySQL Connector/NET installation, MySQL connectivity, and clean semantic model refresh in Power BI Desktop. Optional `powerbi/screenshots/` exports were not generated.
5. **Public GitHub Actions CI Run:** Triggered automatically upon pushing `main` to `origin/main`.
