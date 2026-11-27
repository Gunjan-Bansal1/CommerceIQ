# CommerceIQ — Excel Business Analytics Reconciliation Report (Phase 7)

**Execution Timestamp (UTC):** 2026-11-27 17:14:59
**Workbook:** `excel\commerceiq_business_analytics.xlsx`
**Native PivotTable & PivotChart Verified (Excel COM 16.0):** True
**Interactive Slicers Verified:** 3 (`PeriodScope`, `OrderStatus`, `DeliveryPerformance`)

## 1. Cross-Tool Reconciliation (Excel Formulas & PivotTable vs. MySQL Warehouse)

| KPI / Measure | Excel Calculated Value | MySQL Warehouse Baseline | Status |
|---|---:|---:|---|
| Total Placed Orders (`SUMIFS`) | 99,441 | 99,441 | EXACT MATCH |
| Delivered Orders (`SUMIFS`) | 96,478 | 96,478 | EXACT MATCH |
| Delivered Merchandise Value (BRL) | 13,221,498.11 | 13,221,498.11 | RECONCILED |
| Recorded GMV All Statuses (BRL) | 13,591,643.70 | 13,591,643.70 | EXACT MATCH |
| Recorded Payment Value (BRL) | 16,008,872.12 | 16,008,872.12 | EXACT MATCH |
| Average Delivered Order Value (BRL) | 137.04 | 137.04 | RECONCILED |
| On-Time Delivery Rate (%) | 93.2269% | 93.2269% | EXACT MATCH |
| `XLOOKUP` (`health_beauty` BRL) | 1,233,131.72 | 1,233,131.72 | VERIFIED |
| `CommerceIQ_Pivot` Grand Total Orders | 99,441 | 99,441 | EXACT MATCH |
| `CommerceIQ_Pivot` Grand Total GMV (BRL) | 13,591,643.70 | 13,591,643.70 | EXACT MATCH |
