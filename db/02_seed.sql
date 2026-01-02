-- ============================================================================
-- SEED DATA FOR QB-TOP-SALES DEMO
-- ============================================================================
-- This seed data provides:
-- - 3 merchants (multi-tenant demo)
-- - 18 categories (8 for Merchant 1, 5 each for Merchants 2 & 3)
-- - 120 days of order history (good for Prophet/ARIMA trend detection)
-- - Varied sales patterns (trending, seasonal, stable)
-- - Pre-computed aggregations in forecasting.category_sales_agg
--
-- NOTE: This seed data bypasses Kafka and directly populates both:
--   1. ingestion.orders / ingestion.order_items (raw order data)
--   2. forecasting.category_sales_agg (aggregated data for forecasting)
--
-- For live data that flows through Kafka, use the order-simulator instead.
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
    -- Merchant 2 (EuroStyle) - 5 categories (luxury European fashion)
    (9, 2, 'Fashion'),
    (10, 2, 'Accessories'),
    (11, 2, 'Footwear'),
    (15, 2, 'Jewelry'),
    (16, 2, 'Watches'),
    -- Merchant 3 (BharatBazaar) - 5 categories (Indian marketplace)
    (12, 3, 'Kitchen Appliances'),
    (13, 3, 'Home Decor'),
    (14, 3, 'Traditional Wear'),
    (17, 3, 'Ayurveda & Wellness'),
    (18, 3, 'Handicrafts')
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
    (203, 2, 9, 'Cashmere Coat'),
    -- Merchant 2: Accessories (cat 10)
    (211, 2, 10, 'Leather Handbag'),
    (212, 2, 10, 'Sunglasses Premium'),
    (213, 2, 10, 'Belt Collection'),
    -- Merchant 2: Footwear (cat 11)
    (221, 2, 11, 'Stiletto Heels'),
    (222, 2, 11, 'Sneakers Limited'),
    (223, 2, 11, 'Oxford Shoes'),
    -- Merchant 2: Jewelry (cat 15)
    (231, 2, 15, 'Gold Necklace'),
    (232, 2, 15, 'Diamond Ring'),
    (233, 2, 15, 'Pearl Earrings'),
    -- Merchant 2: Watches (cat 16)
    (241, 2, 16, 'Chronograph Swiss'),
    (242, 2, 16, 'Smart Luxury Watch'),
    (243, 2, 16, 'Vintage Collection'),
    -- Merchant 3: Kitchen Appliances (cat 12)
    (301, 3, 12, 'Mixer Grinder'),
    (302, 3, 12, 'Induction Cooktop'),
    (303, 3, 12, 'Pressure Cooker'),
    -- Merchant 3: Home Decor (cat 13)
    (311, 3, 13, 'Brass Lamp'),
    (312, 3, 13, 'Wall Hanging'),
    (313, 3, 13, 'Tanjore Painting'),
    -- Merchant 3: Traditional Wear (cat 14)
    (321, 3, 14, 'Silk Saree'),
    (322, 3, 14, 'Kurta Set'),
    (323, 3, 14, 'Lehenga Choli'),
    -- Merchant 3: Ayurveda & Wellness (cat 17)
    (331, 3, 17, 'Ashwagandha Pack'),
    (332, 3, 17, 'Chyawanprash'),
    (333, 3, 17, 'Herbal Oil Set'),
    -- Merchant 3: Handicrafts (cat 18)
    (341, 3, 18, 'Marble Sculpture'),
    (342, 3, 18, 'Pashmina Shawl'),
    (343, 3, 18, 'Wooden Chess Set')
ON CONFLICT (id) DO NOTHING;

-- ===================
-- ORDERS & ORDER ITEMS - MERCHANT 1 (120 days of rich data)
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
    FOR day_offset IN 0..120 LOOP
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
-- ORDERS & ORDER ITEMS - MERCHANT 2 (60 days, European luxury patterns)
-- ===================
-- Pattern Strategy:
--   Fashion (cat 9): Trendy with seasonal bursts
--   Accessories (cat 10): Stable premium
--   Footwear (cat 11): Weekend spikes
--   Jewelry (cat 15): Strong growth (luxury market)
--   Watches (cat 16): High-value, low-frequency

