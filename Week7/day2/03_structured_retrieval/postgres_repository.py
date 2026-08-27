import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


class PostgresPropertyRepository:
    """
    Production property repository using PostgreSQL.

    All property, price, location, developer, and amenity
    information is retrieved dynamically from PostgreSQL.
    """

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not configured."
            )

    def search(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose=None,
        amenities=None,
    ):
        query = """
            SELECT
                p.property_id,
                p.name AS property_name,
                l.area,
                l.city,
                p.property_type,
                p.bedrooms,
                p.bathrooms,
                pr.price,
                pr.currency,
                p.available,
                p.status,
                d.name AS developer_name,
                p.purpose,

                COALESCE(
                    ARRAY_AGG(
                        DISTINCT a.amenity
                    ) FILTER (
                        WHERE a.amenity IS NOT NULL
                    ),
                    '{}'
                ) AS amenities

            FROM properties p

            LEFT JOIN prices pr
                ON p.property_id = pr.property_id

            LEFT JOIN locations l
                ON p.location_id = l.location_id

            LEFT JOIN developers d
                ON p.developer_id = d.developer_id

            LEFT JOIN amenities a
                ON p.property_id = a.property_id

            WHERE p.available = TRUE
        """

        parameters = []

        if budget is not None:
            query += """
                AND pr.price <= %s
            """
            parameters.append(budget)

        if city:
            query += """
                AND LOWER(l.city) = LOWER(%s)
            """
            parameters.append(city)

        if area:
            query += """
                AND LOWER(l.area) LIKE LOWER(%s)
            """
            parameters.append(f"%{area}%")

        if bedrooms is not None:
            query += """
                AND p.bedrooms = %s
            """
            parameters.append(bedrooms)

        if property_type:
            query += """
                AND LOWER(p.property_type) = LOWER(%s)
            """
            parameters.append(property_type)

        if purpose:
            query += """
                AND LOWER(p.purpose) = LOWER(%s)
            """
            parameters.append(purpose)

        # Dynamic amenity filtering.
        if amenities:
            for amenity in amenities:
                query += """
                    AND EXISTS (
                        SELECT 1
                        FROM amenities requested_amenity
                        WHERE requested_amenity.property_id = p.property_id
                          AND LOWER(requested_amenity.amenity)
                              = LOWER(%s)
                    )
                """
                parameters.append(amenity)

        query += """
            GROUP BY
                p.property_id,
                p.name,
                l.area,
                l.city,
                p.property_type,
                p.bedrooms,
                p.bathrooms,
                pr.price,
                pr.currency,
                p.available,
                p.status,
                d.name,
                p.purpose

            ORDER BY pr.price ASC
        """

        print("\nSQL PARAMETERS:", parameters)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    query,
                    parameters,
                )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                rows = cursor.fetchall()

        results = [
            dict(zip(columns, row))
            for row in rows
        ]

        print("ROWS FOUND:", len(results))

        return results


if __name__ == "__main__":

    repository = PostgresPropertyRepository()

    results = repository.search(
        budget=40_000_000,
        city="Lahore",
        bedrooms=3,
        purpose="Purchase",
        amenities=[
            "Swimming Pool",
            "Gym",
        ],
    )

    print("\nRESULTS:")

    for property_data in results:
        print(property_data)