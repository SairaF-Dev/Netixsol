# Concept Check 

## 1. Why are multiple CTEs preferred over one large nested query?
* **Readability and Maintainability:** Multiple CTEs break a complex analytical problem into logical, sequential steps (like a data pipeline), making the SQL code much easier to read, debug, and maintain compared to deeply nested subqueries.
* **Reusability:** A CTE acts as a temporary named result set that can be referenced multiple times within the execution scope, avoiding redundant code blocks.
* **Query Optimizer Execution:** Modern database engines like PostgreSQL often optimize CTEs effectively, allowing developers to structure code modularly without sacrificing performance.

## 2. When would you use a window function instead of `GROUP BY`?
* **Preserving Row-Level Detail:** `GROUP BY` collapses multiple rows into a single summary row, causing individual row details to be lost. A window function performs calculations across a set of table rows while **preserving the individual rows and their original details** in the output.
* **Ranking and Partitioning:** Window functions are required when you need to assign ranks, running totals, or moving averages within specific partitions (e.g., finding the top genre per customer) without reducing the dataset to single group summaries.

## 3. Explain the difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()`.
* **`ROW_NUMBER()`:** Assigns a unique sequential integer to each row within a partition, regardless of whether values are tied. If there is a tie, rows receive arbitrary sequential numbers.
* **`RANK()`:** Assigns the same rank to tied values, but leaves **gaps** in the sequence numbers when a tie occurs (e.g., if two rows tie for rank 1, the next rank is 3).
* **`DENSE_RANK()`:** Assigns the same rank to tied values **without gaps** in the sequence (e.g., if two rows tie for rank 1, the next rank is immediately 2).

## 4. What is conditional aggregation?
* **Definition:** The practice of applying aggregate functions (like `SUM`, `COUNT`, or `AVG`) selectively to subsets of data using conditional logic (such as `FILTER (WHERE ...)` or `CASE WHEN` statements inside the aggregate).
* **Use Case:** It allows you to calculate multiple metrics across different conditions in a single query pass without requiring multiple self-joins or separate subqueries.

## 5. How does `CASE WHEN` improve analytical reporting?
* **Categorization and Segmentation:** It allows raw numeric metrics (such as spending totals, purchase frequency, and diversity counts) to be translated into meaningful business tiers like Platinum, Gold, Silver, and Bronze.
* **Dynamic Mapping:** It helps map complex business rules, custom marketing actions, or conditional labeling directly inside the SQL output for executive dashboards.

## 6. Why should SQL queries be broken into logical stages?
* **Incremental Verification:** Breaking queries into stages (profiles $\rightarrow$ segments $\rightarrow$ rankings) allows you to test and validate the data output at each step of the pipeline.
* **Debugging Ease:** If an error occurs or metrics look incorrect, you can isolate which specific CTE or stage introduced the discrepancy rather than combing through a massive monolithic query.

## 7. What makes a SQL query maintainable?
* **Clean Formatting and Aliasing:** Using consistent capitalization, clear indentation, and intuitive table/column aliases (`AS customer_name`).
* **Modular Structure:** Relying on CTEs to separate concerns so that future developers can update individual business rules (like changing a segmentation threshold) without rewriting the entire query.
* **Documentation:** Adding inline comments explaining *why* specific calculations or weightings were chosen.