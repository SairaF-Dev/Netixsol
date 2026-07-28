-- List every table and its primary and foreign key columns
SELECT tc.table_schema,
       tc.table_name,
       kcu.column_name,
       CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN tc.constraint_type END AS primary_key,
       CASE WHEN tc.constraint_type = 'FOREIGN KEY' THEN tc.constraint_type END AS foreign_key
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;


-- 1.Display Customer Name, Email, City, and Country.
SELECT
    c.first_name || ' ' || c.last_name AS customer_name,
    c.email,
    ci.city,
    co.country
FROM customer c
INNER JOIN address a ON c.address_id = a.address_id
INNER JOIN city ci   ON a.city_id     = ci.city_id
INNER JOIN country co ON ci.country_id = co.country_id

-- 2.Display every payment with Customer Name, Film Title, and Amount Paid.   payment → rental → inventory → film
SELECT 
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    f.title AS film_title,
    p.amount AS amount_paid
FROM payment p
INNER JOIN customer c ON p.customer_id = c.customer_id
INNER JOIN rental r ON p.rental_id = r.rental_id
INNER JOIN inventory i ON r.inventory_id = i.inventory_id
INNER JOIN film f ON i.film_id = f.film_id;

-- 3. Every payment with Customer Name, Film Title, and Amount Paid
SELECT 
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    f.title AS film_title,
    p.amount AS amount_paid
FROM payment p
INNER JOIN customer c ON p.customer_id = c.customer_id
INNER JOIN rental r ON p.rental_id = r.rental_id
INNER JOIN inventory i ON r.inventory_id = i.inventory_id
INNER JOIN film f ON i.film_id = f.film_id;

-- 4.Find the Top 10 customers based on total amount spent.
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    SUM(p.amount) AS total_spent
FROM customer c
INNER JOIN payment p ON c.customer_id = p.customer_id
GROUP BY c.customer_id, customer_name
ORDER BY total_spent DESC
LIMIT 10;


-- 5.Display each film with its Category and Rental Rate.
SELECT
    f.title,
    cat.name AS category,
    f.rental_rate
FROM film f
INNER JOIN film_category fc ON f.film_id = fc.film_id
INNER JOIN category cat     ON fc.category_id = cat.category_id
ORDER BY f.title;


-- 6.Find all actors who appeared in each film.
SELECT 
    f.title AS film_title,
    CONCAT(a.first_name, ' ', a.last_name) AS actor_name
FROM film f
INNER JOIN film_actor fa ON f.film_id = fa.film_id
INNER JOIN actor a ON fa.actor_id = a.actor_id
ORDER BY f.title, actor_name;


-- 7.Count how many films belong to each category.
SELECT 
    c.name AS category_name,
    COUNT(fc.film_id) AS film_count
FROM category c
LEFT JOIN film_category fc ON c.category_id = fc.category_id
GROUP BY c.category_id, c.name
ORDER BY film_count DESC;

-- 8.Which categories generated the highest revenue? (Hint: This requires joining multiple tables.)
SELECT
    cat.name AS category,
    SUM(p.amount) AS total_revenue
FROM payment p
INNER JOIN rental r     ON p.rental_id    = r.rental_id
INNER JOIN inventory i  ON r.inventory_id = i.inventory_id
INNER JOIN film f       ON i.film_id      = f.film_id
INNER JOIN film_category fc ON f.film_id  = fc.film_id
INNER JOIN category cat ON fc.category_id = cat.category_id
GROUP BY cat.name
ORDER BY total_revenue DESC;

-- 9.Find customers who have rented more than 20 films.
SELECT 
CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
COUNT(r.rental_id) AS films_rented
FROM customer c
JOIN rental r ON c.customer_id = r.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING COUNT(r.rental_id) > 20

-- 10. Which cities generated the highest rental revenue?
SELECT 
    ci.city,
    co.country,
    SUM(p.amount) AS total_revenue
FROM city ci
INNER JOIN country co ON ci.country_id = co.country_id
INNER JOIN address a ON ci.city_id = a.city_id
INNER JOIN customer c ON a.address_id = c.address_id
INNER JOIN payment p ON c.customer_id = p.customer_id
GROUP BY ci.city_id, ci.city, co.country
ORDER BY total_revenue DESC;


-- Bonus Challenge
-- Without looking at any online solution,
-- Determine the shortest path of table joins needed to answer:
-- Which actor has generated the highest total rental revenue?
-- There is no direct relationship between actor and payment, so students must identify the intermediate tables themselves.
-- actor → film_actor → film → inventory → rental → payment
SELECT 
CONCAT(a.first_name, ' ', a.last_name) AS actor_name, 
SUM(p.amount) as total_revenue from actor as a
JOIN film_actor as fa on a.actor_id = fa.actor_id
JOIN film as f on fa.film_id = f.film_id
JOIN inventory as i on f.film_id = i.film_id
JOIN rental as r on i.inventory_id = r.inventory_id
JOIN payment as p on r.rental_id = p.rental_id
GROUP BY a.first_name, a.last_name, a.actor_id
ORDER BY total_revenue DESC

