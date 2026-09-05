-- Phase 1: persistent customer identity and preferences.
-- This migration is additive and does not alter or delete existing tables.

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    phone_normalized TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT customers_phone_normalized_unique UNIQUE (phone_normalized),
    CONSTRAINT customers_email_not_blank CHECK (email IS NULL OR btrim(email) <> ''),
    CONSTRAINT customers_phone_not_blank CHECK (
        phone_normalized IS NULL OR btrim(phone_normalized) <> ''
    )
);

CREATE INDEX IF NOT EXISTS customers_phone_normalized_idx
    ON customers (phone_normalized);
CREATE INDEX IF NOT EXISTS customers_email_idx
    ON customers (email);

CREATE TABLE IF NOT EXISTS customer_preferences (
    customer_id UUID PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    city TEXT,
    area TEXT,
    budget_min BIGINT,
    budget_max BIGINT,
    bedrooms INTEGER,
    property_type TEXT,
    purpose TEXT,
    amenities JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT customer_preferences_budget_check CHECK (
        budget_min IS NULL OR budget_max IS NULL OR budget_min <= budget_max
    ),
    CONSTRAINT customer_preferences_bedrooms_check CHECK (bedrooms IS NULL OR bedrooms > 0)
);

CREATE INDEX IF NOT EXISTS customer_preferences_customer_id_idx
    ON customer_preferences (customer_id);