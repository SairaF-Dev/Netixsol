from __future__ import annotations

import re
from typing import Any


class KnowledgeService:
    """
    Production knowledge orchestration layer.

    Responsibilities:
        - Normalize incoming questions.
        - Validate route selection.
        - Route structured questions to PostgreSQL.
        - Route knowledge questions to RAG.
        - Combine PostgreSQL and RAG results for mixed queries.
        - Preserve source attribution.
        - Prevent broad accidental PostgreSQL searches.
        - Never invent property facts.

    Routes:
        structured
        rag
        mixed
    """

    VALID_ROUTES = {
        "structured",
        "rag",
        "mixed",
    }

    def __init__(
        self,
        repository,
        rag_service,
        parser=None,
    ):
        if repository is None:
            raise ValueError(
                "repository is required"
            )

        if rag_service is None:
            raise ValueError(
                "rag_service is required"
            )

        self.repository = repository
        self.rag_service = rag_service

        if parser is None:
            try:
                from structured_query_parser import (
                    StructuredQueryParser
                )
            except ImportError as error:
                raise ImportError(
                    "StructuredQueryParser could not be imported."
                ) from error

            parser = StructuredQueryParser()

        if not hasattr(parser, "parse"):
            raise TypeError(
                "parser must provide a parse() method"
            )

        self.parser = parser

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_question(
        question: Any,
    ) -> str:
        if not isinstance(question, str):
            raise TypeError(
                "question must be a string"
            )

        question = re.sub(
            r"\s+",
            " ",
            question.strip(),
        )

        if not question:
            raise ValueError(
                "question cannot be empty"
            )

        return question

    @classmethod
    def validate_route(
        cls,
        route: Any,
    ) -> str:
        if not isinstance(route, str):
            raise TypeError(
                "route must be a string"
            )

        route = route.strip().lower()

        if route not in cls.VALID_ROUTES:
            raise ValueError(
                f"invalid route: {route}"
            )

        return route

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _parse(
        self,
        question: str,
    ) -> dict[str, Any]:
        result = self.parser.parse(
            question
        )

        if not isinstance(result, dict):
            raise TypeError(
                "structured parser must return a dictionary"
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

        unexpected = (
            set(result)
            - allowed_fields
        )

        if unexpected:
            raise ValueError(
                "Parser returned unsupported fields: "
                + ", ".join(sorted(unexpected))
            )

        return result

    # ------------------------------------------------------------------
    # Structured filter detection
    # ------------------------------------------------------------------

    @staticmethod
    def _has_structured_filters(
        filters: dict[str, Any],
    ) -> bool:
        """
        Determine whether the parser found an actual
        property search constraint.
        """

        scalar_fields = (
            "budget",
            "city",
            "area",
            "bedrooms",
            "property_type",
            "purpose",
        )

        for field in scalar_fields:
            value = filters.get(field)

            if value is not None:
                return True

        amenities = filters.get("amenities")

        return bool(amenities)

    # ------------------------------------------------------------------
    # RAG
    # ------------------------------------------------------------------

    def _call_rag(
        self,
        question: str,
    ) -> str | None:
        """
        Call the configured RAG service.

        Supports the expected `.answer(question)` interface.
        """

        if not hasattr(
            self.rag_service,
            "answer",
        ):
            raise TypeError(
                "rag_service must provide an answer() method"
            )

        result = self.rag_service.answer(
            question
        )

        if result is None:
            return None

        if not isinstance(result, str):
            raise TypeError(
                "RAG service must return a string or None"
            )

        return result.strip() or None

    # ------------------------------------------------------------------
    # Structured result validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_structured_results(
        results: Any,
    ) -> list[dict[str, Any]]:
        if results is None:
            return []

        if not isinstance(results, list):
            raise TypeError(
                "repository result must be a list"
            )

        for item in results:
            if not isinstance(item, dict):
                raise TypeError(
                    "each repository result must be a dictionary"
                )

        return results

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_property(
        property_data: dict[str, Any],
        index: int,
    ) -> str:
        property_name = (
            property_data.get(
                "property_name"
            )
            or property_data.get("name")
            or "Unnamed property"
        )

        property_id = (
            property_data.get(
                "property_id"
            )
            or "Unknown ID"
        )

        area = property_data.get(
            "area"
        )

        city = property_data.get(
            "city"
        )

        location = ", ".join(
            part
            for part in (area, city)
            if part
        )

        bedrooms = property_data.get(
            "bedrooms"
        )

        property_type = property_data.get(
            "property_type"
        )

        purpose = property_data.get(
            "purpose"
        )

        price = property_data.get(
            "price"
        )

        currency = property_data.get(
            "currency"
        )

        available = property_data.get(
            "available"
        )

        amenities = property_data.get(
            "amenities"
        )

        parts = [
            f"{index}. {property_name} "
            f"({property_id})"
        ]

        if location:
            parts.append(
                f"is located in {location}."
            )

        if bedrooms is not None:
            parts.append(
                f"It has {bedrooms} bedrooms."
            )

        if property_type:
            parts.append(
                f"Property type: {property_type}."
            )

        if purpose:
            parts.append(
                f"Purpose: {purpose}."
            )

        if price is not None:
            price_text = (
                f"{price:,}"
                if isinstance(
                    price,
                    (int, float),
                )
                else str(price)
            )

            if currency:
                price_text += f" {currency}"

            parts.append(
                f"Verified price: {price_text}."
            )

        if available is not None:
            status = (
                "available"
                if available
                else "not currently available"
            )

            parts.append(
                f"The property is currently "
                f"marked as {status}."
            )

        if amenities:
            parts.append(
                "Amenities: "
                + ", ".join(
                    str(item)
                    for item in amenities
                )
                + "."
            )

        return " ".join(parts)

    def _format_structured_results(
        self,
        results: list[dict[str, Any]],
    ) -> str | None:
        if not results:
            return None

        lines = [
            "I found these verified property options:"
        ]

        for index, item in enumerate(
            results,
            start=1,
        ):
            lines.append(
                self._format_property(
                    item,
                    index,
                )
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def answer(
        self,
        question: str,
        route: str,
    ) -> dict[str, Any]:
        """
        Main knowledge-service API.

        Returns:

        {
            "question": ...,
            "route": ...,
            "filters": ...,
            "structured_results": [...],
            "rag_answer": ...,
            "sources": [...],
            "final_answer": ...
        }
        """

        question = self.normalize_question(
            question
        )

        route = self.validate_route(
            route
        )

        filters: dict[str, Any] = {}

        structured_results: list[
            dict[str, Any]
        ] = []

        rag_answer: str | None = None

        sources: list[str] = []

        # --------------------------------------------------------------
        # STRUCTURED
        # --------------------------------------------------------------

        if route in {
            "structured",
            "mixed",
        }:
            filters = self._parse(
                question
            )

            has_filters = (
                self._has_structured_filters(
                    filters
                )
            )

            if has_filters:
                    structured_results = (
                    self._validate_structured_results(
                        self.repository.search(
                            budget=filters.get("budget"),
                            city=filters.get("city"),
                            area=filters.get("area"),
                            bedrooms=filters.get("bedrooms"),
                            property_type=filters.get("property_type"),
                            purpose=filters.get("purpose"),
                            amenities=filters.get("amenities"),
                        )
                    )
                )
            if structured_results:
                    sources.append(
                        "postgresql"
                    )

            elif route == "structured":
                # CRITICAL SAFETY RULE:
                #
                # Never execute an unfiltered PostgreSQL
                # property search merely because the route says
                # "structured".
                structured_results = []

        # --------------------------------------------------------------
        # RAG
        # --------------------------------------------------------------

        if route in {
            "rag",
            "mixed",
        }:
            rag_answer = self._call_rag(
                question
            )

            if rag_answer:
                sources.append(
                    "rag"
                )

        # --------------------------------------------------------------
        # Final answer
        # --------------------------------------------------------------

        structured_answer = (
            self._format_structured_results(
                structured_results
            )
        )

        if route == "structured":

            if structured_answer:
                final_answer = structured_answer
            else:
                final_answer = (
                    "I couldn't find a verified "
                    "property matching those requirements."
                )

        elif route == "rag":

            final_answer = (
                rag_answer
                or "Verified information is currently unavailable."
            )

        else:
            # mixed

            parts: list[str] = []

            if structured_answer:
                parts.append(
                    structured_answer
                )

            if rag_answer:
                parts.append(
                    rag_answer
                )

            final_answer = (
                "\n\n".join(parts)
                if parts
                else
                "Verified information is currently unavailable."
            )

        return {
            "question": question,
            "route": route,
            "filters": filters,
            "structured_results": structured_results,
            "rag_answer": rag_answer,
            "sources": sources,
            "final_answer": final_answer,
        }


# ---------------------------------------------------------------------------
# Compatibility helper
# ---------------------------------------------------------------------------

def create_knowledge_service(
    repository,
    rag_service,
    parser=None,
) -> KnowledgeService:
    """
    Factory used by the rest of the Week 7 application.
    """
    return KnowledgeService(
        repository=repository,
        rag_service=rag_service,
        parser=parser,
    )