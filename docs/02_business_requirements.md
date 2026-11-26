# CommerceIQ — Business Requirements Document

**Version:** 1.0 | **Status:** Preliminary, subject to source profiling

## Business process
Order placement → approval → processing → carrier handover → delivery → feedback (when available). Cancellation, unavailability and in-progress statuses are distinct outcomes. Shipping limit is a deadline, not a processing timestamp. Reviews can occur without successful delivery.

## Business problems and objectives
| ID | Problem | Objective |
|---|---|---|
| BP-01 | Fragmented data | Consistent reporting |
| BP-02 | Unsuccessful orders | Quantify recorded value at risk |
| BP-03 | Late deliveries | Improve reliability |
| BP-04 | Slow processing | Diagnose bottlenecks |
| BP-05 | Poor satisfaction | Investigate review patterns |
| BP-06 | Limited repeat buying | Evaluate retention |
| BP-07 | Seller variability | Prioritize support |
| BP-08 | Product variability | Identify category opportunities |
| BP-09 | High freight charges | Compare freight affordability |
| BP-10 | Regional differences | Assess geographic performance |
| BP-11 | Uncertain demand | Forecast workload |
| BP-12 | Seller acquisition | Evaluate conversion |
| BP-13 | Reactive management | Estimate delivery risk |
| BP-14 | Unclear intervention benefit | Evaluate scenarios |
| BP-15 | Manual reporting | Automate reproducible processing |

## Stakeholder and functional requirements
| ID | Owner | Required output | Decision |
|---|---|---|---|
| FR-01 | CEO | Executive KPIs | Strategic priorities |
| FR-02 | CFO | Unsuccessful order count, value and coverage | Investigations |
| FR-03 | Customer relationship | RFM and cohorts | Retention |
| FR-04 | Category manager | Product and basket analysis | Assortment |
| FR-05 | Seller manager | Seller scorecards | Support allocation |
| FR-06 | Logistics/operations | SLA and lifecycle report | Process improvement |
| FR-07 | Regional manager | Geographic comparison | Regional opportunities |
| FR-08 | Finance | Payment behaviour and reconciliation | Payment monitoring |
| FR-09 | Marketing | Lead funnel and activation | Acquisition channels |
| FR-10 | Customer experience | Ratings and complaint themes | Service improvement |
| FR-11 | Operations | Forecast and delivery risk | Capacity and prioritization |
| FR-12 | Management | Scenario and optimization model | Budget allocation |
| FR-13 | Engineering | Reproducible ingestion | Data refresh |
| FR-14 | Analyst | Data quality report | Exception treatment |
| FR-15 | Analyst | Reconciled Excel/SQL/BI | Reliable reporting |
| FR-16 | Engineering | Historical batch replay | Automation |

## Non-functional requirements
Accuracy, reproducibility, credential security, modular maintainability, source traceability, idempotency, interpretability, practical local performance, transparent assumptions, source licensing, error logging and raw-file preservation.

## Scope and business rules
Use historical Olist marketplace and sampled seller acquisition records. Monetary reporting is BRL. Merchandise sales are not platform revenue; freight charged is not actual logistics cost. Count orders by distinct order ID and customers by persistent customer ID. Use delivered orders for realized merchandise sales proxy; canceled/unavailable for unsuccessful orders, subject to validation. Missing monetary data is unknown. Compare delivery calendar dates for SLA; use valid timestamps for elapsed durations. Use complete comparable periods and observable retention windows. Pre-aggregate separate transactional grains to avoid fan-out. Multi-seller outcomes indicate exposure, not responsibility. Actual profit, inventory, CAC, ROAS, web conversion, refunds, real-time monitoring and causal impact are out of scope.

## Constraints and risks
Historical and anonymized data; missing values, possible repeated reviews and geographic keys; multiple payments and sellers; incomplete reporting periods; sparse repeat buying; Portuguese review text; sampled leads and incomplete seller linkage; static dataset; separate Colab/local environments; no measured intervention effect. Validate data fields, grain and coverage in Phase 3. Use language-appropriate text methods and separately labeled financial scenarios.

## Acceptance criteria
| ID | Test |
|---|---|
| AC-01 | Verify all 11 files and metadata |
| AC-02 | Preserve raw files |
| AC-03 | Document and address data-quality exceptions |
| AC-04 | Implement relational schema and validated keys |
| AC-05 | Implement fact/dimension model and marts |
| AC-06 | Reconcile critical KPIs across tools |
| AC-07 | Address 120 candidate questions or document infeasibility |
| AC-08 | Report statistical assumptions, effect sizes and limitations |
| AC-09 | Forecast with chronological holdout and baseline |
| AC-10 | Validate risk model on unseen data without leakage |
| AC-11 | Validate BI measures and report pages |
| AC-12 | Expose scenario assumptions and constraints |
| AC-13 | Test idempotent reruns |
| AC-14 | Exclude credentials and restricted data from publishing |
| AC-15 | Document reproducible implementation |
| AC-16 | Link recommendations to evidence |
| AC-17 | Deliver complete portfolio artifacts |

See `04_kpi_dictionary.md` and `05_business_questions.md` for detailed analytical specifications. No actual baseline or management target is established yet.
