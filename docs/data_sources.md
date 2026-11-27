# CommerceIQ — Data Sources and Provenance

## 1. Document Information

| Attribute | Value |
|---|---|
| Project | CommerceIQ |
| Project version | 0.1.0 |
| Document | Data Sources and Provenance |
| Geography | Brazil |
| Currency | BRL |
| Data classification | Historical public datasets |
| Project purpose | Educational and non-commercial portfolio analysis |
| Registered datasets | 12 |
| Total source records | 1,559,806 |
| Documentation date | 2026-11-27 |

## 2. Data Source Overview

CommerceIQ integrates three independent data sources:

1. Olist Brazilian E-Commerce Public Dataset
2. Olist Marketing Funnel Dataset
3. Nager.Date Brazilian Holiday API

These sources support historical analysis of marketplace
transactions, customers, sellers, products, payments,
logistics, customer satisfaction, marketing performance
and calendar-related patterns.

| Source | Files | Acquisition method |
|---|---:|---|
| Olist E-Commerce | 9 | Kaggle CSV download |
| Olist Marketing Funnel | 2 | Kaggle CSV download |
| Nager.Date | 1 | REST API |
| Total | 12 | Multiple sources |

## 3. Source 1 — Olist Brazilian E-Commerce

### 3.1 Source Information

- Publisher: Olist
- Platform: Kaggle
- Source URL:
  https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Geography: Brazil
- Historical coverage: 2016–2018
- Data format: CSV
- Encoding: UTF-8
- Acquisition method: Manual download
- License: CC BY-NC-SA 4.0
- Storage directory: data/raw/ecommerce/

### 3.2 Dataset Inventory

| Dataset | Original filename | Rows | Columns |
|---|---|---:|---:|
| Orders | olist_orders_dataset.csv | 99,441 | 8 |
| Customers | olist_customers_dataset.csv | 99,441 | 5 |
| Order Items | olist_order_items_dataset.csv | 112,650 | 7 |
| Payments | olist_order_payments_dataset.csv | 103,886 | 5 |
| Reviews | olist_order_reviews_dataset.csv | 99,224 | 7 |
| Products | olist_products_dataset.csv | 32,951 | 9 |
| Sellers | olist_sellers_dataset.csv | 3,095 | 4 |
| Geolocation | olist_geolocation_dataset.csv | 1,000,163 | 5 |
| Category Translation | product_category_name_translation.csv | 71 | 2 |

### 3.3 Business Applications

- Marketplace merchandise value analysis
- Order volume and growth analysis
- Customer acquisition and retention
- Customer segmentation
- Product and category performance
- Seller performance
- Payment behaviour
- Delivery performance
- Freight analysis
- Customer satisfaction
- Geographic market analysis
- Review sentiment analysis

### 3.4 Data Limitations

- The dataset represents historical activity.
- Customer and seller identifiers are anonymized.
- Actual marketplace commissions and platform revenue
  are not provided.
- Product procurement costs and operating expenses
  are not available.
- Actual profit margins cannot be calculated directly.
- Actual inventory and stock availability are unavailable.
- Refund amounts are not explicitly available.
- Cancelled-order merchandise value can only be measured
  where corresponding order-item information exists.
- Geographic coordinates may contain multiple observations
  for the same postal code.
- Payment and order-item records may have different
  levels of granularity.
- Historical observations must not be presented as
  current Olist business performance.

## 4. Source 2 — Olist Marketing Funnel

### 4.1 Source Information

- Publisher: Olist
- Platform: Kaggle
- Source URL:
  https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist
- Geography: Brazil
- Lead acquisition period: June 2017 to May 2018
- Data format: CSV
- Encoding: UTF-8
- Acquisition method: Manual download
- License: CC BY-NC-SA 4.0
- Storage directory: data/raw/marketing/

### 4.2 Dataset Inventory

| Dataset | Original filename | Rows | Columns |
|---|---|---:|---:|
| Marketing Leads | olist_marketing_qualified_leads_dataset.csv | 8,000 | 4 |
| Closed Deals | olist_closed_deals_dataset.csv | 842 | 14 |

### 4.3 Business Applications

- Marketing channel performance
- Marketing-qualified lead analysis
- Lead-to-deal conversion
- Sales funnel analysis
- Seller acquisition
- Sales cycle duration
- Sales representative performance
- Lead origin analysis
- Seller onboarding analysis
- Post-acquisition seller performance

### 4.4 Data Limitations

