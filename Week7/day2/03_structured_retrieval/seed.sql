
-- ============================================================
-- Week 7 Day 2  Load verified CSV knowledge base into PostgreSQL
-- ============================================================
--
-- PostgreSQL is the source of truth for structured retrieval.

-- Command:
-- psql "$DATABASE_URL" -f ".\03_structured_retrieval\seed.sql"
--
-- ============================================================

BEGIN;

-- ============================================================
-- STAGING TABLES
-- ============================================================

CREATE TEMP TABLE stg_locations (
    location_id TEXT,
    area TEXT,
    city TEXT,
    zone TEXT,
    classification TEXT,
    region TEXT
);

CREATE TEMP TABLE stg_developers (
    developer_id TEXT,
    name TEXT,
    projects TEXT,
    specialization TEXT,
    area TEXT,
    status TEXT
);

CREATE TEMP TABLE stg_properties (
    property_id TEXT,
    name TEXT,
    location_id TEXT,
    area TEXT,
    city TEXT,
    property_type TEXT,
    bedrooms TEXT,
    bathrooms TEXT,
    plot_size TEXT,
    plot_unit TEXT,
    covered_area TEXT,
    covered_area_unit TEXT,
    available TEXT,
    status TEXT,
    developer_id TEXT,
    purpose TEXT
);

CREATE TEMP TABLE stg_prices (
    property_id TEXT,
    price TEXT,
    currency TEXT,
    transaction_type TEXT,
    price_period TEXT,
    verified_on TEXT,
    verification_status TEXT
);

CREATE TEMP TABLE stg_amenities (
    property_id TEXT,
    amenity TEXT,
    details TEXT
);

CREATE TEMP TABLE stg_schools (
    school_id TEXT,
    name TEXT,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km TEXT,
    reference_property TEXT
);

CREATE TEMP TABLE stg_hospitals (
    hospital_id TEXT,
    name TEXT,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km TEXT,
    reference_property TEXT
);

CREATE TEMP TABLE stg_payment_plans (
    property_id TEXT,
    plan_name TEXT,
    summary TEXT,
    notes TEXT,
    status TEXT
);

CREATE TEMP TABLE stg_faqs (
    faq_id TEXT,
    question TEXT,
    answer TEXT,
    category TEXT,
    status TEXT,
    source TEXT
);

CREATE TEMP TABLE stg_agents (
    agent_id TEXT,
    name TEXT,
    phone TEXT,
    email TEXT,
    city TEXT,
    area TEXT,
    specialization TEXT,
    status TEXT
);

-- IMPORTANT:
-- agent_properties.csv contains 4 columns.
CREATE TEMP TABLE stg_agent_properties (
    agent_id TEXT,
    property_id TEXT,
    assignment_type TEXT,
    assigned_on TEXT
);

-- ============================================================
-- LOAD CSV FILES
-- ============================================================

\copy stg_locations FROM '01_knowledge_base/locations.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_developers FROM '01_knowledge_base/developers.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_properties FROM '01_knowledge_base/properties.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_prices FROM '01_knowledge_base/prices.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_amenities FROM '01_knowledge_base/amenities.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_schools FROM '01_knowledge_base/schools.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_hospitals FROM '01_knowledge_base/hospitals.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_payment_plans FROM '01_knowledge_base/payment_plans.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_faqs FROM '01_knowledge_base/faqs.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_agents FROM '01_knowledge_base/agents.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

\copy stg_agent_properties FROM '01_knowledge_base/agent_properties.csv' WITH (FORMAT csv, HEADER true, NULL 'NA');

-- ============================================================
-- LOCATIONS
-- ============================================================

INSERT INTO locations (
    location_id,
    area,
    city,
    zone,
    classification,
    region
)
SELECT
    TRIM(location_id),
    TRIM(area),
    TRIM(city),
    NULLIF(TRIM(zone), ''),
    NULLIF(TRIM(classification), ''),
    NULLIF(TRIM(region), '')
