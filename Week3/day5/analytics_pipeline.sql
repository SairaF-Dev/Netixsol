
-- -- Create dedicated analytics schema for the transformation layer
-- CREATE SCHEMA IF NOT EXISTS analytics;
-- -- Create a dedicated schema for Executive KPI datasets
-- CREATE SCHEMA IF NOT EXISTS kpi;

-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_schema = 'sales' 
--   AND table_name = 'salesorderdetail';

-- SELECT table_name, column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_schema = 'purchasing'  
--   AND table_name = 'purchaseorderheader';


-- -- Create dedicated analytics schema for the transformation layer
-- CREATE SCHEMA IF NOT EXISTS analytics;
-- -- Create a dedicated schema for Executive KPI datasets
-- CREATE SCHEMA IF NOT EXISTS kpi;

-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_schema = 'sales' 
--   AND table_name = 'salesorderdetail';

-- SELECT table_name, column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_schema = 'purchasing'  
--   AND table_name = 'purchaseorderheader';



-- PRODUCTION-GRADE ADVENTUREWORKS ANALYTICS PIPELINE
-- Architecture: Staging -> Domain Marts -> Business Metrics -> Executive KPIs
-- Standard: Idempotent, Zero-Downtime, Schema-Isolated


-- Ensure schemas exist
CREATE SCHEMA IF NOT EXISTS analytics;


-- STAGE 0 — DATE ANALYTICS (Foundation Dimension)

CREATE TABLE IF NOT EXISTS analytics.date_analytics AS
SELECT
    d::date                                                 AS calendar_date,
    EXTRACT(YEAR FROM d)::int                               AS year_num,
    EXTRACT(MONTH FROM d)::int                              AS month_num,
    EXTRACT(QUARTER FROM d)::int                            AS quarter_num,
    TO_CHAR(d, 'YYYY-MM')                                   AS year_month,
    TO_CHAR(d, 'YYYY') || '-Q' || EXTRACT(QUARTER FROM d)::int AS year_quarter,
    TRIM(TO_CHAR(d, 'Day'))                                 AS day_name,
    CASE WHEN EXTRACT(DOW FROM d) IN (0,6) THEN 1 ELSE 0 END AS is_weekend
FROM GENERATE_SERIES('2022-05-01'::date, '2025-07-31'::date, INTERVAL '1 day') d;



-- STAGE 1 — ENRICHED SALES FACT (The Reuse Base)
-- Using CREATE OR REPLACE VIEW for zero-downtime production updates

CREATE OR REPLACE VIEW analytics.vw_sales_fact AS
SELECT
    h.salesorderid,
    h.orderdate::date                                       AS order_date,
    TO_CHAR(h.orderdate, 'YYYY-MM')                         AS year_month,
    EXTRACT(YEAR FROM h.orderdate)::int                     AS order_year,
    h.customerid,
    h.salespersonid,
    h.territoryid,
    d.productid,
    p.name                                                  AS product_name,
    p.productsubcategoryid,
    sc.name                                                 AS subcategory_name,
    sc.productcategoryid,
    cat.name                                                AS category_name,
    d.orderqty::int                                         AS order_qty,
    d.unitprice::numeric                                    AS unit_price,
    d.unitpricediscount::numeric                            AS unit_price_discount,
    (d.orderqty::numeric * d.unitprice::numeric * (1 - COALESCE(d.unitpricediscount, 0))) AS line_total,
    (p.standardcost::numeric * d.orderqty::numeric)         AS line_cost,
    ((d.orderqty::numeric * d.unitprice::numeric * (1 - COALESCE(d.unitpricediscount, 0))) - (p.standardcost::numeric * d.orderqty::numeric)) AS line_margin
FROM sales.salesorderdetail d
JOIN sales.salesorderheader h       ON h.salesorderid = d.salesorderid
JOIN production.product p           ON p.productid = d.productid
LEFT JOIN production.productsubcategory sc ON sc.productsubcategoryid = p.productsubcategoryid
LEFT JOIN production.productcategory cat   ON cat.productcategoryid = sc.productcategoryid;



-- STAGE 2 — DOMAIN ANALYTICS MARTS


