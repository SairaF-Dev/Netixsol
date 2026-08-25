-- Structured retrieval schema
-- Used for: prices, availability, plot/size, agent names (Task 3, structured half)

CREATE TABLE developers (
    developer_id TEXT PRIMARY KEY,
    developer_name TEXT NOT NULL,
    years_in_business INTEGER,
    projects_completed INTEGER,
    reputation_rating REAL,
    contact_email TEXT
);

CREATE TABLE locations (
    area_id TEXT PRIMARY KEY,
    area_name TEXT NOT NULL,
    city TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    category TEXT,
    distance_to_airport_km REAL,
    distance_to_city_center_km REAL,
    security_rating TEXT
);

CREATE TABLE properties (
    property_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('House','Apartment','Commercial','Plot')),
    purpose TEXT CHECK(purpose IN ('Buy','Rent')),
    city TEXT,
    area TEXT,
    bedrooms INTEGER,
    bathrooms INTEGER,
    size_marla TEXT,
    price_pkr REAL,
    developer_id TEXT,
    status TEXT CHECK(status IN ('Available','Sold','Rented','Under Construction')),
    agent_name TEXT,
    agent_phone TEXT,
    possession_status TEXT,
    FOREIGN KEY (developer_id) REFERENCES developers(developer_id)
);

CREATE TABLE prices (
    property_id TEXT PRIMARY KEY,
    list_price_pkr REAL,
    price_per_marla_or_sqft REAL,
    last_price_update DATE,
    negotiable TEXT,
    advance_percent REAL,
    monthly_rent_pkr REAL,
    FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE amenities (
    property_id TEXT PRIMARY KEY,
    gated_community TEXT,
    parking TEXT,
    gym TEXT,
    swimming_pool TEXT,
    park_nearby TEXT,
    mosque_nearby TEXT,
    generator_backup TEXT,
    solar_panels TEXT,
    servant_quarter TEXT,
    lift TEXT,
    FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE payment_plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT,
    plan_name TEXT,
    advance_percent REAL,
    installment_count INTEGER,
    installment_frequency TEXT,
    installment_amount_pkr REAL,
    possession_percent REAL,
    duration_months INTEGER,
    FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

-- Indexes for the exact-value lookups this agent needs most (price, availability, size, agent)
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_price ON properties(price_pkr);
CREATE INDEX idx_properties_agent ON properties(agent_name);
