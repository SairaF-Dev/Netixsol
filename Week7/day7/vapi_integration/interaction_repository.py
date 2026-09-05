"""Persistent customer-property interaction events."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg

VALID_ACTIONS = frozenset({
    "shown", "viewed", "liked", "rejected", "shortlisted",
    "appointment_booked", "appointment_cancelled",
})


@dataclass
class CustomerInteraction:
    interaction_id: str
    customer_id: str
    conversation_id: str
    property_id: str
    action: str
    reason: str | None = None
    metadata: dict[str, Any] | None = None
    preference_snapshot: dict[str, Any] | None = None
    property_snapshot: dict[str, Any] | None = None
    created_at: datetime | None = None


class InteractionRepository:
    """Repository for raw structured interaction events only."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")

    def _connect(self):
        return psycopg.connect(self.database_url)

    def record_interaction(
        self,
        customer_id: str,
        conversation_id: str,
        property_id: str,
        action: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        preference_snapshot: dict[str, Any] | None = None,
        property_snapshot: dict[str, Any] | None = None,
    ) -> CustomerInteraction:
        if action not in VALID_ACTIONS:
            raise ValueError(f"Unsupported interaction action: {action}")
        query = """
            INSERT INTO customer_interactions
                (interaction_id, customer_id, conversation_id, property_id,
                action, reason, metadata, preference_snapshot, property_snapshot)
            SELECT %s, %s, %s, p.property_id, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb
            FROM properties p
            JOIN prices pr ON pr.property_id = p.property_id
            WHERE p.property_id = %s
              AND pr.verification_status = 'Verified'
              AND (%s <> 'shown' OR p.available = TRUE)
            RETURNING interaction_id, customer_id, conversation_id, property_id,
                      action, reason, metadata, preference_snapshot,
                      property_snapshot, created_at
        """
        values = (
            uuid.uuid4(), customer_id, conversation_id, action, reason,
            json.dumps(metadata or {}), json.dumps(preference_snapshot or {}),
            json.dumps(property_snapshot or {}), property_id, action,
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()
        if not row:
            raise ValueError("Property is not eligible for this interaction event")
        return self._from_row(row)

    def list_customer_interactions(self, customer_id: str) -> list[CustomerInteraction]:
        query = """
            SELECT interaction_id, customer_id, conversation_id, property_id,
                   action, reason, metadata, preference_snapshot,
                   property_snapshot, created_at
            FROM customer_interactions
            WHERE customer_id = %s
            ORDER BY created_at, interaction_id
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (customer_id,))
            return [self._from_row(row) for row in cursor.fetchall()]

    def get_customer_property_history(
        self, customer_id: str, property_id: str
    ) -> list[CustomerInteraction]:
        query = """
            SELECT interaction_id, customer_id, conversation_id, property_id,
                   action, reason, metadata, preference_snapshot,
                   property_snapshot, created_at
            FROM customer_interactions
            WHERE customer_id = %s AND property_id = %s
            ORDER BY created_at, interaction_id
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (customer_id, property_id))
            return [self._from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> CustomerInteraction:
        return CustomerInteraction(
            interaction_id=str(row[0]), customer_id=str(row[1]),
            conversation_id=str(row[2]), property_id=str(row[3]),
            action=row[4], reason=row[5], metadata=row[6],
            preference_snapshot=row[7], property_snapshot=row[8], created_at=row[9],
        )
