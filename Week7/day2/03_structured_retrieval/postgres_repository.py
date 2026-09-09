import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv


load_dotenv()


# ==============================================================================
# Priority Order for Constraint Relaxation (Lowest Penalty = Relaxes First):
# 1. Bedroom (w=1.0): Most flexible; buyers easily consider ±1 bed.
# 2. Budget (w=2.0): Moderately flexible within strict tiered band.
# 3. Property Type (w=3.0): Less flexible; switching type (House vs Apt) is significant.
# 4. Area (w=4.0): Least flexible; buyer strongly prefers target area/neighborhood.
# ==============================================================================
DEFAULT_WEIGHT_BEDROOM = 1.0
DEFAULT_WEIGHT_BUDGET = 2.0
DEFAULT_WEIGHT_TYPE = 3.0
DEFAULT_WEIGHT_AREA = 4.0

# Budget Relaxation Tiers & Absolute Caps (PKR)
PURCHASE_BUDGET_TIERS = [
    (30_000_000, 0.15, 3_000_000),    # Economy (< 3 Crore): 15% tolerance, capped at 30 Lakh
    (60_000_000, 0.10, 4_500_000),    # Mid (3-6 Crore): 10% tolerance, capped at 45 Lakh
    (float("inf"), 0.05, 5_000_000),  # Luxury (> 6 Crore): 5% tolerance, capped at 50 Lakh
]

RENTAL_BUDGET_TIERS = [
    (120_000, 0.15, 15_000),          # Economy (< 1.2 Lakh): 15% tolerance, capped at 15k
    (200_000, 0.10, 18_000),          # Mid (1.2-2 Lakh): 10% tolerance, capped at 18k
    (float("inf"), 0.08, 25_000),     # Luxury (> 2 Lakh): 8% tolerance, capped at 25k
]


