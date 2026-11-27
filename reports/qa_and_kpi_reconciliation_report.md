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

- **Total Tests Executed:** **39** | **Passed:** **39** | **Failed:** **0** | **Skipped:** **0**
  - `tests/test_ingestion.py`: **14 / 14 PASSED**
  - `tests/test_cleaning.py`: **13 / 13 PASSED**
  - `tests/test_ci_synthetic.py`: **5 / 5 PASSED**
  - `tests/test_security.py`: **3 / 3 PASSED**
  - `tests/test_warehouse_and_models.py`: **4 / 4 PASSED**
- **Pipeline Automation Execution:** `pipelines/run_pipeline.py --stages validate_sources,sql_analytics,analytics,validate` succeeded in **126.61s** (`data/metadata/pipeline_execution_summary.json`).

## 3. Security & Repository Integrity Audit

- `.env`, `.venv/`, `data/raw/`, `data/processed/`, `logs/`, and `models/*.joblib` remain excluded by `.gitignore`.
- `git ls-files` verified zero tracked credentials, raw/processed datasets, or binary models.
- No hardcoded database passwords exist in `src/`, `pipelines/`, or `sql/`.

## 4. Remaining Limitations & Unresolved Items Register

1. **`GEO-08` (Orders Relative to Population):** Marked infeasible because external Brazilian population data was outside the 12 source datasets.
2. **Profit, Commission, CAC, ROAS, Refunds:** Excluded from source Olist datasets; monetary values represent recorded BRL merchandise/freight/payment amounts, and Phase 14 scenario financials are explicitly labeled illustrative.
3. **Marketing Seller Activation (`MKT-08`):** 462 of 842 closed deals lack matching `seller_id` in `sellers` (preserved as expected linkage gap).
4. **Power BI Desktop Interactive GUI Refresh:** PBIP, TMDL semantic model, 39 DAX measures, M queries, 10-page PBIR layout, theme JSON, and DAX-to-SQL KPI reconciliation are complete. Interactive opening/refresh in `PBIDesktopStore.exe` and visual screenshot export remain a manual GUI step.
5. **Public GitHub Actions CI Run:** `.github/workflows/ci.yml` is authored locally; remote CI execution occurs upon `git push origin main`.
