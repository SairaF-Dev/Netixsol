CREATE TABLE IF NOT EXISTS voice_sessions (
    token_digest CHAR(64) PRIMARY KEY,
    auth_session_id UUID NOT NULL REFERENCES auth_sessions(session_id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES chat_sessions(conversation_id) ON DELETE CASCADE,
    assistant_id TEXT NOT NULL,
    call_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '35 minutes',
    closed BOOLEAN NOT NULL DEFAULT FALSE
);
