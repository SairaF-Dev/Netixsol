# Concept Check 

**1. What problem does SQL solve that CSV files cannot?**

CSV/Excel files are hard to search and edit manually once they get large. They also have a concurrency problem: if two people work on separate copies ("snapshots") of a file and both save, whoever saves last silently overwrites the other person's changes, causing accidental data loss with no warning. Excel also has a hard row limit (~1,048,576 rows) and loads the entire file into RAM when opened, which can slow down or crash the system with large datasets. SQL solves these problems because: (1) commands target only the specific field being changed, not the whole file, so simultaneous edits to different fields don't overwrite each other; (2) data stays on disk, and only the specific rows a query asks for are loaded into RAM, so there's no row limit and no need to load the whole dataset just to view a few records. This makes SQL more reliable (no accidental data loss) and more scalable for large datasets.

**2. What is the difference between a database table and a spreadsheet?**

In Excel, all data typically sits in one sheet (e.g., customer info and order info together), which causes redundancy since the same customer details get repeated across many rows. In a SQL database, data is organized into separate, related tables (e.g., a Customers table and an Orders table) linked by Primary Keys and Foreign Keys, which eliminates redundancy. Excel also has the concurrency problem described above (whole-file overwrites), while databases only update the specific data targeted by a command, keeping data reliable. Databases also only load query-relevant data into RAM (rather than the whole file), so they scale to much larger datasets without performance issues.

**3. What is a Primary Key?**

A Primary Key is one or more columns that uniquely identify each row in a table. It has two core rules: it must be unique (no two rows can share the same Primary Key value), and it cannot be NULL (a row with no identity can't be referenced by other tables via a Foreign Key). When a single column isn't enough to guarantee uniqueness, two or more columns can be combined into a Composite Primary Key (e.g., StudentID + CourseID in an Enrollments table, where neither column alone is unique but the combination is).

Example — `Customers` table:

| CustomerID (PK) | Name  | Email        |
|------------------|-------|--------------|
| 1                | Ali   | ali@x.com    |
| 2                | Sara  | saira@x.com   |

`CustomerID` is the Primary Key here — every value is unique and never NULL, so it uniquely identifies each customer.

**4. What is a Foreign Key?**

A Foreign Key is a column in one table whose values reference the Primary Key of another table. It establishes a relationship between the two tables, showing which row in one table a row in another table belongs to (e.g., a CustomerID column in an Orders table pointing back to the CustomerID Primary Key in a Customers table). Unlike a Primary Key, a Foreign Key's value can repeat across multiple rows (a customer can have many orders), and this relationship is what allows related data to be split across multiple tables without redundancy.

Example — `Orders` table:

| OrderID (PK) | CustomerID (FK) | OrderItem | Price |
|--------------|------------------|-----------|-------|
| 101          | 1                | Laptop    | 50000 |
| 102          | 1                | Mouse     | 1000  |
| 103          | 2                | Keyboard  | 2000  |

Here, `CustomerID` is a Foreign Key referencing the `CustomerID` Primary Key in the `Customers` table above. Notice `CustomerID = 1` repeats (Ali has two orders) — that's fine for a Foreign Key, since only Primary Keys must be unique.

**5. What is the difference between WHERE and HAVING?**

WHERE filters individual rows before any grouping or aggregation happens, working on raw table data. HAVING filters after GROUP BY has aggregated the data, working on the results of aggregate functions (like SUM, COUNT, AVG). For example, `WHERE sales > 100` filters individual order rows, while `HAVING SUM(sales) > 10000` filters entire groups (like regions) based on their total sales.

**6. What is the difference between ORDER BY and GROUP BY?**

ORDER BY sorts the final result set in ascending or descending order, without changing how many rows you get, just their sequence. GROUP BY combines multiple rows into summary groups based on shared column values (like grouping all orders by region), typically used together with aggregate functions to calculate totals per group.

**7. What does DISTINCT do?**

DISTINCT removes duplicate rows from the result, returning only unique values. For example, `SELECT DISTINCT region FROM superstore_sales` would return each region name only once, even if hundreds of orders share the same region.

**8. When should you use LIMIT?**

LIMIT restricts the number of rows returned by a query. It's used when you only need a preview or sample of data (like checking the first 10 rows to verify a table loaded correctly), or when working with very large tables where returning millions of rows would be slow and unnecessary.

**9. What are aggregate functions?**

Aggregate functions perform a calculation across multiple rows and return a single summary value. Common ones: COUNT() (number of rows), SUM() (total), AVG() (average), MIN() (smallest value), MAX() (largest value). They're often paired with GROUP BY to get per-group summaries.

**10. Why do Data Scientists prefer databases over Excel for large datasets?**

Because databases don't load the entire dataset into RAM; they query only the relevant rows from disk, so they scale to millions/billions of rows without crashing. Databases also avoid Excel's row limit (~1 million), prevent accidental data loss from whole-file overwrites (since updates target specific fields, not the entire file), and enforce data integrity through constraints (Primary Keys, NOT NULL, CHECK) that Excel has no equivalent for.
