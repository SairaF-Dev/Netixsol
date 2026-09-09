"""Opaque, single-call capabilities backed by the existing authenticated session."""
import hashlib
import os
import secrets
from pathlib import Path
from uuid import uuid4

import psycopg

from web_api.auth import AuthIdentity


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class VoiceSessionStore:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def initialize(self):
        with psycopg.connect(self.database_url) as db:
            db.execute(Path(__file__).with_name("voice_schema.sql").read_text())

    def issue(self, identity, auth_token, assistant_id):
        token, cid = secrets.token_urlsafe(32), uuid4()
        with psycopg.connect(self.database_url) as db:
            row = db.execute("""SELECT session_id FROM auth_sessions
                WHERE token_digest=%s AND user_id=%s AND expires_at>NOW() FOR UPDATE""",
                (digest(auth_token), identity.user_id)).fetchone()
            if not row:
                raise PermissionError()
            # One active browser capability per login, including pending starts.
            db.execute("UPDATE voice_sessions SET closed=TRUE WHERE auth_session_id=%s", (row[0],))
            db.execute("""INSERT INTO chat_sessions
                (conversation_id,customer_id,auth_user_id,expires_at)
                VALUES (%s,%s,%s,NOW()+INTERVAL '35 minutes')""", (cid, identity.customer_id, identity.user_id))
            db.execute("""INSERT INTO voice_sessions
                (token_digest,auth_session_id,conversation_id,assistant_id) VALUES (%s,%s,%s,%s)""",
                (digest(token), row[0], cid, assistant_id))
        return {"voice_session": token, "assistant_id": assistant_id}

    def resolve(self, token, call):
        if (not isinstance(token, str) or not 32 <= len(token) <= 128
                or call.get("type") != "webCall" or not call.get("id")):
            raise PermissionError()
        with psycopg.connect(self.database_url) as db:
            row = db.execute("""SELECT u.user_id,u.customer_id,c.full_name,u.email,c.phone_normalized,
                v.conversation_id,v.call_id,v.assistant_id,
                (v.created_at > NOW()-INTERVAL '2 minutes')
                FROM voice_sessions v JOIN auth_sessions s ON s.session_id=v.auth_session_id
                JOIN auth_users u ON u.user_id=s.user_id JOIN customers c ON c.customer_id=u.customer_id
                WHERE v.token_digest=%s AND NOT v.closed AND v.expires_at>NOW() AND s.expires_at>NOW()
                FOR UPDATE OF v""", (digest(token),)).fetchone()
            if (not row or call.get("assistantId") != row[7]
                    or (row[6] is not None and row[6] != call["id"])
                    or (row[6] is None and not row[8])):
                raise PermissionError()
            db.execute("UPDATE voice_sessions SET call_id=%s WHERE token_digest=%s", (call["id"], digest(token)))
        return AuthIdentity(*(str(v) if i < 2 else v for i, v in enumerate(row[:5]))), str(row[5])

    def close(self, token, user_id=None):
        with psycopg.connect(self.database_url) as db:
            db.execute("""UPDATE voice_sessions v SET closed=TRUE FROM auth_sessions s
                WHERE v.auth_session_id=s.session_id AND v.token_digest=%s
                AND (%s::uuid IS NULL OR s.user_id=%s::uuid)""", (digest(token), user_id, user_id))
