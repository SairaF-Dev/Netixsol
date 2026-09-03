from decimal import Decimal
from typing import Any


FALLBACK_ANSWER = (
    "Verified information is currently unavailable."
)


class AnswerComposer:
    """
    Production answer composer for the real-estate agent.

    Source authority:

        PostgreSQL
        ----------
        Exact structured property facts:
            - price
            - availability
            - bedrooms
            - property type
            - purpose
            - location
            - developer
            - amenities
            - property ID
            - payment plans
            - nearby schools / hospitals

        RAG
        ---
        Document/company knowledge:
            - FAQs
            - policies
            - project descriptions
            - general company information

    Important:
        Structured facts must never be replaced by RAG-generated claims.
    """

    SUPPORTED_ROUTES = {
        "structured",
        "rag",
        "mixed",
    }

    def __init__(
        self,
        fallback_answer: str = FALLBACK_ANSWER,
    ):
        if not isinstance(fallback_answer, str):
            raise TypeError(
                "fallback_answer must be a string"
            )

        fallback_answer = fallback_answer.strip()

        if not fallback_answer:
            raise ValueError(
                "fallback_answer cannot be empty"
            )

        self.fallback_answer = fallback_answer

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(value: Any) -> str:
        """Normalize a value for safe comparison."""

        if value is None:
            return ""

        return str(value).strip().lower()

    @staticmethod
    def _format_price(price, currency=None) -> str:
        """Format a property price without changing its numeric value."""

        if price is None:
            return ""

        try:
            decimal_price = Decimal(str(price))
        except Exception:
            return str(price)

        if decimal_price == decimal_price.to_integral_value():
            formatted = f"{int(decimal_price):,}"
        else:
            formatted = f"{decimal_price:,}"

        if currency:
            return f"{formatted} {currency}"

        return formatted

    @staticmethod
    def _format_amenities(amenities) -> str:
        """Format amenities safely."""

        if not amenities:
            return ""

        if isinstance(amenities, str):
            return amenities.strip()

        if not isinstance(amenities, (list, tuple, set)):
            return ""

        values = []

        for amenity in amenities:

            if amenity is None:
                continue

            amenity = str(amenity).strip()

            if amenity:
                values.append(amenity)

        return ", ".join(values)

    # ------------------------------------------------------------------
    # Structured property formatting
    # ------------------------------------------------------------------

    def _format_property(self, property_data):
        """
        Convert one PostgreSQL property record into a concise,
        customer-facing factual response.

        No property information is invented here.
        """

        if not isinstance(property_data, dict):
            return self.fallback_answer

        property_name = property_data.get(
            "property_name"
        )

        property_id = property_data.get(
            "property_id"
        )

        city = property_data.get("city")
        area = property_data.get("area")
        bedrooms = property_data.get("bedrooms")

        property_type = property_data.get(
            "property_type"
        )

        purpose = property_data.get("purpose")
        price = property_data.get("price")
        currency = property_data.get("currency")
        available = property_data.get("available")

        amenities = property_data.get(
            "amenities",
            [],
        )

        parts = []

        if property_name:
            parts.append(
                f"{property_name}"
            )

        if property_id:
            parts.append(
                f"({property_id})"
            )

        if area and city:
            parts.append(
                f"is located in {area}, {city}."
            )

        elif area:
            parts.append(
                f"is located in {area}."
            )

        elif city:
            parts.append(
                f"is located in {city}."
            )

        if bedrooms is not None:

            bedroom_text = (
                "bedroom"
                if bedrooms == 1
                else "bedrooms"
            )

            parts.append(
                f"It has {bedrooms} {bedroom_text}."
            )

        if property_type:
            parts.append(
                f"Property type: {property_type}."
            )

        if purpose:
            parts.append(
                f"Purpose: {purpose}."
            )

        formatted_price = self._format_price(
            price,
            currency,
        )

        if formatted_price:
            parts.append(
                f"Verified price: {formatted_price}."
            )

        if available is True:

            parts.append(
                "The property is currently marked as available."
            )

        elif available is False:

            parts.append(
                "The property is currently marked as unavailable."
            )

        formatted_amenities = (
            self._format_amenities(amenities)
        )

        if formatted_amenities:

            parts.append(
                f"Amenities: {formatted_amenities}."
            )

        if not parts:
            return self.fallback_answer

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Structured answer
    # ------------------------------------------------------------------

    def compose_structured(
        self,
        structured_results,
    ):
        """
        Compose an answer exclusively from PostgreSQL records.

        PostgreSQL is treated as the authoritative source.
        """

        # IMPORTANT:
        # Validate type BEFORE checking truthiness.
        if not isinstance(structured_results, list):
            raise TypeError(
                "structured_results must be a list"
            )

        if not structured_results:
            return self.fallback_answer

        formatted = []

        for property_data in structured_results:

            text = self._format_property(
                property_data
            )

            if text != self.fallback_answer:
                formatted.append(text)

        if not formatted:
            return self.fallback_answer

        if len(formatted) == 1:
            return formatted[0]

        lines = [
            "I found these verified property options:"
        ]

        for index, item in enumerate(
            formatted,
            start=1,
        ):
            lines.append(
                f"{index}. {item}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # RAG answer
    # ------------------------------------------------------------------

    def compose_rag(
        self,
        rag_answer,
    ):
        """
        Return a RAG answer only when it is non-empty.

        The RAG pipeline is responsible for grounding
        document-level answers.
        """

        if not isinstance(
            rag_answer,
            str,
        ):
            return self.fallback_answer

        answer = rag_answer.strip()

        if not answer:
            return self.fallback_answer

        return answer

    # ------------------------------------------------------------------
    # Mixed answer
    # ------------------------------------------------------------------

    def compose_mixed(
        self,
        structured_results,
        rag_answer,
    ):
        """
        Combine authoritative structured facts with RAG knowledge.

        Ordering:

            1. PostgreSQL facts
            2. RAG/document answer
        """

        # Do not silently accept invalid structured input.
        if not isinstance(
            structured_results,
            list,
        ):
            raise TypeError(
                "structured_results must be a list"
            )

        structured_answer = (
            self.compose_structured(
                structured_results
            )
        )

        rag_answer = self.compose_rag(
            rag_answer
        )

        has_structured = (
            structured_answer
            != self.fallback_answer
        )

        has_rag = (
            rag_answer
            != self.fallback_answer
        )

        if has_structured and has_rag:

            return (
                f"{structured_answer}\n\n"
                f"{rag_answer}"
            )

        if has_structured:
            return structured_answer

        if has_rag:
            return rag_answer

        return self.fallback_answer

    # ------------------------------------------------------------------
    # Unified interface
    # ------------------------------------------------------------------

    def compose(
        self,
        route,
        structured_results=None,
        rag_answer=None,
    ):
        """
        Compose the final answer according to the route.

        Supported routes:

            structured
            rag
            mixed
        """

        if not isinstance(route, str):
            raise TypeError(
                "route must be a string"
            )

        route = route.strip().lower()

        if route not in self.SUPPORTED_ROUTES:
            raise ValueError(
                f"Unsupported route: {route}"
            )

        # --------------------------------------------------------------
        # STRUCTURED
        # --------------------------------------------------------------

        if route == "structured":

            if structured_results is None:
                structured_results = []

            return self.compose_structured(
                structured_results
            )

        # --------------------------------------------------------------
        # RAG
        # --------------------------------------------------------------

        if route == "rag":

            return self.compose_rag(
                rag_answer
            )

        # --------------------------------------------------------------
        # MIXED
        # --------------------------------------------------------------

        if route == "mixed":

            if structured_results is None:
                structured_results = []

            return self.compose_mixed(
                structured_results,
                rag_answer,
            )

        # Defensive fallback.
        raise ValueError(
            f"Unsupported route: {route}"
        )


# ----------------------------------------------------------------------
# Manual smoke test
# ----------------------------------------------------------------------

if __name__ == "__main__":

    composer = AnswerComposer()

    property_data = {
        "property_id": "LHR-DHA-APT-001",
        "property_name": "Horizon Heights Apartment",
        "city": "Lahore",
        "area": "DHA Phase 6",
        "bedrooms": 3,
        "property_type": "Apartment",
        "purpose": "Purchase",
        "price": 28_500_000,
        "currency": "PKR",
        "available": True,
        "amenities": [
            "Parking",
            "Swimming Pool",
            "Gym",
            "Security",
        ],
    }

    print("=" * 80)
    print("ANSWER COMPOSER SMOKE TEST")
    print("=" * 80)

    print("\nSTRUCTURED")
    print("-" * 80)

    print(
        composer.compose(
            route="structured",
            structured_results=[
                property_data
            ],
        )
    )

    print("\nRAG")
    print("-" * 80)

    print(
        composer.compose(
            route="rag",
            rag_answer=(
                "Investment returns cannot be guaranteed."
            ),
        )
    )

    print("\nMIXED")
    print("-" * 80)

    print(
        composer.compose(
            route="mixed",
            structured_results=[
                property_data
            ],
            rag_answer=(
                "Verified information about payment "
                "plans is currently unavailable."
            ),
        )
    )