FROM stg_locations
WHERE NULLIF(TRIM(location_id), '') IS NOT NULL

ON CONFLICT (location_id)
DO UPDATE SET
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    zone = EXCLUDED.zone,
    classification = EXCLUDED.classification,
    region = EXCLUDED.region;

-- ============================================================
-- DEVELOPERS
-- ============================================================

INSERT INTO developers (
    developer_id,
    name,
    projects,
    specialization,
    area,
    status
)
SELECT
    TRIM(developer_id),
    TRIM(name),
    NULLIF(TRIM(projects), ''),
    NULLIF(TRIM(specialization), ''),
    NULLIF(TRIM(area), ''),
    TRIM(status)
FROM stg_developers
WHERE NULLIF(TRIM(developer_id), '') IS NOT NULL

ON CONFLICT (developer_id)
DO UPDATE SET
    name = EXCLUDED.name,
    projects = EXCLUDED.projects,
    specialization = EXCLUDED.specialization,
    area = EXCLUDED.area,
    status = EXCLUDED.status;

-- ============================================================
-- PROPERTIES
-- ============================================================

INSERT INTO properties (
    property_id,
    name,
    location_id,
    property_type,
    bedrooms,
    bathrooms,
    plot_size,
    plot_unit,
    covered_area,
    covered_area_unit,
    available,
    status,
    developer_id,
    purpose
)
SELECT
    TRIM(property_id),
    TRIM(name),
    TRIM(location_id),
    TRIM(property_type),

    NULLIF(TRIM(bedrooms), '')::INTEGER,

    NULLIF(TRIM(bathrooms), '')::INTEGER,

    NULLIF(TRIM(plot_size), '')::NUMERIC,

    NULLIF(TRIM(plot_unit), ''),

    NULLIF(TRIM(covered_area), '')::NUMERIC,

    NULLIF(TRIM(covered_area_unit), ''),

    CASE LOWER(TRIM(available))
        WHEN 'yes' THEN TRUE
        WHEN 'true' THEN TRUE
        WHEN 'no' THEN FALSE
        WHEN 'false' THEN FALSE
        ELSE TRUE
    END,

    TRIM(status),

    NULLIF(TRIM(developer_id), ''),

    TRIM(purpose)

FROM stg_properties

WHERE NULLIF(TRIM(property_id), '') IS NOT NULL

ON CONFLICT (property_id)
DO UPDATE SET
    name = EXCLUDED.name,
    location_id = EXCLUDED.location_id,
    property_type = EXCLUDED.property_type,
    bedrooms = EXCLUDED.bedrooms,
    bathrooms = EXCLUDED.bathrooms,
    plot_size = EXCLUDED.plot_size,
    plot_unit = EXCLUDED.plot_unit,
    covered_area = EXCLUDED.covered_area,
    covered_area_unit = EXCLUDED.covered_area_unit,
    available = EXCLUDED.available,
    status = EXCLUDED.status,
    developer_id = EXCLUDED.developer_id,
    purpose = EXCLUDED.purpose;

-- ============================================================
-- PRICES
-- ============================================================

INSERT INTO prices (
    property_id,
    price,
    currency,
    transaction_type,
    price_period,
    verified_on,
    verification_status
)
SELECT
    TRIM(property_id),
    TRIM(price)::NUMERIC,
    TRIM(currency),
    TRIM(transaction_type),
    TRIM(price_period),
    NULLIF(TRIM(verified_on), '')::DATE,
    TRIM(verification_status)

FROM stg_prices

WHERE NULLIF(TRIM(property_id), '') IS NOT NULL

ON CONFLICT (property_id)
DO UPDATE SET
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    transaction_type = EXCLUDED.transaction_type,
    price_period = EXCLUDED.price_period,
    verified_on = EXCLUDED.verified_on,
    verification_status = EXCLUDED.verification_status;

-- ============================================================
-- AMENITIES
-- ============================================================

