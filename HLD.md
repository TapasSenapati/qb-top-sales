## Requirements & Assumptions

## Problem scope (functional)

- Ingest commerce orders for a merchant and persist them via an Orders API.

- Compute and serve "top sales by category" for selectable timeframes (week, month, year) through a user-friendly UI.
    
- Forecast next-period "top sales by category" and allow users to view results via UI/API endpoints (including model selection/compare).
    
## Non-functional requirements

- High availability: the read path (top categories + forecasts) should remain available under partial failures, with graceful degradation when compute pipelines lag.
    
- Accuracy & consistency: aggregates must converge without double-counting; forecasts must be reproducible for a given model/version and input series.
    
- Scalability: support many merchants and increasing order volume with horizontal scaling and partitioning.
    
- Observability: health checks, lag metrics, and failure alerting for ingestion->Kafka->aggregation and forecast generation.
    

## Assumptions

- Merchant catalog (merchants/categories/products) exists and is considered "platform-owned"; this design only consumes those concepts.
    
- Ranking definition: "top sales" means sorting categories by total sales amount for the merchant in a selected timeframe window.
    
- Time semantics: production supports calendar-aligned week/month/year with a configurable merchant timezone + "week starts on X" policy (default can be UTC/Monday).
    
- Consistency model: eventual consistency is acceptable between order creation and aggregate/forecast availability, but the system must converge.

- Flat categories: categories are non-hierarchical (no parent-child relationships). If hierarchical categories are needed in production (e.g., "Smartphones → Phones → Electronics"), add `parent_category_id` with recursive queries for roll-up reporting.

- Single currency per merchant: each merchant operates in a single base currency (e.g., USD, EUR, INR). Currency is stored on the merchant, not per-order. No currency conversion is implemented. Production multi-currency support would require exchange rate tables and normalization at ingestion or aggregation time.
    

## Architecture

## Components (implemented)

- **Order Simulator**: generates/backfills orders and POSTs to ingestion-service; waits on ingestion health endpoint before sending traffic.
    
- **Ingestion Service**: exposes `POST /v1/orders` and persists orders + outbox rows in PostgreSQL.
    
- **Outbox Relay (in ingestion service)**: scheduled publisher reads `ingestion.order_events` and publishes to Kafka topic `order-events`.
    
- **Aggregation Service**: consumes `order-events`, dedupes using `orderId` in DuckDB `processed_events`, and upserts bucketed totals using **dual-write pattern**:
  - **Postgres** `forecasting.category_sales_agg`: for real-time API queries via `/api/top-categories`
  - **DuckDB** `category_sales_agg`: for batch forecasting worker
  
- **Forecasting Service (FastAPI)**: serves UI + endpoints like `/forecast/top-categories` and `/forecast/compare-models`. Reads from DuckDB for analytics, PostgreSQL for category names.
    
- **Forecasting Worker**: periodic scheduler to precompute forecasts for merchants and store them in DuckDB `category_sales_forecast`.
    
- Compose wiring shows ingestion (8081), aggregation (8082), forecasting (8090), plus Kafka/Postgres/Consul.
    

## ASCII HLD diagram 
```
                              +---------------------------+
                              |         End User          |
                              |  Top sales + Forecast UI  |
                              +-------------+-------------+
                                            |
                                            | HTTPS
                                            v
                     +----------------------+----------------------+
                     |     API Gateway / Ingress (prod add-on)     |
                     |  AuthN/AuthZ, TLS, WAF, rate limits, routing|
                     +-----------+---------------------+-----------+
                                 |                     |
                                 |                     |
                                 v                     v
                 +---------------+-----+     +---------+----------------+
                 |  Forecasting Service |     |     Aggregation Service |
                 |  (FastAPI + UI/API)  |     |  (Kafka consumer + API) |
                 |  /forecast/*, /ui    |     |  /api/top-categories    |
                 +----------+-----------+     +-----------+-------------+
                            |                             |
    Read category names     |                             | Write aggregates
                            v                             v
+-------------------+   +------------+             +-------------+
|  Order Simulator  |   | PostgreSQL |             |   DuckDB    |
| (load + backfill) +-->| (OLTP)     |             | (Analytics) |
+-------------------+   +------------+             +-------------+
                        | ingestion.*|             | category_   |
                        | - merchants|             |   sales_agg |
                        | - categories             | processed_  |
                        | - products |             |   events    |
                        | - orders   |             | category_   |
                        | - order_   |             |   sales_    |
                        |   items    |             |   forecast  |
                        | - order_   |             +------^------+
                        |   events   |                    |
                        +-----+------+                    | Read/Write
                              ^                           |
                              | SQL write          +------+------+
                              |                    | Forecasting |
                 +------------+---------+          |   Worker    |
                 |    Ingestion Service |          | (precompute)|
                 |   POST /v1/orders    |          +-------------+
                 | + outbox table write |
                 +----------+-----------+
                            |
                            | Kafka publish (outbox relay)
                            v
                     +------+----------------+
                     |  Kafka topic:         |
                     |     order-events      |
                     +-----------------------+
```