-- STAGE 2.1 — PURCHASING & INVENTORY DOMAIN MARTS
CREATE OR REPLACE VIEW analytics.vw_purchasing_analytics AS
SELECT
    v.businessentityid AS vendor_id,
    v.name AS vendor_name,
    COUNT(DISTINCT poh.purchaseorderid) AS total_purchase_orders,
    COALESCE(SUM(poh.subtotal), 0) AS total_spend,
    COALESCE(AVG(poh.subtotal), 0) AS avg_po_amount,
    MIN(poh.orderdate::date) AS first_order_date,
    MAX(poh.orderdate::date) AS last_order_date
FROM purchasing.vendor v
LEFT JOIN purchasing.purchaseorderheader poh ON poh.vendorid = v.businessentityid
GROUP BY v.businessentityid, v.name;


CREATE OR REPLACE VIEW analytics.vw_inventory_health AS
SELECT
    p.productid,
    p.name AS product_name,
    pi.locationid,
    loc.name AS location_name,
    pi.quantity AS stock_quantity
FROM production.product p
LEFT JOIN production.productinventory pi ON pi.productid = p.productid
LEFT JOIN production.location loc ON loc.locationid = pi.locationid;


CREATE OR REPLACE VIEW analytics.vw_customer_analytics AS
SELECT
    c.customerid,
    c.territoryid,
    COUNT(DISTINCT f.salesorderid)              AS total_orders,
    COALESCE(SUM(f.line_total), 0)              AS total_revenue,
    COALESCE(AVG(ot.order_total), 0)            AS avg_order_value,
    MIN(f.order_date)                           AS first_order_date,
    MAX(f.order_date)                           AS last_order_date,
    (DATE '2025-06-29' - MAX(f.order_date))     AS days_since_last_order
FROM sales.customer c
LEFT JOIN analytics.vw_sales_fact f ON f.customerid = c.customerid
LEFT JOIN (
    SELECT salesorderid, SUM(line_total) AS order_total
    FROM analytics.vw_sales_fact GROUP BY salesorderid
) ot ON ot.salesorderid = f.salesorderid
GROUP BY c.customerid, c.territoryid;


CREATE OR REPLACE VIEW analytics.vw_product_analytics AS
SELECT
    p.productid,
    p.name                                      AS product_name,
    cat.name                                    AS category_name,
    sc.name                                     AS subcategory_name,
    p.standardcost::numeric                     AS standard_cost,
    p.listprice::numeric                        AS list_price,
    COALESCE(SUM(f.order_qty), 0)               AS total_qty_sold,
    COALESCE(SUM(f.line_total), 0)              AS total_revenue,
    COALESCE(SUM(f.line_margin), 0)             AS total_margin,
    CASE WHEN COALESCE(SUM(f.line_total), 0) = 0 THEN 0
         ELSE ROUND(SUM(f.line_margin) * 100.0 / SUM(f.line_total), 2) END AS margin_pct,
    COUNT(DISTINCT f.salesorderid)              AS num_orders
FROM production.product p
LEFT JOIN production.productsubcategory sc ON sc.productsubcategoryid = p.productsubcategoryid
LEFT JOIN production.productcategory cat   ON cat.productcategoryid = sc.productcategoryid
LEFT JOIN analytics.vw_sales_fact f        ON f.productid = p.productid
GROUP BY p.productid, p.name, cat.name, sc.name, p.standardcost, p.listprice;


CREATE OR REPLACE VIEW analytics.vw_employee_analytics AS
SELECT
    sp.businessentityid                         AS salesperson_id,
    pe.firstname || ' ' || pe.lastname          AS salesperson_name,
    sp.territoryid,
    sp.salesquota::numeric                      AS sales_quota,
    COALESCE(SUM(f.line_total), 0)              AS total_revenue,
    COUNT(DISTINCT f.salesorderid)              AS total_orders,
    COALESCE(SUM(f.line_total), 0) / NULLIF(COUNT(DISTINCT f.customerid), 0) AS revenue_per_customer,
    COUNT(DISTINCT f.customerid)                AS customers_served
