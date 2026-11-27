// Power Query M Script: Load CommerceIQ Executive Monthly Mart from MySQL
// Reuses Phase 4/6 modeled mart rather than duplicating raw cleaning.
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    MartExecMonthly = Source{[Schema="commerceiq", Item="mart_executive_monthly"]}[Data],
    TypedTable = Table.TransformColumnTypes(MartExecMonthly, {
        {"year_month_str", type text},
        {"is_core_reporting_period", Int64.Type},
        {"total_orders", Int64.Type},
        {"delivered_orders", Int64.Type},
        {"canceled_orders", Int64.Type},
        {"unavailable_orders", Int64.Type},
        {"unsuccessful_orders", Int64.Type},
        {"delivered_merchandise_brl", Currency.Type},
        {"delivered_freight_brl", Currency.Type},
        {"recorded_gmv_brl", Currency.Type},
        {"recorded_payment_brl", Currency.Type},
        {"avg_delivered_order_value_brl", Currency.Type},
        {"eligible_delivery_orders", Int64.Type},
        {"on_time_orders", Int64.Type},
        {"on_time_delivery_pct", type number},
        {"mean_order_review_score", type number}
    }),
    SortedRows = Table.Sort(TypedTable, {{"year_month_str", Order.Ascending}})
in
    SortedRows
