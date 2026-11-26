# CommerceIQ — Project Charter

**Version:** 1.0 (planning baseline)  
**Status:** Proposed independent educational case study

## Business context and problem
A marketplace coordinates customers, sellers, payments and fulfilment. Fragmented historical records make unified performance analysis difficult. CommerceIQ will integrate these records to investigate unsuccessful orders, delivery reliability, customer behaviour, seller performance and opportunities for intervention. These are case-study hypotheses, not claims about Olist's current operations.

## Objectives
Measure merchandise sales and order outcomes; quantify recorded unsuccessful order value; investigate delivery bottlenecks, customer experience and retention; evaluate products, sellers, regions, payments and seller acquisition; forecast demand and assess delivery risk; evaluate intervention scenarios; establish reproducible reporting.

## Data and technology
- Olist Brazilian E-Commerce Public Dataset (9 CSVs): https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Olist Marketing Funnel (2 CSVs): https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist
- Optional calendar, holiday, population and geographic enrichment, subject to source validation.
- Python, MySQL 8.0, Excel, Power BI, VS Code, Colab, Git/GitHub.

## Scope and constraints
Historical analytics, relational and dimensional modeling, statistics, predictive analytics, scenarios and reproducible ETL are included. Actual marketplace revenue, profit, commissions, refunds, inventory optimization, customer acquisition cost, website conversion and production deployment are excluded because adequate source data or access is unavailable. Financial scenarios are not realized savings. Observational associations do not establish causality.

## Stakeholders
Hypothetical executive, finance, operations, logistics, customer experience, customer relationship, seller relationship, category, marketing and regional managers; data analyst and engineering roles.

## Delivery roadmap
| Phase | Stage |
|---|---|
| 0 | Environment setup |
| 1 | Business understanding |
| 2 | Data acquisition |
| 3 | Data understanding |
| 4 | Data cleaning |
| 5 | Database development |
| 6 | Data warehouse modeling |
| 7 | Excel analytics |
| 8 | SQL analytics |
| 9 | EDA |
| 10 | Statistical analytics |
| 11 | Advanced customer analytics |
| 12 | Predictive analytics |
| 13 | Power BI |
| 14 | Decision intelligence |
| 15 | Automation |
| 16 | Testing and validation |
| 17 | Final delivery |

Indicative duration: 10–12 weeks, flexible. Phase 0–1 grouped; from Phase 2, execute one code cell at a time, inspect output before continuing, and wait for explicit approval at phase boundaries.

## Acceptance
Verify sources and preserve raw files; document exceptions; reconcile critical metrics across tools; assess models against baselines on unseen chronological data; provide transparent scenarios, evidence-linked recommendations, reproducible scripts, tests and portfolio documentation. Never publish credentials or restricted source data.

## Approval and change control
The learner approves each phase. Revisions to scope, formulas and data rules are documented as evidence emerges. No actual stakeholder approval is claimed.
