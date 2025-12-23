# Production Improvements Guide

This document compares the current demo implementation with production-grade patterns, organized by distributed systems concepts.

---

## 1. Outbox Publisher Pattern

### Current Implementation
```java
kafkaTemplate.send(...).get(10, TimeUnit.SECONDS);  // Synchronous with timeout
event.setProcessed(true);  // Mark after ack
```

### Production Improvements

| Aspect | Demo | Production |
|--------|------|------------|
| **Send strategy** | Sequential, blocking | Parallel batch with `CompletableFuture.allOf()` |
| **Timeout** | 10s hardcoded | Configurable via properties |
| **Alternative** | Custom publisher | Debezium CDC (captures outbox → Kafka automatically) |

#### Thundering Herd Prevention
- **Problem**: All ingestion instances poll outbox simultaneously after restart
- **Fix**: Add jitter to `@Scheduled` delay: `fixedDelay = 5000 + random(0, 2000)`
- **Fix**: Use distributed lock (Redis/Zookeeper) for leader election

---

## 2. Idempotency

### Current Implementation
- **API layer**: `externalOrderId` (client-provided UUID) prevents duplicate orders
- **Aggregation layer**: `orderId` in DuckDB `processed_events` prevents reprocessing

### Production Improvements

| Layer | Demo | Production |
|-------|------|------------|
| **ID generation** | DB BIGSERIAL per instance | TSID/Snowflake (globally unique, time-sorted) |
| **Idempotency window** | Forever (store all IDs) | TTL-based cleanup (e.g., 7 days) |
| **Cross-service** | orderId lookup | Distributed cache (Redis) for fast lookups |

#### At-Least-Once vs Exactly-Once
- Demo uses at-least-once + idempotency table
- Production options:
  - Kafka Transactions (exactly-once semantics)
  - Transactional outbox with CDC

---

## 3. CAP Theorem Tradeoffs

### Current Design: AP (Available + Partition-tolerant)
- Eventual consistency between ingestion and aggregation
- Outbox pattern tolerates Kafka partitions (events accumulate in DB)

### Production Considerations

| Scenario | Current Behavior | Production Option |
|----------|------------------|-------------------|
| Kafka down | Outbox accumulates, retries later | Add circuit breaker, alerting |
| DB partitioned | Write fails, client retries | Multi-region DB with failover |
| Aggregation lag | Stale "top categories" | Cache with TTL, show "as of" timestamp |

---

## 4. Concurrency Control

### Current Issues

#### DuckDB Single-Writer
```java
// Multiple services write to same DuckDB file
aggregation-service -> /data/forecasting.duckdb
forecasting-worker  -> /data/forecasting.duckdb  // Contention!
```

#### Production Fixes
- Use file locking or writer queue
- Partition by service: forecasting-worker writes forecasts, aggregation writes aggregates
- Use MotherDuck (managed DuckDB with proper concurrency)

#### Aggregation Order Bug
```java
// Current: Mark processed BEFORE writing aggregates
duckDBRepo.saveProcessedOrders(processedEvents);  // ❌ First
duckDBRepo.bulkUpsert(...);  // Second - crash here = undercount!

// Fix: Write aggregates FIRST, then mark processed
duckDBRepo.bulkUpsert(...);  // First
duckDBRepo.saveProcessedOrders(processedEvents);  // ❌ Second
```

---

## 5. Rate Limiting

### Current Implementation
- No rate limiting on `/v1/orders` API
- Outbox fetches 100 events per tick (implicit limit)

### Production Improvements

| Component | Demo | Production |
|-----------|------|------------|
| **API ingestion** | Unlimited | Token bucket (e.g., 1000 req/min per merchant) |
| **Kafka producer** | No throttling | Backpressure via `linger.ms` + `batch.size` |
| **Aggregation** | Batch of 100 | Configurable batch size + pause on backlog |

#### Implementation
```java
// Spring Rate Limiting with Bucket4j
@RateLimiter(name = "orders", fallbackMethod = "rateLimitFallback")
public OrderCreateResponse createOrder(...) { }
```

---

## 6. Poison Pills & Dead Letter Queue (DLQ)

### Current Implementation
```java
} catch (Exception e) {
    log.error(...);
    throw e;  // Kafka retries forever!
}
```

### Production Improvements

#### Kafka Consumer with DLQ
```java
@KafkaListener(topics = "order-events")
@RetryableTopic(
    attempts = 3,
    backoff = @Backoff(delay = 1000, multiplier = 2),
    dltTopicSuffix = "-dlq"
)
public void consume(String payload) { ... }
```

#### Poison Pill Handling
| Stage | Demo | Production |
|-------|------|------------|
| Parse failure | Throw (blocks partition) | Log + send to DLQ |
| Processing failure | Throw (infinite retry) | Retry 3x, then DLQ |
| DLQ monitoring | None | Alert on DLQ size, manual replay tooling |

---

## 7. Observability

### Current Implementation
- Basic logging (`log.info`, `log.error`)
- Health endpoints (`/actuator/health`, `/health/duckdb`)

### Production Improvements

| Aspect | Demo | Production |
|--------|------|------------|
| **Metrics** | None | Prometheus (consumer lag, latency histograms) |
| **Tracing** | None | OpenTelemetry spans across services |
| **Alerting** | None | PagerDuty on lag > threshold, DLQ > 0 |
| **Dashboards** | None | Grafana for real-time visibility |

#### Key Metrics to Add
```java
// Histogram for publish latency
Timer.builder("outbox.publish.duration")
    .register(meterRegistry)
    .record(() -> kafkaTemplate.send(...).get());

// Counter for events by status
Counter.builder("aggregation.events")
    .tag("status", "processed|skipped|failed")
    .register(meterRegistry)
    .increment();
```

---

## 8. Schema Evolution

### Current Implementation
- JSON payload without versioning
- Consumer and producer must match exactly

### Production Improvements

| Aspect | Demo | Production |
|--------|------|------------|
| **Format** | JSON | Avro/Protobuf with Schema Registry |
| **Compatibility** | None | BACKWARD/FORWARD compatibility rules |
| **Versioning** | None | Schema ID in message header |

---

## Summary: Priority Fixes

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 P0 | Aggregation order (undercount risk) | Low | High |
| 🟠 P1 | Add DLQ for poison pills | Medium | High |
| 🟠 P1 | Thundering herd (jitter) | Low | Medium |
| 🟡 P2 | Rate limiting on API | Medium | Medium |
| 🟡 P2 | Metrics/observability | Medium | High |
| 🟢 P3 | Schema Registry | High | Medium |
| 🟢 P3 | TSID for distributed scaling | Low | Low (until scale) |
