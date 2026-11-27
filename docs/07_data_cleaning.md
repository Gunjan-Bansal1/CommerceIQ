# CommerceIQ - Data Cleaning and Transformation

## 1. Overview

Phase 4 transforms the original Olist e-commerce,
marketing funnel and Brazilian holiday datasets into
validated, analysis-ready datasets.

The transformation process preserves raw source files
and existing business records while addressing
structural, numerical, categorical, temporal and
geographic data quality issues.

## 2. Technology Stack

- Python
- Pandas
- NumPy
- Python Decimal
- PyArrow
- OpenPyXL
- Pytest
- Jupyter Notebook

## 3. Final Cleaning Results

| Metric | Result |
|---|---:|
| Original datasets | 12 |
| Final datasets | 13 |
| Original records | 1,559,806 |
| Geographic duplicates removed | 279,668 |
| Derived and mapping records added | 19,014 |
| Final records | 1,299,152 |
| Original fields | 81 |
| Final fields | 165 |
| Business features created | 27 |
| Cleaning actions | 107 |
| Quality observations reviewed | 43 |
| Final validation checks passed | 20/20 |
| Export validations passed | 26/26 |
| Standalone checksum matches | 26/26 |

## 4. Transformation Methodology

### 4.1 Schema and Missing-Value Standardization

- Standardized column names using snake_case.
- Corrected product metadata spelling inconsistencies.
- Converted empty and whitespace-only strings into
  missing values.
- Preserved numeric zeros and source-defined categories.
- Retained original column mappings for traceability.

### 4.2 Analytical Data Types

- Identifiers and postal prefixes remain strings.
- Integer and Boolean fields use nullable Pandas types.
- Monetary values use Python Decimal.
- Timestamp fields use datetime representations.
- JSON metadata is validated and retained as serialized text.

### 4.3 Duplicate Resolution

Removed 261,831 exact geographic duplicates and
17,837 additional duplicates after text normalization.

Preserved legitimate customer repetitions, multiple
reviews per order and all transactional records.

### 4.4 Missing-Value Treatment

- Assigned unknown to 610 missing product categories.
- Assigned not_recorded to 60 missing marketing origins.
- Removed the completely empty launch_year field.
- Preserved unavailable timestamps, optional reviews,
  seller declarations and product measurements.
- Avoided unsupported statistical imputation.

### 4.5 Categorical Standardization

Standardized geographic labels, state abbreviations
and business categories.

Added three project-defined category translations,
including the unknown reporting category.

All 32,951 products now have a category lookup match.

### 4.6 Numerical Anomalies

Converted four zero product weights into missing
measurements and preserved source anomaly flags.

Retained zero freight, payment, installment and
declared revenue observations.

Potential statistical outliers remain available
with explicit IQR-based quality indicators.

The BRL 10 million declared revenue screening
threshold is provisional and is not an independently
verified industry benchmark.

### 4.7 Temporal Validation

Preserved original timestamp values after their
documented analytical type conversion.

Created chronological quality flags and
metric-specific eligibility indicators.

The core reporting period is January 2017 through
August 2018. Boundary-period records remain available.

The 180-day shipping deadline threshold is a
provisional screening rule, not a contractual SLA.

### 4.8 Geographic Transformation

Created a postal prefix lookup using representative
city-state combinations and median coordinates.

- Remaining geographic observations: 720,495
- Observations excluded from lookup: 27
- Unique postal prefixes: 19,011
- Ambiguous postal prefixes: 552

Coordinates are approximate representative locations,
not verified customer or seller addresses.

The Brazil coordinate screening envelope is not
an authoritative national boundary.

### 4.9 Referential Integrity

Validated eleven dataset relationships:

- Eight required relationships have complete matches.
- Three optional relationships have documented gaps.
- Geographic joins preserve original record counts.

Unmatched records remain available for analysis.

Joining multiple transaction tables directly may
still multiply rows. Aggregate at the intended
business grain before performing such joins.

### 4.10 Business Feature Engineering

Created 27 business features covering:

- Purchase calendar attributes
- Approval, processing and delivery durations
- Delivery performance
- Merchandise and freight calculations
- Product volume and density
- Review availability and rating classification
- Marketing conversion duration

Rating classification is rule-based and does not
represent text sentiment analysis.

Post-outcome features must not be used in predictive
models when they would introduce data leakage.

## 5. Financial Integrity

All original monetary observations were preserved.

| Measure | Amount in BRL |
|---|---:|
| Recorded merchandise value | 13,591,643.70 |
| Recorded freight value | 2,251,909.54 |
| Recorded merchandise plus freight | 15,843,553.24 |
| Recorded payment value | 16,008,872.12 |
| Declared seller monthly revenue | 61,784,006.00 |

These are recorded dataset amounts, not verified
marketplace revenue, profit or settled payments.

Seller-declared revenue remains unverified.

## 6. Data Quality Reconciliation

| Status | Observations |
|---|---:|
| Resolved | 7 |
| Controlled | 26 |
| Accepted limitation | 10 |
| Total | 43 |

Remaining missing values are intentional where
source information cannot be reliably established.

The final dataset contains 186,367 missing cells,
including nullable quality and business indicators.

## 7. Processed Dataset Formats

Both CSV and typed Parquet files are generated
for each of the thirteen datasets.

| Format | Files | Storage |
|---|---:|---:|
| CSV | 13 | 150.26 MiB |
| Parquet | 13 | 58.95 MiB |

Parquet achieved a 60.77% storage reduction.

CSV supports database and business intelligence
integration. Parquet preserves typed analytical
representations including fixed-precision decimals.

Processed data remains local and is excluded
from version control.

## 8. Reproducing the Pipeline

Run the following commands from the project root
using the configured virtual environment:

```bash
python -m pip install -r requirements.txt
python src/transformation/clean.py
python -m pytest tests/test_ingestion.py tests/test_cleaning.py -v
```

## 9. Phase 4 Deliverables

- `src/transformation/clean.py`: Reusable standalone cleaning pipeline (`run_cleaning(export=True)`).
- `notebooks/02_data_cleaning.ipynb`: Interactive transformation notebook with preserved execution outputs.
- `data/processed/`: 13 cleaned CSV files, 13 typed Parquet files, and `processed_schema.json`.
- `data/metadata/cleaning_summary.csv` and `data/metadata/processed_manifest.csv`: Summary metrics and SHA-256 export manifest.
- `reports/data_cleaning_report.xlsx`: 35-worksheet transformation audit workbook.
- `tests/test_cleaning.py`: Session-scoped regression test suite covering schema, keys, finances, delivery, relationships, and exports.
