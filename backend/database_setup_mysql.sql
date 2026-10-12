CREATE DATABASE IF NOT EXISTS turacoz_bidtool
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'turacoz_app'@'localhost'
  IDENTIFIED BY 'replace-with-your-database-password';

ALTER USER 'turacoz_app'@'localhost'
  IDENTIFIED BY 'replace-with-your-database-password';

CREATE USER IF NOT EXISTS 'turacoz_app'@'127.0.0.1'
  IDENTIFIED BY 'replace-with-your-database-password';

ALTER USER 'turacoz_app'@'127.0.0.1'
  IDENTIFIED BY 'replace-with-your-database-password';

GRANT ALL PRIVILEGES ON turacoz_bidtool.* TO 'turacoz_app'@'localhost';
GRANT ALL PRIVILEGES ON turacoz_bidtool.* TO 'turacoz_app'@'127.0.0.1';
FLUSH PRIVILEGES;

USE turacoz_bidtool;

SOURCE deployment.sql;

INSERT IGNORE INTO categories (id, name, parent_id, status, created_at, updated_at) VALUES
('11111111-1111-1111-1111-111111111111', 'Electronics', NULL, 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111112', 'Healthcare Essentials', NULL, 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111113', 'Home Appliance', NULL, 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111114', 'Laptops', '11111111-1111-1111-1111-111111111111', 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111115', 'Medical Storage', '11111111-1111-1111-1111-111111111112', 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111116', 'Displays', '11111111-1111-1111-1111-111111111111', 'active', NOW(), NOW()),
('11111111-1111-1111-1111-111111111117', 'Vacuum Cleaner', '11111111-1111-1111-1111-111111111113', 'active', NOW(), NOW());

INSERT IGNORE INTO locations
(id, country, state, city, area, pincode, latitude, longitude, service_radius_km, status, created_at, updated_at) VALUES
('22222222-2222-2222-2222-222222222221', 'India', 'Maharashtra', 'Mumbai', 'Andheri East', '400069', 19.1155, 72.8727, 15, 'active', NOW(), NOW()),
('22222222-2222-2222-2222-222222222222', 'India', 'Maharashtra', 'Mumbai', 'Powai', '400076', 19.1176, 72.9060, 15, 'active', NOW(), NOW()),
('22222222-2222-2222-2222-222222222223', 'India', 'Maharashtra', 'Mumbai', 'Lower Parel', '400013', 18.9959, 72.8305, 15, 'active', NOW(), NOW());

INSERT IGNORE INTO products
(id, category_id, subcategory_id, location_id, name, brand, model, price_min, price_max, status, created_by, created_at, updated_at) VALUES
('33333333-3333-3333-3333-333333333331', '11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111114', '22222222-2222-2222-2222-222222222221', 'Laptop for medical writing team', 'Lenovo', 'ThinkPad E14', 55000, 72000, 'active', NULL, NOW(), NOW()),
('33333333-3333-3333-3333-333333333332', '11111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111115', '22222222-2222-2222-2222-222222222222', 'Clinic refrigerator', 'Godrej', 'Medical Storage 300L', 42000, 60000, 'active', NULL, NOW(), NOW()),
('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111116', '22222222-2222-2222-2222-222222222223', 'Conference room display', 'Samsung', 'Crystal UHD 65', 68000, 92000, 'active', NULL, NOW(), NOW()),
('33333333-3333-3333-3333-333333333334', '11111111-1111-1111-1111-111111111113', '11111111-1111-1111-1111-111111111117', '22222222-2222-2222-2222-222222222221', 'Clinic vacuum cleaner', 'Dyson', 'V11 Absolute', 38000, 52000, 'active', NULL, NOW(), NOW()),
('33333333-3333-3333-3333-333333333335', '11111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111115', '22222222-2222-2222-2222-222222222222', 'Portable ultrasound trolley', 'BPL', 'Mobile Trolley Pro', 18000, 28000, 'active', NULL, NOW(), NOW());
