-- Week 7 Day 2 — Production Structured Retrieval Queries
--
-- PostgreSQL is the source of truth for exact property facts.
--
-- These named queries are loaded by postgres_repository.py.
-- Do not execute this file directly as one SQL query.
--
-- Supported queries:
--   1. exact_property
--   2. property_name_lookup
--   3. buyer_search
--   4. availability
--   5. developer_lookup
--   6. cheaper_alternatives
--   7. rental_search

-- ============================================================
-- QUERY: exact_property
-- ============================================================

-- Return one property by exact property ID.
-- Only verified pricing is considered authoritative.

SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.property_type,
    p.bedrooms,
    p.bathrooms,
    p.plot_size,
    p.plot_unit,
    p.covered_area,
    p.covered_area_unit,
    pr.price,
    pr.currency,
    pr.transaction_type,
    pr.price_period,
    pr.verified_on,
    pr.verification_status,
    p.available,
    p.status,
    d.name AS developer_name,
    p.purpose

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

LEFT JOIN developers d
    ON p.developer_id = d.developer_id

WHERE p.property_id = %(property_id)s::text
  AND pr.verification_status = 'Verified';


-- ============================================================
-- QUERY: property_name_lookup
-- ============================================================

-- Return one verified property by exact case-insensitive name.

SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.property_type,
    p.bedrooms,
    p.bathrooms,
    p.plot_size,
    p.plot_unit,
    p.covered_area,
    p.covered_area_unit,
    pr.price,
    pr.currency,
    pr.transaction_type,
    pr.price_period,
    pr.verified_on,
    pr.verification_status,
    p.available,
    p.status,
    d.name AS developer_name,
    p.purpose

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

LEFT JOIN developers d
    ON p.developer_id = d.developer_id

WHERE LOWER(TRIM(p.name))
        = LOWER(TRIM(%(property_name)s::text))
  AND pr.verification_status = 'Verified'

ORDER BY
    p.available DESC,
    pr.verified_on DESC NULLS LAST,
    p.property_id ASC

LIMIT 1;

-- ============================================================
-- QUERY: buyer_search
-- ============================================================

-- Search available properties using structured filters.
--
-- All exact property facts come from PostgreSQL.
--
-- Amenity semantics:
-- If multiple amenities are requested, the property must
-- contain ALL requested amenities.


SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.property_type,
    p.bedrooms,
    p.bathrooms,
    p.covered_area,
    p.covered_area_unit,
    pr.price,
    pr.currency,
    p.available,
    p.status,
    d.name AS developer_name,
    p.purpose,

    COALESCE(
        ARRAY_AGG(DISTINCT a.amenity)
        FILTER (WHERE a.amenity IS NOT NULL),
        '{}'::text[]
    ) AS amenities

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

LEFT JOIN developers d
    ON p.developer_id = d.developer_id

LEFT JOIN amenities a
    ON p.property_id = a.property_id

WHERE p.available = TRUE
  AND pr.verification_status = 'Verified'

  -- Budget
  AND (
        %(budget)s::numeric IS NULL
        OR pr.price <= %(budget)s::numeric
      )

  -- City
  AND (
        %(city)s::text IS NULL
        OR LOWER(l.city) = LOWER(%(city)s::text)
      )

  -- Area
  AND (
        %(area)s::text IS NULL
        OR LOWER(l.area) LIKE LOWER(%(area_pattern)s::text)
      )

  -- Bedrooms
  AND (
        %(bedrooms)s::integer IS NULL
        OR p.bedrooms = %(bedrooms)s::integer
      )

  -- Property type
  AND (
        %(property_type)s::text IS NULL
        OR LOWER(p.property_type)
            = LOWER(%(property_type)s::text)
      )

  -- Purpose
  AND (
        %(purpose)s::text IS NULL
        OR LOWER(p.purpose)
            = LOWER(%(purpose)s::text)
      )

  -- Amenities: ALL requested amenities must exist.
  AND (
        %(amenities)s::text[] IS NULL
        OR NOT EXISTS (
            SELECT 1

            FROM unnest(
                %(amenities)s::text[]
            ) AS requested_amenity

            WHERE NOT EXISTS (
                SELECT 1

                FROM amenities property_amenity

                WHERE property_amenity.property_id
                    = p.property_id

                  AND LOWER(property_amenity.amenity)
                    = LOWER(requested_amenity)
            )
        )
      )

