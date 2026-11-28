# CommerceIQ — Power BI DAX & Semantic Model Reconciliation (Phase 13)

## 1. Asset Verification
- `powerbi/CommerceIQ.pbip`: **VERIFIED SOURCE PROJECT**
- `powerbi/CommerceIQ.SemanticModel/definition/`: **12 MySQL Warehouse Tables + 4 Strongly-Typed CSV Tables + `_Measures` (61 explicit DAX measures) + 15 relationships**
- `powerbi/CommerceIQ.Report/report.json`: **10 Report Pages, 84 Visuals** (every visual bound with explicit `prototypeQuery` + `active` projections + explicit measures; `pageNavigator`, dropdown slicers, maps, scatter plots, funnels, combo/line/bar/donut/matrix charts, drill-through enabled)
- Native Power BI Desktop MySQL Refresh & GUI Render: **READY FOR USER REFRESH IN DESKTOP** (MySQL Connector/NET verified registered; `dim_date` `-1` null row filtered, `tinyint(1)` flags normalized to `Int64.Type`, and CSV partitions explicitly typed in `en-US`).

## 2. DAX Measure Definitions Reconciled Against MySQL Warehouse Baselines

| Power BI DAX Measure | MySQL Warehouse Expected Baseline | Definition & Binding Status | Native Power BI Execution |
|---|---:|---|---|
| `Total Placed Orders` | 99,441 | RECONCILED | Pending Desktop GUI refresh |
| `Delivered Orders` | 96,478 | RECONCILED | Pending Desktop GUI refresh |
| `Delivered Merchandise Value (BRL)` | 13,221,498.11 | RECONCILED | Pending Desktop GUI refresh |
| `Recorded GMV All Statuses (BRL)` | 13,591,643.70 | RECONCILED | Pending Desktop GUI refresh |
| `Recorded Freight Value (BRL)` | 2,251,909.54 | RECONCILED | Pending Desktop GUI refresh |
| `Recorded Payment Value (BRL)` | 16,008,872.12 | RECONCILED | Pending Desktop GUI refresh |
| `Average Delivered Order Value (BRL)` | 137.04 | RECONCILED | Pending Desktop GUI refresh |
| `Unsuccessful Orders` | 1,234 | RECONCILED | Pending Desktop GUI refresh |
| `On-Time Delivery Rate %` | 93.2269% | RECONCILED | Pending Desktop GUI refresh |
| `Mean Delivery Duration (Days)` | 12.5582 days | RECONCILED | Pending Desktop GUI refresh |
| `Total Reviews` / `Mean Review Score` | 99,224 / 4.0864 | RECONCILED | Pending Desktop GUI refresh |
| `Qualified Leads (MQL)` / `Converted Closed Deals` | 8,000 / 842 | RECONCILED | Pending Desktop GUI refresh |
