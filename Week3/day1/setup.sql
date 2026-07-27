-- Create database
CREATE DATABASE super_store_db;

-- Set date format (run after connecting to super_store_db)
ALTER DATABASE super_store_db SET datestyle = 'ISO, MDY';

-- Create table with constraints
CREATE TABLE superstore_sales (
    row_id INTEGER PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL,
    order_date DATE NOT NULL,
    ship_date DATE,
    ship_mode VARCHAR(50),
    customer_id VARCHAR(20) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    segment VARCHAR(50),
    country VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(10),
    region VARCHAR(50),
    product_id VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    sub_category VARCHAR(50),
    product_name VARCHAR(200) NOT NULL,
    sales DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    discount DECIMAL(4,2) CHECK (discount >= 0 AND discount <= 1),
    profit DECIMAL(10,2)
);

-- Import data from CSV
COPY superstore_sales(row_id, order_id, order_date, ship_date, ship_mode, customer_id, customer_name, segment,
country, city, state, postal_code, region, product_id, category, sub_category, product_name, sales, 
quantity, discount, profit)
FROM 'C:/Users/MAKIK/Downloads/Netixsol/Week3/day1/dataset/superstore_dataset.csv'
WITH (FORMAT csv, HEADER, DELIMITER ',', ENCODING 'WIN1252', QUOTE '"', ESCAPE '"');

-- count the total rows
SELECT COUNT(*) FROM superstore_sales;

-- preview the first 10 rows
SELECT * FROM superstore_sales LIMIT 10;

-- information_schema.columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'superstore_sales';