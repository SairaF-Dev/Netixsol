"""PostgreSQL persistence for one preference record per customer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import psycopg


@dataclass
class CustomerPreferences:
    customer_id: str
    city: str | None = None
    area: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    bedrooms: int | None = None
    property_type: str | None = None
    purpose: str | None = None
    amenities: list[str] = field(default_factory=list)


class PreferenceRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured")

    def _connect(self):
        return psycopg.connect(self.database_url)

    def get(self, customer_id: str) -> CustomerPreferences | None:
        query = """
            SELECT customer_id, city, area, budget_min, budget_max,
                   bedrooms, property_type, purpose, amenities
            FROM customer_preferences
            WHERE customer_id = %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (customer_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return CustomerPreferences(
            customer_id=str(row[0]), city=row[1], area=row[2],
            budget_min=row[3], budget_max=row[4], bedrooms=row[5],
            property_type=row[6], purpose=row[7],
            amenities=list(row[8] or []),
        )

    def upsert(self, preferences: CustomerPreferences) -> CustomerPreferences:
        query = """
            INSERT INTO customer_preferences
                (customer_id, city, area, budget_min, budget_max, bedrooms,
                 property_type, purpose, amenities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (customer_id) DO UPDATE SET
                city = EXCLUDED.city,
                area = EXCLUDED.area,
                budget_min = EXCLUDED.budget_min,
                budget_max = EXCLUDED.budget_max,
                bedrooms = EXCLUDED.bedrooms,
                property_type = EXCLUDED.property_type,
                purpose = EXCLUDED.purpose,
                amenities = EXCLUDED.amenities,
                updated_at = NOW()
            RETURNING customer_id, city, area, budget_min, budget_max,
                      bedrooms, property_type, purpose, amenities
        """
        values = (
            preferences.customer_id, preferences.city, preferences.area,
            preferences.budget_min, preferences.budget_max, preferences.bedrooms,
            preferences.property_type, preferences.purpose,
            json.dumps(preferences.amenities),
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()
        return CustomerPreferences(
            customer_id=str(row[0]), city=row[1], area=row[2],
            budget_min=row[3], budget_max=row[4], bedrooms=row[5],
            property_type=row[6], purpose=row[7], amenities=list(row[8] or []),
        )

    def update_partial(self, customer_id: str, updates: dict[str, Any]) -> CustomerPreferences:
        """Update only supplied, structured preference fields."""
        allowed = {
            "city", "area", "budget_min", "budget_max", "bedrooms",
            "property_type", "purpose", "amenities",
        }
        values = {key: value for key, value in updates.items() if key in allowed}
        if not values:
            existing = self.get(customer_id)
            return existing or CustomerPreferences(customer_id=customer_id)

        columns = ["customer_id", *values]
        placeholders = ["%s", *["%s::jsonb" if key == "amenities" else "%s" for key in values]]
        assignments = [
            f"{key} = EXCLUDED.{key}"
            for key in values
        ]
        query = f"""
            INSERT INTO customer_preferences ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (customer_id) DO UPDATE SET
                {', '.join(assignments)},
                updated_at = NOW()
            RETURNING customer_id, city, area, budget_min, budget_max,
                      bedrooms, property_type, purpose, amenities
        """
        parameters = [customer_id]
        parameters.extend(
            json.dumps(value) if key == "amenities" else value
            for key, value in values.items()
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            row = cursor.fetchone()
        return CustomerPreferences(
            customer_id=str(row[0]), city=row[1], area=row[2],
            budget_min=row[3], budget_max=row[4], bedrooms=row[5],
            property_type=row[6], purpose=row[7], amenities=list(row[8] or []),
        )