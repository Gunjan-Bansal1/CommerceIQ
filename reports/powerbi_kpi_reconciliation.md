# CommerceIQ — Power BI DAX & Semantic Model Reconciliation (Phase 13)

## 1. Asset Verification
- `powerbi/CommerceIQ.pbip`: **VERIFIED SOURCE PROJECT**
- `powerbi/CommerceIQ.SemanticModel/definition/`: **12 MySQL Warehouse Tables + 4 Strongly-Typed CSV Tables + `_Measures` (61 explicit DAX measures) + 15 relationships**
- `powerbi/CommerceIQ.Report/report.json`: **10 Report Pages, 84 Visuals** (every visual bound with explicit `prototypeQuery` + `active` projections + explicit measures; `pageNavigator`, dropdown slicers, maps, scatter plots, funnels, combo/line/bar/donut/matrix charts, drill-through enabled)
- Native Power BI Desktop MySQL Refresh: **USER CONFIRMED WORKING** (2026-11-28 — user confirmed MySQL Connector/NET `MySql.Data.MySqlClient` installed, MySQL connection succeeded, and semantic model refreshed in Power BI Desktop; Desktop GUI visual numeric values & screenshots were not captured automatically by the agent).

## 2. Automated Source Checks vs. User Desktop Confirmation

| Check Layer | Scope Verified | Verification Source | Status |
|---|---|---|---|
| **PBIR & TMDL Schema** | 10 pages, 84 visuals (`0` unbound), 61 explicit DAX measures, 17 tables, 15 relationships | Agent automated pytest (`test_powerbi_pbir_and_tmdl_bindings`) | PASSED |
| **MySQL / CSV Source Keys** | `dim_date` 1,827 contiguous dates (`-1` filtered in M), `TINYINT(1)` `Int64.From`, 0 null/dup target keys | Agent automated pytest (`test_powerbi_source_data_relationship_and_date_compatibility`) | PASSED |
| **Native Desktop Refresh** | MySQL Connector/NET provider, MySQL connection, semantic model refresh in `PBIDesktop.exe` | User manual confirmation in Power BI Desktop | CONFIRMED |
| **KPI Logic Baselines** | DAX definitions matched against MySQL `commerceiq` warehouse SQL results below | Agent automated MySQL reconciliation | RECONCILED |

| Power BI DAX Measure | MySQL Warehouse Expected Baseline | Definition & Binding Status | Desktop Refresh |
|---|---:|---|---|
| `Total Placed Orders` | 99,441 | RECONCILED | Model refresh confirmed |
| `Delivered Orders` | 96,478 | RECONCILED | Model refresh confirmed |
| `Delivered Merchandise Value (BRL)` | 13,221,498.11 | RECONCILED | Model refresh confirmed |
| `Recorded GMV All Statuses (BRL)` | 13,591,643.70 | RECONCILED | Model refresh confirmed |
| `Recorded Freight Value (BRL)` | 2,251,909.54 | RECONCILED | Model refresh confirmed |
| `Recorded Payment Value (BRL)` | 16,008,872.12 | RECONCILED | Model refresh confirmed |
| `Average Delivered Order Value (BRL)` | 137.04 | RECONCILED | Model refresh confirmed |
| `Unsuccessful Orders` | 1,234 | RECONCILED | Model refresh confirmed |
| `On-Time Delivery Rate %` | 93.2269% | RECONCILED | Model refresh confirmed |
| `Mean Delivery Duration (Days)` | 12.5582 days | RECONCILED | Model refresh confirmed |
| `Total Reviews` / `Mean Review Score` | 99,224 / 4.0864 | RECONCILED | Model refresh confirmed |
| `Qualified Leads (MQL)` / `Converted Closed Deals` | 8,000 / 842 | RECONCILED | Model refresh confirmed |
