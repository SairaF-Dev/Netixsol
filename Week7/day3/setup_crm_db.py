#!/usr/bin/env python3
"""Setup sara_crm database."""
import psycopg
import sys

try:
    # Connect to postgres database
    conn = psycopg.connect(
        "postgresql://postgres:Postgres123!@localhost:5432/postgres",
        autocommit=True
    )
    cur = conn.cursor()
    
    # Check if sara_crm exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'sara_crm'")
    exists = cur.fetchone()
    
    if exists:
        print("✅ sara_crm database already exists")
    else:
        cur.execute("CREATE DATABASE sara_crm")
        print("✅ sara_crm database created")
    
    cur.close()
    conn.close()
    
    # Now create tables in sara_crm
    conn = psycopg.connect("postgresql://postgres:Postgres123!@localhost:5432/sara_crm")
    cur = conn.cursor()
    
    # Create appointments table
    cur.execute("""
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
        )
    """)
    
    # Create workflow_events table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workflow_events (
            id BIGSERIAL PRIMARY KEY,
            appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),
            event_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS appointments_session_idx ON appointments(session_id)")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✅ Tables created successfully")
    print("✅ sara_crm database is ready!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
