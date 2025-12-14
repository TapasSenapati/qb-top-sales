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
 
### Traffic simulator
```docker
docker build -t order-simulator .
```

### verifying sync status
```
sudo docker exec -it qb-postgres psql -U qb_user -d qb_db
select count(*) from ingestion.order_events where processed = false;
```
This number should go to zero over time if you stop live traffic. ```sudo docker stop order-simulator```

### checkign any service logs:
```sudo docker logs -f forecasting-service```