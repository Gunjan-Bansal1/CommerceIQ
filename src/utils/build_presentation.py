"""
CommerceIQ - Phase 17 Executive PowerPoint Deck Generator

Creates `presentation/CommerceIQ_Executive_Presentation.pptx` using actual
computed metrics and exported PNG charts from Phases 9-14.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

PROJECT_ROOT = Path(__file__).resolve().parents[2]

NAVY = RGBColor(23, 54, 93)
BLUE = RGBColor(43, 108, 176)
DARK = RGBColor(30, 41, 59)
MUTED = RGBColor(100, 116, 139)
LIGHT_BG = RGBColor(244, 247, 250)
WHITE = RGBColor(255, 255, 255)


def add_header(slide, title: str, subtitle: str = "") -> None:
    banner = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
    banner.fill.solid()
    banner.fill.fore_color.rgb = NAVY
    banner.line.fill.background()

    tf = banner.text_frame
    tf.margin_left = Inches(0.6)
    tf.margin_top = Inches(0.18)
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = WHITE

    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(12)
        p2.font.color.rgb = RGBColor(203, 213, 225)


def add_bullets(slide, bullets: list[str], left=0.6, top=1.4, width=12.1, height=5.5, font_size=16) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {text}"
        p.font.size = Pt(font_size)
        p.font.color.rgb = DARK
        p.space_after = Pt(10)


def add_image_slide(prs: Presentation, title: str, subtitle: str, img_path: Path, bullets: list[str]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, title, subtitle)
    if img_path.is_file():
        slide.shapes.add_picture(str(img_path), Inches(0.5), Inches(1.35), width=Inches(7.7))
    add_bullets(slide, bullets, left=8.4, top=1.45, width=4.5, height=5.5, font_size=14)


def build_deck() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    fig_dir = PROJECT_ROOT / "reports" / "figures"

    # Slide 1: Title
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s1.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    tb = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(3.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = "CommerceIQ"
    p0.font.size = Pt(48)
    p0.font.bold = True
    p0.font.color.rgb = WHITE
    p1 = tf.add_paragraph()
    p1.text = "End-to-End E-Commerce Analytics, Business Intelligence & Predictive Decision Platform"
    p1.font.size = Pt(22)
    p1.font.color.rgb = RGBColor(147, 197, 253)
    p1.space_before = Pt(12)
    p2 = tf.add_paragraph()
    p2.text = "Independent Historical Portfolio Case Study (Olist Brazil 2016–2018 | 1.56M Raw Records | Python, MySQL 8.0, Excel, Power BI)"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(203, 213, 225)
    p2.space_before = Pt(24)

    # Slide 2: Business Context & Objectives
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(s2, "Business Context & Project Scope", "Unifying fragmented marketplace operations into reconciled decision intelligence")
    add_bullets(s2, [
        "Business Problem: Fragmented order, item, payment, review, seller, geolocation, and marketing logs hindered unified KPI tracking and operational intervention.",
        "Authoritative Scope: 72 defined KPIs and 120 business questions across 11 analytical domains (Commercial, Leakage, Customer, Product, Seller, Logistics, Payments, Geo, Marketing, Experience, Data Quality).",
        "Data Sources: 12 verified datasets (9 Olist E-Commerce CSVs, 2 Olist Marketing Funnel CSVs, 1 Nager.Date Brazilian Holiday snapshot) totaling 1,559,806 raw records.",
        "Governance Discipline: Recorded merchandise value (BRL) is strictly separated from unrecorded marketplace commission/profit; simulated interventions are explicitly labeled illustrative.",
    ])

    # Slide 3: End-to-End Architecture & Data Engineering
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(s3, "Architecture & Data Cleaning Achievements", "From 1.56M raw records to 13 reconciled Parquet & MySQL star-schema tables")
    add_bullets(s3, [
        "Phase 2–4 ETL: Preserved raw checksums (12/12 SHA-256), deduplicated 279,668 geographic rows, built unique 19,011-prefix geolocation_lookup, and engineered 27 features across 13 tables (1,299,152 rows, 165 fields, 20/20 validation checks).",
        "Phase 5 Operational MySQL DB: Loaded 1,299,152 rows with exact DECIMAL(12,2) precision, CHAR(5) leading-zero postal codes, 8 enforced foreign keys, and 3 preserved optional linkage gaps.",
        "Phase 6 Kimball Star Schema: Built 7 dimensions, 5 facts (fact_orders pre-aggregated at order_id grain to eliminate fan-out), and 9 analytical data mart views.",
        "Phase 15–16 Automation & QA: Single CLI runner (pipelines/run_pipeline.py), GitHub Actions CI with disposable MySQL 8.0 validation, and cross-tool KPI reconciliation.",
    ])

    # Slide 4: Commercial Trends
    add_image_slide(
        prs,
        "Commercial Performance & Seasonality",
        "99,441 placed orders | BRL 13.22M delivered merchandise | BRL 13.59M recorded GMV",
        fig_dir / "eda_01_monthly_trends_and_seasonality.png",
        [
            "96,478 delivered orders with items generated BRL 13,221,498.11 (mean AOV BRL 137.04; median BRL 86.57).",
            "1,234 unsuccessful orders (625 canceled, 609 unavailable); BRL 97,242.96 known recorded exposure.",
            "Peak volume occurred in Nov 2017 (Black Friday: 7,289 delivered orders); weekday peak 10:00–22:00 Mon–Thu.",
        ],
    )

    # Slide 5: Category & Seller Concentration
    add_image_slide(
        prs,
        "Product & Seller Concentration",
        "8,351 products (25.9%) drive 80% of sales; Top 10% sellers drive 67.1% of sales",
        fig_dir / "eda_02_category_and_seller_concentration.png",
        [
            "Top categories: health_beauty (BRL 1.23M), watches_gifts, bed_bath_table, sports_leisure, computers_accessories.",
            "Top 10% of active sellers (309 of 3,095) account for 67.11% of delivered merchandise value.",
            "Cross-category basket self-joins reveal highest co-purchase pairing between bed_bath_table and home_confort.",
        ],
    )

    # Slide 6: Logistics & Regional SLA
    add_image_slide(
        prs,
        "Logistics Bottlenecks & Geographic Disparities",
        "93.23% national on-time rate (6,534 late orders); transit drives 74% of delivery time",
        fig_dir / "eda_03_logistics_stages_and_state_sla.png",
        [
            "Mean delivery duration is 12.56 days: Carrier transit averages 9.33 days vs. 2.85 days seller processing & 0.43 days approval.",
            "Distance strongly drives duration (Spearman rho = 0.543) and freight cost (rho = 0.593).",
            "Intra-state fulfillment hits 95.3%+ SLA vs. significantly higher delays and freight ratios in North/Northeast lanes.",
        ],
    )

    # Slide 7: Statistical Findings & Satisfaction
    add_image_slide(
        prs,
        "Customer Satisfaction & Statistical Evidence",
        "Late deliveries impose a -2.02 star rating penalty (Cohen d = 1.71, Holm adj. p < 1e-100)",
        fig_dir / "stat_01_hypothesis_summary.png",
        [
            "Early deliveries average 4.29 stars (9.23% negative) vs. 2.27 stars (62.36% negative) for late deliveries.",
            "Among 10,889 negative written Portuguese reviews, 29.5% cite non-delivery/waiting and 15.0% cite delays.",
            "All 5 business hypotheses remained statistically significant after Holm-Bonferroni correction.",
        ],
    )

    # Slide 8: Customer Intelligence
    add_image_slide(
        prs,
        "Customer Intelligence: RFM, Cohorts & Clustering",
        "93,358 unique customers (customer_unique_id) | 3.00% repeat purchase rate",
        fig_dir / "cust_01_cohort_retention_and_rfm.png",
        [
            "Only 2,801 unique customers placed >= 2 delivered orders; 30-day & 90-day cohort retention stays below ~1%.",
            "Recent Single & High-Spend Single buyers (~39% of base) represent the primary retention opportunity.",
            "K-Means clustering (k=3, Silhouette 0.3983) cleanly separates repeat buyers, recent singles, and dormant accounts.",
        ],
    )

    # Slide 9: Forecasting Model
    add_image_slide(
        prs,
        "Predictive Analytics (Model A): Demand Forecasting",
        "Historical 86-week backtest & illustrative continuation (Holt-Winters WAPE 17.97%)",
        fig_dir / "pred_01_demand_forecast_backtest.png",
        [
            "12-week unseen holdout (Jun–Aug 2018): Holt-Winters achieves 17.97% WAPE on merchandise (vs. 20.78% Naive).",
            "4-week Moving Average achieves 17.14% holdout WAPE (11.87% 4-fold expanding CV WAPE) on order volume.",
            "Framed strictly as historical backtesting and illustrative post-Aug 2018 continuation with 95% bands.",
        ],
    )

    # Slide 10: Delivery Delay Risk Classification
    add_image_slide(
        prs,
        "Predictive Analytics (Model B): Checkout Delay Risk",
        "Zero-leakage purchase-time classification (HistGradientBoosting ROC-AUC 0.7325)",
        fig_dir / "pred_02_delivery_risk_performance.png",
        [
            "Strictly uses checkout-time features + event-time prior seller late rate (delivered strictly before current purchase).",
            "On unseen Jun–Aug 2018 orders (n=18,603), HistGradientBoosting achieves 0.7325 ROC-AUC and 0.0771 PR-AUC (>2.1x dummy).",
            "Top drivers: estimated_delivery_days, approx_distance_km, is_same_state, category, seller_prior_late_rate.",
        ],
    )

    # Slide 11: BI Integration & Decision Intelligence
    add_image_slide(
        prs,
        "BI Integration & Decision Intelligence",
        "Reconciled Excel COM + Power BI PBIP + Prioritized Illustrative Scenarios",
        fig_dir / "dec_01_scenario_prioritization.png",
        [
            "Excel Workbook: Dynamic SUMIFS/XLOOKUP dashboard, PivotTable, PivotChart, and 3 Slicers reconciled 100% with MySQL.",
            "Power BI Project: PBIP + TMDL semantic model (39 DAX measures, 10 pages); ready for GUI credential refresh.",
            "Top Prioritized Actions: (1) Unsuccessful Order Recovery, (2) 14-day Retention Triggers, (3) Checkout Risk Routing.",
        ],
    )

    # Slide 12: Limitations & Delivery Summary
    s12 = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(s12, "Limitations, QA & Final Outcomes", "100% cross-tool reconciliation across Python, MySQL, Excel, and Power BI DAX")
    add_bullets(s12, [
        "Key Data Limitations: Historical 2016–2018 static snapshot; no platform commission/profit/CAC/refund fields; 462/842 closed deals lack marketplace seller match; GEO-08 (per-capita orders) infeasible without external population data.",
        "QA & Security: Automated pytest suites pass across ingestion, cleaning, warehouse, SQL reconciliation, leakage checks, and repository security (no tracked credentials or raw/processed data).",
        "Portfolio Readiness: Reproducible CLI pipeline, GitHub Actions CI, 7 executed notebooks with outputs intact, case study, resume bullets, and interview guide.",
    ])

    out_path = PROJECT_ROOT / "presentation" / "CommerceIQ_Executive_Presentation.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    return out_path


if __name__ == "__main__":
    p = build_deck()
    print("Generated presentation:", p)