INSERT INTO amenities (
    property_id,
    amenity,
    details
)
SELECT
    TRIM(property_id),
    TRIM(amenity),
    NULLIF(TRIM(details), '')
FROM stg_amenities

WHERE NULLIF(TRIM(property_id), '') IS NOT NULL
  AND NULLIF(TRIM(amenity), '') IS NOT NULL

ON CONFLICT (property_id, amenity)
DO UPDATE SET
    details = EXCLUDED.details;

-- ============================================================
-- SCHOOLS
-- ============================================================

INSERT INTO schools (
    school_id,
    name,
    area,
    city,
    type,
    distance_km,
    reference_property
)
SELECT
    TRIM(school_id),
    TRIM(name),
    NULLIF(TRIM(area), ''),
    NULLIF(TRIM(city), ''),
    NULLIF(TRIM(type), ''),
    NULLIF(TRIM(distance_km), '')::NUMERIC,
    NULLIF(TRIM(reference_property), '')
FROM stg_schools

WHERE NULLIF(TRIM(school_id), '') IS NOT NULL

ON CONFLICT (school_id)
DO UPDATE SET
    name = EXCLUDED.name,
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    type = EXCLUDED.type,
    distance_km = EXCLUDED.distance_km,
    reference_property = EXCLUDED.reference_property;

-- ============================================================
-- HOSPITALS
-- ============================================================

INSERT INTO hospitals (
    hospital_id,
    name,
    area,
    city,
    type,
    distance_km,
    reference_property
)
SELECT
    TRIM(hospital_id),
    TRIM(name),
    NULLIF(TRIM(area), ''),
    NULLIF(TRIM(city), ''),
    NULLIF(TRIM(type), ''),
    NULLIF(TRIM(distance_km), '')::NUMERIC,
    NULLIF(TRIM(reference_property), '')
FROM stg_hospitals

WHERE NULLIF(TRIM(hospital_id), '') IS NOT NULL

ON CONFLICT (hospital_id)
DO UPDATE SET
    name = EXCLUDED.name,
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    type = EXCLUDED.type,
    distance_km = EXCLUDED.distance_km,
    reference_property = EXCLUDED.reference_property;

-- ============================================================
-- PAYMENT PLANS
-- ============================================================

INSERT INTO payment_plans (
    property_id,
    plan_name,
    summary,
    notes,
    status
)
SELECT
    TRIM(property_id),
    TRIM(plan_name),
    NULLIF(TRIM(summary), ''),
    NULLIF(TRIM(notes), ''),
    TRIM(status)

FROM stg_payment_plans

WHERE NULLIF(TRIM(property_id), '') IS NOT NULL
  AND NULLIF(TRIM(plan_name), '') IS NOT NULL

  AND NOT EXISTS (
      SELECT 1
      FROM payment_plans pp
      WHERE pp.property_id = TRIM(stg_payment_plans.property_id)
        AND pp.plan_name = TRIM(stg_payment_plans.plan_name)
  );

-- ============================================================
-- FAQS
-- ============================================================

INSERT INTO faqs (
    faq_id,
    question,
    answer,
    category,
    status,
    source
)
SELECT
    TRIM(faq_id),
    TRIM(question),
    TRIM(answer),
    NULLIF(TRIM(category), ''),
    TRIM(status),
    NULLIF(TRIM(source), '')
FROM stg_faqs

WHERE NULLIF(TRIM(faq_id), '') IS NOT NULL

ON CONFLICT (faq_id)
DO UPDATE SET
    question = EXCLUDED.question,
    answer = EXCLUDED.answer,
    category = EXCLUDED.category,
    status = EXCLUDED.status,
    source = EXCLUDED.source;

-- ============================================================
-- AGENTS
-- ============================================================

INSERT INTO agents (
    agent_id,
    name,
    phone,
    email,
    city,
    area,
    specialization,
    status
)
SELECT
    TRIM(agent_id),
    TRIM(name),
    TRIM(phone),
    TRIM(email),
    TRIM(city),
    TRIM(area),
    TRIM(specialization),
    TRIM(status)

