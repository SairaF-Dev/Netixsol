# Enterprise Analytics & Reporting Layer

## Database Overview
The source enterprise database (`Adventureworks`) is optimized for daily transactional processing (OLTP). To facilitate fast business reporting without repeatedly querying raw operational tables, a dedicated `analytics` schema was created to host structured views and aggregated data marts.

## Analytics Architecture
The project follows a Modern Data Stack pipeline approach with a strict dependency chain:
1. **Raw Operational Tables:** Source transactional data across sales, production, person, and purchasing domains.
2. **Intermediate Marts & Business Metrics:** Domain-specific transformations combining multiple business domains (`analytics.vw_sales_fact`, `analytics.vw_customer_analytics`, `analytics.vw_product_analytics`).
3. **Advanced Analytical Views:** Chained CTEs, window functions, ranking functions, and RFM customer segmentation.
4. **Executive Reporting Layer (`analytics.*`):**  Final aggregated views, including monthly revenue, quarterly revenue, customer segmentation, product analytics, territory analytics, inventory analytics, employee analytics, and executive KPI summaries. These reusable datasets power the Python analytics notebook and future business intelligence dashboards.

## Intermediate Tables Created
* `analytics.vw_sales_fact` — Unified sales transaction fact table.
* `analytics.vw_customer_analytics` — Customer-level aggregation tracking total orders, revenue, and average order value.
* `analytics.vw_product_analytics` — Product performance, revenue contribution, and profit margins.
* `analytics.vw_monthly_revenue` — Time-series revenue trend with window functions for MoM growth and moving averages.
* `analytics.vw_quarterly_revenue` — Quarterly revenue summary built from the monthly analytics layer for executive reporting.
* `analytics.vw_customer_segments` — RFM-based customer behavioral segmentation (Champions, At Risk, Loyal, etc.).
* `analytics.vw_product_rankings` — Product rankings across overall sales and category sub-groups.
* `analytics.vw_employee_analytics` — Salesperson performance tracking against quotas and revenue share.
* `analytics.vw_territory_analytics` — Regional revenue and customer distribution breakdowns.
* `analytics.vw_inventory_purchasing_analytics` — Stock health and supplier performance metrics.
* `analytics.vw_executive_kpi_summary` — Single-row high-level company performance summary.


## SQL Design Decisions
* **Pipeline Chaining:** Views build sequentially upon previous analytical layers to avoid redundant calculations.
* **Window Functions:** Utilized `LAG()`, `RANK()`, `DENSE_RANK()`, and `NTILE()` for revenue growth tracking and segmentation.
* **Performance Optimization:** The analytics layer stores reusable monthly, quarterly, customer, territory, product, inventory, and executive KPI datasets. Downstream dashboards query only these analytical views, eliminating repeated calculations against operational tables.

## Challenges Faced
* **Database Schema Complexity:** Navigating multiple enterprise schemas required careful relational mapping using both INNER JOINs and LEFT JOINs to produce accurate analytical datasets.

* **Secure Credential Management:** Configured the PostgreSQL connection using a `.env` file to securely store database credentials and avoid exposing sensitive information in the notebook.

* **Time-Series Analytics:** Quarterly revenue reporting required transforming text-based month values into SQL date objects before performing date-based aggregations, quarterly grouping, and trend analysis.

## Assumptions Made
* **Data Cutoff Assumption:** Assumed partial data points at the end of the timeline (mid-2025) represent data capture limits rather than true business contractions.

## Project Features

✔ Reusable Analytics Layer

✔ 11 Analytical Views

✔ Chained SQL Pipeline

✔ Advanced SQL (CTEs, Window Functions, Ranking Functions)

✔ Executive KPI Dashboard

✔ Python Dashboard (8+ Visualizations)

✔ Executive Recommendations

✔ Modular Design for Future BI Dashboards

## Python Analytics Notebook

The notebook connects directly to PostgreSQL using SQLAlchemy and reads only the reusable analytical views from the analytics schema using pandas.read_sql(). No raw operational tables are queried within the notebook. Dashboard visualizations are generated exclusively from the analytical reporting layer.
```
week3/day5/
├── README.md
├── analytics_pipeline.sql
├── Executive_analysis.ipynb
├── screenshots/
├── charts/
└── documentation/
```
*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*