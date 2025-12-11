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