- The dataset represents a historical sample of leads.
- Complete historical marketing expenditure is unavailable.
- Actual customer acquisition cost cannot be calculated
  without additional cost information.
- Actual marketing return on investment cannot be
  calculated without expenditure data.
- A seller may originate from multiple lead sources.
- Closed deals cannot automatically be assumed to have
  generated marketplace transactions.
- Marketing funnel conversion calculations must account
  for the correct denominator and dataset granularity.

## 5. Source 3 — Brazilian Holiday Data

### 5.1 Source Information

- Provider: Nager.Date
- Country code: BR
- API version used: v3
- Acquisition method: HTTP GET requests
- Response format: JSON
- Local storage format: CSV
- Coverage: 2016–2018
- Records acquired: 42
- Columns: 11
- Acquisition date: 2026-11-27
- Storage path: data/raw/external/brazil_holidays.csv
- Provider repository:
  https://github.com/nager/Nager.Date

### 5.2 API Endpoints Used

- https://date.nager.at/api/v3/PublicHolidays/2016/BR
- https://date.nager.at/api/v3/PublicHolidays/2017/BR
- https://date.nager.at/api/v3/PublicHolidays/2018/BR

### 5.3 Record Distribution

| Year | Records |
|---|---:|
| 2016 | 14 |
| 2017 | 14 |
| 2018 | 14 |
| Total | 42 |

### 5.4 Dataset Fields

| Field | Description |
|---|---|
| date | Holiday date |
| localName | Holiday name in the local language |
| name | English holiday name |
| countryCode | Country identifier |
| fixed | Whether the holiday occurs on a fixed date |
| global | Whether the holiday applies nationwide |
| counties | Applicable regional subdivisions |
| launchYear | Holiday introduction year, when supplied |
| types | Holiday classification |
| source_year | Requested API year |
| source_url | Original API endpoint |

The source_year and source_url fields were added during
acquisition to preserve data provenance.

List-valued API fields were serialized as JSON strings
before CSV export.

### 5.5 Business Applications

- Holiday versus non-holiday order performance
- Seasonal demand analysis
- Holiday-related delivery patterns
- Customer purchasing behaviour
- Calendar dimension enrichment
- Holiday-period operational analysis

### 5.6 Data Limitations

- Holiday records include different classifications,
  including public, bank and optional holidays.
- Regional holidays must not be classified automatically
  as nationwide holidays.
- The API may not capture all local or municipal holidays.
- Holiday classifications require appropriate interpretation.
- Historical holiday records do not establish causal
  relationships with sales or delivery performance.
- API availability and response structures may change.
- The local snapshot is retained for reproducibility.

### 5.7 Licensing and Redistribution

Nager.Date is credited as the original data provider.

The applicable API data redistribution terms must be
confirmed separately from the software repository license.

Until these terms are confirmed, CommerceIQ will retain
the acquired holiday dataset locally and avoid publishing
the raw snapshot publicly.

## 6. Raw Data Directory Structure

```text
data/
├── raw/
│   ├── ecommerce/
│   ├── marketing/
│   └── external/
│       └── brazil_holidays.csv
├── interim/
├── processed/
├── rejected/
└── metadata/
    ├── dataset_manifest.csv
    └── ingestion_summary.csv
```

Original source files must remain unchanged after
acquisition and registration.

Data cleaning and transformation outputs must be stored
separately from the raw data directory.

## 7. Data Acquisition Procedure

### 7.1 Kaggle Datasets

1. Access the original Kaggle dataset pages.
2. Download the source files.
3. Extract the downloaded archives.
4. Place the CSV files in the appropriate raw directories.
5. Preserve the original filenames.
6. Verify file availability and file sizes.
7. Generate SHA-256 checksums.
8. Register the files in the dataset manifest.

### 7.2 External API Data

1. Define country code BR.
2. Request holiday records for 2016, 2017 and 2018.
3. Validate HTTP responses.
4. Parse JSON response data.
5. Record source year and source URL.
6. Serialize list-valued fields.
7. Export records to brazil_holidays.csv.
8. Validate the saved dataset.
9. Generate its SHA-256 checksum.
10. Register it in the dataset manifest.

The original API acquisition procedure is documented
in notebooks/00_data_ingestion.ipynb.

## 8. Dataset Manifest

Manifest location:

data/metadata/dataset_manifest.csv

The manifest provides centralized source inventory,
provenance and file integrity information.

