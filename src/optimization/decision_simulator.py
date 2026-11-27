"""
CommerceIQ - Phase 14: Decision Intelligence & Business Scenario Simulator

Separates observed historical baselines (2016-2018 BRL) from clearly labeled
illustrative sensitivity assumptions across Low, Base, and High scenarios.
Produces:
  - `data/processed/decision_scenarios.csv`
  - `excel/commerceiq_decision_simulator.xlsx` (interactive adjustable inputs)
  - `reports/figures/dec_01_scenario_prioritization.png`
  - `reports/executive_recommendations_report.md`
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def compute_observed_baselines() -> dict[str, float]:
    """Compute observed baselines directly from Phase 4 cleaned Parquet files."""
    pq_dir = PROJECT_ROOT / "data" / "processed" / "parquet"
    orders = pd.read_parquet(pq_dir / "orders.parquet")
    customers = pd.read_parquet(pq_dir / "customers.parquet")
    order_items = pd.read_parquet(pq_dir / "order_items.parquet")
    reviews = pd.read_parquet(pq_dir / "reviews.parquet")
    leads = pd.read_parquet(pq_dir / "marketing_leads.parquet")

    for c in ["price", "freight_value"]:
        order_items[c] = order_items[c].astype(float)

    item_agg = order_items.groupby("order_id", as_index=False).agg(
        merch_brl=("price", "sum"),
        freight_brl=("freight_value", "sum"),
    )
    ord_full = orders.merge(customers[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left").merge(item_agg, on="order_id", how="left")
    ord_full["merch_brl"] = ord_full["merch_brl"].fillna(0.0)
    ord_full["freight_brl"] = ord_full["freight_brl"].fillna(0.0)

    deliv = ord_full[ord_full["order_status"].eq("delivered") & ord_full["has_order_items"]]
    unsucc = ord_full[ord_full["order_status"].isin(["canceled", "unavailable"]) & ord_full["has_order_items"]]
    late_deliv = deliv[deliv["delivery_performance"].eq("late")]

    unique_custs = int(deliv["customer_unique_id"].nunique())
    cust_orders = deliv.groupby("customer_unique_id")["order_id"].count()
    repeat_rate = float((cust_orders >= 2).mean())

    # High-freight distant states (North & Northeast)
    ne_n_states = {"BA", "PE", "CE", "RN", "PB", "AL", "SE", "PI", "MA", "AM", "PA", "RO", "RR", "AC", "AP", "TO"}
    ne_n_deliv = deliv[deliv["customer_state"].isin(ne_n_states)]

    # Negative review rate among late deliveries vs on-time
    rev_ord = deliv.merge(reviews.groupby("order_id", as_index=False)["review_score"].mean(), on="order_id", how="inner")
    late_neg_rate = float((rev_ord.loc[rev_ord["delivery_performance"].eq("late"), "review_score"] <= 2).mean())
    ontime_neg_rate = float((rev_ord.loc[rev_ord["is_on_time_delivery"].eq(True), "review_score"] <= 2).mean())

    return {
        "delivered_orders": float(len(deliv)),
        "delivered_merch_brl": float(deliv["merch_brl"].sum()),
        "delivered_aov_brl": float(deliv["merch_brl"].mean()),
        "unique_delivered_customers": float(unique_custs),
        "repeat_purchase_rate": repeat_rate,
        "late_deliveries": float(len(late_deliv)),
        "late_merch_brl": float(late_deliv["merch_brl"].sum()),
        "late_neg_review_rate": late_neg_rate,
        "ontime_neg_review_rate": ontime_neg_rate,
        "known_unsuccessful_merch_brl": float(unsucc["merch_brl"].sum()),
        "qualified_leads": float(len(leads)),
        "closed_deals": float(leads["has_closed_deal"].sum()),
        "ne_n_freight_brl": float(ne_n_deliv["freight_brl"].sum()),
        "ne_n_merch_brl": float(ne_n_deliv["merch_brl"].sum()),
    }


def build_scenarios(base: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate Low/Base/High scenario table & opportunity prioritization matrix."""
    # Illustrative parameters (explicitly labeled as assumptions, NOT observed Olist margins)
    ILLUST_CONTRIB_MARGIN = 0.15  # Illustrative 15% marketplace/seller contribution margin sensitivity

    scenario_defs = [
        {
            "scenario_id": "SIM-01",
            "scenario_name": "Retention & Repeat Purchase Lift",
            "baseline_metric": "Unique Delivered Customers (repeat=3.00%)",
            "observed_baseline_value": base["unique_delivered_customers"],
            "driver_unit": "Percentage-point lift in repeat rate",
            "low_input": 0.005,
            "base_input": 0.010,
            "high_input": 0.020,
            "calc_fn": lambda x: x * base["unique_delivered_customers"] * base["delivered_aov_brl"],
            "illustrative_cost_brl": 120000.0,
            "effort": "Medium",
            "confidence": "Medium",
            "risk": "Low",
            "feasibility": "High",
            "recommendation": "Launch 14-day post-delivery replenishment & cross-category email triggers for Recent Single Buyers.",
        },
        {
            "scenario_id": "SIM-02",
            "scenario_name": "Late Delivery Reduction (Risk-Targeted)",
            "baseline_metric": "Late Delivered Orders (6,534 orders)",
            "observed_baseline_value": base["late_deliveries"],
            "driver_unit": "Fraction of late deliveries shifted on-time",
            "low_input": 0.10,
            "base_input": 0.20,
            "high_input": 0.35,
            "calc_fn": lambda x: (x * base["late_deliveries"]) * 0.03 * base["delivered_aov_brl"],
            "illustrative_cost_brl": 95000.0,
            "effort": "Medium",
            "confidence": "High",
            "risk": "Low",
            "feasibility": "High",
            "recommendation": "Use checkout delay-risk model to flag high-risk inter-state orders for SLA buffer & priority seller dispatch.",
        },
        {
            "scenario_id": "SIM-03",
            "scenario_name": "Unsuccessful Order Recovery",
            "baseline_metric": "Recorded Unsuccessful Merch Value (BRL)",
            "observed_baseline_value": base["known_unsuccessful_merch_brl"],
            "driver_unit": "Fraction of known canceled/unavailable value recovered",
            "low_input": 0.15,
            "base_input": 0.25,
            "high_input": 0.40,
            "calc_fn": lambda x: x * base["known_unsuccessful_merch_brl"],
            "illustrative_cost_brl": 35000.0,
            "effort": "Low",
            "confidence": "Medium",
            "risk": "Low",
            "feasibility": "High",
            "recommendation": "Enforce real-time seller stock validation and automated payment retry nudges before cancellation.",
        },
        {
            "scenario_id": "SIM-04",
            "scenario_name": "Marketing Seller Funnel Conversion Lift",
            "baseline_metric": "Qualified Leads (8,000 MQLs, 10.53% conv)",
            "observed_baseline_value": base["qualified_leads"],
            "driver_unit": "Percentage-point lift in MQL-to-deal conversion",
            "low_input": 0.015,
            "base_input": 0.030,
            "high_input": 0.050,
            "calc_fn": lambda x: (x * base["qualified_leads"]) * 0.45 * 4200.0,  # 45% active match * illustrative annual seller GMV
            "illustrative_cost_brl": 65000.0,
            "effort": "Medium",
            "confidence": "Low-Medium",
            "risk": "Medium",
            "feasibility": "Medium",
            "recommendation": "Reallocate SDR follow-up priority toward organic_search and paid_search leads with faster onboarding.",
        },
        {
            "scenario_id": "SIM-05",
            "scenario_name": "North/Northeast Freight Burden Reduction",
            "baseline_metric": "North/Northeast Delivered Freight (BRL)",
            "observed_baseline_value": base["ne_n_freight_brl"],
            "driver_unit": "Fraction reduction in regional freight friction",
            "low_input": 0.03,
            "base_input": 0.06,
            "high_input": 0.10,
            "calc_fn": lambda x: x * base["ne_n_freight_brl"],
            "illustrative_cost_brl": 150000.0,
            "effort": "High",
            "confidence": "Low-Medium",
            "risk": "Medium",
            "feasibility": "Medium",
            "recommendation": "Onboard regional Northeast/North sellers in high-demand categories to reduce inter-state shipping distance.",
        },
    ]

    rows = []
    prio_rows = []
    for s in scenario_defs:
        for tier, inp_key in [("Low", "low_input"), ("Base", "base_input"), ("High", "high_input")]:
            inp = s[inp_key]
            sim_gmv = round(float(s["calc_fn"](inp)), 2)
            contrib = round(sim_gmv * ILLUST_CONTRIB_MARGIN, 2)
            net_ben = round(contrib - s["illustrative_cost_brl"], 2)
            rows.append({
                "scenario_id": s["scenario_id"],
                "scenario_name": s["scenario_name"],
                "tier": tier,
                "observed_baseline_label": s["baseline_metric"],
                "observed_baseline_value": round(s["observed_baseline_value"], 2),
                "assumed_input_parameter": inp,
                "driver_unit": s["driver_unit"],
                "illustrative_margin_assumption": ILLUST_CONTRIB_MARGIN,
                "illustrative_intervention_cost_brl": s["illustrative_cost_brl"],
                "simulated_gmv_or_savings_brl": sim_gmv,
                "simulated_illustrative_contribution_brl": contrib,
                "simulated_illustrative_net_benefit_brl": net_ben,
                "is_illustrative_simulation": True,
            })

        base_gmv = round(float(s["calc_fn"](s["base_input"])), 2)
        base_net = round(base_gmv * ILLUST_CONTRIB_MARGIN - s["illustrative_cost_brl"], 2)
        effort_score = {"Low": 1, "Medium": 2, "High": 3}[s["effort"]]
        conf_score = {"High": 3, "Medium": 2, "Low-Medium": 1}[s["confidence"]]
        impact_score = 3 if base_gmv >= 120000 else (2 if base_gmv >= 40000 else 1)
        prio_score = round((impact_score * 2 + conf_score * 1.5) / effort_score, 2)
        prio_rows.append({
            "scenario_id": s["scenario_id"],
            "initiative": s["scenario_name"],
            "base_simulated_gmv_brl": base_gmv,
            "base_illustrative_net_brl": base_net,
            "effort": s["effort"],
            "confidence": s["confidence"],
            "risk": s["risk"],
            "feasibility": s["feasibility"],
            "priority_score": prio_score,
            "recommendation": s["recommendation"],
        })

    scen_df = pd.DataFrame(rows)
    prio_df = pd.DataFrame(prio_rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    return scen_df, prio_df


def build_excel_simulator(scen_df: pd.DataFrame, prio_df: pd.DataFrame, base: dict[str, float]) -> Path:
    """Create interactive Excel simulator with adjustable inputs and live formulas."""
    out_path = PROJECT_ROOT / "excel" / "commerceiq_decision_simulator.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Decision Simulator"
    ws.views.sheetView[0].showGridLines = False

    navy = PatternFill("solid", fgColor="17365D")
    input_fill = PatternFill("solid", fgColor="FFF2CC")
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    thin = Side(border_style="thin", color="D0D7DE")
    bdr = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:I1")
    ws["A1"] = "COMMERCEIQ — INTERACTIVE BUSINESS DECISION SIMULATOR (ILLUSTRATIVE SCENARIOS)"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = navy
    ws.row_dimensions[1].height = 32

    ws["A2"] = "Disclaimer: Yellow cells are adjustable ILLUSTRATIVE assumptions, not observed Olist margins or costs."
    ws["A2"].font = Font(italic=True, size=10, color="9B2C2C")

    # Global adjustable assumptions block
    ws["A4"] = "Global Illustrative Contribution Margin (%):"
    ws["A4"].font = Font(bold=True)
    ws["B4"] = 0.15
    ws["B4"].fill = input_fill
    ws["B4"].number_format = "0.0%"
    ws["B4"].border = bdr

    ws["D4"] = "Observed Delivered AOV (BRL):"
    ws["D4"].font = Font(bold=True)
    ws["E4"] = round(base["delivered_aov_brl"], 2)
    ws["E4"].number_format = "#,##0.00"

    headers = [
        "Scenario ID", "Initiative", "Observed Baseline Value",
        "Base Input (Editable)", "Illustrative Cost (BRL, Editable)",
        "Simulated Impact (BRL)", "Illustrative Contribution (BRL)",
        "Illustrative Net Benefit (BRL)", "Priority Score",
    ]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(6, c_idx, h)
        cell.fill = navy
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[6].height = 28

    base_only = scen_df[scen_df["tier"] == "Base"].merge(
        prio_df[["scenario_id", "priority_score"]], on="scenario_id", how="left"
    )
    formula_map = {
        "SIM-01": "=D7*C7*$E$4",
        "SIM-02": "=D8*C8*0.03*$E$4",
        "SIM-03": "=D9*C9",
        "SIM-04": "=D10*C10*0.45*4200",
        "SIM-05": "=D11*C11",
    }
    for r_offset, row in enumerate(base_only.itertuples(index=False), start=7):
        ws.cell(r_offset, 1, row.scenario_id).border = bdr
        ws.cell(r_offset, 2, row.scenario_name).border = bdr
        c_base = ws.cell(r_offset, 3, row.observed_baseline_value)
        c_base.number_format = "#,##0.00"
        c_base.border = bdr

        c_inp = ws.cell(r_offset, 4, row.assumed_input_parameter)
        c_inp.fill = input_fill
        c_inp.number_format = "0.00%"
        c_inp.border = bdr

        c_cost = ws.cell(r_offset, 5, row.illustrative_intervention_cost_brl)
        c_cost.fill = input_fill
        c_cost.number_format = "#,##0.00"
        c_cost.border = bdr

        c_imp = ws.cell(r_offset, 6, formula_map[row.scenario_id])
        c_imp.number_format = "#,##0.00"
        c_imp.border = bdr

        c_con = ws.cell(r_offset, 7, f"=F{r_offset}*$B$4")
        c_con.number_format = "#,##0.00"
        c_con.border = bdr

        c_net = ws.cell(r_offset, 8, f"=G{r_offset}-E{r_offset}")
        c_net.number_format = "#,##0.00"
        c_net.border = bdr

        c_prio = ws.cell(r_offset, 9, row.priority_score)
        c_prio.number_format = "0.00"
        c_prio.border = bdr

    # Sensitivity & Prioritization detail sheets
    ws_sens = wb.create_sheet("Low-Base-High Sensitivity")
    ws_sens.append(list(scen_df.columns))
    for r in scen_df.itertuples(index=False, name=None):
        ws_sens.append(list(r))

    ws_prio = wb.create_sheet("Prioritization Matrix")
    ws_prio.append(list(prio_df.columns))
    for r in prio_df.itertuples(index=False, name=None):
        ws_prio.append(list(r))

    ch = BarChart()
    ch.title = "Base Scenario Simulated Impact vs. Illustrative Contribution (BRL)"
    ch.add_data(Reference(ws, min_col=6, max_col=7, min_row=6, max_row=11), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=7, max_row=11))
    ch.width = 20
    ch.height = 10
    ws.add_chart(ch, "A14")

    for i in range(1, 10):
        ws.column_dimensions[get_column_letter(i)].width = 24
    wb.save(out_path)
    return out_path


