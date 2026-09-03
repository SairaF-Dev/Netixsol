from __future__ import annotations

import importlib.util
import logging
import os
import re
import sys
from difflib import SequenceMatcher
from decimal import Decimal
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class Day2Adapter:
    """
    Bridge between Day 3 conversation logic and verified Day 2 data.

    Important rule:
    The LLM decides what the user means, but PostgreSQL-backed Day 2 data
    decides which real cities/areas/properties actually exist.
    """

    SEARCH_FIELDS = {
        "budget",
        "city",
        "area",
        "bedrooms",
        "property_type",
        "purpose",
        "amenities",
    }

    DEFAULT_CANDIDATE_LIMIT = 100
    MAX_CANDIDATE_LIMIT = 200

    def _candidate_limit(
        self,
    ) -> int:
        """
        Candidate pool size is a system-performance setting, not a
        business rule. Sara still presents only a small human-sized batch.
        """

        raw = os.getenv(
            "SARA_MAX_CANDIDATES"
        )

        if raw is None:
            return self.DEFAULT_CANDIDATE_LIMIT

        try:
            value = int(raw)
        except (TypeError, ValueError):
            return self.DEFAULT_CANDIDATE_LIMIT

        return max(
            20,
            min(
                self.MAX_CANDIDATE_LIMIT,
                value,
            ),
        )

    def __init__(
        self,
        repository=None,
        recommendation_engine=None,
    ):
        self.repository = (
            repository
            or self._load_repository()
        )

        if recommendation_engine is not None:
            self.recommendation_engine = recommendation_engine
        elif repository is not None:
            # When a repository is explicitly injected (for tests or
            # alternate runtimes), do not require DAY2_ROOT only to
            # discover an optional recommendation engine.
            self.recommendation_engine = None
        else:
            self.recommendation_engine = self._load_recommendation_engine(
                self.repository
            )

        self._location_catalog_cache: list[
            dict[str, str]
        ] | None = None

    # ------------------------------------------------------------------
    # Day 2 loading
    # ------------------------------------------------------------------

    def _day2_root(self) -> Path:
        root = os.getenv("DAY2_ROOT")

        if not root:
            raise ValueError(
                "DAY2_ROOT is not configured"
            )

        path = Path(root)

        if not path.exists():
            raise FileNotFoundError(
                f"DAY2_ROOT not found: {path}"
            )

        return path

    def _load_repository(self):
        path = (
            self._day2_root()
            / "03_structured_retrieval"
            / "postgres_repository.py"
        )

        spec = importlib.util.spec_from_file_location(
            "day2_postgres_repository",
            path,
        )

        if not spec or not spec.loader:
            raise ImportError(
                "cannot load Day2 repository"
            )

        module = importlib.util.module_from_spec(
            spec
        )

        spec.loader.exec_module(module)

        return module.PostgresPropertyRepository()

    def _load_recommendation_engine(
        self,
        repository,
    ):
        folder = (
            self._day2_root()
            / "04_recommendation"
        )

        if str(folder) not in sys.path:
            sys.path.insert(
                0,
                str(folder),
            )

        try:
            from recommendation_engine import (
                RecommendationEngine,
            )

            return RecommendationEngine(
                repository
            )

        except Exception:
            # Recommendation engine is optional for Day 3 runtime.
            # Structured retrieval must continue to work.
            logger.exception("Optional Day 2 recommendation engine failed to load")
            return None

    def check_database(
        self,
    ) -> bool:
        """Lightweight PostgreSQL readiness check without reading business rows."""

        connect = getattr(
            self.repository,
            "_connect",
            None,
        )

        if not callable(connect):
            return False

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1"
                )
                row = cur.fetchone()

        return bool(
            row
            and row[0] == 1
        )

    # ------------------------------------------------------------------
    # Main property retrieval
    # ------------------------------------------------------------------

    def execute_plan(
        self,
        plan,
        recommendation: bool = False,
    ) -> list[dict[str, Any]]:
        if plan.needs_clarification:
            return []

        filters = self._sanitize(
            plan.required
        )

        if (
            recommendation
            and self.recommendation_engine
        ):
            results = (
                self.recommendation_engine
                .recommend(
                    budget=filters.get("budget"),
                    city=filters.get("city"),
                    area=filters.get("area"),
                    bedrooms=filters.get("bedrooms"),
                    property_type=filters.get(
                        "property_type"
                    ),
                    purpose=filters.get("purpose"),
                    desired_amenities=filters.get(
                        "amenities"
                    ),
                    investment_goal=(
                        plan.preferred.get(
                            "investment_goal"
                        )
                    ),
                    limit=self._candidate_limit(),
                )
            )

        elif (
            plan.comparison_field == "price"
            and plan.comparison_operator == "lt"
        ):
            results = (
                self.repository
                .get_cheaper_alternatives(
                    budget=plan.comparison_value,
                    city=filters.get("city"),
                    area=filters.get("area"),
                    bedrooms=filters.get(
                        "bedrooms"
                    ),
                    purpose=filters.get("purpose"),
                    limit=self._candidate_limit(),
                )
            )

        else:
            results = self.repository.search(
                **filters,
                limit=self._candidate_limit(),
            )

            if plan.comparison_field:
                results = self._numeric_compare(
                    results,
                    plan.comparison_field,
                    plan.comparison_operator,
                    plan.comparison_value,
                )

        results = self._exclude(
            results,
            plan.excluded,
        )

        results = self._rank_soft_preferences(
            results,
            plan.preferred,
        )

        return results[
            : self._candidate_limit()
        ]

    def get_property(
        self,
        property_id,
    ):
        return self.repository.get_property(
            property_id
        )

    def get_property_by_name(
        self,
        property_name: str,
    ):
        """Return one exact verified property by canonical name."""

        native = getattr(
            self.repository,
            "get_property_by_name",
            None,
        )

        if not callable(native):
            return None

        return native(
            property_name
        )

    def get_property_amenities(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """Return current structured amenities for one exact property."""

        return self._get_property_linked_rows(
            """
            SELECT
                amenity,
                details
            FROM amenities
            WHERE property_id = %s
            ORDER BY amenity ASC
            """,
            property_id,
        )

    def get_payment_plans(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """Return verified structured payment-plan rows for a property."""

        return self._get_property_linked_rows(
            """
            SELECT
                plan_name,
                summary,
                notes,
                status
            FROM payment_plans
            WHERE property_id = %s
            ORDER BY payment_plan_id ASC
            """,
            property_id,
        )

    def get_developer(
        self,
        property_id: str,
    ) -> dict[str, Any] | None:
        native = getattr(
            self.repository,
            "get_developer",
            None,
        )

        if not callable(native):
            return None

        return native(
            property_id
        )

    def get_agents_for_property(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        native = getattr(
            self.repository,
            "get_agents_for_property",
            None,
        )

        if not callable(native):
            return []

        return list(
            native(
                property_id
            )
            or []
        )

    def _get_property_linked_rows(
        self,
        query: str,
        property_id: str,
    ) -> list[dict[str, Any]]:
        if not isinstance(
            property_id,
            str,
        ):
            return []

        property_id = property_id.strip()

        if not property_id:
            return []

        connect = getattr(
            self.repository,
            "_connect",
            None,
        )

        if not callable(connect):
            return []

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (property_id,),
                )

                columns = [
                    item.name
                    for item in (
                        cur.description
                        or []
                    )
                ]

                return [
                    dict(
                        zip(
                            columns,
                            row,
                        )
                    )
                    for row in cur.fetchall()
                ]

    # ------------------------------------------------------------------
    # Verified selected-property facts
    # ------------------------------------------------------------------

    def get_nearby_schools(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return only school records explicitly linked to this property.

        Distances are not inferred from another property in the same area.
        """

        return self._get_nearby_entities(
            table_name="schools",
            id_column="school_id",
            property_id=property_id,
        )

    def get_nearby_hospitals(
        self,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return only hospital records explicitly linked to this property.
        """

        return self._get_nearby_entities(
            table_name="hospitals",
            id_column="hospital_id",
            property_id=property_id,
        )

    def get_verification_info(
        self,
        property_id: str,
    ) -> dict[str, Any] | None:
        """
        Re-read the exact property through Day 2's verified lookup.

        exact_property only returns rows whose price record has
        verification_status='Verified'.
        """

        if not isinstance(property_id, str):
            return None

        property_id = property_id.strip()

        if not property_id:
            return None

        row = self.repository.get_property(
            property_id
        )

        if not row:
            return None

        return {
            "property_id": row.get("property_id"),
            "property_name": row.get("property_name"),
            "verification_status": row.get(
                "verification_status"
            ),
            "verified_on": row.get("verified_on"),
            "available": row.get("available"),
            "status": row.get("status"),
            "price": row.get("price"),
            "currency": row.get("currency"),
            "transaction_type": row.get(
                "transaction_type"
            ),
            "price_period": row.get("price_period"),
        }

    def _get_nearby_entities(
        self,
        table_name: str,
        id_column: str,
        property_id: str,
    ) -> list[dict[str, Any]]:
        """
        Query Day 2 PostgreSQL directly for property-linked nearby facts.

        Table/column names are chosen only from internal allowlisted calls;
        user input is never interpolated into identifiers.
        """

        allowed = {
            ("schools", "school_id"),
            ("hospitals", "hospital_id"),
        }

        if (
            table_name,
            id_column,
        ) not in allowed:
            raise ValueError(
                "unsupported nearby-entity table"
            )

        if not isinstance(property_id, str):
            return []

        property_id = property_id.strip()

        if not property_id:
            return []

        connector = getattr(
            self.repository,
            "_connect",
            None,
        )

        if not callable(connector):
            return []

        query = f"""
            SELECT
                {id_column} AS entity_id,
                name,
                area,
                city,
                type,
                distance_km,
                reference_property
            FROM {table_name}
            WHERE reference_property = %(property_id)s
            ORDER BY
                distance_km ASC NULLS LAST,
                name ASC
        """

        with connector() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {
                        "property_id": property_id,
                    },
                )

                rows = cur.fetchall()

                columns = [
                    description[0]
                    for description
                    in cur.description
                ]

        return [
            dict(
                zip(
                    columns,
                    row,
                )
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Verified location intelligence
    # ------------------------------------------------------------------

    def resolve_locations(
        self,
        text: str,
        city_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve city/area names mentioned in a user message against the
        VERIFIED Day 2 property catalog.

        No city, society, phase or sector names are hard-coded here.

        Returns for example:
            {"city": "Islamabad"}
            {"area": "Bahria Town"}
            {"city": "Islamabad", "area": "F-11"}
        """

        if not isinstance(text, str):
            return {}

        normalized_text = self._normalize_text(
            text
        )

        if not normalized_text:
            return {}

        catalog = self._location_catalog()

        cities = sorted(
            {
                row["city"]
                for row in catalog
                if row.get("city")
            },
            key=lambda value: len(
                self._normalize_text(value)
            ),
            reverse=True,
        )

        areas = sorted(
            {
                row["area"]
                for row in catalog
                if row.get("area")
            },
            key=lambda value: len(
                self._normalize_text(value)
            ),
            reverse=True,
        )

        resolved: dict[str, str] = {}

        # Exact catalog phrase in current message.
        for city in cities:
            if self._phrase_in_text(
                city,
                normalized_text,
            ):
                resolved["city"] = city
                break

        for area in areas:
            if self._phrase_in_text(
                area,
                normalized_text,
            ):
                resolved["area"] = area
                break

        # Conservative short-name recovery for areas.
        #
        # Examples derived from VERIFIED catalog values:
        #   "Bahria Town" -> "bahria"
        #   "DHA Phase 6" -> "dha 6"
        #
        # No actual place names are hard-coded. An alias is accepted only
        # when it maps uniquely to one verified catalog area.
        if "area" not in resolved:
            aliases: dict[str, set[str]] = {}

            for area in areas:
                for alias in self._safe_area_aliases(
                    area
                ):
                    aliases.setdefault(
                        alias,
                        set(),
                    ).add(area)

            # Prefer longer aliases first so a more specific verified
            # phrase wins over a shorter shorthand.
            for alias in sorted(
                aliases,
                key=len,
                reverse=True,
            ):
                matches = aliases[alias]

                if (
                    len(matches) == 1
                    and self._phrase_in_text(
                        alias,
                        normalized_text,
                    )
                ):
                    resolved["area"] = next(
                        iter(matches)
                    )
                    break

        # ----------------------------------------------------------
        # Conservative typo recovery against VERIFIED catalog values.
        # ----------------------------------------------------------
        # This allows ordinary speech/STT errors such as "Lahor" or
        # "Bagria Town" without hard-coding any actual location mapping.
        if "city" not in resolved:
            city_match = self._fuzzy_catalog_phrase(
                normalized_text,
                cities,
                minimum_score=0.86,
                minimum_margin=0.08,
            )

            if city_match:
                resolved["city"] = city_match

        if "area" not in resolved:
            active_city = (
                resolved.get("city")
                or city_hint
            )
            candidate_areas = [
                row["area"]
                for row in catalog
                if (
                    row.get("area")
                    and (
                        not active_city
                        or self._normalize_text(row.get("city", ""))
                        == self._normalize_text(active_city)
                    )
                )
            ]

            area_match = self._fuzzy_catalog_phrase(
                normalized_text,
                candidate_areas,
                minimum_score=0.80,
                minimum_margin=0.08,
            )

            if area_match:
                resolved["area"] = area_match

        # ----------------------------------------------------------
        # City-scoped structural fragment recovery
        # ----------------------------------------------------------
        # Examples:
        #   "Lahore mein phase5 mein dikhao"
        #   "phase 6 mein"
        #
        # The parent society name is NOT guessed. We search the VERIFIED
        # catalog for areas containing the requested phase/sector/block.
        # If exactly one area matches inside the active city, it is safe
        # to resolve. If multiple match, return candidates so the chatbot
        # can ask a clarification question.
        if "area" not in resolved:
            fragment = self._extract_location_fragment(
                normalized_text
            )

            if fragment:
                active_city = (
                    resolved.get("city")
                    or city_hint
                )

                candidates = self._match_fragment_areas(
                    fragment=fragment,
                    city=active_city,
                    catalog=catalog,
                )

                if len(candidates) == 1:
                    resolved["area"] = candidates[0]

                elif len(candidates) > 1:
                    resolved["_area_candidates"] = candidates

        # If an area is verified but the city was not explicitly spoken,
        # infer the city ONLY when Day 2 data proves the mapping is unique,
        # or when the active city_hint is one of the verified matches.
        if (
            resolved.get("area")
            and not resolved.get("city")
        ):
            area_value = resolved["area"]
            matching_cities = sorted(
                {
                    row["city"]
                    for row in catalog
                    if (
                        self._normalize_text(
                            row.get("area", "")
                        )
                        ==
                        self._normalize_text(
                            area_value
                        )
                    )
                    and row.get("city")
                },
                key=lambda value: value.casefold(),
            )

            if (
                city_hint
                and any(
                    self._normalize_text(city_hint)
                    ==
                    self._normalize_text(candidate)
                    for candidate in matching_cities
                )
            ):
                resolved["city"] = next(
                    candidate
                    for candidate in matching_cities
                    if (
                        self._normalize_text(candidate)
                        ==
                        self._normalize_text(city_hint)
                    )
                )

            elif len(matching_cities) == 1:
                resolved["city"] = matching_cities[0]

        return resolved

    def _fuzzy_catalog_phrase(
        self,
        normalized_text: str,
        values: list[str],
        *,
        minimum_score: float,
        minimum_margin: float,
    ) -> str | None:
        """Find one clearly dominant fuzzy phrase from verified values."""
        text_tokens = self._normalize_text(
            normalized_text
        ).replace("-", " ").split()

        if not text_tokens:
            return None

        scores: list[tuple[float, str]] = []

        for value in dict.fromkeys(values):
            if not isinstance(value, str) or not value.strip():
                continue

            value_norm = self._normalize_text(value).replace("-", " ")
            value_tokens = value_norm.split()

            if not value_tokens:
                continue

            widths = {
                max(1, len(value_tokens) - 1),
                len(value_tokens),
                len(value_tokens) + 1,
            }

            best = 0.0

            for width in widths:
                if width > len(text_tokens):
                    continue

                for start in range(
                    0,
                    len(text_tokens) - width + 1,
                ):
                    phrase = " ".join(
                        text_tokens[start:start + width]
                    )

                    ratio = SequenceMatcher(
                        None,
                        phrase,
                        value_norm,
                    ).ratio()

                    best = max(best, ratio)

            if best:
                scores.append((best, value))

        if not scores:
            return None

        scores.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_value = scores[0]
        second_score = (
            scores[1][0]
            if len(scores) > 1
            else 0.0
        )

        if best_score < minimum_score:
            return None

        if (
            len(scores) > 1
            and (best_score - second_score) < minimum_margin
        ):
            return None

        return best_value

    def _extract_location_fragment(
        self,
        normalized_text: str,
    ) -> tuple[str, str] | None:
        """
        Extract a generic phase/sector/block identifier.

        Handles both spaced and compact forms:
            phase 5 / phase5
            sector F-11 / sectorF-11
            block C / blockC
        """

        if not isinstance(
            normalized_text,
            str,
        ):
            return None

        patterns = (
            (
                "phase",
                r"\bphase\s*[-#]?\s*([a-z0-9]+)\b",
            ),
            (
                "sector",
                r"\bsector\s*[-#]?\s*([a-z0-9]+(?:[-/][a-z0-9]+)?)\b",
            ),
            (
                "block",
                r"\bblock\s*[-#]?\s*([a-z0-9]+)\b",
            ),
        )

        for kind, pattern in patterns:
            match = re.search(
                pattern,
                normalized_text,
                flags=re.IGNORECASE,
            )

            if match:
                return (
                    kind,
                    match.group(1).casefold(),
                )

        return None

    def _match_fragment_areas(
        self,
        fragment: tuple[str, str],
        city: str | None,
        catalog: list[dict[str, str]],
    ) -> list[str]:
        """
        Match a structural fragment against verified catalog areas.

        If city is known, matching is scoped to that city.
        """

        kind, identifier = fragment

        if not kind or not identifier:
            return []

        city_norm = (
            self._normalize_text(city)
            if city
            else None
        )

        matched: list[str] = []
        seen: set[str] = set()

        for row in catalog:
            row_city = row.get("city")
            area = row.get("area")

            if not isinstance(
                row_city,
                str,
            ):
                continue

            if not isinstance(
                area,
                str,
            ):
                continue

            if (
                city_norm
                and self._normalize_text(row_city)
                != city_norm
            ):
                continue

            area_norm = self._normalize_text(
                area
            )

            pattern = (
                rf"\b{re.escape(kind)}\s*[-#]?\s*"
                rf"{re.escape(identifier)}\b"
            )

            if not re.search(
                pattern,
                area_norm,
                flags=re.IGNORECASE,
            ):
                continue

            key = self._normalize_text(area)

            if key in seen:
                continue

            seen.add(key)
            matched.append(area)

        return sorted(
            matched,
            key=lambda value: value.casefold(),
        )

    def list_cities(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[str]:
        """List DISTINCT verified cities with matching inventory.

        Prefer a repository-native distinct-city API when available. The
        fallback uses the normal verified search path and is sufficient for
        smaller datasets.
        """
        query_filters = self._sanitize(filters or {})
        query_filters.pop("city", None)
        query_filters.pop("area", None)

        native = getattr(self.repository, "list_cities", None)

        if callable(native):
            rows = native(**query_filters)

            cities = []
            for item in rows or []:
                value = (
                    item.get("city")
                    if isinstance(item, dict)
                    else item
                )

                if isinstance(value, str) and value.strip():
                    cities.append(value.strip())

            return sorted(
                dict.fromkeys(cities),
                key=lambda value: value.casefold(),
            )

        rows = self.repository.search(
            **query_filters,
            limit=self._candidate_limit(),
        )

        cities: list[str] = []
        seen: set[str] = set()

        for row in rows:
            city = row.get("city")
            if not isinstance(city, str):
                continue

            city = city.strip()
            if not city:
                continue

            key = self._normalize_text(city)
            if key in seen:
                continue

            seen.add(key)
            cities.append(city)

        return sorted(
            cities,
            key=lambda value: value.casefold(),
        )

    def list_areas(
        self,
        city: str,
        filters: dict[str, Any] | None = None,
    ) -> list[str]:
        """List DISTINCT verified areas with matching inventory in a city.

        Prefer a repository-native distinct-area API when available so the
        result remains complete for large datasets. Fallback uses verified
        repository.search().
        """
        if not isinstance(city, str) or not city.strip():
            return []

        city = city.strip()
        query_filters = self._sanitize(filters or {})
        query_filters.pop("area", None)
        query_filters["city"] = city

        native = getattr(self.repository, "list_areas", None)

        if callable(native):
            rows = native(**query_filters)

            areas = []
            for item in rows or []:
                value = (
                    item.get("area")
                    if isinstance(item, dict)
                    else item
                )

                if isinstance(value, str) and value.strip():
                    areas.append(value.strip())

            return sorted(
                dict.fromkeys(areas),
                key=lambda value: value.casefold(),
            )

        rows = self.repository.search(
            **query_filters,
            limit=self._candidate_limit(),
        )

        areas: list[str] = []
        seen: set[str] = set()

        for row in rows:
            area = row.get("area")
            if not isinstance(area, str):
                continue

            area = area.strip()
            if not area:
                continue

            key = self._normalize_text(area)
            if key in seen:
                continue

            seen.add(key)
            areas.append(area)

        return sorted(
            areas,
            key=lambda value: value.casefold(),
        )

    def refresh_location_catalog(
        self,
    ) -> None:
        """
        Clear the small in-process location cache.

        Useful if Day 2 property/location data is updated while the
        Day 3 process is still running.
        """

        self._location_catalog_cache = None

    def _location_catalog(
        self,
    ) -> list[dict[str, str]]:
        if self._location_catalog_cache is not None:
            return list(self._location_catalog_cache)

        native = getattr(
            self.repository,
            "list_locations",
            None,
        )

        if callable(native):
            rows = native()
        else:
            rows = self.repository.search(
                limit=self._candidate_limit(),
            )

        catalog: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for row in rows or []:
            if not isinstance(row, dict):
                continue

            city = row.get("city")
            area = row.get("area")

            if not isinstance(city, str) or not isinstance(area, str):
                continue

            city = city.strip()
            area = area.strip()

            if not city or not area:
                continue

            key = (
                self._normalize_text(city),
                self._normalize_text(area),
            )

            if key in seen:
                continue

            seen.add(key)
            catalog.append(
                {
                    "city": city,
                    "area": area,
                }
            )

        self._location_catalog_cache = catalog
        return list(catalog)

    def _sanitize(
        self,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            key: value
            for key, value in values.items()
            if (
                key in self.SEARCH_FIELDS
                and value not in (
                    None,
                    "",
                    [],
                )
            )
        }

    def _normalize(
        self,
        value: Any,
    ) -> str:
        return str(
            value
        ).strip().casefold()

    def _normalize_text(
        self,
        value: Any,
    ) -> str:
        text = str(
            value
        ).strip().casefold()

        # Keep letters/numbers/hyphens; normalize punctuation/spacing.
        text = re.sub(
            r"[^a-z0-9\-]+",
            " ",
            text,
        )

        return " ".join(
            text.split()
        )

    def _phrase_in_text(
        self,
        phrase: str,
        normalized_text: str,
    ) -> bool:
        normalized_phrase = self._normalize_text(
            phrase
        )

        if not normalized_phrase:
            return False

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(
                normalized_phrase
            )
            + r"(?![a-z0-9])"
        )

        return (
            re.search(
                pattern,
                normalized_text,
            )
            is not None
        )

    def _safe_area_aliases(
        self,
        area: str,
    ) -> list[str]:
        """
        Generate conservative aliases from a VERIFIED area value.

        Examples:
            "Bahria Town" -> ["bahria"]
            "DHA Phase 6" -> ["dha 6"]

        These are structural aliases only. Actual location names always
        originate from the Day 2 catalog.
        """

        normalized = self._normalize_text(
            area
        )

        if not normalized:
            return []

        aliases: set[str] = set()
        words = normalized.split()

        generic_suffixes = {
            "town",
            "city",
            "estate",
            "estates",
            "society",
            "residency",
            "residences",
        }

        if (
            len(words) >= 2
            and words[-1] in generic_suffixes
        ):
            alias = " ".join(
                words[:-1]
            ).strip()

            if len(alias) >= 3:
                aliases.add(alias)

        # Generic phase shorthand:
        #   "<name> Phase <id>" -> "<name> <id>"
        phase_match = re.fullmatch(
            r"(.+?)\s+phase\s+([a-z0-9]+)",
            normalized,
            flags=re.IGNORECASE,
        )

        if phase_match:
            prefix = phase_match.group(1).strip()
            identifier = phase_match.group(2).strip()

            if prefix and identifier:
                aliases.add(
                    f"{prefix} {identifier}"
                )

        # Generic sector-style shorthand from VERIFIED catalog values.
        # Examples:
        #   F-10 -> "f 10", "f10"
        #   B-17 -> "b 17", "b17"
        #
        # This is structural normalization only; actual area names still
        # originate from the verified Day 2 catalog.
        sector_code = re.fullmatch(
            r"([a-z]+)-([0-9]+[a-z]?)",
            normalized,
            flags=re.IGNORECASE,
        )

        if sector_code:
            prefix = sector_code.group(1)
            number = sector_code.group(2)

            aliases.add(
                f"{prefix} {number}"
            )
            aliases.add(
                f"{prefix}{number}"
            )

        return sorted(
            aliases,
            key=len,
            reverse=True,
        )

    def _exclude(
        self,
        results,
        excluded,
    ):
        if not excluded:
            return results

        kept = []

        for item in results:
            reject = False

            for field, values in excluded.items():
                actual = item.get(field)

                if actual is None:
                    continue

                if not isinstance(
                    values,
                    list,
                ):
                    values = [values]

                if isinstance(
                    actual,
                    (list, tuple, set),
                ):
                    actual_values = {
                        self._normalize(value)
                        for value in actual
                    }

                    if any(
                        self._normalize(value)
                        in actual_values
                        for value in values
                    ):
                        reject = True

                elif isinstance(
                    actual,
                    (int, float, Decimal),
                ):
                    if any(
                        actual == value
                        for value in values
                    ):
                        reject = True

                else:
                    actual_text = self._normalize(
                        actual
                    )

                    if any(
                        (
                            wanted := self._normalize(
                                value
                            )
                        )
                        and (
                            wanted == actual_text
                            or wanted in actual_text
                            or actual_text in wanted
                        )
                        for value in values
                    ):
                        reject = True

                if reject:
                    break

            if not reject:
                kept.append(item)

        return kept

    def _numeric_compare(
        self,
        results,
        field,
        operator,
        reference,
    ):
        if (
            field
            not in {
                "price",
                "bedrooms",
                "bathrooms",
                "plot_size",
                "covered_area",
            }
            or operator
            not in {
                "lt",
                "gt",
                "lte",
                "gte",
                "eq",
            }
            or reference is None
        ):
            return []

        functions = {
            "lt": lambda a, b: a < b,
            "gt": lambda a, b: a > b,
            "lte": lambda a, b: a <= b,
            "gte": lambda a, b: a >= b,
            "eq": lambda a, b: a == b,
        }

        output = []

        for item in results:
            value = item.get(field)

            if (
                isinstance(value, bool)
                or not isinstance(
                    value,
                    (int, float, Decimal),
                )
            ):
                continue

            if functions[operator](
                value,
                reference,
            ):
                output.append(item)

        return output

    def _rank_soft_preferences(
        self,
        results,
        preferred,
    ):
        if not preferred:
            return results

        def score(item):
            total = 0

            for field, wanted in preferred.items():
                if field == "investment_goal":
                    continue

                actual = item.get(field)

                if actual is None:
                    continue

                if isinstance(
                    wanted,
                    list,
                ):
                    total += sum(
                        1
                        for value in wanted
                        if self._normalize(value)
                        in self._normalize(actual)
                    )

                elif (
                    self._normalize(wanted)
                    in self._normalize(actual)
                ):
                    total += 1

            return total

        return sorted(
            results,
            key=score,
            reverse=True,
        )