DO $$
DECLARE
    day_offset INTEGER;
    order_date DATE;
    is_weekend BOOLEAN;
    day_of_week INTEGER;
    item_id_base INTEGER := 60000;
    
    -- Base values (EUR)
    fashion_base DECIMAL := 350;
    accessories_base DECIMAL := 180;
    footwear_base DECIMAL := 250;
    jewelry_base DECIMAL := 500;
    watches_base DECIMAL := 800;
    
BEGIN
    FOR day_offset IN 0..120 LOOP
        order_date := CURRENT_DATE - (day_offset || ' days')::INTERVAL;
        day_of_week := EXTRACT(DOW FROM order_date);
        is_weekend := day_of_week IN (0, 6);
        
        INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
        VALUES (20000 + day_offset, 2, order_date, 'EUR', 0)
        ON CONFLICT (id) DO NOTHING;
        
        -- Fashion: Trendy bursts (higher on Fridays/Saturdays)
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 1,
            20000 + day_offset,
            201 + FLOOR(RANDOM() * 3),
            1 + FLOOR(RANDOM() * 2),
            149.99,
            ROUND((fashion_base * (CASE WHEN day_of_week IN (5, 6) THEN 1.5 ELSE 1.0 END) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Accessories: Stable premium
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 2,
            20000 + day_offset,
            211 + FLOOR(RANDOM() * 3),
            1 + FLOOR(RANDOM() * 2),
            89.99,
            ROUND((accessories_base * (0.9 + RANDOM() * 0.2))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Footwear: Weekend spikes
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 3,
            20000 + day_offset,
            221 + FLOOR(RANDOM() * 3),
            1,
            199.99,
            ROUND((footwear_base * (CASE WHEN is_weekend THEN 1.8 ELSE 1.0 END) * (0.8 + RANDOM() * 0.4))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Jewelry: Strong growth (1.2% daily)
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 4,
            20000 + day_offset,
            231 + FLOOR(RANDOM() * 3),
            1,
            599.99,
            ROUND((jewelry_base * POWER(1.012, 60 - day_offset) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Watches: High-value, slight growth
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 5,
            20000 + day_offset,
            241 + FLOOR(RANDOM() * 3),
            1,
            1299.99,
            ROUND((watches_base * POWER(1.005, 60 - day_offset) * (0.75 + RANDOM() * 0.5))::NUMERIC, 2)
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
-- ORDERS & ORDER ITEMS - MERCHANT 3 (60 days, Indian marketplace patterns)
-- ===================
-- Pattern Strategy:
--   Kitchen Appliances (cat 12): Stable with slight growth
--   Home Decor (cat 13): Festival spikes (simulate Diwali effect mid-period)
--   Traditional Wear (cat 14): Strong weekend + festival patterns
--   Ayurveda & Wellness (cat 17): Steady growth (health trend)
--   Handicrafts (cat 18): Seasonal, gift-driven

DO $$
DECLARE
    day_offset INTEGER;
    order_date DATE;
    is_weekend BOOLEAN;
    day_of_week INTEGER;
    is_festival_period BOOLEAN;
    item_id_base INTEGER := 70000;
    
    -- Base values (INR)
    kitchen_base DECIMAL := 5000;
    decor_base DECIMAL := 2500;
    wear_base DECIMAL := 8000;
    ayurveda_base DECIMAL := 1500;
    handicraft_base DECIMAL := 3000;
    
BEGIN
    FOR day_offset IN 0..120 LOOP
        order_date := CURRENT_DATE - (day_offset || ' days')::INTERVAL;
        day_of_week := EXTRACT(DOW FROM order_date);
        is_weekend := day_of_week IN (0, 6);
        -- Simulate festival period (days 25-35 from today = ~1 month ago)
        is_festival_period := day_offset BETWEEN 25 AND 35;
        
        INSERT INTO ingestion.orders (id, merchant_id, order_date, currency, total_amount)
        VALUES (30000 + day_offset, 3, order_date, 'INR', 0)
        ON CONFLICT (id) DO NOTHING;
        
        -- Kitchen Appliances: Stable with slight growth
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 1,
            30000 + day_offset,
            301 + FLOOR(RANDOM() * 3),
            1 + FLOOR(RANDOM() * 2),
            4999.00,
            ROUND((kitchen_base * POWER(1.003, 60 - day_offset) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Home Decor: Festival spikes
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 2,
            30000 + day_offset,
            311 + FLOOR(RANDOM() * 3),
            1 + FLOOR(RANDOM() * 3),
            1999.00,
            ROUND((decor_base * (CASE WHEN is_festival_period THEN 2.5 ELSE 1.0 END) * (0.8 + RANDOM() * 0.4))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Traditional Wear: Weekend + festival pattern
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 3,
            30000 + day_offset,
            321 + FLOOR(RANDOM() * 3),
            1,
            7999.00,
            ROUND((wear_base * (CASE WHEN is_weekend THEN 1.5 ELSE 1.0 END) * (CASE WHEN is_festival_period THEN 2.0 ELSE 1.0 END) * (0.75 + RANDOM() * 0.5))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Ayurveda & Wellness: Steady growth (1% daily)
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 4,
            30000 + day_offset,
            331 + FLOOR(RANDOM() * 3),
            2 + FLOOR(RANDOM() * 3),
            499.00,
            ROUND((ayurveda_base * POWER(1.01, 60 - day_offset) * (0.85 + RANDOM() * 0.3))::NUMERIC, 2)
        ) ON CONFLICT (id) DO NOTHING;
        
        -- Handicrafts: Gift-driven, weekend + festival boost
        INSERT INTO ingestion.order_items (id, order_id, product_id, quantity, unit_price, line_amount)
        VALUES (
            item_id_base + (day_offset * 5) + 5,
            30000 + day_offset,
            341 + FLOOR(RANDOM() * 3),
            1,
            2999.00,
            ROUND((handicraft_base * (CASE WHEN is_weekend THEN 1.3 ELSE 1.0 END) * (CASE WHEN is_festival_period THEN 1.8 ELSE 1.0 END) * (0.8 + RANDOM() * 0.4))::NUMERIC, 2)
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
-- Merchants: 3 (TechMart USA, EuroStyle, BharatBazaar)
-- Categories: 18 (8 for Merchant 1, 5 each for Merchants 2 & 3)
-- Products: 54 (24 for M1, 15 each for M2 & M3)
-- Orders: 360 (120 per merchant)
-- Order Items: 2160 (8 per M1 order, 5 per M2/M3 order)
-- 
-- Sales Patterns by Merchant:
-- 
-- Merchant 1 (TechMart USA - USD):
--   Electronics: Strong upward trend (~1.5%/day)
--   Books: Stable with slight growth
--   Clothing: Weekend seasonal spikes
--   Home & Garden: Moderate growth
--   Sports: Strong weekend seasonality
--   Toys: Stable/flat
--   Health: Steady growth
--   Automotive: Low, consistent
-- 
-- Merchant 2 (EuroStyle - EUR):
--   Fashion: Trendy with Friday/Saturday bursts
--   Accessories: Stable premium
--   Footwear: Weekend spikes
--   Jewelry: Strong growth (luxury market, ~1.2%/day)
--   Watches: High-value, slight growth
-- 
-- Merchant 3 (BharatBazaar - INR):
--   Kitchen Appliances: Stable with slight growth
--   Home Decor: Festival spikes (mid-period Diwali effect)
--   Traditional Wear: Weekend + festival pattern
--   Ayurveda & Wellness: Steady growth (~1%/day)
--   Handicrafts: Gift-driven, weekend + festival boost

-- ===================
-- SEED AGGREGATED DATA FOR FORECASTING
-- ===================
-- The aggregation-service normally populates forecasting.category_sales_agg via Kafka events.
-- Since seed data bypasses Kafka, we need to populate this table directly for forecasting to work.

-- Aggregate order data into forecasting.category_sales_agg (DAY buckets)
INSERT INTO forecasting.category_sales_agg (merchant_id, category_id, bucket_type, bucket_start, bucket_end, total_sales_amount, total_units_sold, order_count)
SELECT 
    m.id as merchant_id,
    p.category_id,
    'DAY' as bucket_type,
    DATE_TRUNC('day', o.order_date) as bucket_start,
    DATE_TRUNC('day', o.order_date) + INTERVAL '1 day' as bucket_end,
    SUM(oi.line_amount) as total_sales_amount,
    SUM(oi.quantity) as total_units_sold,
    COUNT(DISTINCT o.id) as order_count
FROM ingestion.orders o
JOIN ingestion.order_items oi ON o.id = oi.order_id
JOIN ingestion.products p ON oi.product_id = p.id
JOIN ingestion.merchants m ON o.merchant_id = m.id
WHERE o.id >= 10000  -- Only seeded orders
GROUP BY m.id, p.category_id, DATE_TRUNC('day', o.order_date)
ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start) 
DO UPDATE SET 
    total_sales_amount = EXCLUDED.total_sales_amount,
    total_units_sold = EXCLUDED.total_units_sold,
    order_count = EXCLUDED.order_count,
    updated_at = now();

-- Also create WEEK buckets for weekly forecasting
INSERT INTO forecasting.category_sales_agg (merchant_id, category_id, bucket_type, bucket_start, bucket_end, total_sales_amount, total_units_sold, order_count)
SELECT 
    m.id as merchant_id,
    p.category_id,
    'WEEK' as bucket_type,
    DATE_TRUNC('week', o.order_date) as bucket_start,
    DATE_TRUNC('week', o.order_date) + INTERVAL '1 week' as bucket_end,
    SUM(oi.line_amount) as total_sales_amount,
    SUM(oi.quantity) as total_units_sold,
    COUNT(DISTINCT o.id) as order_count
FROM ingestion.orders o
JOIN ingestion.order_items oi ON o.id = oi.order_id
JOIN ingestion.products p ON oi.product_id = p.id
JOIN ingestion.merchants m ON o.merchant_id = m.id
WHERE o.id >= 10000
GROUP BY m.id, p.category_id, DATE_TRUNC('week', o.order_date)
ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start) 
DO UPDATE SET 
    total_sales_amount = EXCLUDED.total_sales_amount,
    total_units_sold = EXCLUDED.total_units_sold,
    order_count = EXCLUDED.order_count,
    updated_at = now();

-- Also create MONTH buckets for monthly forecasting
INSERT INTO forecasting.category_sales_agg (merchant_id, category_id, bucket_type, bucket_start, bucket_end, total_sales_amount, total_units_sold, order_count)
SELECT 
    m.id as merchant_id,
    p.category_id,
    'MONTH' as bucket_type,
    DATE_TRUNC('month', o.order_date) as bucket_start,
    DATE_TRUNC('month', o.order_date) + INTERVAL '1 month' as bucket_end,
    SUM(oi.line_amount) as total_sales_amount,
    SUM(oi.quantity) as total_units_sold,
    COUNT(DISTINCT o.id) as order_count
FROM ingestion.orders o
JOIN ingestion.order_items oi ON o.id = oi.order_id
JOIN ingestion.products p ON oi.product_id = p.id
JOIN ingestion.merchants m ON o.merchant_id = m.id
WHERE o.id >= 10000
GROUP BY m.id, p.category_id, DATE_TRUNC('month', o.order_date)
ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start) 
DO UPDATE SET 
    total_sales_amount = EXCLUDED.total_sales_amount,
    total_units_sold = EXCLUDED.total_units_sold,
    order_count = EXCLUDED.order_count,
    updated_at = now();

-- Mark seeded orders as processed (for idempotency)
INSERT INTO forecasting.processed_events (order_id)
SELECT id FROM ingestion.orders WHERE id >= 10000
ON CONFLICT (order_id) DO NOTHING;

