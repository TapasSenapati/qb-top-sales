-- DuckDB Schema for Forecasting Analytics
-- This schema is used to initialize DuckDB tables for analytics/OLAP workloads

-- Sequences for auto-increment IDs
CREATE SEQUENCE IF NOT EXISTS category_sales_agg_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS category_sales_forecast_id_seq START 1;

-- category_sales_agg: Aggregated sales by merchant, category, and time bucket
CREATE TABLE IF NOT EXISTS category_sales_agg (
    id                 BIGINT PRIMARY KEY,
    merchant_id        BIGINT NOT NULL,
    category_id        BIGINT NOT NULL,
    bucket_type        VARCHAR NOT NULL,
    bucket_start       TIMESTAMP WITH TIME ZONE NOT NULL,
    bucket_end         TIMESTAMP WITH TIME ZONE NOT NULL,
    total_sales_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    total_units_sold   BIGINT NOT NULL DEFAULT 0,
    order_count        BIGINT NOT NULL DEFAULT 0,
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Unique constraint for upserts
CREATE UNIQUE INDEX IF NOT EXISTS uq_category_sales_bucket 
    ON category_sales_agg (merchant_id, category_id, bucket_type, bucket_start);

-- Query optimization indexes
CREATE INDEX IF NOT EXISTS idx_cat_sales_merchant_bucket
    ON category_sales_agg (merchant_id, bucket_type, bucket_start);

-- processed_events: Idempotency tracking for Kafka consumer
CREATE TABLE IF NOT EXISTS processed_events (
    order_id     BIGINT PRIMARY KEY,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- category_sales_forecast: Pre-computed forecasts
CREATE TABLE IF NOT EXISTS category_sales_forecast (
    id                 BIGINT PRIMARY KEY,
    merchant_id        BIGINT NOT NULL,
    category_id        BIGINT NOT NULL,
    model_name         VARCHAR NOT NULL,
    generated_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    forecast_horizon   INTEGER NOT NULL,
    forecasted_values  VARCHAR NOT NULL,
    mae                DOUBLE
);

-- Unique constraint for forecasts
CREATE UNIQUE INDEX IF NOT EXISTS uq_category_sales_forecast
    ON category_sales_forecast (merchant_id, category_id, model_name, generated_at);

-- Query optimization index
CREATE INDEX IF NOT EXISTS idx_cat_sales_forecast_lookup
    ON category_sales_forecast (merchant_id, generated_at);
