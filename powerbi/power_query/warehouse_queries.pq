// CommerceIQ Power BI Power Query M Definitions
// Connects to MySQL Warehouse (`commerceiq`, requires 64-bit MySQL Connector/NET 8.0.x)
// and strongly typed downstream Phase 11/12/14 CSV outputs.

// 1. dim_date (filters out unknown member date_key = -1 with NULL full_date; normalizes tinyint(1) flags)
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_date"]}[Data],
    ValidDates = Table.SelectRows(Data, each [date_key] > 0 and [full_date] <> null),
    TypedFlags = Table.TransformColumns(ValidDates, {{"is_weekend", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_core_reporting_period", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_brazil_national_holiday", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_brazil_any_holiday", each if _ = null then null else Int64.From(_), Int64.Type}})
in
    TypedFlags

// 2-12: Remaining Warehouse Tables (example: fact_orders with tinyint(1) -> Int64.Type normalization)
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_orders"]}[Data],
    TypedFlags = Table.TransformColumns(Data, {{"is_delivered", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_canceled", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_unavailable", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_unsuccessful", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_core_reporting_period", each if _ = null then null else Int64.From(_), Int64.Type}, {"has_order_items", each if _ = null then null else Int64.From(_), Int64.Type}, {"has_payment_records", each if _ = null then null else Int64.From(_), Int64.Type}, {"has_review_records", each if _ = null then null else Int64.From(_), Int64.Type}, {"has_written_review", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_valid_delivery_promise_comparison", each if _ = null then null else Int64.From(_), Int64.Type}, {"is_on_time_delivery", each if _ = null then null else Int64.From(_), Int64.Type}})
in
    TypedFlags

// 13. customer_rfm_segments (Typed CSV)
let
    Source = Csv.Document(File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\customer_rfm_segments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {{"customer_unique_id", type text}, {"primary_state", type text}, {"recency_days", Int64.Type}, {"frequency", Int64.Type}, {"monetary_brl", type number}, {"r_score", Int64.Type}, {"f_score", Int64.Type}, {"m_score", Int64.Type}, {"rfm_segment", type text}, {"cluster_id", Int64.Type}, {"is_repeat", type logical}, {"illustrative_15pct_gross_margin_brl", type number}})
in
    TypedTable

// 14. forecast_outputs (Typed CSV)
let
    Source = Csv.Document(File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\forecast_outputs.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {{"week_start", type date}, {"actual_value", type number}, {"target", type text}, {"record_type", type text}, {"model", type text}, {"predicted_value", type number}, {"ci_lower_95", type number}, {"ci_upper_95", type number}})
in
    TypedTable

// 15. delivery_risk_predictions (Typed CSV)
let
    Source = Csv.Document(File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\delivery_risk_predictions.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {{"order_id", type text}, {"order_purchase_timestamp", type datetime}, {"customer_state", type text}, {"seller_state", type text}, {"customer_region", type text}, {"seller_region", type text}, {"estimated_delivery_days", type number}, {"approx_distance_km", type number}, {"is_late", Int64.Type}, {"predicted_late_prob", type number}, {"predicted_high_risk_flag", Int64.Type}, {"risk_tier", type text}})
in
    TypedTable

// 16. decision_scenarios (Typed CSV)
let
    Source = Csv.Document(File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\decision_scenarios.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {{"scenario_id", type text}, {"scenario_name", type text}, {"tier", type text}, {"observed_baseline_label", type text}, {"observed_baseline_value", type number}, {"assumed_input_parameter", type number}, {"driver_unit", type text}, {"illustrative_margin_assumption", type number}, {"illustrative_intervention_cost_brl", type number}, {"simulated_gmv_or_savings_brl", type number}, {"simulated_illustrative_contribution_brl", type number}, {"simulated_illustrative_net_benefit_brl", type number}, {"is_illustrative_simulation", type logical}})
in
    TypedTable
