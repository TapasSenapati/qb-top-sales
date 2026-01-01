-- PostgreSQL Schema for Ingestion (OLTP)
-- Analytics/forecasting data is stored in DuckDB (see db/03_duckdb_schema.sql)
-- but category_sales_agg is also in Postgres for JPA queries that join with ingestion tables
CREATE SCHEMA IF NOT EXISTS ingestion;
CREATE SCHEMA IF NOT EXISTS forecasting;

-- forecasting.category_sales_agg (for JPA queries joining with ingestion tables if needed)
CREATE TABLE IF NOT EXISTS forecasting.category_sales_agg (
    id                 BIGSERIAL PRIMARY KEY,
    merchant_id        BIGINT NOT NULL,
    category_id        BIGINT NOT NULL,
    bucket_type        VARCHAR(10) NOT NULL,  -- DAY | WEEK | MONTH
    bucket_start       TIMESTAMPTZ NOT NULL,
    bucket_end         TIMESTAMPTZ NOT NULL,
    total_sales_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_units_sold   BIGINT NOT NULL DEFAULT 0,
    order_count        BIGINT NOT NULL DEFAULT 0,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_category_sales_bucket UNIQUE (merchant_id, category_id, bucket_type, bucket_start)
);

CREATE INDEX IF NOT EXISTS idx_cat_sales_merchant_bucket
    ON forecasting.category_sales_agg (merchant_id, bucket_type, bucket_start);

-- ingestion.merchants
-- Each merchant operates in a single base currency (no multi-currency orders)
CREATE TABLE IF NOT EXISTS ingestion.merchants
(
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT        NOT NULL,
    currency   TEXT        NOT NULL,  -- Merchant's base currency (e.g., USD, EUR, INR)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ingestion.categories
CREATE TABLE IF NOT EXISTS ingestion.categories
(
    id                 BIGSERIAL PRIMARY KEY,
    merchant_id        BIGINT NOT NULL REFERENCES ingestion.merchants (id),
    name               TEXT   NOT NULL,
    parent_category_id BIGINT NULL REFERENCES ingestion.categories (id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ingestion.products
CREATE TABLE IF NOT EXISTS ingestion.products
(
    id          BIGSERIAL PRIMARY KEY,
    merchant_id BIGINT      NOT NULL REFERENCES ingestion.merchants (id),
    category_id BIGINT      NOT NULL REFERENCES ingestion.categories (id),
    name        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ingestion.orders
-- CURRENCY STRATEGY: Snapshot. 
-- We store the currency on the order to ensure immutability and historical accuracy.
-- Ideally matches the merchant's base currency.
CREATE TABLE IF NOT EXISTS ingestion.orders
(
    id                BIGSERIAL PRIMARY KEY,
    merchant_id       BIGINT         NOT NULL REFERENCES ingestion.merchants (id),
    order_date        TIMESTAMPTZ    NOT NULL,
    currency          TEXT           NOT NULL,  -- Snapshot of currency at order time
    total_amount      NUMERIC(18, 2) NOT NULL,
    external_order_id TEXT UNIQUE,
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- ingestion.order_items
CREATE TABLE IF NOT EXISTS ingestion.order_items
(
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT         NOT NULL REFERENCES ingestion.orders (id),
    product_id  BIGINT         NOT NULL REFERENCES ingestion.products (id),
    quantity    INT            NOT NULL,
    unit_price  NUMERIC(18, 2) NOT NULL,
    line_amount NUMERIC(18, 2) NOT NULL,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- ingestion.order_events (outbox)
-- TODO (Production): Use TSID/Snowflake for globally unique, time-sorted event IDs
-- when scaling to multiple ingestion instances
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

-- Useful indexes for ingestion schema
CREATE INDEX IF NOT EXISTS idx_orders_merchant_date
    ON ingestion.orders (merchant_id, order_date);

CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON ingestion.order_items (order_id);

-- Partial index for outbox publisher: speeds up findByProcessedFalse query
CREATE INDEX IF NOT EXISTS idx_order_events_unprocessed
    ON ingestion.order_events (created_at)
    WHERE processed = false;
