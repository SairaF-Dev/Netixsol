CREATE TABLE IF NOT EXISTS auth_users (
    user_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(customer_id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS auth_users_email_unique ON auth_users (LOWER(email));

CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
    token_digest CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS auth_sessions_user_idx ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS auth_sessions_expiry_idx ON auth_sessions(expires_at);
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS csrf_token_digest CHAR(64);

CREATE TABLE IF NOT EXISTS auth_appointment_ownership (
    appointment_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS auth_appointment_owner_idx ON auth_appointment_ownership(user_id);

CREATE TABLE IF NOT EXISTS recommendation_sessions (
    recommendation_session_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    auth_user_id UUID REFERENCES auth_users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','expired')),
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS recommendation_sessions_customer_idx
    ON recommendation_sessions(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS recommendation_sessions_expiry_idx
    ON recommendation_sessions(expires_at);

CREATE TABLE IF NOT EXISTS recommendation_session_properties (
    recommendation_session_id UUID NOT NULL REFERENCES recommendation_sessions(recommendation_session_id) ON DELETE CASCADE,
    property_id VARCHAR(50) NOT NULL REFERENCES properties(property_id),
    display_position INTEGER NOT NULL CHECK (display_position >= 0),
    preference_snapshot JSONB NOT NULL,
    property_snapshot JSONB NOT NULL,
    shown_recorded BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (recommendation_session_id, property_id),
    UNIQUE (recommendation_session_id, display_position)
);
ALTER TABLE recommendation_session_properties
    ADD COLUMN IF NOT EXISTS shown_recorded BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS auth_rate_limits (
    scope TEXT NOT NULL,
    identifier_hash CHAR(64) NOT NULL,
    window_started_at TIMESTAMPTZ NOT NULL,
    attempt_count INTEGER NOT NULL,
    PRIMARY KEY(scope, identifier_hash)
);

CREATE TABLE IF NOT EXISTS auth_audit_events (
    event_id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth_users(user_id) ON DELETE SET NULL,
    normalized_email_hash CHAR(64),
    event_type TEXT NOT NULL CHECK (event_type IN
        ('login_success','login_failure','logout','registration','rate_limited','session_expired','logout_all')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS auth_audit_events_created_idx ON auth_audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS auth_audit_events_user_idx ON auth_audit_events(user_id, created_at DESC);