GROUP BY
    p.property_id,
    p.name,
    l.area,
    l.city,
    p.property_type,
    p.bedrooms,
    p.bathrooms,
    p.covered_area,
    p.covered_area_unit,
    pr.price,
    pr.currency,
    p.available,
    p.status,
    d.name,
    p.purpose

ORDER BY
    pr.price ASC,
    p.property_id ASC

LIMIT %(limit)s;


-- ============================================================
-- QUERY: availability
-- ============================================================

-- Return currently available properties with verified prices.

SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.property_type,
    p.bedrooms,
    pr.price,
    pr.currency,
    pr.price_period,
    p.status

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

WHERE p.available = TRUE
  AND pr.verification_status = 'Verified'

  -- Optional city filter
  AND (
        %(city)s::text IS NULL
        OR LOWER(l.city)
            = LOWER(%(city)s::text)
      )

  -- Optional property type filter
  AND (
        %(property_type)s::text IS NULL
        OR LOWER(p.property_type)
            = LOWER(%(property_type)s::text)
      )

ORDER BY
    pr.price ASC;


-- ============================================================
-- QUERY: developer_lookup
-- ============================================================

-- Return developer information associated with a property.

SELECT
    p.property_id,
    p.name AS property_name,
    d.developer_id,
    d.name AS developer_name

FROM properties p

LEFT JOIN developers d
    ON p.developer_id = d.developer_id

WHERE p.property_id = %(property_id)s::text;


-- ============================================================
-- QUERY: cheaper_alternatives
-- ============================================================

-- Return available, verified properties cheaper than
-- the requested budget.
--
-- Results are ordered from highest price below the budget
-- to lowest price, so the closest cheaper alternatives
-- appear first.

SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.bedrooms,
    p.bathrooms,
    p.property_type,
    pr.price,
    pr.currency,
    p.status,
    p.purpose

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

WHERE p.available = TRUE
  AND pr.verification_status = 'Verified'

  -- Optional purpose
  AND (
        %(purpose)s::text IS NULL
        OR LOWER(p.purpose)
            = LOWER(%(purpose)s::text)
      )

  -- Optional city
  AND (
        %(city)s::text IS NULL
        OR LOWER(l.city)
            = LOWER(%(city)s::text)
      )

  -- Optional bedrooms
  AND (
        %(bedrooms)s::integer IS NULL
        OR p.bedrooms
            = %(bedrooms)s::integer
      )

  -- Required budget
  AND pr.price < %(budget)s::numeric

ORDER BY
    pr.price DESC;


-- ============================================================
-- QUERY: rental_search
-- ============================================================

-- Return verified rental properties only.
--
-- Rental records must satisfy both:
--   purpose = Rental
--   transaction_type = Rental

SELECT
    p.property_id,
    p.name AS property_name,
    l.area,
    l.city,
    p.bedrooms,
    p.bathrooms,
    p.property_type,
    pr.price,
    pr.currency,
    pr.price_period,
    p.status

FROM properties p

JOIN locations l
    ON p.location_id = l.location_id

JOIN prices pr
    ON p.property_id = pr.property_id

WHERE p.available = TRUE

  AND LOWER(p.purpose) = 'rental'

  AND pr.transaction_type = 'Rental'

  AND pr.verification_status = 'Verified'

  -- Optional city
  AND (
        %(city)s::text IS NULL
        OR LOWER(l.city)
            = LOWER(%(city)s::text)
      )

  -- Optional bedrooms
  AND (
        %(bedrooms)s::integer IS NULL
        OR p.bedrooms
            = %(bedrooms)s::integer
      )

  -- Optional rental budget
  AND (
        %(budget)s::numeric IS NULL
        OR pr.price <= %(budget)s::numeric
      )

ORDER BY
    pr.price ASC;