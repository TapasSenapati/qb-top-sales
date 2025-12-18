## Requirements & assumptions

## Problem scope (functional)

- Ingest commerce orders for a merchant and persist them via an Orders API.​

- Compute and serve “top sales by category” for selectable timeframes (week, month, year) through a user-friendly UI.
    
- Forecast next-period “top sales by category” and allow users to view results via UI/API endpoints (including model selection/compare).​
    
## Non-functional requirements

- High availability: the read path (top categories + forecasts) should remain available under partial failures, with graceful degradation when compute pipelines lag.
    
- Accuracy & consistency: aggregates must converge without double-counting; forecasts must be reproducible for a given model/version and input series.
    
- Scalability: support many merchants and increasing order volume with horizontal scaling and partitioning.
    
- Observability: health checks, lag metrics, and failure alerting for ingestion→Kafka→aggregation and forecast generation.
    

## Assumptions

- Merchant catalog (merchants/categories/products) exists and is considered “platform-owned”; this design only consumes those concepts.​
    
- Ranking definition: “top sales” means sorting categories by total sales amount for the merchant in a selected timeframe window.​
    
- Time semantics: production supports calendar-aligned week/month/year with a configurable merchant timezone + “week starts on X” policy (default can be UTC/Monday).
    
- Consistency model: eventual consistency is acceptable between order creation and aggregate/forecast availability, but the system must converge.
    

## Architecture

## Components (implemented)

- **Order Simulator**: generates/backfills orders and POSTs to ingestion-service; waits on ingestion health endpoint before sending traffic.​
    
- **Ingestion Service**: exposes `POST /v1/orders` and persists orders + outbox rows in Postgres.​
    
- **Outbox Relay (in ingestion service)**: scheduled publisher reads `ingestion.order_events` and publishes to Kafka topic `order-events`.​
    
- **Aggregation Service**: consumes `order-events`, dedupes using `forecasting.processed_events`, and upserts bucketed totals into `forecasting.category_sales_agg`; also exposes `/api/top-categories`.​
    
- **Forecasting Service (FastAPI)**: serves UI + endpoints like `/forecast/top-categories` and `/forecast/compare-models`.​
    
- **Forecasting Worker**: periodic scheduler to precompute forecasts for merchants and store them in `forecasting.category_sales_forecast`.​
    
- Compose wiring shows ingestion (8081), aggregation (8082), forecasting (8090), plus Kafka/Postgres/Consul.​
    

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
                            |                             ^
                            | SQL read/write              | Kafka consume
                            v                             |
+-------------------+   +---+-----------------------------+-------------------+
|  Order Simulator  |   |                        PostgreSQL                    |
| (load + backfill) +-->| ingestion.* (OLTP + outbox) | forecasting.* (facts) |
+-------------------+   +---+-----------------------------+-------------------+
                            ^                             |
                            | SQL write                    | SQL write
                            |                             v
                 +----------+-----------+      +----------+-----------+
                 |    Ingestion Service |      |   Forecasting Worker |
                 |   POST /v1/orders    |      | (scheduled precompute|
                 | + outbox table write |      |  writes forecasts)    |
                 +----------+-----------+      +----------------------+
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
    
- **DLQ + retry topics**: poison-message handling for `order-events`, with dead-letter routing and replay tooling.
    
- **Centralized observability**: metrics (consumer lag, job duration), tracing, structured logs, alerting.
    
- **Caching layer**: Redis for hot “top categories” and forecast results.
    
- **Job orchestration**: replace in-process scheduler with a distributed scheduler (K8s CronJob/Airflow/Temporal) supporting retries, sharding, and leader election.
    
- **HA data stores**: Postgres replication/failover, read replicas for query-heavy endpoints, partitioning/retention for forecasts.
- Separate analytics DB
- FLink/spark stream aggregates
    

## Interfaces (API + events)

## Ingestion service API

- **POST** `/v1/orders` → creates an order (201 response).​
    
    - Used by order-simulator to drive load/backfill.​

## Aggregation service API (actuals)

- **GET** `/api/top-categories` with `merchantId`, `bucketType`, `bucketStart`, `limit` returns top categories by aggregated sales amount.​
## Forecasting service API (predictions)

- **GET** `/forecast/top-categories` supports `merchant_id`, `bucket_type`, `model`, `lookback`, `limit` and returns top forecasted categories.​
    
- **GET** `/forecast/compare-models` fetches the latest precomputed forecasts for a merchant.​
    
- **GET** `/health` for service health checks (used by infra/Consul).​

## Event contract (internal)

- Kafka topic: `order-events` produced by ingestion outbox relay and consumed by aggregation service.​
    
- Production recommendation: versioned schema + explicit event idempotency key, to support evolution and replay safety.
    
## Data model (DB schemas with PK/FK)

## Schema separation

- `ingestion.*` stores OLTP entities and the outbox.​
    
- `forecasting.*` stores derived facts (aggregates), idempotency state, and forecast outputs.​

## ingestion schema (PK/FK)

- `ingestion.merchants`
    
    - **PK**: `id`.​
        
