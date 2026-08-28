-- Week 7 Day 2 — Load verified CSV knowledge base into PostgreSQL
-- Run from the week7_day2 directory with psql.
--
-- Example:
--   psql "$DATABASE_URL" -f 03_structured_retrieval/schema.sql
--   psql "$DATABASE_URL" -f 03_structured_retrieval/seed.sql
--
-- The staging tables preserve the CSV format and convert Yes/No and NA
-- values before inserting into the normalized production tables.

BEGIN;

CREATE TEMP TABLE stg_locations (
    location_id TEXT, area TEXT, city TEXT, zone TEXT,
    classification TEXT, region TEXT
);

CREATE TEMP TABLE stg_developers (
    developer_id TEXT, name TEXT, projects TEXT,
    specialization TEXT, area TEXT, status TEXT
);

CREATE TEMP TABLE stg_properties (
    property_id TEXT, name TEXT, location_id TEXT, area TEXT, city TEXT,
    property_type TEXT, bedrooms TEXT, bathrooms TEXT, plot_size TEXT,
    plot_unit TEXT, covered_area TEXT, covered_area_unit TEXT,
    available TEXT, status TEXT, developer_id TEXT, purpose TEXT
);

CREATE TEMP TABLE stg_prices (
    property_id TEXT, price TEXT, currency TEXT, transaction_type TEXT,
    price_period TEXT, verified_on TEXT, verification_status TEXT
);

CREATE TEMP TABLE stg_amenities (
    property_id TEXT, amenity TEXT, details TEXT
);

CREATE TEMP TABLE stg_schools (
    school_id TEXT, name TEXT, area TEXT, city TEXT, type TEXT,
    distance_km TEXT, reference_property TEXT
);

CREATE TEMP TABLE stg_hospitals (
    hospital_id TEXT, name TEXT, area TEXT, city TEXT, type TEXT,
    distance_km TEXT, reference_property TEXT
);

CREATE TEMP TABLE stg_payment_plans (
    property_id TEXT, plan_name TEXT, summary TEXT, notes TEXT, status TEXT
);

CREATE TEMP TABLE stg_faqs (
    faq_id TEXT, question TEXT, answer TEXT, category TEXT,
    status TEXT, source TEXT
);

\copy stg_locations FROM '01_knowledge_base/locations.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_developers FROM '01_knowledge_base/developers.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_properties FROM '01_knowledge_base/properties.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_prices FROM '01_knowledge_base/prices.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_amenities FROM '01_knowledge_base/amenities.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_schools FROM '01_knowledge_base/schools.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_hospitals FROM '01_knowledge_base/hospitals.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_payment_plans FROM '01_knowledge_base/payment_plans.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')
\copy stg_faqs FROM '01_knowledge_base/faqs.csv' WITH (FORMAT csv, HEADER true, NULL 'NA')

INSERT INTO locations (location_id, area, city, zone, classification, region)
SELECT location_id, area, city, zone, classification, region
FROM stg_locations
ON CONFLICT (location_id) DO UPDATE SET
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    zone = EXCLUDED.zone,
    classification = EXCLUDED.classification,
    region = EXCLUDED.region;

INSERT INTO developers (developer_id, name, projects, specialization, area, status)
SELECT developer_id, name, projects, specialization, area, status
FROM stg_developers
ON CONFLICT (developer_id) DO UPDATE SET
    name = EXCLUDED.name,
    projects = EXCLUDED.projects,
    specialization = EXCLUDED.specialization,
    area = EXCLUDED.area,
    status = EXCLUDED.status;