## Production-grade components (not implemented, recommended)

- **Identity/tenancy**: JWT/OAuth, merchant scoping, RBAC, audit logs.
    
- **Schema management**: schema registry for events (Avro/Protobuf/JSON Schema) + compatibility enforcement.
    
- **DLQ + retry topics**: poison-message handling for `order-events`, with dead-letter routing and replay tooling.
    
- **Centralized observability**: metrics (consumer lag, job duration), tracing, structured logs, alerting.
    
- **Caching layer**: Redis for hot "top categories" and forecast results.
    
- **Job orchestration**: replace in-process scheduler with a distributed scheduler (K8s CronJob/Airflow/Temporal) supporting retries, sharding, and leader election.
    
- **HA data stores**: Postgres replication/failover, read replicas for query-heavy endpoints.

- **TSID/Snowflake IDs**: Replace DB-generated `orderId` with globally unique, time-sorted IDs when scaling to multiple ingestion instances.
    
- **Flink/Spark streaming**: Replace batch aggregation with real-time stream processing for lower latency.
    

## Interfaces (API + events)

## Ingestion service API

- **POST** `/v1/orders` -> creates an order (201 response).
    
    - Used by order-simulator to drive load/backfill.
    - Uses `externalOrderId` for API-level idempotency (client-provided UUID prevents duplicates on retries).

## Aggregation service API (actuals)

- **GET** `/api/top-categories` with `merchantId`, `bucketType`, `bucketStart`, `limit` returns top categories by aggregated sales amount.

## Forecasting service API (predictions)

- **GET** `/forecast/top-categories` supports `merchant_id`, `bucket_type`, `model`, `lookback`, `limit` and returns top forecasted categories.
    
- **GET** `/forecast/compare-models` fetches the latest precomputed forecasts for a merchant.
    
- **GET** `/health` and `/health/duckdb` for service health checks (used by infra/Consul).

## Event contract (internal)

- Kafka topic: `order-events` produced by ingestion outbox relay and consumed by aggregation service.
    
- Simplified payload (uses `orderId` for downstream idempotency):
```json
{
  "orderId": 12345,
  "merchantId": 1,
  "orderDate": "2024-01-15T10:30:00Z",
  "items": [
    {"categoryId": 2, "quantity": 3, "lineAmount": 59.97}
  ]
}
```
    
- Production recommendation: versioned schema + TSID/Snowflake for globally unique IDs when scaling.
    
## Data model (DB schemas with PK/FK)

## Schema separation

- **PostgreSQL** (`ingestion.*`): OLTP entities and the outbox table for transactional workloads.
    
- **DuckDB** (analytics): Aggregated sales facts, idempotency tracking, and forecast outputs. This separation enables:
  - Optimized columnar storage for time-series queries
  - No impact on OLTP performance during analytical queries
  - Independent scaling of OLTP and OLAP layers

## ingestion schema - PostgreSQL (PK/FK)

- `ingestion.merchants`
    - **PK**: `id` (BIGSERIAL).
    - `currency` (TEXT NOT NULL): merchant's base currency (single currency per merchant).
        
- `ingestion.categories`
    - **PK**: `id` (BIGSERIAL).
    - **FK**: `merchant_id -> ingestion.merchants(id)`.
    - Flat structure (no hierarchy).
        
- `ingestion.products`
    - **PK**: `id` (BIGSERIAL).
    - **FK**: `merchant_id -> ingestion.merchants(id)`.
    - **FK**: `category_id -> ingestion.categories(id)`.
        
- `ingestion.orders`
    - **PK**: `id` (BIGSERIAL).
    - **FK**: `merchant_id -> ingestion.merchants(id)`.
    - **UNIQUE**: `external_order_id` (for API idempotency).
    - Currency is derived from merchant (not stored per-order).
        
- `ingestion.order_items`
    - **PK**: `id` (BIGSERIAL).
    - **FK**: `order_id -> ingestion.orders(id)`.
    - **FK**: `product_id -> ingestion.products(id)`.
        
