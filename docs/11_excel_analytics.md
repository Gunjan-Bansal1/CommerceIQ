# CommerceIQ — Excel Business Analytics Workbook (Phase 7)

## 1. Workbook Architecture

**Workbook:** [`commerceiq_business_analytics.xlsx`](file:///c:/Users/bgunj/Desktop/commerceIQ/excel/commerceiq_business_analytics.xlsx)  
**Generator:** [`build_excel_workbook.py`](file:///c:/Users/bgunj/Desktop/commerceIQ/src/analytics/build_excel_workbook.py)  
**Power Query Scripts:** [`excel/power_query/`](file:///c:/Users/bgunj/Desktop/commerceIQ/excel/power_query/)

## 2. Worksheets & Implemented Capabilities

| Worksheet | Excel Table(s) | Key Formulas & Features |
|---|---|---|
| `Executive Dashboard` | — | Dynamic scope dropdown (`All History` / `Core (2017-01..2018-08)`), `SUMIFS`, `IF`, `IFERROR`, Named Ranges (`rng_*`), `XLOOKUP` + `INDEX`/`MATCH` interactive Category Explorer, native Line & Bar Charts |
| `Monthly Trends` | `tbl_monthly` | MoM growth `IFERROR`, cumulative sales `SUM($H$2:H2)`, Data Bars, On-Time % Color Scale |
| `Category Performance` | `tbl_categories` | Category sales share %, cumulative Pareto %, Data Bars |
| `Customer Segments` | `tbl_customer_rfm` | Segment revenue share %, persistent `customer_unique_id` KPI summary |
| `Seller Performance` | `tbl_sellers` | Top 500 sellers scorecard (orders, sales, unsuccessful & late exposure, ratings) |
| `Delivery & Logistics` | `tbl_logistics` | 417 state-to-state lanes with intra/inter-state split & SLA Color Scale |
| `Payments & Geography` | `tbl_geography`, `tbl_payments` | State-level performance + payment method shares |
| `Marketing & Satisfaction` | `tbl_marketing`, `tbl_satisfaction` | Channel conversion funnel + delivery-bucket review scores |
| `Warehouse Cube` | `tbl_warehouse_cube` | Aggregated `YearMonth × Region × State × Status × DeliveryPerformance` cube |
| `Pivot Analysis` | `CommerceIQ_Pivot` | Native Excel PivotTable, PivotChart, and 3 Slicers (`PeriodScope`, `OrderStatus`, `DeliveryPerformance`) built via Excel COM |

## 3. Power Query Refresh Scripts

- `pq_mart_executive_monthly.pq`: Connects to MySQL `commerceiq.mart_executive_monthly`.
- `pq_mart_product_categories.pq`: Connects to MySQL `commerceiq.mart_product_category_performance`.
- `pq_mart_geographic_performance.pq`: Connects to MySQL `commerceiq.mart_geographic_performance`.
- `pq_processed_orders_csv.pq`: File-based fallback reading `data/processed/csv/orders.csv`.

## 4. Reconciliation

See [`excel_reconciliation_report.md`](file:///c:/Users/bgunj/Desktop/commerceIQ/reports/excel_reconciliation_report.md) for verified formula and PivotTable reconciliation against the MySQL warehouse.
