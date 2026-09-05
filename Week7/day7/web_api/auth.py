from __future__ import annotations

import hashlib
import os
import secrets
import uuid
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
import psycopg


SESSION_COOKIE = "sara_session"
SESSION_HOURS = int(os.getenv("SARA_AUTH_SESSION_HOURS", "24"))


@dataclass
class AuthIdentity:
    user_id: str
    customer_id: str
    full_name: str | None
    email: str
    phone: str | None


class DuplicateRegistration(ValueError): pass
class InvalidCredentials(ValueError): pass


class AuthRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")

    def initialize(self) -> None:
        sql = Path(__file__).with_name("auth_schema.sql").read_text(encoding="utf-8")
        with psycopg.connect(self.database_url) as connection:
            connection.execute(sql)

    def get_user_by_email(self, email: str):
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT user_id, customer_id, email, password_hash FROM auth_users WHERE LOWER(email)=LOWER(%s)", (email,))
            return cursor.fetchone()

    def create_user(self, customer_id: str, email: str, password_hash: str) -> str:
        user_id = str(uuid.uuid4())
        try:
            with psycopg.connect(self.database_url) as connection:
                connection.execute("INSERT INTO auth_users(user_id,customer_id,email,password_hash) VALUES (%s,%s,%s,%s)", (user_id, customer_id, email, password_hash))
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateRegistration("Email is already registered") from exc
        return user_id

    def create_session(self, user_id: str, digest: str, expires_at: datetime) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("INSERT INTO auth_sessions(session_id,user_id,token_digest,expires_at) VALUES (%s,%s,%s,%s)", (uuid.uuid4(), user_id, digest, expires_at))

    def set_csrf_digest(self, session_digest: str, csrf_digest: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("UPDATE auth_sessions SET csrf_token_digest=%s WHERE token_digest=%s AND expires_at>NOW()", (csrf_digest, session_digest))

    def csrf_digest_for_session(self, session_digest: str) -> str | None:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT csrf_token_digest FROM auth_sessions WHERE token_digest=%s AND expires_at>NOW()", (session_digest,))
            row = cursor.fetchone()
        return row[0] if row else None

    def identity_for_digest(self, digest: str) -> AuthIdentity | None:
        query = """SELECT u.user_id,u.customer_id,c.full_name,u.email,c.phone_normalized
                   FROM auth_sessions s JOIN auth_users u ON u.user_id=s.user_id
                   JOIN customers c ON c.customer_id=u.customer_id
                   WHERE s.token_digest=%s AND s.expires_at>NOW()"""
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (digest,)); row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT u.user_id FROM auth_sessions s JOIN auth_users u ON u.user_id=s.user_id WHERE s.token_digest=%s AND s.expires_at<=NOW()", (digest,))
                expired = cursor.fetchone()
                if expired:
                    connection.execute("INSERT INTO auth_audit_events(event_id,user_id,event_type,metadata) VALUES (%s,%s,'session_expired','{}'::jsonb)", (uuid.uuid4(), expired[0]))
        return AuthIdentity(*map(str, row[:2]), row[2], row[3], row[4]) if row else None

    def delete_session(self, digest: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_digest=%s", (digest,))

    def delete_user_sessions(self, user_id: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("DELETE FROM auth_sessions WHERE user_id=%s", (user_id,))

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT session_id,created_at,expires_at FROM auth_sessions WHERE user_id=%s AND expires_at>NOW() ORDER BY created_at DESC", (user_id,))
            return [{"session_id": str(r[0]), "created_at": r[1], "expires_at": r[2]} for r in cursor.fetchall()]

    def list_appointment_ids(self, user_id: str) -> list[str]:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT appointment_id FROM auth_appointment_ownership WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
            return [str(row[0]) for row in cursor.fetchall()]

    def consume_rate_limit(self, scope: str, identifier_hash: str, limit: int, window_seconds: int) -> bool:
        query = """INSERT INTO auth_rate_limits(scope,identifier_hash,window_started_at,attempt_count)
            VALUES (%s,%s,NOW(),1) ON CONFLICT(scope,identifier_hash) DO UPDATE SET
            window_started_at=CASE WHEN auth_rate_limits.window_started_at <= NOW()-(%s * INTERVAL '1 second') THEN NOW() ELSE auth_rate_limits.window_started_at END,
            attempt_count=CASE WHEN auth_rate_limits.window_started_at <= NOW()-(%s * INTERVAL '1 second') THEN 1 ELSE auth_rate_limits.attempt_count+1 END
            RETURNING attempt_count"""
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (scope, identifier_hash, window_seconds, window_seconds)); count = cursor.fetchone()[0]
        return count <= limit

    def audit(self, event_type: str, user_id: str | None = None, email_hash: str | None = None,
              metadata: dict[str, Any] | None = None) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("INSERT INTO auth_audit_events(event_id,user_id,normalized_email_hash,event_type,metadata) VALUES (%s,%s,%s,%s,%s::jsonb)",
                               (uuid.uuid4(), user_id, email_hash, event_type, json.dumps(metadata or {})))

    def own_appointment(self, user_id: str, appointment_id: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("INSERT INTO auth_appointment_ownership(appointment_id,user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (appointment_id, user_id))

    def owns_appointment(self, user_id: str, appointment_id: str) -> bool:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM auth_appointment_ownership WHERE appointment_id=%s AND user_id=%s", (appointment_id, user_id))
            return cursor.fetchone() is not None


class AuthService:
    def __init__(self, repository: AuthRepository, customer_service: Any) -> None:
        self.repository, self.customers = repository, customer_service

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def register(self, full_name: str, email: str, phone: str, password: str):
        email = email.strip().casefold()
        if self.repository.get_user_by_email(email):
            raise DuplicateRegistration("Email is already registered")
        creator = getattr(self.customers, "create_web_customer", self.customers.create_or_get_test_customer)
        context = creator(full_name=full_name, email=email, phone=phone)
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
        user_id = self.repository.create_user(context.customer.customer_id, email, password_hash)
        self._audit("registration", user_id, email)
        token, expires = self._new_session(user_id)
        return token, expires, AuthIdentity(user_id, context.customer.customer_id, context.customer.full_name, email, context.customer.phone_normalized)

    def login(self, email: str, password: str):
        email = email.strip().casefold(); row = self.repository.get_user_by_email(email)
        if not row or not bcrypt.checkpw(password.encode(), row[3].encode()):
            self._audit("login_failure", None, email)
            raise InvalidCredentials("Invalid email or password")
        token, expires = self._new_session(str(row[0]))
        identity = self.repository.identity_for_digest(self.digest(token))
        self._audit("login_success", str(row[0]), email)
        return token, expires, identity

    def _new_session(self, user_id: str):
        token = secrets.token_urlsafe(32); expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        self.repository.create_session(user_id, self.digest(token), expires)
        return token, expires

    def authenticate(self, token: str | None):
        return self.repository.identity_for_digest(self.digest(token)) if token else None

    def logout(self, token: str | None) -> None:
        if token:
            identity = self.authenticate(token)
            self.repository.delete_session(self.digest(token))
            self._audit("logout", identity.user_id if identity else None)

    def issue_csrf(self, token: str) -> str:
        csrf = secrets.token_urlsafe(32)
        self.repository.set_csrf_digest(self.digest(token), self.digest(csrf))
        return csrf

    def validate_csrf(self, token: str | None, csrf: str | None) -> bool:
        if not token or not csrf:
            return False
        expected = self.repository.csrf_digest_for_session(self.digest(token))
        return bool(expected and secrets.compare_digest(expected, self.digest(csrf)))

    def logout_all(self, user_id: str) -> None:
        self.repository.delete_user_sessions(user_id); self._audit("logout_all", user_id)

    def rate_allowed(self, scope: str, email: str, identifier: str = "") -> bool:
        limit = int(os.getenv(f"SARA_AUTH_{scope.upper()}_LIMIT", "10" if scope == "login" else "5"))
        window = int(os.getenv("SARA_AUTH_RATE_WINDOW_SECONDS", "900"))
        key = self.digest(f"{email.strip().casefold()}|{identifier}")
        allowed = self.repository.consume_rate_limit(scope, key, limit, window)
        if not allowed: self._audit("rate_limited", None, email, {"scope": scope})
        return allowed

    def _audit(self, event_type: str, user_id: str | None = None, email: str | None = None,
               metadata: dict[str, Any] | None = None) -> None:
        method = getattr(self.repository, "audit", None)
        if method:
            method(event_type, user_id, self.digest(email.strip().casefold()) if email else None, metadata)
