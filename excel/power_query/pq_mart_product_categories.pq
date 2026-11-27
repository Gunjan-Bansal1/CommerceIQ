// Power Query M Script: Load Product Category Performance Mart from MySQL
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    MartCategory = Source{[Schema="commerceiq", Item="mart_product_category_performance"]}[Data],
    TypedTable = Table.TransformColumnTypes(MartCategory, {
        {"product_category_name", type text},
        {"product_category_name_english", type text},
        {"catalog_products", Int64.Type},
        {"total_orders", Int64.Type},
        {"total_items", Int64.Type},
        {"delivered_items", Int64.Type},
        {"delivered_merchandise_brl", Currency.Type},
        {"delivered_freight_brl", Currency.Type},
        {"recorded_merchandise_brl", Currency.Type},
        {"avg_delivered_item_price_brl", Currency.Type},
        {"avg_freight_to_price_pct", type number},
        {"avg_order_review_score", type number}
    }),
    SortedRows = Table.Sort(TypedTable, {{"delivered_merchandise_brl", Order.Descending}})
in
    SortedRows
