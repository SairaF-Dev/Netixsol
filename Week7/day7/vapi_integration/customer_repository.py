"""PostgreSQL persistence for customer identity records."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg


@dataclass
class Customer:
    customer_id: str
    full_name: str | None = None
    email: str | None = None
    phone_normalized: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomerRepository:
    """Repository for customer identity, keyed by a generated UUID."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")

    def _connect(self):
        return psycopg.connect(self.database_url)

    def get_by_id(self, customer_id: str) -> Customer | None:
        query = """
            SELECT customer_id, full_name, email, phone_normalized,
                   created_at, updated_at
            FROM customers
            WHERE customer_id = %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (customer_id,))
            row = cursor.fetchone()
        return self._from_row(row) if row else None

    def get_by_phone(self, phone_normalized: str) -> Customer | None:
        query = """
            SELECT customer_id, full_name, email, phone_normalized,
                   created_at, updated_at
            FROM customers
            WHERE phone_normalized = %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (phone_normalized,))
            row = cursor.fetchone()
        return self._from_row(row) if row else None

    def get_by_email(self, email: str) -> Customer | None:
        query = """
            SELECT customer_id, full_name, email, phone_normalized,
                   created_at, updated_at
            FROM customers
            WHERE lower(email) = lower(%s)
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (email,))
            row = cursor.fetchone()
        return self._from_row(row) if row else None

    def list_customers(self, limit: int = 100) -> list[Customer]:
        query = """
            SELECT customer_id, full_name, email, phone_normalized,
                   created_at, updated_at
            FROM customers
            ORDER BY updated_at DESC, customer_id
            LIMIT %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (max(1, min(limit, 500)),))
            return [self._from_row(row) for row in cursor.fetchall()]

    def get_or_create_by_phone(self, phone_normalized: str) -> Customer:
        query = """
            INSERT INTO customers (customer_id, phone_normalized)
            VALUES (%s, %s)
            ON CONFLICT (phone_normalized) DO UPDATE
                SET updated_at = NOW()
            RETURNING customer_id, full_name, email, phone_normalized,
                      created_at, updated_at
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (uuid.uuid4(), phone_normalized))
            row = cursor.fetchone()
        return self._from_row(row)

    def create(self, *, full_name: str | None = None, email: str | None = None,
               phone_normalized: str | None = None) -> Customer:
        query = """
            INSERT INTO customers (customer_id, full_name, email, phone_normalized)
            VALUES (%s, %s, %s, %s)
            RETURNING customer_id, full_name, email, phone_normalized,
                      created_at, updated_at
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (uuid.uuid4(), full_name, email, phone_normalized))
            row = cursor.fetchone()
        return self._from_row(row)

    def update_name(self, customer_id: str, full_name: str) -> Customer:
        query = """
            UPDATE customers
            SET full_name = %s, updated_at = NOW()
            WHERE customer_id = %s
            RETURNING customer_id, full_name, email, phone_normalized,
                      created_at, updated_at
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (full_name, customer_id))
            row = cursor.fetchone()
        if not row:
            raise ValueError("Customer does not exist")
        return self._from_row(row)

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> Customer:
        return Customer(
            customer_id=str(row[0]),
            full_name=row[1],
            email=row[2],
            phone_normalized=row[3],
            created_at=row[4],
            updated_at=row[5],
        )