INSERT INTO properties (
    property_id, name, location_id, property_type, bedrooms, bathrooms,
    plot_size, plot_unit, covered_area, covered_area_unit,
    available, status, developer_id, purpose
)
SELECT
    property_id,
    name,
    location_id,
    property_type,
    NULLIF(bedrooms, '')::INTEGER,
    NULLIF(bathrooms, '')::INTEGER,
    NULLIF(plot_size, '')::NUMERIC,
    NULLIF(plot_unit, ''),
    NULLIF(covered_area, '')::NUMERIC,
    NULLIF(covered_area_unit, ''),
    CASE LOWER(available)
        WHEN 'yes' THEN TRUE
        WHEN 'true' THEN TRUE
        WHEN 'no' THEN FALSE
        WHEN 'false' THEN FALSE
        ELSE TRUE
    END,
    status,
    NULLIF(developer_id, ''),
    purpose
FROM stg_properties
ON CONFLICT (property_id) DO UPDATE SET
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

INSERT INTO prices (
    property_id, price, currency, transaction_type,
    price_period, verified_on, verification_status
)
SELECT
    property_id,
    price::NUMERIC,
    currency,
    transaction_type,
    price_period,
    verified_on::DATE,
    verification_status
FROM stg_prices
ON CONFLICT (property_id) DO UPDATE SET
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    transaction_type = EXCLUDED.transaction_type,
    price_period = EXCLUDED.price_period,
    verified_on = EXCLUDED.verified_on,
    verification_status = EXCLUDED.verification_status;

INSERT INTO amenities (property_id, amenity, details)
SELECT property_id, amenity, details
FROM stg_amenities
ON CONFLICT (property_id, amenity) DO UPDATE SET
    details = EXCLUDED.details;

INSERT INTO schools (
    school_id, name, area, city, type, distance_km, reference_property
)
SELECT
    school_id, name, area, city, type,
    NULLIF(distance_km, '')::NUMERIC,
    NULLIF(reference_property, '')
FROM stg_schools
ON CONFLICT (school_id) DO UPDATE SET
    name = EXCLUDED.name,
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    type = EXCLUDED.type,
    distance_km = EXCLUDED.distance_km,
    reference_property = EXCLUDED.reference_property;

INSERT INTO hospitals (
    hospital_id, name, area, city, type, distance_km, reference_property
)
SELECT
    hospital_id, name, area, city, type,
    NULLIF(distance_km, '')::NUMERIC,
    NULLIF(reference_property, '')
FROM stg_hospitals
ON CONFLICT (hospital_id) DO UPDATE SET
    name = EXCLUDED.name,
    area = EXCLUDED.area,
    city = EXCLUDED.city,
    type = EXCLUDED.type,
    distance_km = EXCLUDED.distance_km,
    reference_property = EXCLUDED.reference_property;

INSERT INTO payment_plans (
    property_id, plan_name, summary, notes, status
)
SELECT property_id, plan_name, summary, notes, status
FROM stg_payment_plans
WHERE NOT EXISTS (
    SELECT 1
    FROM payment_plans pp
    WHERE pp.property_id = stg_payment_plans.property_id
      AND pp.plan_name = stg_payment_plans.plan_name
);

INSERT INTO faqs (
    faq_id, question, answer, category, status, source
)
SELECT faq_id, question, answer, category, status, source
FROM stg_faqs
ON CONFLICT (faq_id) DO UPDATE SET
    question = EXCLUDED.question,
    answer = EXCLUDED.answer,
    category = EXCLUDED.category,
    status = EXCLUDED.status,
    source = EXCLUDED.source;

COMMIT;

-- Verification
SELECT 'locations' AS table_name, COUNT(*) AS row_count FROM locations
UNION ALL
SELECT 'developers', COUNT(*) FROM developers
UNION ALL
SELECT 'properties', COUNT(*) FROM properties
UNION ALL
SELECT 'prices', COUNT(*) FROM prices
UNION ALL
SELECT 'amenities', COUNT(*) FROM amenities
UNION ALL
SELECT 'schools', COUNT(*) FROM schools
UNION ALL
SELECT 'hospitals', COUNT(*) FROM hospitals
UNION ALL
SELECT 'payment_plans', COUNT(*) FROM payment_plans
UNION ALL
SELECT 'faqs', COUNT(*) FROM faqs
ORDER BY table_name;
