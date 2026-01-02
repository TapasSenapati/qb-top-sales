-- ============================================================================
-- SEED DATA FOR QB-TOP-SALES DEMO
-- ============================================================================
-- This seed data provides:
-- - 3 merchants (multi-tenant demo)
-- - 8 categories for Merchant 1 (primary demo merchant)
-- - 60 days of order history (good for Prophet/ARIMA trend detection)
-- - Varied sales patterns (trending, seasonal, stable)
-- ============================================================================

-- ===================
-- MERCHANTS
-- ===================
INSERT INTO ingestion.merchants (id, name, currency)
VALUES 
    (1, 'TechMart USA', 'USD'),
    (2, 'EuroStyle', 'EUR'),
    (3, 'BharatBazaar', 'INR')
ON CONFLICT (id) DO NOTHING;

-- ===================
-- CATEGORIES
-- ===================
-- Merchant 1 (TechMart USA) - Primary demo merchant with 8 categories
INSERT INTO ingestion.categories (id, merchant_id, name)
VALUES 
    (1, 1, 'Electronics'),
    (2, 1, 'Books'),
    (3, 1, 'Clothing'),
    (4, 1, 'Home & Garden'),
    (5, 1, 'Sports & Outdoors'),
    (6, 1, 'Toys & Games'),
    (7, 1, 'Health & Beauty'),
    (8, 1, 'Automotive'),
    -- Merchant 2 (EuroStyle) - 3 categories
    (9, 2, 'Fashion'),
    (10, 2, 'Accessories'),
    (11, 2, 'Footwear'),
    -- Merchant 3 (BharatBazaar) - 3 categories
    (12, 3, 'Kitchen Appliances'),
    (13, 3, 'Home Decor'),
    (14, 3, 'Traditional Wear')
ON CONFLICT (id) DO NOTHING;

-- ===================
-- PRODUCTS
-- ===================
INSERT INTO ingestion.products (id, merchant_id, category_id, name)
VALUES 
    -- Merchant 1: Electronics (cat 1)
    (101, 1, 1, 'Smartphone Pro'),
    (102, 1, 1, 'Wireless Earbuds'),
    (103, 1, 1, 'Smart Watch'),
    (104, 1, 1, '4K Monitor'),
    -- Merchant 1: Books (cat 2)
    (111, 1, 2, 'Tech Guide 2024'),
    (112, 1, 2, 'Business Strategy'),
    (113, 1, 2, 'Fiction Bestseller'),
    -- Merchant 1: Clothing (cat 3)
    (121, 1, 3, 'Cotton T-Shirt'),
    (122, 1, 3, 'Denim Jeans'),
    (123, 1, 3, 'Winter Jacket'),
    -- Merchant 1: Home & Garden (cat 4)
    (131, 1, 4, 'Garden Tool Set'),
    (132, 1, 4, 'Indoor Plant Pot'),
    (133, 1, 4, 'LED Grow Light'),
    -- Merchant 1: Sports & Outdoors (cat 5)
    (141, 1, 5, 'Yoga Mat Premium'),
    (142, 1, 5, 'Running Shoes'),
    (143, 1, 5, 'Camping Tent'),
    -- Merchant 1: Toys & Games (cat 6)
    (151, 1, 6, 'Building Blocks Set'),
    (152, 1, 6, 'Board Game Classic'),
    (153, 1, 6, 'RC Car Deluxe'),
    -- Merchant 1: Health & Beauty (cat 7)
    (161, 1, 7, 'Vitamin Pack'),
    (162, 1, 7, 'Skincare Set'),
    (163, 1, 7, 'Hair Dryer Pro'),
    -- Merchant 1: Automotive (cat 8)
    (171, 1, 8, 'Car Phone Mount'),
    (172, 1, 8, 'Dash Cam HD'),
    (173, 1, 8, 'Leather Seat Covers'),
    -- Merchant 2: Fashion (cat 9)
    (201, 2, 9, 'Designer Dress'),
    (202, 2, 9, 'Silk Blouse'),
    -- Merchant 2: Accessories (cat 10)
    (211, 2, 10, 'Leather Handbag'),
    (212, 2, 10, 'Sunglasses Premium'),
    -- Merchant 2: Footwear (cat 11)
    (221, 2, 11, 'Stiletto Heels'),
    (222, 2, 11, 'Sneakers Limited'),
    -- Merchant 3: Kitchen Appliances (cat 12)
    (301, 3, 12, 'Mixer Grinder'),
    (302, 3, 12, 'Induction Cooktop'),
    -- Merchant 3: Home Decor (cat 13)
    (311, 3, 13, 'Brass Lamp'),
    (312, 3, 13, 'Wall Hanging'),
    -- Merchant 3: Traditional Wear (cat 14)
    (321, 3, 14, 'Silk Saree'),
    (322, 3, 14, 'Kurta Set')
