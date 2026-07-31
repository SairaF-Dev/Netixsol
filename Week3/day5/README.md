# Enterprise Analytics & Reporting Layer

## Database Overview
The source enterprise database (`Adventureworks`) is optimized for daily transactional processing (OLTP). To facilitate fast business reporting without repeatedly querying raw operational tables, a dedicated `analytics` schema was created to host structured views and aggregated data marts.

## Analytics Architecture
The project follows a Modern Data Stack pipeline approach with a strict dependency chain:
1. **Raw Operational Tables:** Source transactional data across sales, production, person, and purchasing domains.
2. **Intermediate Marts & Business Metrics:** Domain-specific transformations combining multiple business domains (`analytics.vw_sales_fact`, `analytics.vw_customer_analytics`, `analytics.vw_product_analytics`).
3. **Advanced Analytical Views:** Chained CTEs, window functions, ranking functions, and RFM customer segmentation.
4. **Executive Reporting Layer (`analytics.*`):** Final aggregated views powering both business intelligence dashboards and the Python analytics notebook.

## Intermediate Tables Created
* `analytics.vw_sales_fact` — Unified sales transaction fact table.
* `analytics.vw_customer_analytics` — Customer-level aggregation tracking total orders, revenue, and average order value.
* `analytics.vw_product_analytics` — Product performance, revenue contribution, and profit margins.
* `analytics.vw_monthly_revenue` — Time-series revenue trend with window functions for MoM growth and moving averages.
* `analytics.vw_customer_segments` — RFM-based customer behavioral segmentation (Champions, At Risk, Loyal, etc.).
* `analytics.vw_product_rankings` — Product rankings across overall sales and category sub-groups.
* `analytics.vw_employee_analytics` — Salesperson performance tracking against quotas and revenue share.
* `analytics.vw_territory_analytics` — Regional revenue and customer distribution breakdowns.
* `analytics.vw_inventory_purchasing_analytics` — Stock health and supplier performance metrics.
* `analytics.vw_executive_kpi_summary` — Single-row high-level company performance summary.

## SQL Design Decisions
* **Pipeline Chaining:** Views build sequentially upon previous analytical layers to avoid redundant calculations.
* **Window Functions:** Utilized `LAG()`, `RANK()`, `DENSE_RANK()`, and `NTILE()` for revenue growth tracking and segmentation.
* **Performance Optimization:** Pre-aggregating metrics into schema views ensures that downstream tools (like Python/Pandas or future BI dashboards) execute queries instantly without straining operational tables.

## Challenges Faced
* **Database Schema Complexity:** Navigating multiple enterprise schemas required careful relational mapping via inner and left joins.
* **Special Character Handling:** Managed connection string parsing issues for secure database authentication in Python where special characters like `@` appeared in passwords.

## Assumptions Made
* **Data Cutoff Assumption:** Assumed partial data points at the end of the timeline (mid-2025) represent data capture limits rather than true business contractions.

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*