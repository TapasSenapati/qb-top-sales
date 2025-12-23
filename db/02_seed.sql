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
-- Each merchant has a single base currency (no conversion needed for demo):
--   Merchant 1 = USD, Merchant 2 = EUR, Merchant 3 = INR
INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
VALUES
    -- Last 7 days of orders for Merchant 1
    (1001, 1, CURRENT_DATE - INTERVAL '7 days', 'USD', 150.00),
    (1002, 1, CURRENT_DATE - INTERVAL '6 days', 'USD', 200.00),
    (1003, 1, CURRENT_DATE - INTERVAL '5 days', 'USD', 250.00),
    (1004, 1, CURRENT_DATE - INTERVAL '4 days', 'USD', 180.00),
    (1005, 1, CURRENT_DATE - INTERVAL '3 days', 'USD', 300.00),
    (1006, 1, CURRENT_DATE - INTERVAL '2 days', 'USD', 220.00),
    (1007, 1, CURRENT_DATE - INTERVAL '1 day', 'USD', 190.00),

    -- Last 7 days of orders for Merchant 2
    (2001, 2, CURRENT_DATE - INTERVAL '7 days', 'EUR',  80.00),
    (2002, 2, CURRENT_DATE - INTERVAL '6 days', 'EUR', 120.00),
    (2003, 2, CURRENT_DATE - INTERVAL '5 days', 'EUR',  90.00),
    (2004, 2, CURRENT_DATE - INTERVAL '4 days', 'EUR', 110.00),
    (2005, 2, CURRENT_DATE - INTERVAL '3 days', 'EUR', 150.00),
    (2006, 2, CURRENT_DATE - INTERVAL '2 days', 'EUR', 130.00),
    (2007, 2, CURRENT_DATE - INTERVAL '1 day', 'EUR', 100.00),

    -- Last 7 days of orders for Merchant 3
    (3001, 3, CURRENT_DATE - INTERVAL '7 days', 'INR',  90.00),
    (3002, 3, CURRENT_DATE - INTERVAL '6 days', 'INR', 110.00),
    (3003, 3, CURRENT_DATE - INTERVAL '5 days', 'INR', 130.00),
    (3004, 3, CURRENT_DATE - INTERVAL '4 days', 'INR', 100.00),
    (3005, 3, CURRENT_DATE - INTERVAL '3 days', 'INR', 140.00),
    (3006, 3, CURRENT_DATE - INTERVAL '2 days', 'INR', 120.00),
    (3007, 3, CURRENT_DATE - INTERVAL '1 day', 'INR', 150.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
VALUES
    -- Items for Merchant 1's orders
    (5001, 1001, 101, 1, 150.00, 150.00),
    (5002, 1002, 101, 2, 100.00, 200.00),
    (5003, 1003, 102, 1, 250.00, 250.00),
    (5004, 1004, 103, 2,  90.00, 180.00),
    (5005, 1005, 101, 3, 100.00, 300.00),
    (5006, 1006, 102, 1, 220.00, 220.00),
    (5007, 1007, 103, 1, 190.00, 190.00),

    -- Items for Merchant 2's orders
    (6001, 2001, 104, 2,  40.00,  80.00),
    (6002, 2002, 104, 3,  40.00, 120.00),
    (6003, 2003, 104, 2,  45.00,  90.00),
    (6004, 2004, 104, 2,  55.00, 110.00),
    (6005, 2005, 104, 3,  50.00, 150.00),
    (6006, 2006, 104, 2,  65.00, 130.00),
    (6007, 2007, 104, 2,  50.00, 100.00),

    -- Items for Merchant 3's orders
    (7001, 3001, 105, 1,  90.00,  90.00),
    (7002, 3002, 105, 1, 110.00, 110.00),
    (7003, 3003, 105, 2,  65.00, 130.00),
    (7004, 3004, 105, 1, 100.00, 100.00),
    (7005, 3005, 105, 2,  70.00, 140.00),
    (7006, 3006, 105, 1, 120.00, 120.00),
    (7007, 3007, 105, 3,  50.00, 150.00)
ON CONFLICT (id) DO NOTHING;
