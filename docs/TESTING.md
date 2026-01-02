# Testing Guide

This document covers manual testing procedures for the QB-Top-Sales system. Unit and integration tests will be added in a future iteration.

## Prerequisites

```bash
# Start all services
docker-compose up -d

# Wait for healthy status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## 1. Health Checks

```bash
# Ingestion Service
curl http://localhost:8081/actuator/health

# Aggregation Service
curl http://localhost:8082/actuator/health

# Forecasting Service
curl http://localhost:8090/health
curl http://localhost:8090/health/postgres
```

**Expected Results:**
| Endpoint | Expected Response |
|----------|-------------------|
| `/actuator/health` | `{"status":"UP"}` |
| `/health` | `{"status":"UP"}` |
| `/health/postgres` | `{"status":"UP","database":"Postgres"}` |

---

## 2. API Endpoint Testing

### Ingestion API
```bash
# Create a test order
curl -X POST http://localhost:8081/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "externalOrderId": "test-001",
    "merchantId": 1,
    "orderDate": "2024-01-01T10:00:00Z",
    "items": [{"productId": 101, "quantity": 2, "unitPrice": 99.99}]
  }'
```
**Expected:** `201 Created` with order ID in response.

### Aggregation API
```bash
# Get top categories (actuals)
curl "http://localhost:8082/api/top-categories?merchantId=1&bucketType=DAY&limit=5"
```
**Expected:** JSON array with category sales data.

### Forecasting API
```bash
# Top categories forecast
curl "http://localhost:8090/forecast/top-categories?merchant_id=1&bucket_type=DAY&limit=5"

# Compare models (pre-computed)
curl "http://localhost:8090/forecast/compare-models?merchant_id=1"
```
**Expected:** JSON with `forecasts` array containing forecasts from all 5 models for top categories.

### Swagger UI
- Ingestion: http://localhost:8081/swagger-ui.html
- Aggregation: http://localhost:8082/swagger-ui.html
- Forecasting: http://localhost:8090/docs

---

## 3. Database Verification

Access psql:
```bash
docker exec -it qb-postgres psql -U qb_user -d qb_db
```

### Seed Data Counts
```bash
docker exec qb-postgres psql -U qb_user -d qb_db -c \
  "SELECT 'merchants' as entity, COUNT(*) FROM ingestion.merchants
   UNION ALL SELECT 'categories', COUNT(*) FROM ingestion.categories
   UNION ALL SELECT 'products', COUNT(*) FROM ingestion.products
   UNION ALL SELECT 'orders', COUNT(*) FROM ingestion.orders WHERE id >= 10000;"
```

**Expected Results:**
| Entity | Count |
|--------|-------|
| merchants | 3 |
| categories | 18 |
| products | 54 |
| orders | 180 |

### Aggregated Sales (by merchant)
```bash
docker exec qb-postgres psql -U qb_user -d qb_db -c \
  "SELECT merchant_id, COUNT(DISTINCT category_id) as categories, COUNT(*) as records
   FROM forecasting.category_sales_agg GROUP BY merchant_id;"
```

**Expected Results:**
| merchant_id | categories | records |
|-------------|------------|---------|
| 1 | 8 | ~480 |
| 2 | 5 | ~300 |
| 3 | 5 | ~300 |

### Latest Forecasts
```sql
SELECT 
    c.name as category_name,
    f.model_name,
    f.forecasted_values,
    f.generated_at
FROM forecasting.category_sales_forecast f
JOIN ingestion.categories c ON f.category_id = c.id
WHERE f.merchant_id = 1
ORDER BY f.generated_at DESC
LIMIT 10;
```

### Actual vs Forecast Comparison
```sql
WITH latest_forecast AS (
    SELECT category_id, 
           cast(forecasted_values->0->>'value' as decimal) as predicted
    FROM forecasting.category_sales_forecast
    WHERE generated_at > NOW() - INTERVAL '1 hour'
),
actual_sales AS (
    SELECT category_id, total_sales_amount as actual
    FROM forecasting.category_sales_agg
    WHERE bucket_type = 'DAY' AND bucket_start = CURRENT_DATE
)
SELECT l.category_id, l.predicted, a.actual, (a.actual - l.predicted) as diff
FROM latest_forecast l
JOIN actual_sales a ON l.category_id = a.category_id;
```

---

## 4. Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f forecasting-worker
docker logs -f aggregation-service
docker logs -f ingestion-service
```

**Expected in forecasting-worker logs:**
```
INFO:__main__:Generating forecasts for 3 merchants: [1, 2, 3]
INFO:__main__:Generated X forecasts for merchant 1
INFO:__main__:Forecast job completed. Generated X total forecast records.
```

---

## 5. Reset & Maintenance

### Full Reset (Clear All Data)
```bash
docker-compose down -v
docker-compose up -d
```

### Truncate Tables (Keep Schema)
```sql
TRUNCATE TABLE ingestion.orders CASCADE;
TRUNCATE TABLE ingestion.order_items CASCADE;
TRUNCATE TABLE forecasting.category_sales_agg CASCADE;
TRUNCATE TABLE forecasting.processed_events CASCADE;
TRUNCATE TABLE forecasting.category_sales_forecast CASCADE;
```

---

## 6. Future: Automated Tests

> **TODO**: Add unit and integration tests
> - [ ] Python pytest for forecasting-service
> - [ ] JUnit for ingestion-service and aggregation-service
> - [ ] Integration tests with Testcontainers
