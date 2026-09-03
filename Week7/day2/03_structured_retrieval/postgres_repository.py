import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv


load_dotenv()


QUERIES_FILE = Path(__file__).with_name("property_queries.sql")


class PostgresPropertyRepository:
    """
    Production repository for verified real-estate data.

    PostgreSQL is the single source of truth for structured
    property facts.

    Responsibilities:
        - Execute parameterized SQL queries.
        - Retrieve verified property information.
        - Search properties using structured filters.
        - Never generate or infer property facts.
        - Return deterministic Python dictionaries.

    PostgreSQL owns:
        - property IDs
        - property names
        - prices
        - availability
        - locations
        - bedrooms
        - bathrooms
        - property types
        - purposes
        - developers
        - amenities
        - agent identities and property assignments
    """

    QUERY_NAMES = {
        "exact_property",
        "property_name_lookup",
        "buyer_search",
        "availability",
        "developer_lookup",
        "cheaper_alternatives",
        "rental_search",
        "agent_lookup",
        "property_agents",
    }

    DEFAULT_SEARCH_LIMIT = 20
    MAX_SEARCH_LIMIT = 100

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(
        self,
        database_url: str | None = None,
        queries_file: str | Path | None = None,
    ):
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
        )

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not configured."
            )

        self.queries_file = Path(
            queries_file or QUERIES_FILE
        )

        self.queries = self._load_queries()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _connect(self):
        """
        Create a PostgreSQL connection.

        A connection is created per operation.
        This keeps the repository stateless and safe for the
        current Week 7 architecture.
        """
        return psycopg.connect(
            self.database_url
        )

    # ------------------------------------------------------------------
    # SQL loading
    # ------------------------------------------------------------------

    def _load_queries(self) -> dict[str, str]:
        """
        Load named SQL queries from property_queries.sql.
        """

        if not self.queries_file.exists():
            raise FileNotFoundError(
                f"SQL queries file not found: "
                f"{self.queries_file}"
            )

        content = self.queries_file.read_text(
            encoding="utf-8"
        )

        queries: dict[str, str] = {}

        current_query: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("-- QUERY:"):
                # Save previous query
                if current_query is not None:
                    query = "\n".join(
                        current_lines
                    ).strip()

                    if query:
                        queries[current_query] = query

                # Start new query
                current_query = (
                    stripped
                    .replace("-- QUERY:", "")
                    .strip()
                )

                current_lines = []

            elif current_query is not None:
                current_lines.append(line)

        # Save final query
        if current_query is not None:
            query = "\n".join(
                current_lines
            ).strip()

            if query:
                queries[current_query] = query

        missing = (
            self.QUERY_NAMES
            - queries.keys()
        )

        if missing:
            raise ValueError(
                "Missing SQL queries: "
                + ", ".join(
                    sorted(missing)
                )
            )

        return queries

    # ------------------------------------------------------------------
    # Query access
    # ------------------------------------------------------------------

    def _get_query(
        self,
        name: str,
    ) -> str:
        """
        Return a named SQL query.
        """

        if not isinstance(name, str):
            raise TypeError(
                "query name must be a string"
            )

        name = name.strip()

        if not name:
            raise ValueError(
                "query name cannot be empty"
            )

        if name not in self.queries:
            raise KeyError(
                f"Unknown query: {name}"
            )

        return self.queries[name]

    # ------------------------------------------------------------------
    # Row conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(
        cursor,
        rows,
    ) -> list[dict[str, Any]]:
        """
        Convert PostgreSQL rows into dictionaries.
        """

        if cursor.description is None:
            return []

        columns = [
            description.name
            for description in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    @staticmethod
    def _row_to_dict(
        cursor,
        row,
    ) -> dict[str, Any] | None:
        """
        Convert one PostgreSQL row into a dictionary.
        """

        if row is None:
            return None

        if cursor.description is None:
            return None

        columns = [
            description.name
            for description in cursor.description
        ]

        return dict(
            zip(columns, row)
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_optional_string(
        value: Any,
        field_name: str,
    ) -> str | None:
        """
        Validate optional string fields.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        value = value.strip()

        return value or None

    @staticmethod
    def _validate_optional_integer(
        value: Any,
        field_name: str,
    ) -> int | None:
        """
        Validate optional integer fields.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer or None"
            )

        if not isinstance(value, int):
            raise TypeError(
                f"{field_name} must be an integer or None"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative"
            )

        return value

    @staticmethod
    def _validate_optional_budget(
        value: Any,
    ) -> int | float | Decimal | None:
        """
        Validate optional numeric budget.

        Supports:
            - int
            - float
            - Decimal

        Decimal is required because PostgreSQL NUMERIC
        columns are returned by psycopg as Decimal.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                "budget must be numeric or None"
            )

        if not isinstance(
            value,
            (int, float, Decimal),
        ):
            raise TypeError(
                "budget must be numeric or None"
            )

        if value < 0:
            raise ValueError(
                "budget cannot be negative"
            )

        return value

    @staticmethod
    def _validate_amenities(
        amenities: Any,
    ) -> list[str] | None:
        """
        Validate and normalize amenities.

        Duplicate amenities are removed.
        Empty strings are ignored.
        """

        if amenities is None:
            return None

        if not isinstance(
            amenities,
            (list, tuple),
        ):
            raise TypeError(
                "amenities must be a list or tuple"
            )

        normalized: list[str] = []

        for amenity in amenities:

            if not isinstance(
                amenity,
                str,
            ):
                raise TypeError(
                    "each amenity must be a string"
                )

            amenity = amenity.strip()

            if not amenity:
                continue

            if amenity.lower() not in {
                item.lower()
                for item in normalized
            }:
                normalized.append(amenity)

        return normalized or None

    @classmethod
    def _validate_limit(
        cls,
        limit: Any,
    ) -> int:
        """
        Validate search result limit.
        """

        if isinstance(limit, bool):
            raise TypeError(
                "limit must be an integer"
            )

        if not isinstance(limit, int):
            raise TypeError(
                "limit must be an integer"
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        if limit > cls.MAX_SEARCH_LIMIT:
            raise ValueError(
                f"limit cannot exceed "
                f"{cls.MAX_SEARCH_LIMIT}"
            )

        return limit

    # ------------------------------------------------------------------
    # Exact property ID lookup
    # ------------------------------------------------------------------

    def get_property(
        self,
        property_id: str,
    ) -> dict[str, Any] | None:
        """
        Return one verified property by exact property ID.
        """

        if not isinstance(
            property_id,
            str,
        ):
            raise TypeError(
                "property_id must be a string"
            )

        property_id = property_id.strip()

        if not property_id:
            raise ValueError(
                "property_id is required"
            )

        query = self._get_query(
            "exact_property"
        )

        params = {
            "property_id": property_id
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._row_to_dict(
                    cur,
                    cur.fetchone(),
                )

    # ------------------------------------------------------------------
    # Exact property name lookup
    # ------------------------------------------------------------------

    def get_property_by_name(
        self,
        property_name: str,
    ) -> dict[str, Any] | None:
        """
        Return a verified property by exact
        case-insensitive property name.
        """

        if not isinstance(
            property_name,
            str,
        ):
            raise TypeError(
                "property_name must be a string"
            )

        property_name = property_name.strip()

        if not property_name:
            raise ValueError(
                "property_name is required"
            )

        query = self._get_query(
            "property_name_lookup"
        )

        params = {
            "property_name": property_name
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._row_to_dict(
                    cur,
                    cur.fetchone(),
                )

    # ------------------------------------------------------------------
    # Structured search
    # ------------------------------------------------------------------

    def search(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose=None,
        amenities=None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Search verified available properties.

        All filters are applied by PostgreSQL.

        Multiple amenities use AND semantics.
        """

        budget = self._validate_optional_budget(
            budget
        )

        city = self._validate_optional_string(
            city,
            "city",
        )

        area = self._validate_optional_string(
            area,
            "area",
        )

        bedrooms = self._validate_optional_integer(
            bedrooms,
            "bedrooms",
        )

        property_type = self._validate_optional_string(
            property_type,
            "property_type",
        )

        purpose = self._validate_optional_string(
            purpose,
            "purpose",
        )

        amenities = self._validate_amenities(
            amenities
        )

        limit = self._validate_limit(
            limit
        )

        query = self._get_query(
            "buyer_search"
        )

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
            "amenities": amenities,
            "limit": limit,
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                rows = cur.fetchall()

                return self._rows_to_dicts(
                    cur,
                    rows,
                )

    # ------------------------------------------------------------------
    # Natural language search
    # ------------------------------------------------------------------

    def search_question(
        self,
        question: str,
        parser=None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Convert a natural-language property search
        into deterministic structured filters.
        """

        if not isinstance(
            question,
            str,
        ):
            raise TypeError(
                "question must be a string"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question cannot be empty"
            )

        if parser is None:

            try:
                from structured_query_parser import (
                    StructuredQueryParser
                )

            except ImportError:

                import sys

                integration_dir = (
                    Path(__file__).resolve().parent.parent
                    / "07_integration"
                )

                if str(integration_dir) not in sys.path:
                    sys.path.insert(
                        0,
                        str(integration_dir),
                    )

                try:
                    from structured_query_parser import (
                        StructuredQueryParser
                    )

                except ImportError as error:

                    raise ImportError(
                        "StructuredQueryParser "
                        "could not be imported from "
                        f"{integration_dir}"
                    ) from error

            parser = StructuredQueryParser()

        if not hasattr(
            parser,
            "parse",
        ):
            raise TypeError(
                "parser must provide a parse() method"
            )

        filters = parser.parse(
            question
        )

        if not isinstance(
            filters,
            dict,
        ):
            raise TypeError(
                "structured parser must return "
                "a dictionary"
            )

        allowed_fields = {
            "budget",
            "city",
            "area",
            "bedrooms",
            "property_type",
            "purpose",
            "amenities",
        }

        unexpected_fields = (
            set(filters)
            - allowed_fields
        )

        if unexpected_fields:
            raise ValueError(
                "Parser returned unsupported fields: "
                + ", ".join(
                    sorted(unexpected_fields)
                )
            )

        return self.search(
            budget=filters.get(
                "budget"
            ),
            city=filters.get(
                "city"
            ),
            area=filters.get(
                "area"
            ),
            bedrooms=filters.get(
                "bedrooms"
            ),
            property_type=filters.get(
                "property_type"
            ),
            purpose=filters.get(
                "purpose"
            ),
            amenities=filters.get(
                "amenities"
            ),
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def get_availability(
        self,
        city=None,
        property_type=None,
    ) -> list[dict[str, Any]]:
        """
        Return currently available properties
        with verified prices.
        """

        city = self._validate_optional_string(
            city,
            "city",
        )

        property_type = self._validate_optional_string(
            property_type,
            "property_type",
        )

        query = self._get_query(
            "availability"
        )

        params = {
            "city": city,
            "property_type": property_type,
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._rows_to_dicts(
                    cur,
                    cur.fetchall(),
                )

    # ------------------------------------------------------------------
    # Developer lookup
    # ------------------------------------------------------------------

    def get_developer(
        self,
        property_id: str,
    ) -> dict[str, Any] | None:
        """
        Return developer information
        associated with a property.
        """

        if not isinstance(
            property_id,
            str,
        ):
            raise TypeError(
                "property_id must be a string"
            )

        property_id = property_id.strip()

        if not property_id:
            raise ValueError(
                "property_id is required"
            )

        query = self._get_query(
            "developer_lookup"
        )

        params = {
            "property_id": property_id
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._row_to_dict(
                    cur,
                    cur.fetchone(),
                )

    # ------------------------------------------------------------------
    # Cheaper alternatives
    # ------------------------------------------------------------------

    def get_cheaper_alternatives(
        self,
        budget,
        city=None,
        area=None,
        bedrooms=None,
        purpose=None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Return verified available properties cheaper
        than the requested budget.

        Optional filters:
            city
            area
            bedrooms
            purpose

        Results are ordered from highest price below
        the budget to lowest price.

        PostgreSQL remains the source of truth.
        """

        # Validate budget
        budget = self._validate_optional_budget(
            budget
        )

        if budget is None:
            raise ValueError(
                "budget is required"
            )

        # Validate optional filters
        city = self._validate_optional_string(
            city,
            "city",
        )

        area = self._validate_optional_string(
            area,
            "area",
        )

        bedrooms = self._validate_optional_integer(
            bedrooms,
            "bedrooms",
        )

        purpose = self._validate_optional_string(
            purpose,
            "purpose",
        )

        limit = self._validate_limit(
            limit
        )

        # Load SQL
        query = self._get_query(
            "cheaper_alternatives"
        )

        # Parameters
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
            "purpose": purpose,
            "limit": limit,
        }

        # Execute
        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._rows_to_dicts(
                    cur,
                    cur.fetchall(),
                )

    # ------------------------------------------------------------------
    # Rental search
    # ------------------------------------------------------------------

    def search_rentals(
        self,
        city=None,
        bedrooms=None,
        budget=None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Search verified available rental properties.
        """

        city = self._validate_optional_string(
            city,
            "city",
        )

        bedrooms = self._validate_optional_integer(
            bedrooms,
            "bedrooms",
        )

        budget = self._validate_optional_budget(
            budget
        )

        limit = self._validate_limit(
            limit
        )

        query = self._get_query(
            "rental_search"
        )

        params = {
            "city": city,
            "bedrooms": bedrooms,
            "budget": budget,
            "limit": limit,
        }

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    query,
                    params,
                )

                return self._rows_to_dicts(
                    cur,
                    cur.fetchall(),
                )

    # ------------------------------------------------------------------
    # Agent lookup
    # ------------------------------------------------------------------

    def get_agent(
        self,
        agent_id: str,
    ) -> dict[str, Any] | None:
        """Return one active agent by exact agent ID."""

        if not isinstance(agent_id, str):
            raise TypeError(
                "agent_id must be a string"
            )

        agent_id = agent_id.strip()

        if not agent_id:
            raise ValueError(
                "agent_id is required"
            )

        query = self._get_query(
            "agent_lookup"
        )

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {"agent_id": agent_id},
                )

                return self._row_to_dict(
                    cur,
                    cur.fetchone(),
                )

    def get_agents_for_property(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """Return active agents assigned to an exact property ID."""

        if not isinstance(property_id, str):
            raise TypeError(
                "property_id must be a string"
            )

        property_id = property_id.strip()

        if not property_id:
            raise ValueError(
                "property_id is required"
            )

        query = self._get_query(
            "property_agents"
        )

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {"property_id": property_id},
                )

                return self._rows_to_dicts(
                    cur,
                    cur.fetchall(),
                )


# ======================================================================
# SMOKE TEST
# ======================================================================

if __name__ == "__main__":

    repo = PostgresPropertyRepository()

    print("=" * 80)
    print("POSTGRES PROPERTY REPOSITORY SMOKE TEST")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. EXACT PROPERTY
    # ------------------------------------------------------------------

    print("\n1. EXACT PROPERTY")

    property_data = repo.get_property(
        "LHR-DHA-APT-002"
    )

    print(property_data)

    # ------------------------------------------------------------------
    # 2. PROPERTY NAME LOOKUP
    # ------------------------------------------------------------------

    print("\n2. PROPERTY NAME LOOKUP")

    property_data = repo.get_property_by_name(
        "Horizon Heights Apartment"
    )

    print(property_data)

    # ------------------------------------------------------------------
    # 3. STRUCTURED SEARCH
    # ------------------------------------------------------------------

    print("\n3. STRUCTURED SEARCH")

    results = repo.search(
        budget=40_000_000,
        city="Lahore",
        area="DHA",
        bedrooms=3,
        purpose="Purchase",
        limit=10,
    )

    print(
        f"Rows found: {len(results)}"
    )

    for item in results:
        print(item)

    # ------------------------------------------------------------------
    # 4. NATURAL LANGUAGE SEARCH
    # ------------------------------------------------------------------

    print("\n4. NATURAL-LANGUAGE SEARCH")

    results = repo.search_question(
        "Lahore mein DHA mein "
        "3 bedroom apartment "
        "4 crore ke andar chahiye."
    )

    print(
        f"Rows found: {len(results)}"
    )

    for item in results:
        print(item)

    # ------------------------------------------------------------------
    # 5. CHEAPER ALTERNATIVES
    # ------------------------------------------------------------------

    print("\n5. CHEAPER ALTERNATIVES")

    cheaper = repo.get_cheaper_alternatives(
        budget=40_000_000,
        city="Lahore",
        area="DHA",
        bedrooms=3,
        purpose="Purchase",
        limit=10,
    )

    print(
        f"Rows found: {len(cheaper)}"
    )

    for item in cheaper:
        print(item)

    # ------------------------------------------------------------------
    # 6. RENTAL SEARCH
    # ------------------------------------------------------------------

    print("\n6. RENTAL SEARCH")

    rentals = repo.search_rentals(
        city="Lahore",
        bedrooms=3,
        limit=10,
    )

    print(
        f"Rental rows found: {len(rentals)}"
    )

    for item in rentals:
        print(item)

    print("\n" + "=" * 80)
    print("SMOKE TEST COMPLETED")
    print("=" * 80)
