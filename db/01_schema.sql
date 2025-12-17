-- Schemas
CREATE SCHEMA IF NOT EXISTS ingestion;
CREATE SCHEMA IF NOT EXISTS forecasting;

-- ingestion.merchants
CREATE TABLE IF NOT EXISTS ingestion.merchants
(
    id   BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

-- ingestion.categories
CREATE TABLE IF NOT EXISTS ingestion.categories
(
    id                 BIGSERIAL PRIMARY KEY,
    merchant_id        BIGINT NOT NULL REFERENCES ingestion.merchants (id),
    name               TEXT   NOT NULL,
    parent_category_id BIGINT NULL REFERENCES ingestion.categories (id)
);

-- ingestion.products
CREATE TABLE IF NOT EXISTS ingestion.products
(
    id          BIGSERIAL PRIMARY KEY,
    merchant_id BIGINT NOT NULL REFERENCES ingestion.merchants (id),
    category_id BIGINT NOT NULL REFERENCES ingestion.categories (id),
    name        TEXT   NOT NULL
);

-- ingestion.orders
CREATE TABLE IF NOT EXISTS ingestion.orders
(
    id           BIGSERIAL PRIMARY KEY,
    merchant_id  BIGINT         NOT NULL REFERENCES ingestion.merchants (id),
    order_date   TIMESTAMPTZ    NOT NULL,
    currency     TEXT           NOT NULL,
    total_amount NUMERIC(18, 2) NOT NULL
);

-- ingestion.order_items
CREATE TABLE IF NOT EXISTS ingestion.order_items
(
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT         NOT NULL REFERENCES ingestion.orders (id),
    product_id  BIGINT         NOT NULL REFERENCES ingestion.products (id),
    quantity    INT            NOT NULL,
    unit_price  NUMERIC(18, 2) NOT NULL,
    line_amount NUMERIC(18, 2) NOT NULL
);

-- ingestion.order_events (outbox)
CREATE TABLE IF NOT EXISTS ingestion.order_events
(
    id           BIGSERIAL PRIMARY KEY,
    order_id     BIGINT      NOT NULL REFERENCES ingestion.orders (id),
    merchant_id  BIGINT      NOT NULL REFERENCES ingestion.merchants (id),
    event_type   TEXT        NOT NULL,
    payload      TEXT,
    created_at   TIMESTAMPTZ NOT NULL,
    processed    BOOLEAN     NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ NULL
);

-- forecasting.category_sales_agg
CREATE TABLE IF NOT EXISTS forecasting.category_sales_agg
(
    id                 BIGSERIAL PRIMARY KEY,
    merchant_id        BIGINT         NOT NULL,
    category_id        BIGINT         NOT NULL,
    bucket_type        TEXT           NOT NULL, -- DAY | WEEK | MONTH
    bucket_start       TIMESTAMPTZ    NOT NULL,
    bucket_end         TIMESTAMPTZ    NOT NULL,
    total_sales_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_units_sold   BIGINT         NOT NULL DEFAULT 0,
    order_count        BIGINT         NOT NULL DEFAULT 0,
    updated_at         TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT uq_category_sales_bucket
        UNIQUE (merchant_id, category_id, bucket_type, bucket_start)
);

CREATE INDEX IF NOT EXISTS idx_cat_sales_merchant_bucket
    ON forecasting.category_sales_agg (merchant_id, bucket_type, bucket_start);

CREATE INDEX IF NOT EXISTS idx_cat_sales_top_amount
    ON forecasting.category_sales_agg (merchant_id, bucket_type, bucket_start, total_sales_amount DESC);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_orders_merchant_date
    ON ingestion.orders (merchant_id, order_date);

CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON ingestion.order_items (order_id);

CREATE INDEX IF NOT EXISTS idx_category_sales_agg_lookup
    ON forecasting.category_sales_agg (merchant_id, bucket_type, bucket_start);

CREATE TABLE IF NOT EXISTS forecasting.processed_events
(
    event_id     BIGINT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL
);

-- forecasting.category_sales_forecast
CREATE TABLE IF NOT EXISTS forecasting.category_sales_forecast
(
    id                 BIGSERIAL PRIMARY KEY,
    merchant_id        BIGINT         NOT NULL,
    category_id        BIGINT         NOT NULL,
    model_name         TEXT           NOT NULL,
    generated_at       TIMESTAMPTZ    NOT NULL,
    forecast_horizon   INT            NOT NULL,
    forecasted_values  JSONB          NOT NULL,
    mae                FLOAT,
    CONSTRAINT uq_category_sales_forecast
        UNIQUE (merchant_id, category_id, model_name, generated_at)
);

CREATE INDEX IF NOT EXISTS idx_cat_sales_forecast_lookup
    ON forecasting.category_sales_forecast (merchant_id, generated_at);

