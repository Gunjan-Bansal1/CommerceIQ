// Power Query M Script: Load Processed Orders CSV directly (file-based fallback)
// Useful when MySQL ODBC/Connector is unavailable on a client workstation.
let
    Source = Csv.Document(
        File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\csv\orders.csv"),
        [Delimiter=",", Columns=40, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    SelectedColumns = Table.SelectColumns(PromotedHeaders, {
        "order_id", "customer_id", "order_status", "purchase_date",
        "purchase_year_month", "is_core_reporting_period",
        "delivery_duration_days", "is_on_time_delivery", "delivery_performance"
    }),
    TypedTable = Table.TransformColumnTypes(SelectedColumns, {
        {"order_id", type text},
        {"customer_id", type text},
        {"order_status", type text},
        {"purchase_date", type date},
        {"purchase_year_month", type text},
        {"is_core_reporting_period", type logical},
        {"delivery_duration_days", type number},
        {"is_on_time_delivery", type logical},
        {"delivery_performance", type text}
    })
in
    TypedTable
