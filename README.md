# qb-top-sales

A multi-service forecasting pipeline for commerce sales analytics.

## 🚀 Quick Start

```bash
# Start all services
docker-compose up -d

# Reset and rebuild everything
mvn clean package && docker-compose down -v && docker-compose build --no-cache && docker-compose up -d
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [HLD.md](docs/HLD.md) | High-Level Design & Architecture |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | Monitoring, Tracing, Metrics |
| [TESTING.md](docs/TESTING.md) | Testing Guide & Expected Results |
| [PRODUCTION_IMPROVEMENTS.md](docs/PRODUCTION_IMPROVEMENTS.md) | Production Patterns |

## 🖥️ Dashboards & UI

| UI | URL |
|----|-----|
| **Forecasting UI** | [http://localhost:8090](http://localhost:8090/) |
| **Observability Dashboard** | [ui/observability-dashboard.html](ui/observability-dashboard.html) |

## 🔌 API Documentation (Swagger)

| Service | Swagger UI | OpenAPI JSON |
|---------|------------|--------------|
| **Ingestion** (8081) | [swagger-ui](http://localhost:8081/swagger-ui/index.html) | [api-docs](http://localhost:8081/v3/api-docs) |
| **Aggregation** (8082) | [swagger-ui](http://localhost:8082/swagger-ui/index.html) | [api-docs](http://localhost:8082/v3/api-docs) |
| **Forecasting** (8090) | [docs](http://localhost:8090/docs) | [openapi.json](http://localhost:8090/openapi.json) |

## 🔧 Useful Commands

```bash
# View service logs
docker logs -f forecasting-service
docker logs -f ingestion-service
docker logs -f aggregation-service

# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## 📁 Project Structure

```
qb-top-sales/
├── docs/                  # Documentation
├── ui/                    # Frontend dashboards
├── db/                    # Database schema & seed
├── ingestion-service/     # Order ingestion (Spring Boot)
├── aggregation-service/   # Sales aggregation (Spring Boot)
├── forecasting-service/   # ML forecasting (FastAPI)
├── order-simulator/       # Load generator (Python)
└── docker-compose.yml
```

## 📊 Data Sources

The system uses two complementary data sources to populate sales data:

### 1. Seed Data (Historical) — `db/02_seed.sql`

**Purpose**: Pre-populate the database with 120 days of historical order data for immediate demo capability.

| What it provides | Details |
|-----------------|---------|
| **Merchants** | 3 merchants (TechMart USA, EuroStyle, BharatBazaar) |
| **Categories** | 18 categories with distinct sales patterns |
| **Products** | 54 products across all categories |
| **Orders** | 120 days of historical orders (360 total) |
| **Aggregations** | Pre-computed DAY/WEEK/MONTH buckets in `forecasting.category_sales_agg` |

**Sales patterns included**:
- Trending categories (Electronics with 1.5% daily growth)
- Seasonal patterns (Clothing with weekend spikes)
- Stable categories (Toys with consistent sales)
- Festival effects (Traditional Wear with Diwali spike)

**Note**: Seed data bypasses Kafka and directly populates both the orders table AND the aggregation table, so forecasting works immediately.

---

### 2. Order Simulator (Live) — `order-simulator/`

**Purpose**: Generate live order traffic to simulate real-time commerce activity.

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BACKFILL_DAYS` | `0` | Days of historical orders to generate on startup |
| `MAX_ORDERS_PER_DAY` | `50` | Max orders per day during backfill |
| `ORDER_COUNT` | `20` | Number of orders to send (non-continuous mode) |
| `ORDER_DELAY_SECONDS` | `1.0` | Delay between orders |
| `ORDER_CONTINUOUS` | `true` | Run indefinitely if true |

**How it works**:
1. Posts orders to the ingestion-service API
2. Orders flow through Kafka to the aggregation-service
3. Aggregation-service updates `forecasting.category_sales_agg`
4. Forecasting models use the updated aggregations

**When to use each**:
- **Seed data**: For demos, testing forecasting models, immediate data availability
- **Order simulator**: For testing real-time data flow, Kafka integration, live aggregation