def compute_allowed_budget_increase(
    budget: int | float | Decimal | None,
    purpose: str | None = "Purchase",
) -> float:
    """
    Computes maximum allowed budget increase using tiered tolerance bands
    and absolute PKR caps. Returns min(budget * tolerance_pct, absolute_cap_pkr).
    Prevents unrealistic windows (e.g. 12 Crore on 80 Crore).
    """
    if budget is None:
        return 0.0
    try:
        b = float(budget)
    except (ValueError, TypeError):
        return 0.0
    if b <= 0:
        return 0.0

    p = (purpose or "Purchase").strip().lower()
    is_rental = p == "rental" or (b <= 1_000_000 and p != "purchase")
    tiers = RENTAL_BUDGET_TIERS if is_rental else PURCHASE_BUDGET_TIERS

    for max_budget, tolerance_pct, absolute_cap in tiers:
        if b <= max_budget:
            return min(b * tolerance_pct, float(absolute_cap))
    return min(b * 0.05, 5_000_000.0)


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
        "available_cities",
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

    def list_available_cities(self, purpose: str | None = None) -> list[str]:
        """Return distinct cities that currently have verified available inventory, optionally filtered by purpose."""
        if not purpose:
            query = self._get_query("available_cities")
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    return [str(row[0]).strip() for row in cur.fetchall() if row[0]]

        norm_purpose = "rental" if str(purpose).strip().lower() in ("rent", "rental") else str(purpose).strip().lower()
        sql = """
            SELECT DISTINCT l.city
            FROM properties p
            JOIN locations l ON l.location_id = p.location_id
            JOIN prices pr ON pr.property_id = p.property_id
            WHERE p.available = TRUE
              AND pr.verification_status = 'Verified'
              AND NULLIF(TRIM(l.city), '') IS NOT NULL
              AND LOWER(p.purpose) = %s
            ORDER BY l.city;
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (norm_purpose,))
                return [str(row[0]).strip() for row in cur.fetchall() if row[0]]

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

    @staticmethod
    def compute_distance_metrics(
        candidate: dict[str, Any],
        requested_bedrooms: int | None = None,
        requested_budget: int | float | Decimal | None = None,
        requested_area: str | None = None,
        requested_type: str | None = None,
        requested_purpose: str | None = "Purchase",
    ) -> tuple[float, float, float, float]:
        """
        Compute normalized distance metrics for candidate property.
        All metrics are strictly normalized between [0.0, 1.0].
        Returns (d_bedroom, d_budget, d_area, d_type).
        """
        # 1. Bedroom distance: min(|diff|, 3) / 3.0 (capped at 1.0)
        if requested_bedrooms is not None:
            cand_bed = candidate.get("bedrooms")
            cand_type = (candidate.get("property_type") or "").strip().lower()
            if cand_bed is None or cand_type in ("plot", "commercial", "office"):
                d_bedroom = 1.0
            else:
                diff = abs(int(cand_bed) - int(requested_bedrooms))
                d_bedroom = min(diff, 3) / 3.0
        else:
            d_bedroom = 0.0

        # 2. Budget distance: min(1.0, max(0, price - budget) / allowed_increase)
        if requested_budget is not None:
            cand_price = float(candidate.get("price") or 0)
            req_budget = float(requested_budget)
            if cand_price <= req_budget:
                d_budget = 0.0
            else:
                allowed_inc = compute_allowed_budget_increase(req_budget, requested_purpose)
                if allowed_inc > 0:
                    d_budget = min(1.0, (cand_price - req_budget) / allowed_inc)
                else:
                    d_budget = 1.0
        else:
            d_budget = 0.0

        # 3. Area distance: 0 if area matches else 1
        if requested_area is not None and requested_area.strip():
            cand_area = (candidate.get("area") or "").strip().lower()
            req_area = requested_area.strip().lower()
            if req_area in cand_area or cand_area in req_area:
                d_area = 0.0
            else:
                d_area = 1.0
        else:
            d_area = 0.0

        # 4. Type distance: 0 if property_type matches else 1
        if requested_type is not None and requested_type.strip():
            cand_type = (candidate.get("property_type") or "").strip().lower()
            req_type = requested_type.strip().lower()
            d_type = 0.0 if cand_type == req_type else 1.0
        else:
            d_type = 0.0

        # Enforce strict normalization [0.0, 1.0]
        d_bedroom = max(0.0, min(1.0, float(d_bedroom)))
        d_budget = max(0.0, min(1.0, float(d_budget)))
        d_area = max(0.0, min(1.0, float(d_area)))
        d_type = max(0.0, min(1.0, float(d_type)))

        return d_bedroom, d_budget, d_area, d_type

    def search_relaxed(
        self,
        budget=None,
        city=None,
        area=None,
        bedrooms=None,
        property_type=None,
        purpose=None,
        amenities=None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        w_bedroom: float = DEFAULT_WEIGHT_BEDROOM,
        w_budget: float = DEFAULT_WEIGHT_BUDGET,
        w_area: float = DEFAULT_WEIGHT_AREA,
        w_type: float = DEFAULT_WEIGHT_TYPE,
    ) -> dict[str, Any]:
        """
        Search properties with weighted relaxation if exact match returns 0 rows.

        Priority order (Lowest penalty = Relaxes first):
        1. Bedroom (w=1.0)
        2. Budget (w=2.0)
        3. Property Type (w=3.0)
        4. Area (w=4.0)

        Steps:
        1. Run exact query. If non-empty, return exact_matches.
        2. If 0 rows:
           - Fetch candidate properties from city and purpose.
           - HARD CUTOFF: Exclude any property where price > budget + allowed_increase.
           - Normalize all distance metrics to [0.0, 1.0].
           - Calculate score = w_bedroom * d_bedroom + w_budget * d_budget + w_area * d_area + w_type * d_type.
           - Rank candidates ascending by score.
           - Call list_available_areas() for cross-area alternatives.
        """
        exact_matches = self.search(
            budget=budget,
            city=city,
            area=area,
            bedrooms=bedrooms,
            property_type=property_type,
            purpose=purpose,
            amenities=amenities,
            limit=limit,
        )

        if exact_matches:
            return {
                "exact_matches": exact_matches,
                "relaxed_matches": [],
                "relaxed_scores": [],
                "relaxed_constraint": None,
                "relaxed_meta": {},
                "cross_area_alternatives": [],
            }

        # 1. Fetch broader candidate set for the city & purpose
        candidates = self.search(
            city=city,
            purpose=purpose,
            limit=self.MAX_SEARCH_LIMIT,
        )

        # 2. HARD BUDGET CUTOFF BEFORE SCORING
        # Candidates exceeding budget + allowed_increase are excluded entirely.
        if budget is not None:
            allowed_inc = compute_allowed_budget_increase(budget, purpose)
            max_allowed_price = float(budget) + allowed_inc
            candidates = [
                c for c in candidates
                if float(c.get("price") or 0) <= max_allowed_price
            ]

        # Filter candidates strictly for same area when area is requested
        if area:
            area_l = str(area).strip().lower()
            candidates = [
                c for c in candidates
                if str(c.get("area") or "").strip().lower() == area_l
            ]

        # Filter candidates for amenities if requested
        if amenities:
            req_amenities = {a.strip().lower() for a in amenities}
            candidates = [
                c for c in candidates
                if req_amenities.issubset({a.lower() for a in (c.get("amenities") or [])})
            ]

        # 3. Score candidates with normalized distances
        scored_candidates: list[tuple[float, dict[str, Any], tuple[float, float, float, float]]] = []
        for cand in candidates:
            d_bed, d_bud, d_ar, d_ty = self.compute_distance_metrics(
                cand,
                requested_bedrooms=bedrooms,
                requested_budget=budget,
                requested_area=area,
                requested_type=property_type,
                requested_purpose=purpose,
            )
            score = (
                w_bedroom * d_bed
                + w_budget * d_bud
                + w_area * d_ar
                + w_type * d_ty
            )
            scored_candidates.append((score, cand, (d_bed, d_bud, d_ar, d_ty)))

        # Sort by score ascending (lowest score = closest match)
        scored_candidates.sort(key=lambda item: (item[0], float(item[1].get("price") or 0)))

        relaxed_matches = [item[1] for item in scored_candidates[:limit]]
        relaxed_scores = [item[0] for item in scored_candidates[:limit]]

        # Determine primary relaxed constraint and metadata
        relaxed_constraint = None
        relaxed_meta = {}
        if scored_candidates:
            best_score, best_cand, (d_bed, d_bud, d_ar, d_ty) = scored_candidates[0]
            if d_bed > 0:
                relaxed_constraint = "bedrooms"
                relaxed_meta = {
                    "original_bedrooms": bedrooms,
                    "relaxed_bedrooms": best_cand.get("bedrooms"),
                    "score": best_score,
                }
            elif d_bud > 0:
                relaxed_constraint = "budget"
                relaxed_meta = {
                    "original_budget": budget,
                    "relaxed_price": float(best_cand.get("price") or 0),
                    "score": best_score,
                }
            elif d_ty > 0:
                relaxed_constraint = "property_type"
                relaxed_meta = {
                    "original_property_type": property_type,
                    "relaxed_property_type": best_cand.get("property_type"),
                    "score": best_score,
                }
            elif d_ar > 0:
                relaxed_constraint = "area"
                relaxed_meta = {
                    "original_area": area,
                    "relaxed_area": best_cand.get("area"),
                    "score": best_score,
                }

        # 4. Cross-area alternatives using list_available_areas
        cross_area_alternatives: list[str] = []
        if city:
            cross_areas = self.list_available_areas(
                city=city,
                property_type=property_type,
                purpose=purpose,
                budget=budget,
                bedrooms=bedrooms,
            )
            if not cross_areas and bedrooms is not None:
                cross_areas = self.list_available_areas(
                    city=city,
                    property_type=property_type,
                    purpose=purpose,
                    budget=budget,
                )
            if area:
                area_clean = area.strip().lower()
                cross_area_alternatives = [
                    a for a in cross_areas
                    if area_clean not in a.lower() and a.lower() not in area_clean
                ]
            else:
                cross_area_alternatives = cross_areas

        return {
            "exact_matches": [],
            "relaxed_matches": relaxed_matches,
            "relaxed_scores": relaxed_scores,
            "relaxed_constraint": relaxed_constraint,
            "relaxed_meta": relaxed_meta,
            "cross_area_alternatives": cross_area_alternatives,
        }

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

    def budget_area_options(self, *, city, purpose=None, budget=None, property_type=None):
        """Aggregate ALL verified inventory, ranking affordable areas by proximity.

        Budget is a hard ceiling. Above-budget inventory is returned separately
        as the cheapest alternative, never silently advertised as a match.
        """
        budget = self._validate_optional_budget(budget)
        city = self._validate_optional_string(city, "city")
        purpose = self._validate_optional_string(purpose, "purpose")
        property_type = self._validate_optional_string(property_type, "property_type")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT l.area, MIN(pr.price) AS min_price, MAX(pr.price) AS max_price,
                           MAX(CASE WHEN %(budget)s::numeric IS NULL OR pr.price <= %(budget)s
                                    THEN pr.price END) AS match_price
                    FROM properties p
                    JOIN locations l ON p.location_id = l.location_id
                    JOIN prices pr ON p.property_id = pr.property_id
                    WHERE p.available = TRUE AND pr.verification_status = 'Verified'
                      AND l.city ILIKE %(city)s
                      AND (%(purpose)s::text IS NULL OR p.purpose ILIKE %(purpose)s)
                      AND (%(property_type)s::text IS NULL OR p.property_type ILIKE %(property_type)s)
                    GROUP BY l.area
                    ORDER BY MIN(pr.price), l.area
                """, {"city": city, "purpose": purpose, "budget": budget, "property_type": property_type})
                rows = self._rows_to_dicts(cur, cur.fetchall())
        matches = [row for row in rows if row["match_price"] is not None]
        if budget is not None:
            matches.sort(key=lambda row: (abs(Decimal(str(budget)) - Decimal(str(row["match_price"]))), row["area"]))
        return {"areas": matches, "cheapest": rows[0] if rows else None}

    def list_available_areas(
        self,
        city: str | None = None,
        property_type: str | None = None,
        purpose: str | None = None,
        budget: int | float | Decimal | None = None,
        limit: int = 6,
        bedrooms: int | None = None,
    ) -> list[str]:
        """
        Dynamically return distinct available areas in PostgreSQL for a city
        matching optional property filters. Guarantees 100% search/list consistency
        by querying self.search directly. No area names are hardcoded.
        """
        results = self.search(
            budget=budget,
            city=city,
            area=None,
            bedrooms=bedrooms,
            property_type=property_type,
            purpose=purpose,
            limit=self.MAX_SEARCH_LIMIT,
        )
        areas: list[str] = []
        if budget is not None:
            results.sort(key=lambda row: abs(budget - (row.get("price") or 0)))
        for r in results:
            area_name = r.get("area")
            if area_name and area_name not in areas:
                areas.append(area_name)
                if len(areas) >= limit:
                    break
        return areas

    def get_city_price_summary(self, city: str, property_type: str | None = None, purpose: str | None = None) -> list[dict[str, Any]]:
        """Return price summary by property_type and purpose for a city with verified prices."""
        if not city:
            return []
        sql = """
            SELECT p.property_type, p.purpose, MIN(pr.price) as min_price, MAX(pr.price) as max_price, COUNT(*) as count
            FROM properties p
            JOIN locations l ON p.location_id = l.location_id
            JOIN prices pr ON p.property_id = pr.property_id
            WHERE l.city ILIKE %s AND p.available = TRUE AND pr.verification_status = 'Verified'
        """
        params: list[Any] = [city.strip()]
        if property_type:
            sql += " AND p.property_type ILIKE %s"
            params.append(property_type.strip())
        if purpose:
            sql += " AND p.purpose ILIKE %s"
            params.append(purpose.strip())
        sql += """
            GROUP BY p.property_type, p.purpose
            ORDER BY p.purpose, p.property_type
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_minimum_price(self, city: str, purpose: str = "Purchase", property_type: str | None = None) -> dict[str, Any] | None:
        """Return lowest price verified listing for a city and purpose, optionally filtered by property type."""
        if not city:
            return None
        sql = """
            SELECT p.property_id, p.name AS property_name, l.area, l.city, p.property_type,
                   p.bedrooms, p.bathrooms, pr.price, p.purpose
            FROM properties p
            JOIN locations l ON p.location_id = l.location_id
            JOIN prices pr ON p.property_id = pr.property_id
            WHERE l.city ILIKE %s AND p.available = TRUE AND pr.verification_status = 'Verified'
        """
        params: list[Any] = [city.strip()]
        if purpose:
            sql += " AND p.purpose ILIKE %s"
            params.append(purpose.strip())
        if property_type:
            sql += " AND p.property_type ILIKE %s"
            params.append(property_type.strip())
        sql += " ORDER BY pr.price ASC LIMIT 1"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if not row:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))


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
