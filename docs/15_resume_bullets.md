# CommerceIQ — ATS-Friendly Resume Bullets

## Concise Project Summary (For Projects Section)
**CommerceIQ — End-to-End E-Commerce Analytics, BI & Predictive Decision Platform** | *Python, MySQL 8.0, SQLAlchemy, Power BI (DAX/TMDL), Excel/Power Query, Scikit-Learn, Statsmodels, Pytest, GitHub Actions*

- Engineered a modular Python ETL pipeline transforming **1.56M** raw records across **12** Olist e-commerce, marketing funnel, and holiday datasets into **13** SHA-256 verified Parquet/CSV tables (**1.30M** rows, **165** fields, **27** engineered features) backed by **27** automated ingestion and cleaning regression tests.
- Architected a **MySQL 8.0** relational database (enforcing **8** foreign keys while preserving **748** documented optional linkage gaps) and a Kimball **7-dimension, 5-fact** star/constellation warehouse with **9** analytical data mart views, achieving **100%** monetary reconciliation (**BRL 13.59M** GMV, **BRL 16.01M** payments) with zero join fan-out.
- Authored **41** domain SQL queries (CTEs, window functions, cohort retention, Pareto concentration, `EXPLAIN` tuning) tracing **120** business questions and **72** KPIs across commercial, logistics, satisfaction, and funnel domains.
- Built an interactive **Excel** executive workbook via OpenPyXL and Excel COM (`XLOOKUP`, `SUMIFS`, PivotTables, PivotCharts, Slicers) and a **Power BI** PBIP semantic model with **39** explicit DAX measures across **10** analytical pages, reconciling core KPIs across Python, MySQL, Excel, and DAX.
- Quantified operational drivers via Holm-Bonferroni corrected hypothesis testing (identifying a **2.02-star** review penalty on late deliveries, Cohen *d* = **1.71**, *n* = 95,824), segmented **93,358** unique customers via RFM, cohorts, and K-Means, and trained a zero-leakage checkout delivery-risk classifier (**0.7325 ROC-AUC**, >2.1x baseline PR-AUC) alongside Holt-Winters weekly demand backtests (**17.97%** holdout WAPE).
- Automated end-to-end orchestration (`pipelines/run_pipeline.py`) and GitHub Actions CI with disposable MySQL 8.0 schema validation and repository security tests.
