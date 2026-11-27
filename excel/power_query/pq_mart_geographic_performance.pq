// Power Query M Script: Load Geographic & Logistics Summary from MySQL
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    MartGeo = Source{[Schema="commerceiq", Item="mart_geographic_performance"]}[Data],
    TypedTable = Table.TransformColumnTypes(MartGeo, {
        {"customer_state", type text},
        {"customer_region", type text},
        {"total_orders", Int64.Type},
        {"unique_customers", Int64.Type},
        {"delivered_orders", Int64.Type},
        {"delivered_merchandise_brl", Currency.Type},
        {"delivered_freight_brl", Currency.Type},
        {"freight_to_merchandise_pct", type number},
        {"on_time_rate_pct", type number},
        {"mean_delivery_days", type number},
        {"mean_review_score", type number}
    }),
    SortedRows = Table.Sort(TypedTable, {{"delivered_merchandise_brl", Order.Descending}})
in
    SortedRows
