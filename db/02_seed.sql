-- Seed merchants
INSERT INTO ingestion.merchants (id, name)
VALUES (1, 'Merchant A'),
       (2, 'Merchant B'),
       (3, 'Merchant C') ON CONFLICT (id) DO NOTHING;

-- Seed categories
INSERT INTO ingestion.categories (id, merchant_id, name, parent_category_id)
VALUES (1, 1, 'Electronics', NULL),
       (2, 1, 'Books', NULL),
       (3, 2, 'Fashion', NULL),
       (4, 3, 'Home & Kitchen', NULL) ON CONFLICT (id) DO NOTHING;

-- Seed products
INSERT INTO ingestion.products (id, merchant_id, category_id, name)
VALUES (101, 1, 1, 'Smartphone X'),
       (102, 1, 1, 'Wireless Headphones'),
       (103, 1, 2, 'Tech Book'),
       (104, 2, 3, 'T-Shirt'),
       (105, 3, 4, 'Blender') ON CONFLICT (id) DO NOTHING;

-- Optional: seed a few historical orders for each merchant to ensure
-- multiple time-series points are available even before the simulator runs.
-- These are simple examples; the aggregation-service will transform them
-- into category_sales_agg entries once events are processed.

-- Note: IDs are fixed for idempotency; ON CONFLICT ensures re-runs are safe.
INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
VALUES
    (1001, 1, '2024-01-01T10:00:00Z', 'USD', 150.00),
    (1002, 1, '2024-01-02T11:00:00Z', 'USD', 200.00),
    (1003, 1, '2024-01-03T12:00:00Z', 'USD', 250.00),
    (2001, 2, '2024-01-01T09:30:00Z', 'EUR',  80.00),
    (2002, 2, '2024-01-02T14:15:00Z', 'EUR', 120.00),
    (3001, 3, '2024-01-01T08:45:00Z', 'INR',  90.00),
    (3002, 3, '2024-01-02T16:20:00Z', 'INR', 110.00),
    (3003, 3, '2024-01-03T18:05:00Z', 'INR', 130.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
VALUES
    (5001, 1001, 101, 1, 150.00, 150.00),
    (5002, 1002, 101, 2, 100.00, 200.00),
    (5003, 1003, 102, 1, 250.00, 250.00),
    (6001, 2001, 104, 2,  40.00,  80.00),
    (6002, 2002, 104, 3,  40.00, 120.00),
    (7001, 3001, 105, 1,  90.00,  90.00),
    (7002, 3002, 105, 1, 110.00, 110.00),
    (7003, 3003, 105, 2,  65.00, 130.00)
ON CONFLICT (id) DO NOTHING;
