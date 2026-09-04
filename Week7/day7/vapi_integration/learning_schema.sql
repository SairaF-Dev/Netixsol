-- Learned customer preferences only. Property facts remain in Day 2 tables.
CREATE TABLE IF NOT EXISTS customer_preference_profiles (
    customer_key TEXT PRIMARY KEY,
    profile_json JSONB NOT NULL,
    sample_count INTEGER NOT NULL CHECK (sample_count >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