ON CONFLICT (id) DO NOTHING;

-- ===================
-- ORDERS & ORDER ITEMS - MERCHANT 1 (60 days of rich data)
-- ===================
-- Pattern Strategy for Prophet/ARIMA:
--   Electronics (cat 1): Strong upward trend
--   Books (cat 2): Stable with slight growth
--   Clothing (cat 3): Seasonal pattern (weekend spikes)
--   Home & Garden (cat 4): Moderate growth
--   Sports (cat 5): Strong seasonal (weekends)
--   Toys (cat 6): Stable
--   Health (cat 7): Steady growth
--   Automotive (cat 8): Low but consistent

-- Generate 60 days of orders using a DO block
DO $$
DECLARE
    day_offset INTEGER;
    order_id_base INTEGER := 10000;
    item_id_base INTEGER := 50000;
    order_date DATE;
    is_weekend BOOLEAN;
    day_of_week INTEGER;
    
    -- Sales multipliers for patterns
    electronics_base DECIMAL := 800;
    books_base DECIMAL := 400;
    clothing_base DECIMAL := 300;
    home_base DECIMAL := 250;
    sports_base DECIMAL := 200;
    toys_base DECIMAL := 150;
    health_base DECIMAL := 180;
    auto_base DECIMAL := 120;
    
    -- Growth factors (per day)
    electronics_growth DECIMAL := 1.015;  -- 1.5% daily growth
    books_growth DECIMAL := 1.003;        -- 0.3% daily growth
    health_growth DECIMAL := 1.008;       -- 0.8% daily growth
    home_growth DECIMAL := 1.005;         -- 0.5% daily growth
    
