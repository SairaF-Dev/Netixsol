CREATE TABLE IF NOT EXISTS chat_sessions (
    conversation_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    auth_user_id UUID NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','expired')),
    state JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS chat_sessions_owner_idx ON chat_sessions(auth_user_id, customer_id);
CREATE INDEX IF NOT EXISTS chat_sessions_expiry_idx ON chat_sessions(expires_at);
