# CommerceIQ — End-to-End Pipeline Automation & CI (Phase 15)

## 1. Automated Pipeline Runner

Script: [`pipelines/run_pipeline.py`](file:///c:/Users/bgunj/Desktop/commerceIQ/pipelines/run_pipeline.py)

### Supported Stages (in Dependency Order)
1. `validate_sources`: Verify all 12 registered raw files and manifest schema.
2. `ingest`: Execute `src/ingestion/extract.py` (`run_ingestion()`).
3. `clean`: Execute `src/transformation/clean.py` (`run_cleaning(export=True)`).
4. `load_db`: Load all 13 cleaned Parquet datasets into MySQL 8.0 (`src/database/load_database.py`).
5. `build_warehouse`: Build 7 dimensions, 5 facts, and 9 data mart views (`src/warehouse/build_warehouse.py`).
6. `sql_analytics`: Execute all 41 SQL analytics queries (`src/analytics/run_sql_analytics.py`).
7. `excel`: Build & recalculate Excel Business Analytics workbook via OpenPyXL + Excel COM (`src/analytics/build_excel_workbook.py`).
8. `analytics`: Execute Decision Intelligence scenario simulations (`src/optimization/decision_simulator.py`).
9. `models`: Train & evaluate forecasting and purchase-time delivery risk models when requested (`--train-models`).
10. `validate`: Run CI-safe unit and repository security checks.

### CLI Examples

```powershell
# Default refresh (skip clean & heavy model retraining)
python pipelines/run_pipeline.py

# Full pipeline including cleaning, Excel rebuild, and model training
python pipelines/run_pipeline.py --stages all --train-models

# Dry-run stage verification
python pipelines/run_pipeline.py --stages all --dry-run
```

## 2. GitHub Actions CI Workflow

Workflow: [`.github/workflows/ci.yml`](file:///c:/Users/bgunj/Desktop/commerceIQ/.github/workflows/ci.yml)

- **`python-and-security-checks`:** Compiles Python modules (`compileall`) and runs `tests/test_ci_synthetic.py` + `tests/test_security.py` using strictly synthetic fixtures (never depends on uncommitted raw/processed data).
- **`mysql-schema-validation`:** Spins up a disposable `mysql:8.0` service container and executes operational (`sql/01_schema/`) and warehouse (`sql/02_warehouse/`) DDL + data mart views.
