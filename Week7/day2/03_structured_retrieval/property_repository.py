import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()


class PropertyRepository:
    """
    Production-style PostgreSQL repository.

    Structured property information is retrieved directly
    from PostgreSQL using parameterized queries.
    """

    def __init__(self, database_url=None):
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
        )

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not configured."
            )

    def _connect(self):
        return psycopg.connect(self.database_url)

    def get_property(self, property_id):
        """
        Retrieve one property using its exact property ID.
        """

        if not property_id:
            raise ValueError(
                "property_id is required"
            )

        query = """
            SELECT
                property_id,
                name,
                area,
                city,
                property_type,
                bedrooms,
                bathrooms,
                price,
                currency,
                available,
                status,
                developer,
                purpose
            FROM properties
            WHERE property_id = %(property_id)s;
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "property_id": property_id
                    },
                )

                row = cur.fetchone()

                if row is None:
                    return None

                columns = [
                    "property_id",
                    "name",
                    "area",
                    "city",
                    "property_type",
                    "bedrooms",
                    "bathrooms",
                    "price",
                    "currency",
                    "available",
                    "status",
                    "developer",
                    "purpose",
                ]

                return dict(zip(columns, row))

    def search(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose="Purchase",
    ):
        """
        Search available properties using structured filters.
        """

        query = """
            SELECT
                property_id,
                name,
                area,
                city,
                property_type,
                bedrooms,
                bathrooms,
                price,
                currency,
                available,
                status,
                developer,
                purpose
            FROM properties
            WHERE available = TRUE
              AND (%(budget)s IS NULL OR price <= %(budget)s)
              AND (%(city)s IS NULL OR LOWER(city) = LOWER(%(city)s))
              AND (
                    %(area)s IS NULL
                    OR LOWER(area) LIKE LOWER(%(area_pattern)s)
                  )
              AND (%(bedrooms)s IS NULL OR bedrooms = %(bedrooms)s)
              AND (
                    %(property_type)s IS NULL
                    OR LOWER(property_type) = LOWER(%(property_type)s)
                  )
              AND (
                    %(purpose)s IS NULL
                    OR LOWER(purpose) = LOWER(%(purpose)s)
                  )
            ORDER BY price ASC;
        """

        params = {
            "budget": budget,
            "city": city,
            "area": area,
            "area_pattern": (
                f"%{area}%"
                if area
                else None
            ),
            "bedrooms": bedrooms,
            "property_type": property_type,
            "purpose": purpose,
        }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)

                rows = cur.fetchall()

                columns = [
                    "property_id",
                    "name",
                    "area",
                    "city",
                    "property_type",
                    "bedrooms",
                    "bathrooms",
                    "price",
                    "currency",
                    "available",
                    "status",
                    "developer",
                    "purpose",
                ]

                return [
                    dict(zip(columns, row))
                    for row in rows
                ]


if __name__ == "__main__":

    repo = PropertyRepository()

    property_data = repo.get_property(
        "DHA-APT-001"
    )

    print("\nEXACT PROPERTY LOOKUP")
    print("=" * 60)
    print(property_data)

    results = repo.search(
        budget=30_000_000,
        city="Lahore",
        bedrooms=3,
        purpose="Purchase",
    )

    print("\nPROPERTY SEARCH")
    print("=" * 60)

    for property_data in results:
        print(property_data)