def run_decision_intelligence() -> dict[str, Any]:
    base = compute_observed_baselines()
    scen_df, prio_df = build_scenarios(base)

    scen_df.to_csv(PROJECT_ROOT / "data" / "processed" / "decision_scenarios.csv", index=False)
    excel_path = build_excel_simulator(scen_df, prio_df, base)

    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    piv = scen_df.pivot(index="scenario_name", columns="tier", values="simulated_gmv_or_savings_brl")[["Low", "Base", "High"]]
    ax = piv.plot(kind="barh", figsize=(11, 5), color=["#90cdf4", "#2b6cb0", "#1a365d"])
    ax.set_title("Decision Intelligence: Low / Base / High Illustrative Scenario Impact (BRL)", fontweight="bold")
    ax.set_xlabel("Simulated Gross Impact or Freight Savings (BRL, Illustrative)")
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "dec_01_scenario_prioritization.png", dpi=150)
    plt.close()

    # Save executive recommendations report
    lines = [
        "# CommerceIQ — Decision Intelligence & Executive Recommendations (Phase 14)",
        "",
        "> **Important Distinction:** Observed historical figures (`2016–2018`) are strictly separated from **illustrative scenario assumptions** (15% contribution margin, assumed intervention costs). Simulated gains are sensitivity estimates, not guaranteed financial returns.",
        "",
        "## 1. Observed Marketplace Baselines",
        f"- Delivered Orders: **{int(base['delivered_orders']):,}** | Delivered Merchandise Value: **BRL {base['delivered_merch_brl']:,.2f}** | AOV: **BRL {base['delivered_aov_brl']:,.2f}**",
        f"- Unique Delivered Customers: **{int(base['unique_delivered_customers']):,}** | Repeat Rate: **{base['repeat_purchase_rate']*100:.2f}%**",
        f"- Late Deliveries: **{int(base['late_deliveries']):,}** (Negative Review Rate: **{base['late_neg_review_rate']*100:.2f}%** vs. **{base['ontime_neg_review_rate']*100:.2f}%** when on-time)",
        f"- Known Unsuccessful Order Value: **BRL {base['known_unsuccessful_merch_brl']:,.2f}**",
        "",
        "## 2. Opportunity Prioritization Matrix (Base Scenario)",
        "",
        "| Rank | Initiative | Base Simulated Impact (BRL) | Effort | Confidence | Priority Score | Recommendation |",
        "|---:|---|---:|---|---|---:|---|",
    ]
    for idx, r in enumerate(prio_df.itertuples(index=False), start=1):
        lines.append(
            f"| {idx} | {r.initiative} | {r.base_simulated_gmv_brl:,.2f} | {r.effort} | {r.confidence} | {r.priority_score:.2f} | {r.recommendation} |"
        )
    lines.append("")
    (PROJECT_ROOT / "reports" / "executive_recommendations_report.md").write_text("\n".join(lines), encoding="utf-8")

    return {"baselines": base, "scenarios": scen_df, "prioritization": prio_df, "excel_path": str(excel_path)}


if __name__ == "__main__":
    res = run_decision_intelligence()
    print(res["prioritization"].to_string(index=False))