- `ingestion.order_events` (outbox)
    - **PK**: `id` (BIGSERIAL).
    - **FK**: `order_id -> ingestion.orders(id)`.
    - **FK**: `merchant_id -> ingestion.merchants(id)`.
    - TODO (Production): Use TSID/Snowflake for globally unique, time-sorted event IDs when scaling to multiple ingestion instances.
        

## DuckDB analytics schema

- `category_sales_agg`
    - **PK**: `id`.
    - **Unique business key**: `(merchant_id, category_id, bucket_type, bucket_start)` for safe upserts.
    - Stores aggregated sales by DAY, WEEK, MONTH buckets.
        
- `processed_events`
    - **PK**: `order_id` (idempotency for Kafka consumer).
    - Uses `orderId` from ingestion for tracking processed orders.
        
- `category_sales_forecast`
    - **PK**: `id`.
    - Stores precomputed forecasts with model results as JSON.


## "Year" timeframe modeling (required by scope)

- Production options:
    - Add `bucket_type = 'YEAR'` to `category_sales_agg` and compute yearly buckets in aggregation.
    - Or derive "year view" by summing 12 monthly buckets on read (lower write cost, higher read complexity).
        
- Recommended: store YEAR aggregates if "year view" is frequently queried and must be fast.
    

## Operations (dataflow, failures, HA/scale knobs, tradeoffs)

## End-to-end dataflow

- **Orders**: simulator posts to ingestion `/v1/orders`, ingestion writes OLTP rows + outbox row.
    
- **Events**: outbox publisher periodically reads unprocessed events and publishes to Kafka `order-events`.
    
- **Aggregates**: aggregation service consumes `order-events`, dedupes via DuckDB `processed_events` using `orderId`, and uses **dual-write** to upsert bucketed totals into both PostgreSQL `forecasting.category_sales_agg` (for low-latency API reads) and DuckDB (for forecasting batch jobs); the UI can query `/api/top-categories` from Postgres.
    
- **Forecasts**: forecasting worker periodically fetches series from DuckDB and writes results to DuckDB `category_sales_forecast`; forecasting API serves UI/API endpoints.
    

## Idempotency model

Two layers of idempotency protect against duplicates:

1. **API layer** (`externalOrderId`): Client-provided UUID prevents duplicate orders at ingestion entry point. If API call times out but order was saved, retry won't create duplicate.

2. **Aggregation layer** (`orderId`): DB-generated ID prevents reprocessing same order in Kafka consumer. Stored in DuckDB `processed_events`.

## Failure modes (and mitigations)

- **Kafka outage**: ingestion outbox accumulates `processed=false` rows; once Kafka recovers the relay can drain (eventual consistency).
    
- **Outbox publish ack ambiguity**: current relay marks events processed even though send completion is async; in production, mark processed only after broker ack (or use a proven CDC/outbox relay).
    
- **Aggregation double/under counting**:
    - At-least-once Kafka can duplicate events; idempotency table prevents double counting.
    - Current ordering risk: marking processed before writing aggregates can cause undercount on crash; production should make this atomic and correctly ordered.
        
- **Forecasting worker downtime**: precomputed forecasts stop updating; API can still compute on-demand (degraded performance) until worker recovers.
    
- **DB growth**: forecast table can grow quickly; enforce retention/partitioning.
    
## HA / scale knobs

- **Ingestion service**: scale stateless API horizontally; use DB connection pooling and ensure write capacity.
    
- **Kafka**: increase partitions for `order-events` to scale consumers; use consumer groups for parallelism; add DLQ/retry topics.
    
- **Aggregation service**: scale consumer instances with partitions; keep idempotency checks efficient via indexed PK and batch existence queries.
    
- **PostgreSQL**:
    - HA via primary/replica + automated failover.
    - Read replicas for forecasting/aggregation read endpoints.
        
- **DuckDB**:
    - Currently embedded (single-writer, multi-reader).
    - For HA, consider MotherDuck (managed DuckDB) or replicated file storage.
        
- **Forecasting worker**: shard by merchant (hash ranges) and use leader election to avoid duplicate scheduling in multi-worker deployments.
    
## Key tradeoffs

- **Event-driven + outbox** improves decoupling and resilience (Kafka outages don't lose events) but introduces eventual consistency and extra moving parts.
    
- **PostgreSQL + DuckDB separation** optimizes for both OLTP and OLAP workloads but adds operational complexity (two databases to manage).
    
- **Materialized aggregates** make "top categories" queries fast and cheap at read time, trading off more complex writes and careful idempotency.
    
- **Precompute forecasts** improves UI latency and enables model comparison, trading off storage growth and job orchestration complexity.
    
- **orderId for idempotency** is simple for single-instance demo but needs TSID/Snowflake for multi-instance production scaling.