BEGIN
    FOR day_offset IN 1..60 LOOP
        order_date := CURRENT_DATE - (day_offset || ' days')::INTERVAL;
        day_of_week := EXTRACT(DOW FROM order_date);
        is_weekend := day_of_week IN (0, 6);  -- Sunday=0, Saturday=6
        
        -- Insert order for Merchant 1
        INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
        VALUES (order_id_base + day_offset, 1, order_date, 'USD', 0)
        ON CONFLICT (id) DO NOTHING;
        
        -- Electronics: Trending UP (strong)
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 1,
            order_id_base + day_offset,
            101,  -- Smartphone
            2 + FLOOR(RANDOM() * 3),
            299.99,
            ROUND((electronics_base * POWER(electronics_growth, 60 - day_offset) * (0.9 + RANDOM() * 0.2))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Books: Stable with slight growth
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 2,
            order_id_base + day_offset,
            111,  -- Tech Guide
            3 + FLOOR(RANDOM() * 4),
            29.99,
            ROUND((books_base * POWER(books_growth, 60 - day_offset) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Clothing: Weekend spikes (seasonal pattern)
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 3,
            order_id_base + day_offset,
            121,  -- T-Shirt
            2 + FLOOR(RANDOM() * 3),
            49.99,
            ROUND((clothing_base * (CASE WHEN is_weekend THEN 1.8 ELSE 1.0 END) * (0.8 + RANDOM() * 0.4))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Home & Garden: Moderate growth
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 4,
            order_id_base + day_offset,
            131,  -- Garden Tools
            1 + FLOOR(RANDOM() * 2),
            89.99,
            ROUND((home_base * POWER(home_growth, 60 - day_offset) * (0.8 + RANDOM() * 0.4))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Sports: Strong weekend pattern
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 5,
            order_id_base + day_offset,
            141,  -- Yoga Mat
            1 + FLOOR(RANDOM() * 3),
            59.99,
            ROUND((sports_base * (CASE WHEN is_weekend THEN 2.0 ELSE 0.7 END) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Toys: Stable
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 6,
            order_id_base + day_offset,
            151,  -- Building Blocks
            2 + FLOOR(RANDOM() * 2),
            34.99,
            ROUND((toys_base * (0.9 + RANDOM() * 0.2))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Health & Beauty: Steady growth
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 7,
            order_id_base + day_offset,
            161,  -- Vitamins
            3 + FLOOR(RANDOM() * 3),
            24.99,
            ROUND((health_base * POWER(health_growth, 60 - day_offset) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Automotive: Low but consistent
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 10) + 8,
            order_id_base + day_offset,
            171,  -- Phone Mount
            1 + FLOOR(RANDOM() * 2),
            29.99,
            ROUND((auto_base * (0.9 + RANDOM() * 0.2))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
    END LOOP;
END $$;

-- Update order totals
UPDATE ingestion.orders o
SET total_amount = (
    SELECT COALESCE(SUM(line_amount), 0) 
    FROM ingestion.order_items oi 
    WHERE oi.order_id = o.id
)
WHERE o.merchant_id = 1 AND o.id >= 10000;

-- ===================
-- ORDERS & ORDER ITEMS - MERCHANT 2 (30 days)
-- ===================
DO $$
DECLARE
    day_offset INTEGER;
BEGIN
    FOR day_offset IN 1..30 LOOP
        INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
        VALUES (20000 + day_offset, 2, CURRENT_DATE - (day_offset || ' days')::INTERVAL, 'EUR', 0)
        ON CONFLICT (id) DO NOTHING;
        
        -- Fashion
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            60000 + (day_offset * 3) + 1,
            20000 + day_offset,
            201,
            1 + FLOOR(RANDOM() * 2),
            149.99,
            ROUND((200 + RANDOM() * 100)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Accessories
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            60000 + (day_offset * 3) + 2,
            20000 + day_offset,
            211,
            1 + FLOOR(RANDOM() * 2),
            89.99,
            ROUND((100 + RANDOM() * 80)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Footwear
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            60000 + (day_offset * 3) + 3,
            20000 + day_offset,
            221,
            1,
            199.99,
            ROUND((150 + RANDOM() * 100)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;

UPDATE ingestion.orders o
SET total_amount = (
    SELECT COALESCE(SUM(line_amount), 0) 
    FROM ingestion.order_items oi 
    WHERE oi.order_id = o.id
)
WHERE o.merchant_id = 2 AND o.id >= 20000;

-- ===================
-- ORDERS & ORDER ITEMS - MERCHANT 3 (30 days)
-- ===================
DO $$
DECLARE
    day_offset INTEGER;
BEGIN
    FOR day_offset IN 1..30 LOOP
        INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
        VALUES (30000 + day_offset, 3, CURRENT_DATE - (day_offset || ' days')::INTERVAL, 'INR', 0)
        ON CONFLICT (id) DO NOTHING;
        
        -- Kitchen Appliances
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            70000 + (day_offset * 3) + 1,
            30000 + day_offset,
            301,
            1 + FLOOR(RANDOM() * 2),
            4999.00,
            ROUND((4000 + RANDOM() * 2000)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Home Decor
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            70000 + (day_offset * 3) + 2,
            30000 + day_offset,
            311,
            1 + FLOOR(RANDOM() * 3),
            1999.00,
            ROUND((2000 + RANDOM() * 1500)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Traditional Wear
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            70000 + (day_offset * 3) + 3,
            30000 + day_offset,
            321,
            1,
            7999.00,
            ROUND((6000 + RANDOM() * 4000)::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;

UPDATE ingestion.orders o
SET total_amount = (
    SELECT COALESCE(SUM(line_amount), 0) 
    FROM ingestion.order_items oi 
    WHERE oi.order_id = o.id
)
WHERE o.merchant_id = 3 AND o.id >= 30000;

-- ===================
-- Summary of seeded data
-- ===================
-- Merchants: 3
-- Categories: 14 (8 for Merchant 1, 3 each for Merchants 2 & 3)
-- Products: 26
-- Orders: 120 (60 for M1, 30 for M2, 30 for M3)
-- Order Items: 840+ (8 per M1 order, 3 per M2/M3 order)
-- 
-- Sales Patterns (for Prophet/ARIMA):
--   Electronics: Strong upward trend (~1.5%/day)
--   Books: Stable with slight growth
--   Clothing: Weekend seasonal spikes
--   Home & Garden: Moderate growth
--   Sports: Strong weekend seasonality
--   Toys: Stable/flat
--   Health: Steady growth
--   Automotive: Low, consistent