FROM sales.salesperson sp
JOIN person.person pe ON pe.businessentityid = sp.businessentityid
LEFT JOIN analytics.vw_sales_fact f ON f.salespersonid = sp.businessentityid
GROUP BY sp.businessentityid, pe.firstname, pe.lastname, sp.territoryid, sp.salesquota;


CREATE OR REPLACE VIEW analytics.vw_territory_analytics AS
SELECT
    t.territoryid,
    t.name                                      AS territory_name,
    t.countryregioncode,
    t."group"                                   AS region_group,
    COALESCE(SUM(f.line_total), 0)              AS total_revenue,
    COUNT(DISTINCT f.salesorderid)              AS total_orders,
    COUNT(DISTINCT f.customerid)                AS total_customers
FROM sales.salesterritory t
LEFT JOIN analytics.vw_sales_fact f ON f.territoryid = t.territoryid
GROUP BY t.territoryid, t.name, t.countryregioncode, t."group";



-- STAGE 3 — BUSINESS METRICS (Advanced Window Functions)


CREATE OR REPLACE VIEW analytics.vw_monthly_revenue AS
WITH monthly AS (
    SELECT year_month, SUM(line_total) AS revenue, COUNT(DISTINCT salesorderid) AS orders
    FROM analytics.vw_sales_fact GROUP BY year_month
)
SELECT
    year_month, revenue, orders,
    LAG(revenue) OVER (ORDER BY year_month) AS prev_month_revenue,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY year_month)) * 100.0 / NULLIF(LAG(revenue) OVER (ORDER BY year_month), 0), 2) AS mom_growth_pct,
    ROUND(AVG(revenue) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS revenue_3mo_avg
FROM monthly ORDER BY year_month;


CREATE OR REPLACE VIEW analytics.vw_customer_segments AS
WITH scored AS (
    SELECT
        customerid, territoryid, total_orders, total_revenue, avg_order_value, days_since_last_order,
        NTILE(4) OVER (ORDER BY total_revenue ASC) AS revenue_quartile,
        NTILE(4) OVER (ORDER BY days_since_last_order DESC) AS recency_quartile
    FROM analytics.vw_customer_analytics WHERE total_orders > 0
)
SELECT *,
    CASE
        WHEN revenue_quartile = 4 AND recency_quartile = 4 THEN 'Champion'
        WHEN revenue_quartile >= 3 AND recency_quartile >= 3 THEN 'Loyal'
        WHEN revenue_quartile >= 3 AND recency_quartile < 3  THEN 'At Risk (High Value)'
        WHEN revenue_quartile < 3  AND recency_quartile >= 3 THEN 'Promising'
        WHEN total_orders = 1                              THEN 'One-Time Buyer'
        ELSE 'Needs Attention'
    END AS customer_segment
FROM scored;


CREATE OR REPLACE VIEW analytics.vw_product_rankings AS
SELECT
    productid, product_name, category_name, subcategory_name,
    total_qty_sold, total_revenue, total_margin, margin_pct,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
    RANK() OVER (PARTITION BY category_name ORDER BY total_revenue DESC) AS rank_in_category,
    DENSE_RANK() OVER (ORDER BY margin_pct DESC) AS margin_rank,
    CASE
        WHEN total_revenue = 0 THEN 'No Sales'
        WHEN RANK() OVER (ORDER BY total_revenue DESC) <= 10 THEN 'Best Seller'
        WHEN RANK() OVER (ORDER BY total_revenue ASC) <= 10 THEN 'Lowest Performer'
        ELSE 'Mid-Tier'
    END AS performance_tag
FROM analytics.vw_product_analytics;



-- STAGE 4 — EXECUTIVE KPI SUMMARY VIEW

CREATE OR REPLACE VIEW analytics.vw_executive_kpi_summary AS
SELECT
    (SELECT SUM(total_revenue) FROM analytics.vw_territory_analytics) AS total_company_revenue,
    (SELECT SUM(total_margin)  FROM analytics.vw_product_analytics) AS total_company_margin,
    (SELECT COUNT(*) FROM analytics.vw_customer_analytics WHERE total_orders > 0) AS total_active_customers,
    (SELECT COUNT(*) FROM analytics.vw_customer_segments WHERE customer_segment = 'Champion') AS champion_customers,
    (SELECT COUNT(*) FROM analytics.vw_customer_segments WHERE customer_segment LIKE 'At Risk%') AS at_risk_customers,
    (SELECT territory_name FROM analytics.vw_territory_analytics ORDER BY total_revenue DESC LIMIT 1) AS top_territory,
    (SELECT product_name FROM analytics.vw_product_rankings ORDER BY total_revenue DESC LIMIT 1) AS top_product,
    (SELECT ROUND(AVG(mom_growth_pct), 2) FROM analytics.vw_monthly_revenue WHERE mom_growth_pct IS NOT NULL) AS avg_mom_growth_pct;



-- TASK 1: Design an Analytics Layer & Sales Fact Output
-- Description: Displays the enriched core sales fact dataset joining multiple domains.

-- SELECT 
--     salesorderid, 
--     order_date, 
--     customerid, 
--     territoryid, 
--     product_name, 
--     category_name, 
--     order_qty, 
--     unit_price, 
--     line_total, 
--     line_margin
-- FROM analytics.vw_sales_fact
-- LIMIT 50;


-- TASK 2: Intermediate Domain Analytics Marts (Customer Analytics)
-- Description: Displays customer-level aggregations and purchase metrics.

-- SELECT 
--     customerid, 
--     territoryid, 
--     total_orders, 
--     total_revenue, 
--     avg_order_value, 
--     first_order_date, 
--     last_order_date, 
--     days_since_last_order
-- FROM analytics.vw_customer_analytics
-- WHERE total_orders > 0
-- LIMIT 50;


-- TASK 2 (Cont.): Product Analytics Mart
-- Description: Displays product performance, total revenue, and profit margins.


-- SELECT 
--     productid, 
--     product_name, 
--     category_name, 
--     total_qty_sold, 
--     total_revenue, 
--     total_margin, 
--     margin_pct
-- FROM analytics.vw_product_analytics
-- WHERE total_revenue > 0
-- LIMIT 50;


-- TASK 3: Executive KPI Datasets - Monthly Revenue & Growth (Sales Domain)
-- Description: Displays window functions for LAG, MoM growth, and 3-month moving average.

-- SELECT 
--     year_month, 
--     revenue, 
--     orders, 
--     prev_month_revenue, 
--     mom_growth_pct, 
--     revenue_3mo_avg
-- FROM analytics.vw_monthly_revenue
-- LIMIT 50;


-- TASK 3 (Cont.): Customer Segmentation (RFM Analysis)
-- Description: Categorizes customers into Champions, Loyal, At Risk, etc. using NTILE.


-- SELECT 
--     customerid, 
--     total_orders, 
--     total_revenue, 
--     revenue_quartile, 
--     recency_quartile, 
--     customer_segment
-- FROM analytics.vw_customer_segments
-- LIMIT 50;


-- TASK 3 (Cont.): Product Rankings & Performance Tags
-- Description: Ranks products overall and within categories using RANK & DENSE_RANK.


-- SELECT 
--     productid, 
--     product_name, 
--     category_name, 
--     total_revenue, 
--     revenue_rank, 
--     rank_in_category, 
--     performance_tag
-- FROM analytics.vw_product_rankings
-- LIMIT 50;


-- TASK 3 (Cont.): Regional & Territory Analysis
-- Description: Regional revenue breakdown and percentage share calculation.


-- SELECT 
--     territoryid, 
--     territory_name, 
--     region_group, 
--     total_revenue, 
--     total_customers
-- FROM analytics.vw_territory_analytics;



-- TASK 4: Advanced SQL Concepts Executive Summary (KPI Dashboard)
-- Description: Single-row high-level summary utilizing multi-layered views & subqueries.

SELECT 
    total_company_revenue, 
    total_company_margin, 
    total_active_customers, 
    champion_customers, 
    at_risk_customers, 
    top_territory, 
    top_product, 
    avg_mom_growth_pct
FROM analytics.vw_executive_kpi_summary;