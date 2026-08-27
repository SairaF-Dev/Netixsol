CREATE TABLE IF NOT EXISTS properties (
    property_id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    city TEXT NOT NULL,
    property_type TEXT NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    price NUMERIC NOT NULL,
    currency VARCHAR(10) NOT NULL,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL,
    developer TEXT,
    purpose TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_properties_city
    ON properties(city);

CREATE INDEX IF NOT EXISTS idx_properties_area
    ON properties(area);

CREATE INDEX IF NOT EXISTS idx_properties_price
    ON properties(price);

CREATE INDEX IF NOT EXISTS idx_properties_available
    ON properties(available);

CREATE INDEX IF NOT EXISTS idx_properties_bedrooms
    ON properties(bedrooms);

CREATE INDEX IF NOT EXISTS idx_properties_purpose
    ON properties(purpose);

CREATE INDEX IF NOT EXISTS idx_properties_property_type
    ON properties(property_type);