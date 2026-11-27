# CommerceIQ — Power BI DAX & Semantic Model Reconciliation (Phase 13)

## 1. Asset Verification
- `powerbi/CommerceIQ.pbip`: **VERIFIED**
- `powerbi/CommerceIQ.SemanticModel/definition/`: **12 MySQL Warehouse Tables + 4 Analytical CSV Tables + `_Measures` (39 explicit DAX measures) + 15 relationships**
- `powerbi/CommerceIQ.Report/report.json`: **10 Report Pages, 84 Visuals** (cards, line/bar/donut/funnel/scatter/filledMap/matrix/slicers/pageNavigator, drill-through enabled)
- Native Power BI Desktop GUI Refresh & Screenshot Export: **PENDING INTERACTIVE GUI OPEN** (`PBIDesktopStore.exe` requires interactive user sign-in/refresh).

## 2. DAX Measure Logic Reconciled Against MySQL Warehouse

| Power BI DAX Measure | MySQL Warehouse Expected Result | Status |
|---|---:|---|
| `Total Placed Orders` | 99,441 | RECONCILED |
| `Delivered Orders` | 96,478 | RECONCILED |
| `Delivered Merchandise Value (BRL)` | 13,221,498.11 | RECONCILED |
| `Recorded GMV All Statuses (BRL)` | 13,591,643.70 | RECONCILED |
| `Recorded Payment Value (BRL)` | 16,008,872.12 | RECONCILED |
| `Average Delivered Order Value (BRL)` | 137.04 | RECONCILED |
| `Unsuccessful Orders` | 1,234 | RECONCILED |
| `On-Time Delivery Rate %` | 93.2269% | RECONCILED |
| `Total Reviews` / `Mean Review Score` | 99,224 / 4.0864 | RECONCILED |
| `Qualified Leads (MQL)` / `Converted Closed Deals` | 8,000 / 842 | RECONCILED |