| Field | Description |
|---|---|
| dataset | Logical dataset identifier |
| source | Source classification |
| filename | Original or acquired filename |
| relative_path | Project-relative file location |
| size_bytes | File size in bytes |
| size_mb | File size in MiB |
| last_modified_utc | File modification timestamp |
| sha256 | SHA-256 checksum |
| file_exists | File availability indicator |
| correct_extension | CSV extension validation |
| non_empty | Non-empty file indicator |
| status | Source validation status |
| source_url | Source location or API endpoint template |
| registered_at_utc | Manifest registration timestamp |

The registration timestamp represents manifest
registration and not necessarily the original download date.

## 9. Ingestion Pipeline

Script location:

src/ingestion/extract.py

The ingestion pipeline performs:

- Project configuration loading
- Dataset manifest validation
- Source path validation
- File existence verification
- File extension validation
- Empty file detection
- SHA-256 integrity verification
- CSV ingestion
- Raw value preservation
- Exception handling
- Execution logging
- Ingestion summary generation

Run from the project root:

```powershell
python src/ingestion/extract.py
```

All source columns are initially ingested as strings to
avoid premature type conversion and preserve identifiers,
leading zeros and original textual values.

Data type conversion is performed during subsequent
data preparation stages.

## 10. Ingestion Logging

Log location:

logs/ingestion.log

The logging system records:

- Pipeline execution timestamps
- Dataset ingestion status
- Dataset row and column counts
- Dataset loading duration
- Validation failures
- Error messages
- Pipeline completion status

The logging system uses file and console handlers.

## 11. Automated Testing

Test script:

tests/test_ingestion.py

Execute:

```powershell
python -m pytest tests/test_ingestion.py -v
```

Validated test scenarios include:

- Valid CSV ingestion
- Missing source files
- Empty source files
- Incorrect file extensions
- Header-only CSV files
- Malformed CSV files
- Valid checksums
- Invalid checksums
- Leading-zero preservation
- Raw empty and literal text preservation
- Invalid character encoding
- File modification detection
- Configuration validation
- Dataset manifest validation

### Baseline Test Results

| Metric | Result |
|---|---:|
| Test date | 2026-11-27 |
| Total tests | 14 |
| Passed | 14 |
| Failed | 0 |
| Pass rate | 100% |
| Execution time | 1.57 seconds |

## 12. Baseline Ingestion Results

| Metric | Result |
|---|---:|
| Registered datasets | 12 |
| Successfully ingested | 12 |
| Failed datasets | 0 |
| Total source records | 1,559,806 |
| Integrity checks passed | 12 |
| Standalone execution time | 3.01 seconds |

Execution time represents the recorded local baseline
and may vary by hardware and system conditions.

The total source record count combines multiple datasets
with different levels of granularity. It must not be
interpreted as the number of unique business transactions.

## 13. Data Governance Principles

CommerceIQ follows these principles:

1. Preserve original source files.
2. Maintain dataset provenance.
3. Track file integrity through checksums.
4. Separate raw and transformed data.
5. Document data transformations.
6. Maintain reproducible ingestion procedures.
7. Prevent unauthorized source modifications.
8. Record validation failures.
9. Respect original data licensing.
10. Avoid attempts to re-identify anonymized individuals.
11. Distinguish observed metrics from estimated metrics.
12. Clearly label hypothetical business simulations.
13. Avoid unsupported financial or operational claims.
14. Avoid publishing restricted source data.

## 14. Licensing and Attribution

### Olist Datasets

Both Olist datasets are published under the Creative
Commons Attribution-NonCommercial-ShareAlike 4.0
International license.

License reference:

https://creativecommons.org/licenses/by-nc-sa/4.0/

The license requires appropriate attribution, restricts
commercial use and imposes share-alike requirements
when adapted material is distributed.

CommerceIQ is intended as an independent educational
and non-commercial portfolio project.

### External Holiday Data

Holiday information was acquired from Nager.Date.

Public redistribution of the acquired API snapshot is
subject to confirmation of the applicable API data terms.

### Repository Licensing

Any license applied to original CommerceIQ source code
does not override the licenses or usage restrictions
applicable to third-party datasets.

Raw data and data-containing artifacts should be reviewed
before publication in the public GitHub repository.

## 15. Acknowledgements

CommerceIQ acknowledges Olist for publishing the
historical Brazilian e-commerce and marketing datasets,
Kaggle for hosting those datasets, and Nager.Date for
providing holiday information.

CommerceIQ is an independent portfolio project and is
not affiliated with or endorsed by these organizations.