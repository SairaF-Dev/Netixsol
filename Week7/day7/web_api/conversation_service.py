"""PostgreSQL-owned conversations; no raw message history or auth secrets."""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg


class ConversationDenied(PermissionError):
    pass


class ConversationExpired(PermissionError):
    pass


class PostgresConversationStore:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def initialize(self):
        with psycopg.connect(self.database_url) as connection:
            connection.execute(Path(__file__).with_name("chat_schema.sql").read_text())

    def _begin(self, conversation_id, identity):
        # Sync psycopg in a worker thread works on Windows Proactor as well as
        # Unix event loops. The DB transaction, not the thread, owns the lock.
        connection = psycopg.connect(self.database_url, connect_timeout=5)
        try:
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 9))", (identity.customer_id,))
            if conversation_id is None:
                conversation_id = uuid4()
                connection.execute("""INSERT INTO chat_sessions
                    (conversation_id,customer_id,auth_user_id,expires_at) VALUES (%s,%s,%s,%s)""",
                    (conversation_id, identity.customer_id, identity.user_id,
                     datetime.now(timezone.utc) + timedelta(hours=24)))
            row = connection.execute("""SELECT state, expires_at, status FROM chat_sessions
                WHERE conversation_id=%s AND customer_id=%s AND auth_user_id=%s FOR UPDATE""",
                (conversation_id, identity.customer_id, identity.user_id)).fetchone()
            if not row:
                raise ConversationDenied()
            if row[1] <= datetime.now(timezone.utc) or row[2] != "active":
                raise ConversationExpired()
            return connection, str(conversation_id), row[0]
        except BaseException:
            connection.close()
            raise

    @staticmethod
    def _commit(connection, conversation_id, state):
        connection.execute("UPDATE chat_sessions SET state=%s::jsonb, updated_at=NOW() WHERE conversation_id=%s",
                           (json.dumps(state), conversation_id))
        connection.commit()

    @asynccontextmanager
    async def turn(self, conversation_id, identity):
        opening = asyncio.create_task(asyncio.to_thread(self._begin, conversation_id, identity))
        try:
            connection, conversation_id, state = await asyncio.shield(opening)
        except asyncio.CancelledError:
            # A cancelled request must not abandon a background-acquired DB lock.
            try:
                connection, _, _ = await opening
                await asyncio.to_thread(connection.close)
            finally:
                raise
        try:
            yield conversation_id, state
            await asyncio.to_thread(self._commit, connection, conversation_id, state)
        finally:
            # Closing an uncommitted connection rolls back its conversation state.
            await asyncio.to_thread(connection.close)
