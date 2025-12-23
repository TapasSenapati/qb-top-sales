-- PostgreSQL Schema for Ingestion (OLTP)
--Analytics/forecasting data is stored in DuckDB (see db/03_duckdb_schema.sql)
CREATE SCHEMA IF NOT EXISTS ingestion;

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
-- CURRENCY ASSUMPTION (demo): Each merchant uses a single base currency.
-- No currency conversion is implemented in aggregation/forecasting.
-- Production: Normalize amounts to base currency at ingestion or aggregation
-- using exchange rate table or external API.
CREATE TABLE IF NOT EXISTS ingestion.orders
(
    id           BIGSERIAL PRIMARY KEY,
    merchant_id  BIGINT         NOT NULL REFERENCES ingestion.merchants (id),
    order_date   TIMESTAMPTZ    NOT NULL,
    currency     TEXT           NOT NULL,  -- Merchant's base currency (no conversion)
    total_amount NUMERIC(18, 2) NOT NULL,
    external_order_id TEXT UNIQUE
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


