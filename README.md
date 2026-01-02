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
