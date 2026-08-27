-- Exact property lookup
SELECT
    property_id,
    name,
    price,
    currency,
    available,
    status
FROM properties
WHERE property_id = %(property_id)s;


-- Buyer property search
SELECT
    property_id,
    name,
    area,
    city,
    property_type,
    bedrooms,
    bathrooms,
    price,
    currency,
    available,
    status,
    developer,
    purpose
FROM properties
WHERE available = TRUE
  AND purpose = %(purpose)s
  AND (%(city)s IS NULL OR LOWER(city) = LOWER(%(city)s))
  AND (%(area)s IS NULL OR LOWER(area) LIKE LOWER(%(area_pattern)s))
  AND (%(bedrooms)s IS NULL OR bedrooms = %(bedrooms)s)
  AND (%(property_type)s IS NULL OR LOWER(property_type) = LOWER(%(property_type)s))
  AND (%(budget)s IS NULL OR price <= %(budget)s)
ORDER BY price ASC;


-- Cheaper alternatives
SELECT
    property_id,
    name,
    area,
    bedrooms,
    price,
    currency
FROM properties
WHERE available = TRUE
  AND purpose = %(purpose)s
  AND (%(city)s IS NULL OR LOWER(city) = LOWER(%(city)s))
  AND (%(bedrooms)s IS NULL OR bedrooms = %(bedrooms)s)
  AND price < %(budget)s
ORDER BY price DESC;


-- Rental search
SELECT
    property_id,
    name,
    area,
    bedrooms,
    price,
    currency
FROM properties
WHERE available = TRUE
  AND purpose = 'Rental'
  AND (%(city)s IS NULL OR LOWER(city) = LOWER(%(city)s))
  AND (%(bedrooms)s IS NULL OR bedrooms = %(bedrooms)s)
  AND price <= %(budget)s
ORDER BY price DESC;