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
---DAY
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

---WEEK
SELECT
    merchant_id,
    category_id,
    bucket_type,
    bucket_start,
    total_sales_amount,
    total_units_sold,
    order_count
FROM forecasting.category_sales_agg
WHERE bucket_type = 'WEEK'
ORDER BY bucket_start DESC;

SELECT total_sales_amount
FROM forecasting.category_sales_agg
WHERE merchant_id = 1
  AND category_id = 1
  AND bucket_type = 'WEEK'; //50832.59
                          
-- DAY sum for same window
SELECT SUM(total_sales_amount)
FROM forecasting.category_sales_agg
WHERE merchant_id = 1
  AND category_id = 1
  AND bucket_type = 'DAY'
  AND bucket_start >= TIMESTAMPTZ '2025-12-08 05:30:00+0530'
  AND bucket_start <  TIMESTAMPTZ '2025-12-15 05:30:00+0530'; //50832.59

SELECT total_sales_amount
FROM forecasting.category_sales_agg
WHERE merchant_id = 1
  AND category_id = 1
  AND bucket_type = 'MONTH'
  AND bucket_start = TIMESTAMPTZ '2025-12-01 05:30:00+05:30';

SELECT SUM(total_sales_amount)
FROM forecasting.category_sales_agg
WHERE merchant_id = 1
  AND category_id = 1
  AND bucket_type = 'DAY'
  AND bucket_start >= TIMESTAMPTZ '2025-12-01 05:30:00+05:30'
  AND bucket_start <  TIMESTAMPTZ '2026-01-01 05:30:00+05:30';             

---idempotency checks
UPDATE ingestion.order_events SET processed = false;

SELECT SUM(total_sales_amount)
FROM forecasting.category_sales_agg;

UPDATE ingestion.order_events SET processed = false;

SELECT SUM(total_sales_amount)
FROM forecasting.category_sales_agg;
```