
-- Week 7 Day 2 Normalized PostgreSQL schema
--
-- Source of truth for structured property retrieval,
-- agent assignment, and real-estate business workflows.
--
-- Relationship:
--   Agent <-> Property = Many-to-Many
--
-- One agent can handle multiple properties.
-- One property can be handled by multiple agents.

-- ============================================================
-- LOCATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(50) PRIMARY KEY,
    area TEXT NOT NULL,
    city TEXT NOT NULL,
    zone TEXT,
    classification TEXT,
    region TEXT
);

-- ============================================================
-- DEVELOPERS
-- ============================================================

CREATE TABLE IF NOT EXISTS developers (
    developer_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    projects TEXT,
    specialization TEXT,
    area TEXT,
    status TEXT
);

-- ============================================================
-- PROPERTIES
-- ============================================================

CREATE TABLE IF NOT EXISTS properties (
    property_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    location_id VARCHAR(50) NOT NULL
        REFERENCES locations(location_id),
    property_type TEXT NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    plot_size NUMERIC,
    plot_unit VARCHAR(20),
    covered_area NUMERIC,
    covered_area_unit VARCHAR(20),
    available BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL,
    developer_id VARCHAR(50)
        REFERENCES developers(developer_id),
    purpose TEXT NOT NULL
);

-- ============================================================
-- PRICES
-- ============================================================

CREATE TABLE IF NOT EXISTS prices (
    property_id VARCHAR(50) PRIMARY KEY
        REFERENCES properties(property_id)
        ON DELETE CASCADE,
    price NUMERIC NOT NULL,
    currency VARCHAR(10) NOT NULL,
    transaction_type TEXT NOT NULL,
    price_period TEXT NOT NULL,
    verified_on DATE,
    verification_status TEXT NOT NULL
);

-- ============================================================
-- AMENITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS amenities (
    property_id VARCHAR(50) NOT NULL
        REFERENCES properties(property_id)
        ON DELETE CASCADE,
    amenity TEXT NOT NULL,
    details TEXT,
    PRIMARY KEY (property_id, amenity)
);

-- ============================================================
-- SCHOOLS
-- ============================================================

CREATE TABLE IF NOT EXISTS schools (
    school_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km NUMERIC,
    reference_property VARCHAR(50)
        REFERENCES properties(property_id)
        ON DELETE SET NULL
);

-- ============================================================
-- HOSPITALS
-- ============================================================

CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT,
    city TEXT,
    type TEXT,
    distance_km NUMERIC,
    reference_property VARCHAR(50)
        REFERENCES properties(property_id)
        ON DELETE SET NULL
);

-- ============================================================
-- PAYMENT PLANS
-- ============================================================

CREATE TABLE IF NOT EXISTS payment_plans (
    payment_plan_id BIGSERIAL PRIMARY KEY,
    property_id VARCHAR(50) NOT NULL
        REFERENCES properties(property_id)
        ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    summary TEXT,
    notes TEXT,
    status TEXT NOT NULL
);

-- ============================================================
-- FAQS
-- ============================================================

CREATE TABLE IF NOT EXISTS faqs (
    faq_id VARCHAR(50) PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT,
    status TEXT NOT NULL,
    source TEXT
);

-- ============================================================
-- AGENTS
-- ============================================================
--
-- Real-estate agents available for:
--   - customer lead handoff
--   - property inquiries
--   - property visits
--   - sales/rental assistance
--   - commercial property assistance
--
-- Agent specialization and location are stored here.
-- Property assignments are stored separately in agent_properties.

CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email TEXT NOT NULL,
    city TEXT NOT NULL,
    area TEXT NOT NULL,
    specialization TEXT NOT NULL,
    status TEXT NOT NULL
);

-- ============================================================
-- AGENT <-> PROPERTY ASSIGNMENT
-- ============================================================
--
-- Many-to-Many relationship:
--
--   One agent    -> many properties
--   One property -> many agents
--
-- agent_properties is the junction table.

CREATE TABLE IF NOT EXISTS agent_properties (
    agent_id VARCHAR(50) NOT NULL
        REFERENCES agents(agent_id)
        ON DELETE CASCADE,

    property_id VARCHAR(50) NOT NULL
        REFERENCES properties(property_id)
        ON DELETE CASCADE,

    assignment_type TEXT NOT NULL DEFAULT 'Primary',

    assigned_on DATE,

    PRIMARY KEY (agent_id, property_id)
);

-- ============================================================
-- LOCATION INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_locations_city
    ON locations(city);

CREATE INDEX IF NOT EXISTS idx_locations_area
    ON locations(area);

-- ============================================================
-- PROPERTY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_properties_location
    ON properties(location_id);

CREATE INDEX IF NOT EXISTS idx_properties_developer
    ON properties(developer_id);

CREATE INDEX IF NOT EXISTS idx_properties_available
    ON properties(available);

CREATE INDEX IF NOT EXISTS idx_properties_type
    ON properties(property_type);

CREATE INDEX IF NOT EXISTS idx_properties_bedrooms
    ON properties(bedrooms);

CREATE INDEX IF NOT EXISTS idx_properties_purpose
    ON properties(purpose);

-- ============================================================
-- PRICE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_prices_price
    ON prices(price);

CREATE INDEX IF NOT EXISTS idx_prices_verification
    ON prices(verification_status);

-- ============================================================
-- RELATED DATA INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_amenities_property
    ON amenities(property_id);

CREATE INDEX IF NOT EXISTS idx_schools_reference_property
    ON schools(reference_property);

CREATE INDEX IF NOT EXISTS idx_hospitals_reference_property
    ON hospitals(reference_property);

CREATE INDEX IF NOT EXISTS idx_payment_plans_property
    ON payment_plans(property_id);

-- ============================================================
-- AGENT INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_agents_city
    ON agents(city);

CREATE INDEX IF NOT EXISTS idx_agents_area
    ON agents(area);

CREATE INDEX IF NOT EXISTS idx_agents_status
    ON agents(status);

CREATE INDEX IF NOT EXISTS idx_agents_city_area
    ON agents(city, area);

-- ============================================================
-- AGENT-PROPERTY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_agent_properties_agent
    ON agent_properties(agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_properties_property
    ON agent_properties(property_id);

CREATE INDEX IF NOT EXISTS idx_agent_properties_assignment_type
    ON agent_properties(assignment_type);

