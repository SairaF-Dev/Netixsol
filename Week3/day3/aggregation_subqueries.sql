-- Part 1 — Aggregation Basics

-- 1. Find the total revenue generated per store.
-- payment → staff → store
SELECT
    s.store_id,
    SUM(p.amount) AS total_revenue
FROM payment p
JOIN staff st ON p.staff_id = st.staff_id
JOIN store s  ON st.store_id = s.store_id
GROUP BY s.store_id
ORDER BY s.store_id;

-- 2. Find the average rental duration per film category.
SELECT
    c.name AS category,
    ROUND(AVG(f.rental_duration), 2) AS avg_rental_duration
FROM film f
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
GROUP BY c.name
ORDER BY avg_rental_duration DESC;

-- 3. Find the number of rentals made each month.
SELECT
    DATE_TRUNC('month', rental_date)::DATE AS rental_month,
    COUNT(*) AS total_rentals
FROM rental
GROUP BY rental_month
ORDER BY rental_month;

-- 4. Find categories with more than 50 films (use HAVING).
SELECT
    c.name AS category,
    COUNT(fc.film_id) AS film_count
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
GROUP BY c.name
HAVING COUNT(fc.film_id) > 50
ORDER BY film_count DESC;

-- Part 2 — Subquery Challenges

-- 5. Find customers who spent more than the average customer spend.
SELECT 
    p.customer_id, 
    c.first_name || ' ' || c.last_name AS customer_name, 
    SUM(p.amount) AS total_spent
FROM payment p
JOIN customer c ON p.customer_id = c.customer_id
GROUP BY 
    p.customer_id, 
    c.first_name, 
    c.last_name
HAVING SUM(p.amount) > (
    SELECT AVG(customer_total)
    FROM (
        SELECT SUM(amount) AS customer_total
        FROM payment
        GROUP BY customer_id
    ) AS per_customer
)
ORDER BY 
    total_spent DESC;

-- 6. Find the film(s) with the highest rental rate in each category (use a correlated subquery).
SELECT 
    c.name AS category_name, 
    f.title AS film_title, 
    f.rental_rate
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
JOIN film f ON fc.film_id = f.film_id
WHERE f.rental_rate = (
    -- Correlated subquery: calculates the max rental rate for the current category
    SELECT MAX(f2.rental_rate)
    FROM film f2
    JOIN film_category fc2 ON f2.film_id = fc2.film_id
    WHERE fc2.category_id = c.category_id
)
ORDER BY 
    c.name, 
    f.title;

-- 7. Find customers who have never rented a film (use NOT IN / NOT EXISTS).
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name
FROM customer c
WHERE NOT EXISTS (
    SELECT 1
    FROM rental r
    WHERE r.customer_id = c.customer_id
);

-- 8. Find the store with the highest total revenue using a subquery in the WHERE clause.
SELECT store_id, total_revenue
FROM (
    SELECT
        s.store_id,
        SUM(p.amount) AS total_revenue
    FROM payment p
    JOIN staff st ON p.staff_id = st.staff_id
    JOIN store s  ON st.store_id = s.store_id
    GROUP BY s.store_id
) AS store_revenue
WHERE total_revenue = (
    SELECT MAX(total_revenue)
    FROM (
        SELECT
            s.store_id,
            SUM(p.amount) AS total_revenue
        FROM payment p
        JOIN staff st ON p.staff_id = st.staff_id
        JOIN store s  ON st.store_id = s.store_id
        GROUP BY s.store_id
    ) AS all_store_revenue);

-- Part 3 — CTE & Window Function Challenges

-- 9. Using a CTE, rank customers by total spend within each city.
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        ci.city,
        SUM(p.amount) AS total_spent
    FROM customer c
    JOIN address a ON c.address_id = a.address_id
    JOIN city ci    ON a.city_id = ci.city_id
    JOIN payment p  ON c.customer_id = p.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, ci.city
)
SELECT
    customer_id,
    customer_name,
    city,
    total_spent,
    RANK() OVER (PARTITION BY city ORDER BY total_spent DESC) AS spend_rank_in_city
