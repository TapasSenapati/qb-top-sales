# System Observability Guide 🔭

This document outlines how to monitor the health, performance, and behavior of the **qb-top-sales** system.

> **📊 Quick Access**: Open [observability-dashboard.html](../ui/observability-dashboard.html) in your browser for a consolidated view of all observability links.

## 1. System Health 💓

| Component | Health Endpoint | Type | Details |
| :--- | :--- | :--- | :--- |
| **Ingestion Service** | `http://localhost:8081/actuator/health` | HTTP JSON | Checks DB Connection, Disk Space |
| **Aggregation Service** | `http://localhost:8082/actuator/health` | HTTP JSON | Checks DB, Kafka Consumer, Disk |
| **Forecasting Service** | `http://localhost:8090/health` | HTTP JSON | Simple Service UP/DOWN + Postgres Connectivity |
| **PostgreSQL** | `docker exec qb-postgres pg_isready` | CLI | Native Postgres check |

## 2. Distributed Tracing (Zipkin) 🕵️‍♂️

Trace the full lifecycle of an order: `Simulator` -> `Ingestion` -> `Kafka` -> `Aggregation` -> `Postgres`.

*   **UI URL**: [http://localhost:9411](http://localhost:9411)
*   **How to test**:
    1.  Ensure `order-simulator` is running.
    2.  Open Zipkin UI.
    3.  Click "Run Query".
    4.  Click on a trace (e.g., `ingestion-service`) to see the waterfall chart.

## 3. Metrics 📊

We expose metrics in JSON and Prometheus formats.

### Ingestion Service (Port 8081)
*   **Summary**: [http://localhost:8081/actuator/metrics](http://localhost:8081/actuator/metrics)
*   **Prometheus Format**: [http://localhost:8081/actuator/prometheus](http://localhost:8081/actuator/prometheus)
*   **Key Metrics**:
    *   `http.server.requests`: Request count, latency.
    *   `kafka.producer.*`: Message send rates.

### Aggregation Service (Port 8082)
*   **Summary**: [http://localhost:8082/actuator/metrics](http://localhost:8082/actuator/metrics)
*   **Prometheus Format**: [http://localhost:8082/actuator/prometheus](http://localhost:8082/actuator/prometheus)
*   **Key Metrics**:
    *   `kafka.consumer.*`: Lag, messages consumed.
    *   `category.aggregated`: Custom metric (count of rows upserted to Postgres).

### Forecasting Service (Port 8090)
*   **Prometheus Format**: [http://localhost:8090/metrics](http://localhost:8090/metrics)
*   **Key Metrics**:
    *   `http_requests_total`: Rate of API calls.
    *   `http_request_duration_seconds`: Latency.

## 4. Container & Service Discovery 🐳

*   **Consul UI**: [http://localhost:8500](http://localhost:8500)
    *   View all registered services and their health status in real-time.
*   **Docker Stats**:
    *   Run `docker stats` to see CPU/Memory usage of containers.

## 5. Quick Verification Commands

```bash
# Check if Tracing is reachable
curl -I http://localhost:9411/health

# Check Ingestion Metrics (JSON)
curl -s http://localhost:8081/actuator/metrics/http.server.requests | jq .

# Check Forecasting Metrics (Text)
curl -s http://localhost:8090/metrics | head -n 5
```
