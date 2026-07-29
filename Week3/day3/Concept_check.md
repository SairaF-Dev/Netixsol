## Concept Check

**1. What is the difference between WHERE and HAVING?**
`WHERE` filters individual rows *before* grouping happens, and can't reference aggregate functions. `HAVING` filters *groups* after `GROUP BY` has run, and is used specifically to filter on aggregate values like `COUNT()` or `SUM()`.

**2. When would you use a correlated subquery instead of a JOIN?**
A correlated subquery is useful when you need a per-row comparison against a dynamically calculated value that depends on that same row (e.g., "find the film with the highest rental rate in its own category"). It's often more readable than an equivalent JOIN when the logic is "compare this row against an aggregate scoped to itself," though it can be less performant on large datasets since it re-executes once per outer row.

**3. What is a CTE, and why is it more readable than a nested subquery?**
A CTE (`WITH name AS (...)`) is a named, temporary result set defined at the top of a query and referenced later in the same query. It's more readable than a nested subquery because it breaks complex logic into clearly labeled, sequential steps instead of deeply nested brackets, and it can be reused multiple times or chained into other CTEs.

**4. Explain the difference between RANK() and DENSE_RANK().**
Both assign the same rank to tied values, but `RANK()` leaves a gap in the ranking sequence after a tie (1, 2, 2, 4), while `DENSE_RANK()` does not skip any numbers (1, 2, 2, 3).

**5. What does PARTITION BY do differently from GROUP BY?**
`GROUP BY` collapses multiple rows into one row per group. `PARTITION BY` (used inside window functions) divides rows into groups for calculation purposes but keeps every individual row in the output, just adding a computed column based on its group.

**6. Can a subquery return multiple rows? What operator would you use in that case?**
Yes. If a subquery can return multiple rows, you can't use `=`; instead use `IN`, `NOT IN`, `ANY`, `ALL`, `EXISTS`, or `NOT EXISTS` depending on the logic needed.

**7. Give an example of when CASE WHEN is useful inside an aggregate function.**
`CASE WHEN` inside `SUM()` or `COUNT()` allows conditional aggregation in a single query. for example, `SUM(CASE WHEN rating = 'R' THEN 1 ELSE 0 END)` counts only rows meeting a condition, letting you compute multiple conditional totals without writing separate queries.