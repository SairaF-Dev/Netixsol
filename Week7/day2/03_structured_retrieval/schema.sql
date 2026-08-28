-- Week 7 Day 2 — Normalized PostgreSQL schema
-- Source of truth for structured property retrieval.

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(50) PRIMARY KEY,
    area TEXT NOT NULL,
    city TEXT NOT NULL,
    zone TEXT,
    classification TEXT,
    region TEXT
);

CREATE TABLE IF NOT EXISTS developers (
    developer_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    projects TEXT,
    specialization TEXT,
    area TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS properties (
    property_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    location_id VARCHAR(50) NOT NULL REFERENCES locations(location_id),
    property_type TEXT NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    plot_size NUMERIC,
    plot_unit VARCHAR(20),
    covered_area NUMERIC,
    covered_area_unit VARCHAR(20),
    available BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL,
    developer_id VARCHAR(50) REFERENCES developers(developer_id),
    purpose TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    property_id VARCHAR(50) PRIMARY KEY REFERENCES properties(property_id) ON DELETE CASCADE,
    price NUMERIC NOT NULL,
    currency VARCHAR(10) NOT NULL,
    transaction_type TEXT NOT NULL,
    price_period TEXT NOT NULL,
    verified_on DATE,
    verification_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS amenities (
    property_id VARCHAR(50) NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
    amenity TEXT NOT NULL,
    details TEXT,
    PRIMARY KEY (property_id, amenity)
);

CREATE TABLE IF NOT EXISTS schools (
    school_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km NUMERIC,
    reference_property VARCHAR(50) REFERENCES properties(property_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km NUMERIC,
    reference_property VARCHAR(50) REFERENCES properties(property_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS payment_plans (
    payment_plan_id BIGSERIAL PRIMARY KEY,
    property_id VARCHAR(50) NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    summary TEXT,
    notes TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faqs (
    faq_id VARCHAR(50) PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT,
    status TEXT NOT NULL,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_locations_city ON locations(city);
CREATE INDEX IF NOT EXISTS idx_locations_area ON locations(area);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(location_id);
CREATE INDEX IF NOT EXISTS idx_properties_developer ON properties(developer_id);
CREATE INDEX IF NOT EXISTS idx_properties_available ON properties(available);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties(bedrooms);
CREATE INDEX IF NOT EXISTS idx_properties_purpose ON properties(purpose);
CREATE INDEX IF NOT EXISTS idx_prices_price ON prices(price);
CREATE INDEX IF NOT EXISTS idx_prices_verification ON prices(verification_status);
CREATE INDEX IF NOT EXISTS idx_amenities_property ON amenities(property_id);
CREATE INDEX IF NOT EXISTS idx_schools_reference_property ON schools(reference_property);
CREATE INDEX IF NOT EXISTS idx_hospitals_reference_property ON hospitals(reference_property);
CREATE INDEX IF NOT EXISTS idx_payment_plans_property ON payment_plans(property_id);