- `ingestion.categories`
    
    - **PK**: `id`.​
        
    - **FK**: `merchant_id → ingestion.merchants(id)`.​
        
    - **FK (self)**: `parent_category_id → ingestion.categories(id)` (nullable).​
        
- `ingestion.products`
    
    - **PK**: `id`.​
        
    - **FK**: `merchant_id → ingestion.merchants(id)`.​
        
    - **FK**: `category_id → ingestion.categories(id)`.​
        
- `ingestion.orders`
    
    - **PK**: `id`.​
        
    - **FK**: `merchant_id → ingestion.merchants(id)`.​
        
- `ingestion.order_items`
    
    - **PK**: `id`.​
        
    - **FK**: `order_id → ingestion.orders(id)`.​
        
    - **FK**: `product_id → ingestion.products(id)`.​
        
- `ingestion.order_events` (outbox)
    
    - **PK**: `id`.​
        
    - **FK**: `order_id → ingestion.orders(id)`.​
        
    - **FK**: `merchant_id → ingestion.merchants(id)`.​
        

## forecasting schema (PK/FK + constraints)

- `forecasting.category_sales_agg`
    
    - **PK**: `id`.​
        
    - **Unique business key**: `(merchant_id, category_id, bucket_type, bucket_start)` for safe upserts.​
        
    - **Indexes**: `(merchant_id, bucket_type, bucket_start)` and a top-N support index ending with `total_sales_amount DESC`.​
        
    - **Recommended FKs (prod)**: `merchant_id → ingestion.merchants(id)`, `category_id → ingestion.categories(id)` (not present in current DDL).​
        
- `forecasting.processed_events`
    
    - **PK**: `event_id` (idempotency for consumer).​
        
- `forecasting.category_sales_forecast`
    
    - **PK**: `id`.​
        
    - **Unique**: `(merchant_id, category_id, model_name, generated_at)` to avoid duplicates for the same run.​
        
    - **Recommended FKs (prod)**: `merchant_id → ingestion.merchants(id)`, `category_id → ingestion.categories(id)` (not present in current DDL).​
        

## “Year” timeframe modeling (required by scope)

- Production options:
    
    - Add `bucket_type = 'YEAR'` to `forecasting.category_sales_agg` and compute yearly buckets in aggregation.
        
    - Or derive “year view” by summing 12 monthly buckets on read (lower write cost, higher read complexity).
        
- Recommended: store YEAR aggregates if “year view” is frequently queried and must be fast.
    

## Operations (dataflow, failures, HA/scale knobs, tradeoffs)

## End-to-end dataflow

- **Orders**: simulator posts to ingestion `/v1/orders`, ingestion writes OLTP rows + outbox row.​
    
- **Events**: outbox publisher periodically reads unprocessed events and publishes to Kafka `order-events`.​
    
- **Aggregates**: aggregation service consumes `order-events`, dedupes via `forecasting.processed_events`, and upserts bucketed totals into `forecasting.category_sales_agg`; the UI can query `/api/top-categories`.​
    
- **Forecasts**: forecasting worker periodically fetches series and writes results to `forecasting.category_sales_forecast`; forecasting API serves UI/API endpoints.​
    

## Failure modes (and mitigations)

- **Kafka outage**: ingestion outbox accumulates `processed=false` rows; once Kafka recovers the relay can drain (eventual consistency).​
    
- **Outbox publish ack ambiguity**: current relay marks events processed even though send completion is async; in production, mark processed only after broker ack (or use a proven CDC/outbox relay).​
    
- **Aggregation double/under counting**:
    
    - At-least-once Kafka can duplicate events; idempotency table prevents double counting.​
        
    - Current ordering risk: marking processed before writing aggregates can cause undercount on crash; production should make this atomic and correctly ordered (apply aggregates then mark processed).​
        
- **Forecasting worker downtime**: precomputed forecasts stop updating; API can still compute on-demand (degraded performance) until worker recovers.​
    
- **DB growth**: forecast table can grow quickly; enforce retention/partitioning and/or upsert by period key.
    
## HA / scale knobs

- **Ingestion service**: scale stateless API horizontally; use DB connection pooling and ensure write capacity.
    
- **Kafka**: increase partitions for `order-events` to scale consumers; use consumer groups for parallelism; add DLQ/retry topics.​
    
- **Aggregation service**: scale consumer instances with partitions; keep idempotency checks efficient via indexed PK and batch existence queries.​
    
- **Postgres**:
    
    - HA via primary/replica + automated failover.
        
    - Read replicas for forecasting/aggregation read endpoints.
        
    - Partition `category_sales_forecast` by time and apply retention policies.​
        
- **Forecasting worker**: shard by merchant (hash ranges) and use leader election to avoid duplicate scheduling in multi-worker deployments.
    
## Key tradeoffs

- **Event-driven + outbox** improves decoupling and resilience (Kafka outages don’t lose events) but introduces eventual consistency and extra moving parts.​
    
- **Materialized aggregates** make “top categories” queries fast and cheap at read time, trading off more complex writes and careful idempotency.​
    
- **Precompute forecasts** improves UI latency and enables model comparison, trading off storage growth and job orchestration complexity.​
    