FROM stg_agents

WHERE NULLIF(TRIM(agent_id), '') IS NOT NULL

ON CONFLICT (agent_id)
DO UPDATE SET
    name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    city = EXCLUDED.city,
    area = EXCLUDED.area,
    specialization = EXCLUDED.specialization,
    status = EXCLUDED.status;

-- ============================================================
-- AGENT <-> PROPERTY ASSIGNMENTS
-- ============================================================
--
-- CSV columns:
-- agent_id, property_id, assignment_type, assigned_on
--
-- All four values are preserved.
-- ============================================================

INSERT INTO agent_properties (
    agent_id,
    property_id,
    assignment_type,
    assigned_on
)
SELECT DISTINCT
    TRIM(agent_id),
    TRIM(property_id),

    COALESCE(
        NULLIF(TRIM(assignment_type), ''),
        'Primary'
    ),

    NULLIF(TRIM(assigned_on), '')::DATE

FROM stg_agent_properties

WHERE NULLIF(TRIM(agent_id), '') IS NOT NULL
  AND NULLIF(TRIM(property_id), '') IS NOT NULL

ON CONFLICT (agent_id, property_id)
DO UPDATE SET
    assignment_type = EXCLUDED.assignment_type,
    assigned_on = EXCLUDED.assigned_on;

-- ============================================================
-- COMMIT
-- ============================================================

COMMIT;

-- ============================================================
-- VERIFICATION: ROW COUNTS
-- ============================================================

SELECT
    'agents' AS table_name,
    COUNT(*) AS row_count
FROM agents

UNION ALL

SELECT
    'agent_properties',
    COUNT(*)
FROM agent_properties

UNION ALL

SELECT
    'amenities',
    COUNT(*)
FROM amenities

UNION ALL

SELECT
    'developers',
    COUNT(*)
FROM developers

UNION ALL

SELECT
    'faqs',
    COUNT(*)
FROM faqs

UNION ALL

SELECT
    'hospitals',
    COUNT(*)
FROM hospitals

UNION ALL

SELECT
    'locations',
    COUNT(*)
FROM locations

UNION ALL

SELECT
    'payment_plans',
    COUNT(*)
FROM payment_plans

UNION ALL

SELECT
    'prices',
    COUNT(*)
FROM prices

UNION ALL

SELECT
    'properties',
    COUNT(*)
FROM properties

UNION ALL

SELECT
    'schools',
    COUNT(*)
FROM schools

ORDER BY table_name;

-- ============================================================
-- VERIFICATION: AGENT <-> PROPERTY RELATIONSHIP
-- ============================================================

SELECT
    a.agent_id,
    a.name AS agent_name,
    a.city AS agent_city,
    a.area AS agent_area,
    a.specialization,

    ap.property_id,
    ap.assignment_type,
    ap.assigned_on,

    p.name AS property_name,
    p.property_type,
    p.purpose

FROM agent_properties ap

JOIN agents a
    ON ap.agent_id = a.agent_id

JOIN properties p
    ON ap.property_id = p.property_id

ORDER BY
    a.agent_id,
    ap.property_id;

-- ============================================================
-- VERIFICATION: UNASSIGNED PROPERTIES
-- ============================================================

SELECT
    p.property_id,
    p.name AS property_name,
    p.status,
    p.purpose

FROM properties p

LEFT JOIN agent_properties ap
    ON p.property_id = ap.property_id

WHERE ap.property_id IS NULL

ORDER BY p.property_id;

-- ============================================================
-- VERIFICATION: AGENTS WITHOUT PROPERTIES
-- ============================================================

SELECT
    a.agent_id,
    a.name,
    a.city,
    a.area,
    a.status

FROM agents a

LEFT JOIN agent_properties ap
    ON a.agent_id = ap.agent_id

WHERE ap.agent_id IS NULL

ORDER BY a.agent_id;