FROM customer_spend
ORDER BY city, spend_rank_in_city;

-- 10. Using ROW_NUMBER(), find the most recently rented film for each customer.
WITH RankedRentals AS (
    SELECT 
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        f.title AS film_title,
        r.rental_date,
        ROW_NUMBER() OVER (PARTITION BY c.customer_id ORDER BY r.rental_date DESC) AS rn
    FROM customer c
    JOIN rental r ON c.customer_id = r.customer_id
    JOIN inventory i ON r.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
)
SELECT 
    customer_id,
    customer_name,
    film_title,
    rental_date
FROM RankedRentals
WHERE rn = 1
ORDER BY 
    customer_id;

-- 11. Using a CTE, calculate month-over-month rental revenue growth.
WITH MonthlyRevenue AS (
    -- Calculate total revenue for each month
    SELECT 
        TO_CHAR(payment_date, 'YYYY-MM') AS payment_month, 
        SUM(amount) AS current_revenue
    FROM payment
    GROUP BY 
        TO_CHAR(payment_date, 'YYYY-MM')
)
SELECT 
    payment_month,
    current_revenue,
    LAG(current_revenue) OVER (ORDER BY payment_month) AS previous_revenue,
    ROUND(
        (current_revenue - LAG(current_revenue) OVER (ORDER BY payment_month)) 
        / LAG(current_revenue) OVER (ORDER BY payment_month) * 100, 
    2) AS mom_growth_percentage
FROM MonthlyRevenue
ORDER BY 
    payment_month;

-- 12. Find the top 3 highest-grossing films per category using RANK() inside a CTE.
WITH FilmRevenue AS (
    SELECT 
        c.name AS category_name,
        f.title AS film_title,
        SUM(p.amount) AS total_revenue,
        RANK() OVER (PARTITION BY c.name ORDER BY SUM(p.amount) DESC) AS revenue_rank
    FROM category c
    JOIN film_category fc ON c.category_id = fc.category_id
    JOIN film f ON fc.film_id = f.film_id
    JOIN inventory i ON f.film_id = i.film_id
    JOIN rental r ON i.inventory_id = r.inventory_id
    JOIN payment p ON r.rental_id = p.rental_id
    GROUP BY 
        c.name, 
        f.title
)
SELECT 
    category_name,
    film_title,
    total_revenue,
    revenue_rank
FROM FilmRevenue
WHERE revenue_rank <= 3
ORDER BY 
    category_name, 
    revenue_rank;

-- Bonus Challenge

-- write a single query (using CTEs) that finds: Which staff member processed the highest revenue in each store,
-- and what percentage of that store's total revenue did they contribute? 
-- This requires combining aggregation, a CTE, and a percentage calculation in the same query.
WITH StaffStoreRevenue AS (
    SELECT 
        s.store_id,
        s.first_name || ' ' || s.last_name AS staff_name,
        SUM(p.amount) AS staff_revenue,
        -- Window function to calculate the total store revenue across all staff in that store
        SUM(SUM(p.amount)) OVER (PARTITION BY s.store_id) AS store_total_revenue,
        -- Rank staff members within each store based on their revenue
        RANK() OVER (PARTITION BY s.store_id ORDER BY SUM(p.amount) DESC) AS revenue_rank
    FROM payment p
    JOIN staff s ON p.staff_id = s.staff_id
    GROUP BY 
        s.store_id, 
        p.staff_id, 
        s.first_name, 
        s.last_name
)
SELECT 
    store_id,
    staff_name,
    staff_revenue AS highest_staff_revenue,
    ROUND((staff_revenue / store_total_revenue) * 100, 2) AS contribution_percentage
FROM StaffStoreRevenue
WHERE revenue_rank = 1;








