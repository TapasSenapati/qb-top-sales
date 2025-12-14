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

### checkingW any service logs:
```sudo docker logs -f forecasting-service```

### verifying aggregations day
```sql
SELECT *
FROM forecasting.category_sales_agg
WHERE merchant_id = 1
  AND category_id = 1
  AND bucket_type = 'DAY';

SELECT
    SUM(oi.quantity)      AS units,
    COUNT(*)              AS order_items,
    SUM(oi.line_amount)   AS sales
FROM ingestion.orders o
         JOIN ingestion.order_items oi
              ON oi.order_id = o.id
         JOIN ingestion.products p
              ON p.id = oi.product_id
WHERE o.merchant_id = 1
  AND p.category_id = 1
  AND o.order_date >= TIMESTAMPTZ '2025-12-14 05:30:00+05:30'
  AND o.order_date <  TIMESTAMPTZ '2025-12-15 05:30:00+05:30';
```