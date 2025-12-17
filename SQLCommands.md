### verifying sync status

```sql
sudo docker exec -it qb-postgres psql -U qb_user -d qb_db
select count(*) from ingestion.order_events where processed = false;
```

This number should go to zero over time if you stop live traffic. ```sudo docker stop order-simulator```

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

✦ Here are some SQL queries you can use to inspect the data and verify the model's behavior.

  1. View Raw Time Series Data

  This query shows the raw aggregated data for a specific merchant and time bucket that is fed directly into the forecasting models.

    1 SELECT
    2     category_id,
    3     bucket_start,
    4     total_sales_amount
    5 FROM
    6     forecasting.category_sales_agg
    7 WHERE
    8     merchant_id = 1
    9     AND bucket_type = 'DAY'
   10 ORDER BY
   11     category_id,
   12     bucket_start;

  2. See the Most Recently Added Data

  This query shows the most recent data points that have been added to the aggregation table, which are causing the forecasts to change.

    1 SELECT
    2     category_id,
    3     bucket_start,
    4     total_sales_amount,
    5     last_updated_at
    6 FROM
    7     forecasting.category_sales_agg
    8 WHERE
    9     merchant_id = 1
   10     AND bucket_type = 'DAY'
   11 ORDER BY
   12     last_updated_at DESC
   13 LIMIT 10;

  3. Check Total Sales for a Category

  This query calculates the total sales for a specific category from the raw order items. You can use this to verify that the aggregated values in the category_sales_agg table are correct.

    1 SELECT
    2     p.category_id,
    3     SUM(oi.quantity * oi.price) AS total_sales
    4 FROM
    5     ingestion.order_items oi
    6 JOIN
    7     ingestion.products p ON oi.product_id = p.id
    8 JOIN
    9     ingestion.orders o ON oi.order_id = o.id
   10 WHERE
   11     o.merchant_id = 1 AND p.category_id = <your_category_id>
   12 GROUP BY
   13     p.category_id;

  Replace <your_category_id> with a category ID from the previous queries. By running these queries, you can observe how the underlying data changes over time and get a better understanding of why the forecasting results are dynamic.
