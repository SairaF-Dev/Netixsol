CREATE TABLE IF NOT EXISTS appointments (
    appointment_id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','confirmed','rescheduled','cancelled')),
    request_json JSONB NOT NULL,
    calendar_event_id TEXT,
    calendar_link TEXT,
    previous_starts_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS appointments_session_idx ON appointments(session_id);
CREATE TABLE IF NOT EXISTS workflow_events (
    id BIGSERIAL PRIMARY KEY,
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
