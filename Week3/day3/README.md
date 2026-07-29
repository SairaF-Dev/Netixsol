# Advanced SQL: Aggregation, Subqueries, CTEs, and Window Functions

This repository contains SQL solutions for a set of business questions built on the DVD Rental (Pagila) sample database, covering aggregation with `GROUP BY`/`HAVING`, scalar and correlated subqueries, Common Table Expressions (CTEs), and window functions (`RANK()`, `ROW_NUMBER()`, `LAG()`). All queries are in `aggregation_subqueries.sql`, with supporting screenshots of query results in the `screenshots/` folder.

## 1. Concept Explanations: Subqueries vs. CTEs vs. Window Functions

Understanding when to use these different SQL tools is crucial for writing efficient and readable queries:

*   **Subqueries**: Best used for scalar value lookups (e.g., finding an overall average to use in a `WHERE` or `HAVING` clause) or for filtering records using `IN`, `EXISTS`, or `NOT EXISTS`. While powerful, heavily nested subqueries can become difficult to read and maintain.
*   **CTEs (Common Table Expressions)**: Defined using the `WITH` clause, CTEs act as temporary, named result sets that exist only during the execution of a single query. They are best used to improve readability by breaking complex, multi-step logic into sequential, manageable chunks. They also prevent code duplication if you need to reference the same derived data multiple times in the main query.
*   **Window Functions**: Best used when you need to perform calculations across a set of rows related to the current row, **without** collapsing those rows into a single output row (which is what `GROUP BY` does). They are essential for running totals, moving averages, and ranking items within categories (using `PARTITION BY`).

---

## 2. Explanation of Query Logic

Here is how each business question in the SQL script was solved:

### Part 1 — Aggregation Basics
*   **Q1. Total revenue per store**: Joined the `payment`, `staff`, and `store` tables, grouped the results by `store_id`, and used the `SUM()` aggregate function on the payment amounts.
*   **Q2. Average rental duration per category**: Joined `film`, `film_category`, and `category`, grouped by category name, and used `AVG()` on the rental duration, wrapped in a `ROUND()` function to keep it to two decimal places.
*   **Q3. Number of rentals each month**: Used the `DATE_TRUNC()` function to extract the month and year from the `rental_date`, grouped by this derived column, and counted the total rows per group.
*   **Q4. Categories with > 50 films**: Grouped films by category and used the `HAVING` clause to filter out any aggregated groups where the `COUNT()` of `film_id` was 50 or less.

### Part 2 — Subquery Challenges
*   **Q5. Customers spending more than average**: Grouped total spending per customer, then used a `HAVING` clause with a scalar subquery. The subquery calculated the global average of total customer spends to filter the grouped results.
*   **Q6. Highest rental rate per category**: Used a **correlated subquery** in the `WHERE` clause. For each film evaluated in the outer query, the inner query calculates the `MAX(rental_rate)` specifically for that film's category, returning the row if it matches.
*   **Q7. Customers who never rented**: Used a `NOT EXISTS` subquery to look for any matching `customer_id` in the `rental` table. If no match exists, the customer record is returned.
*   **Q8. Store with highest revenue**: Used a subquery in the `FROM` clause to calculate total revenue per store, and filtered it in the `WHERE` clause using another subquery to dynamically find the `MAX(total_revenue)`.

### Part 3 — CTE & Window Function Challenges
*   **Q9. Rank customers by spend within each city**: Built a CTE to aggregate total spend per customer and city. The main query applied the `RANK()` window function, partitioning by `city` and ordering by `total_spent DESC`.
*   **Q10. Most recently rented film per customer**: Used a CTE with the `ROW_NUMBER()` window function partitioned by `customer_id` and ordered by `rental_date DESC`. The outer query filtered for `rn = 1` to isolate the newest rental.
*   **Q11. Month-over-month revenue growth**: Aggregated total revenue by month in a CTE. The outer query used the `LAG()` window function to retrieve the previous month's revenue and applied standard percentage growth math.
*   **Q12. Top 3 grossing films per category**: Aggregated revenue per film inside a CTE and applied the `RANK()` window function partitioned by `category_name`. The outer query filtered the results where the rank was `<= 3`.

### Bonus Challenge
*   **Highest revenue staff per store + percentage**: Grouped revenue by staff and store inside a CTE. Used a window function (`SUM(SUM(amount)) OVER (PARTITION BY store_id)`) to calculate the store's total revenue without collapsing the staff rows. Simultaneously applied `RANK()` to find the top performer. The outer query filtered for the rank 1 staff member and divided their revenue by the windowed store total to get the percentage.

---

## 3. Business Insights

Based on the analysis of the provided query outputs, here are three actionable business insights:

*   **Volatile Month-over-Month Revenue Trends:** Revenue saw a massive surge in March 2007, growing by 186.00% compared to February. It continued to grow by a solid 19.56% in April 2007, reaching a peak of $28,559.46. However, May 2007 experienced a severe drop of -98.20%, netting only $514.18. This extreme drop likely indicates a data cutoff (an incomplete month of data at the time the export was taken) rather than a true business collapse.
*   **Single Points of Failure in Store Operations:** The bonus query reveals a significant operational bottleneck regarding staff payment processing. In Store 1, Mike Hillyer processed $30,252.12, accounting for exactly 100.00% of the store's revenue. Similarly, Jon Stephens processed 100.00% of the $31,059.92 revenue for Store 2. This means each store relies entirely on a single staff member to process payments, indicating a lack of staff overlap or shared register duties.
*   **VIP Customer Loyalty Opportunities:** The query identifying customers spending more than the average highlights top spenders like Eleanor Hunt ($211.55) and Karl Seal ($208.58). Given that standard rental rates hover between $0.99 and $4.99, a customer accumulating over $200 in lifetime spend represents an exceptionally high frequency of return visits. These specific power-users are prime candidates for a targeted loyalty program, VIP perks, or referral incentives to maximize their high lifetime value.

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*