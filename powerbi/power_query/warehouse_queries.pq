// CommerceIQ Power BI Power Query M Definitions
// Connects to MySQL Warehouse (`commerceiq`) and downstream Phase 11/12/14 CSV outputs.

// 1. dim_date
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_date"]}[Data]
in
    Data

// 2. dim_customer
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_customer"]}[Data]
in
    Data

// 3. dim_seller
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_seller"]}[Data]
in
    Data

// 4. dim_product
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_product"]}[Data]
in
    Data

// 5. dim_geography
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="dim_geography"]}[Data]
in
    Data

// 6. fact_orders
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_orders"]}[Data]
in
    Data

// 7. fact_order_items
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_order_items"]}[Data]
in
    Data

// 8. fact_payments
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_payments"]}[Data]
in
    Data

// 9. fact_reviews
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_reviews"]}[Data]
in
    Data

// 10. fact_marketing_funnel
let
    Source = MySQL.Database("localhost", "commerceiq", [ReturnSingleDatabase=true]),
    Data = Source{[Schema="commerceiq", Item="fact_marketing_funnel"]}[Data]
in
    Data

// 11. Downstream Python Analytics Outputs (RFM, Forecasts, Delivery Risk, Decision Scenarios)
let
    RFM = Csv.Document(File.Contents("C:\Users\bgunj\Desktop\commerceIQ\data\processed\customer_rfm_segments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    RFM_Typed = Table.PromoteHeaders(RFM, [PromoteAllScalars=true])
in
    RFM_Typed
