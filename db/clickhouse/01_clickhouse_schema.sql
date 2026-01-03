-- ClickHouse Schema for Analytics (category_sales_agg, category_sales_forecast)
-- Uses ReplacingMergeTree for upsert semantics on aggregation data

-- Category Sales Aggregation (main analytics table)
-- ReplacingMergeTree: keeps the row with the latest updated_at for each unique key
CREATE TABLE IF NOT EXISTS category_sales_agg (
    merchant_id        UInt64,
    category_id        UInt64,
    bucket_type        LowCardinality(String),  -- DAY, WEEK, MONTH, YEAR
    bucket_start       DateTime64(3, 'UTC'),
    bucket_end         DateTime64(3, 'UTC'),
    total_sales_amount Decimal(18, 2),
    total_units_sold   UInt64,
    order_count        UInt64,
    updated_at         DateTime64(3, 'UTC') DEFAULT now64()
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(bucket_start)
ORDER BY (merchant_id, category_id, bucket_type, bucket_start);

-- Category Sales Forecast (ML model outputs)
CREATE TABLE IF NOT EXISTS category_sales_forecast (
    id                UInt64,
    merchant_id       UInt64,
    category_id       UInt64,
    model_name        LowCardinality(String),  -- rolling, wma, ses, arima, snaive, ensemble
    generated_at      DateTime64(3, 'UTC'),
    forecast_horizon  UInt16,
    forecasted_values String,  -- JSON array of forecasts
    mae               Nullable(Float64)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(generated_at)
ORDER BY (merchant_id, category_id, model_name, generated_at);

-- Processed Events (idempotency tracking)
CREATE TABLE IF NOT EXISTS processed_events (
    order_id     UInt64,
    processed_at DateTime64(3, 'UTC') DEFAULT now64()
)
ENGINE = ReplacingMergeTree(processed_at)
ORDER BY order_id;
