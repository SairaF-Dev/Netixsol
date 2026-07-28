# Concept Check — SQL Joins & Relational Database Analysis

**1. Why do relational databases split data into multiple tables?**

To avoid storing the same fact more than once. If every rental row repeated
the customer's full address, an address typo would need fixing in
thousands of rows. Splitting data into `customer`, `address`, `city`,
`country` etc. means each fact lives in exactly one place, and tables are
linked by keys instead of duplicated text.

**2. Difference between INNER JOIN and LEFT JOIN.**

`INNER JOIN` returns only the rows that have a match in *both* tables — if
a customer has never made a payment, that customer disappears from an
`INNER JOIN` between `customer` and `payment`. `LEFT JOIN` keeps every row
from the left (first) table regardless of whether a match exists on the
right; unmatched columns come back as `NULL`. Use `LEFT JOIN` when you need
to know about rows that *might not* have a related record.

**3. When would you use a FULL OUTER JOIN?**

When you need every row from *both* tables, matched where possible and
`NULL`-padded where not — useful for finding mismatches in both directions
at once, e.g., "films that were never rented" AND "rentals whose film
record is missing," in a single result set.

**4. Why are Primary Keys and Foreign Keys important?**

A primary key guarantees every row in a table is uniquely identifiable and
never duplicated. A foreign key links a row in one table to the correct
row in another, and the database enforces that the link is valid (you
can't insert a rental for a customer_id that doesn't exist). Together
they're what make JOINs reliable.

**5. Explain normalization in simple words.**

Normalization is the process of organizing tables so each piece of
information is stored once, in the table it logically belongs to, and
related tables are connected by keys instead of repeated data. It reduces
duplicate data and prevents update anomalies.

**6. What is an ER Diagram?**

An Entity-Relationship diagram is a visual map of a database: each table
is an "entity" box listing its columns, and lines between boxes show how
tables relate (one-to-one, one-to-many, many-to-many) via their primary
and foreign keys.

**7. What happens if a JOIN condition is incorrect?**

Wrong or missing join conditions cause either a cartesian product (every
row in table A matched with every row in table B, producing a huge,
meaningless result), or rows silently matched to the wrong related row,
giving numbers that look plausible but are factually wrong. Both are
dangerous because the query still "runs" without an error.
