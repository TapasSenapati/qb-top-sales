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

Ensure Postgres Docker container and other containers is running. ```sudo docker ps```
sudo psql -h localhost -p 5432 -U qb_user -d qb_db
Actuator health will be at:
http://localhost:8081/actuator/health (locally)

http://ingestion-service:8081/actuator/health

*** Traffic sumulator
```docker
docker build -t order-simulator .
```
```docker
docker run --rm \
--network your_docker_network \
-e INGESTION_BASE_URL=http://ingestion-service:8081 \
-e ORDER_COUNT=100 \
-e ORDER_DELAY_SECONDS=1 \
order-simulator
```