-- Phase 3: raw customer-property interaction events.
-- Additive migration; property facts remain owned by the verified Day 2 tables.

CREATE TABLE IF NOT EXISTS customer_interactions (
    interaction_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    conversation_id TEXT NOT NULL,
    property_id VARCHAR(50) NOT NULL REFERENCES properties(property_id),
    action TEXT NOT NULL,
    reason TEXT,
    metadata JSONB,
    preference_snapshot JSONB,
    property_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT customer_interactions_action_check CHECK (
        action IN (
            'shown', 'viewed', 'liked', 'rejected', 'shortlisted',
            'appointment_booked', 'appointment_cancelled'
        )
    )
);

CREATE INDEX IF NOT EXISTS customer_interactions_customer_id_idx
    ON customer_interactions (customer_id);
CREATE INDEX IF NOT EXISTS customer_interactions_property_id_idx
    ON customer_interactions (property_id);
CREATE INDEX IF NOT EXISTS customer_interactions_action_idx
    ON customer_interactions (action);
CREATE INDEX IF NOT EXISTS customer_interactions_created_at_idx
    ON customer_interactions (created_at);
CREATE INDEX IF NOT EXISTS customer_interactions_customer_property_idx
    ON customer_interactions (customer_id, property_id);

ALTER TABLE customer_interactions
    ADD COLUMN IF NOT EXISTS preference_snapshot JSONB;
ALTER TABLE customer_interactions
    ADD COLUMN IF NOT EXISTS property_snapshot JSONB;
