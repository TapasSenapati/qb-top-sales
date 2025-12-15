# qb-top-sales
Qb craft project
```
sudo docker compose down -v
sudo docker builder prune -af
sudo docker system prune -af
sudo systemctl restart docker
sudo docker ps -> verify empty

mvn clean package -DskipTests
sudo docker compose build
sudo docker compose up -d
```
## Swagger api docs url
Docs URLs:
Ingestion service (Spring Boot, port 8081)
http://localhost:8081/swagger-ui/index.html
http://localhost:8081/v3/api-docs

Aggregation service (Spring Boot, port 8082)
Swagger UI: http://localhost:8082/swagger-ui/index.html
OpenAPI JSON: http://localhost:8082/v3/api-docs

Forecasting service (FastAPI, port 8090)
Swagger UI: http://localhost:8090/docs
ReDoc: http://localhost:8090/redoc
OpenAPI JSON: http://localhost:8090/openapi.json

### checking any service logs:
```docker logs -f forecasting-service```
