"""
Deterministic natural-language parser for structured real-estate queries.

Purpose
-------
Convert user questions into safe PostgreSQL search filters.

Important behavior
------------------
- No LLM is used.
- No property facts are generated.
- Only explicitly detected filters are returned.
- Unknown values remain None / [].
- Money expressions are normalized to PKR.
- UrduLish / English phrasing is supported.
- Purpose is detected ONLY when explicitly mentioned.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Canonical mappings
# ---------------------------------------------------------------------------

CITY_ALIASES = {
    "lahore": "Lahore",
    "lhr": "Lahore",
    "islamabad": "Islamabad",
    "isb": "Islamabad",
    "rawalpindi": "Rawalpindi",
    "rwp": "Rawalpindi",
    "karachi": "Karachi",
    "khi": "Karachi",
    "faisalabad": "Faisalabad",
    "multan": "Multan",
    "peshawar": "Peshawar",
    "gujranwala": "Gujranwala",
}


PROPERTY_TYPE_ALIASES = {
    "apartments": "Apartment",
    "apartment": "Apartment",
    "flats": "Apartment",
    "flat": "Apartment",
    "houses": "House",
    "house": "House",
    "villas": "Villa",
    "villa": "Villa",
    "plots": "Plot",
    "plot": "Plot",
    "penthouses": "Penthouse",
    "penthouse": "Penthouse",
}


PURPOSE_ALIASES = {
    # Purchase
    "purchasing": "Purchase",
    "purchase": "Purchase",
    "buying": "Purchase",
    "buy": "Purchase",
    "for sale": "Purchase",
    "sale": "Purchase",
    "sell": "Purchase",
    "khareed": "Purchase",
    "khareedna": "Purchase",
    "kharid": "Purchase",
    "kharidna": "Purchase",

    # Rental
    "renting": "Rental",
    "rental": "Rental",
    "rent": "Rental",
    "leasing": "Rental",
    "lease": "Rental",
    "kiraya": "Rental",
    "kiraye": "Rental",
    "kiraye par": "Rental",
}


AMENITY_ALIASES = {
    "24/7 security": "Security",
    "swimming pool": "Swimming Pool",
    "children play area": "Children Play Area",
    "kids play area": "Children Play Area",
    "backup power": "Backup Power",
    "community park": "Community Park",
    "fitness": "Gym",
    "parking": "Parking",
    "security": "Security",
    "elevator": "Elevator",
    "lift": "Elevator",
    "generator": "Backup Power",
    "gym": "Gym",
    "pool": "Swimming Pool",
    "park": "Community Park",
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _normalize_text(value: str) -> str:
    """Normalize whitespace and casing."""
    return re.sub(r"\s+", " ", value.strip().lower())


def _contains_word(text: str, value: str) -> bool:
    """
    Case-insensitive exact word / phrase detection.

    Prevents partial matches.
    """
    pattern = (
        rf"(?<!\w)"
        rf"{re.escape(value)}"
        rf"(?!\w)"
    )

    return re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    ) is not None


def _parse_decimal(value: str) -> Decimal:
    """Safely parse a non-negative decimal."""

    cleaned = value.replace(",", "").strip()

    try:
        number = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        raise ValueError(
            f"Invalid numeric value: {value}"
        )

    if number < 0:
        raise ValueError(
            "numeric value cannot be negative"
        )

    return number


def _money_to_pkr(
    number: Decimal,
    unit: str | None,
) -> int:
    """
    Convert money expressions to PKR.

    Examples:
        4 crore      -> 40,000,000
        2.5 crore    -> 25,000,000
        50 lakh      -> 5,000,000
        40 million   -> 40,000,000
    """

    normalized_unit = (
        unit.lower().strip()
        if unit
        else None
    )

    multipliers = {
        "crore": Decimal("10000000"),
        "crores": Decimal("10000000"),
        "cr": Decimal("10000000"),

        "lakh": Decimal("100000"),
        "lakhs": Decimal("100000"),
        "lac": Decimal("100000"),
        "lacs": Decimal("100000"),

        "million": Decimal("1000000"),
        "millions": Decimal("1000000"),

        "billion": Decimal("1000000000"),
        "billions": Decimal("1000000000"),

        "thousand": Decimal("1000"),
        "thousands": Decimal("1000"),

        "k": Decimal("1000"),
    }

    multiplier = multipliers.get(
        normalized_unit,
        Decimal("1"),
    )

    result = number * multiplier

    if result != result.to_integral_value():
        raise ValueError(
            "Budget must resolve to a whole PKR amount."
        )

    return int(result)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class StructuredQueryParser:
    """
    Production deterministic parser for real-estate search filters.

    Supported filters:
        - budget
        - city
        - area
        - bedrooms
        - property_type
        - purpose
        - amenities
    """

    def __init__(
        self,
        city_aliases: dict[str, str] | None = None,
        property_type_aliases: dict[str, str] | None = None,
        purpose_aliases: dict[str, str] | None = None,
        amenity_aliases: dict[str, str] | None = None,
    ):
        self.city_aliases = (
            city_aliases.copy()
            if city_aliases is not None
            else CITY_ALIASES.copy()
        )

        self.property_type_aliases = (
            property_type_aliases.copy()
            if property_type_aliases is not None
            else PROPERTY_TYPE_ALIASES.copy()
        )

        self.purpose_aliases = (
            purpose_aliases.copy()
            if purpose_aliases is not None
            else PURPOSE_ALIASES.copy()
        )

        self.amenity_aliases = (
            amenity_aliases.copy()
            if amenity_aliases is not None
            else AMENITY_ALIASES.copy()
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_question(question: Any) -> str:
        if not isinstance(question, str):
            raise TypeError(
                "question must be a string"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question cannot be empty"
            )

        return question

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------

    def parse_budget(
        self,
        question: str,
    ) -> int | None:
        """
        Extract budget expressions.

        Supported examples:
            4 crore
            4 crores
            4 cr
            2.5 crore
            50 lakh
            40 lac
            40 million
            150000
            150,000 PKR
            4 crore ke andar
            under 4 crore
            budget 4 crore
            budget 40000000
            under 40,000,000
        """

        text = _normalize_text(question)

        # --------------------------------------------------------------
        # Crore / lakh / million / billion / thousand
        # --------------------------------------------------------------

        unit_pattern = (
            r"(crore|crores|cr|"
            r"lakh|lakhs|lac|lacs|"
            r"million|millions|"
            r"billion|billions|"
            r"thousand|thousands|k)"
        )

        unit_match = re.search(
            rf"(\d+(?:\.\d+)?)\s*{unit_pattern}\b",
            text,
            flags=re.IGNORECASE,
        )

        if unit_match:
            number = _parse_decimal(
                unit_match.group(1)
            )

            unit = unit_match.group(2)

            return _money_to_pkr(
                number,
                unit,
            )

        # --------------------------------------------------------------
        # Explicit PKR / Rs / Rupees
        # --------------------------------------------------------------

        pkr_match = re.search(
            r"(?:pkr|rs\.?|rupees?)\s*"
            r"(\d[\d,]*(?:\.\d+)?)"
            r"|"
            r"(\d[\d,]*(?:\.\d+)?)\s*"
            r"(?:pkr|rs\.?|rupees?)\b",
            text,
            flags=re.IGNORECASE,
        )

        if pkr_match:
            raw_value = (
                pkr_match.group(1)
                or pkr_match.group(2)
            )

            number = _parse_decimal(
                raw_value
            )

            return _money_to_pkr(
                number,
                None,
            )

        # --------------------------------------------------------------
        # Bare amount after budget / under / below / within / upto
        # --------------------------------------------------------------

        bare_match = re.search(
            r"(?:budget|under|below|within|upto|up to)"
            r"\s*(?:is|of|around)?\s*"
            r"(\d[\d,]*(?:\.\d+)?)",
            text,
            flags=re.IGNORECASE,
        )

        if bare_match:
            number = _parse_decimal(
                bare_match.group(1)
            )

            return _money_to_pkr(
                number,
                None,
            )

        return None

    # ------------------------------------------------------------------
    # City
    # ------------------------------------------------------------------

    def parse_city(
        self,
        question: str,
    ) -> str | None:

        text = _normalize_text(question)

        aliases = sorted(
            self.city_aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for alias, canonical in aliases:
            if _contains_word(
                text,
                alias,
            ):
                return canonical

        return None

    # ------------------------------------------------------------------
    # Area
    # ------------------------------------------------------------------

        
    def parse_area(
        self,
        question: str,
    ) -> str | None:
        """
        Extract explicit real-estate area expressions.

        Supported examples:
            DHA Phase 6
            DHA Phase 8
            DHA
            Bahria Town
            Gulberg III
            Gulberg 3
            Model Town
            F-11
            F11
            Sector F-11
            F-10
            E-11
            B-17
            Ghauri Town
            Blue Area
            Clifton
            Gulshan-e-Iqbal
            Saddar
        """

        text = re.sub(
            r"\s+",
            " ",
            question.strip(),
        )

        # --------------------------------------------------------------
        # DHA Phase X
        # --------------------------------------------------------------

        match = re.search(
            r"\b(DHA\s+Phase\s+\d+)\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            parts = match.group(1).split()
            return f"DHA Phase {parts[-1]}"

        # --------------------------------------------------------------
        # Plain DHA
        # --------------------------------------------------------------

        match = re.search(
            r"\bDHA\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return "DHA"

        # --------------------------------------------------------------
        # Bahria Town
        # --------------------------------------------------------------

        match = re.search(
            r"\b(Bahria(?:\s+Town)?)\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return "Bahria Town"

        # --------------------------------------------------------------
        # Gulberg III / Gulberg 3 / Gulberg-III
        # --------------------------------------------------------------

        match = re.search(
            r"\bGulberg(?:\s+|-)?(?:III|3)\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return "Gulberg III"

        # --------------------------------------------------------------
        # Plain Gulberg
        # --------------------------------------------------------------

        match = re.search(
            r"\bGulberg\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return "Gulberg"

        # --------------------------------------------------------------
        # Model Town
        # --------------------------------------------------------------

        match = re.search(
            r"\b(Model\s+Town)\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return "Model Town"

        # --------------------------------------------------------------
        # Islamabad sectors
        # --------------------------------------------------------------

        sector_match = re.search(
            r"\b(?:sector\s+)?([EFB])(?:\s+|-)?(10|11|17)\b",
            text,
            flags=re.IGNORECASE,
        )

        if sector_match:
            letter = sector_match.group(1).upper()
            number = sector_match.group(2)

            return f"{letter}-{number}"

        # --------------------------------------------------------------
        # Ghauri Town
        # --------------------------------------------------------------

        if re.search(
            r"\bGhauri\s+Town\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "Ghauri Town"

        # --------------------------------------------------------------
        # Blue Area
        # --------------------------------------------------------------

        if re.search(
            r"\bBlue\s+Area\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "Blue Area"

        # --------------------------------------------------------------
        # Clifton
        # --------------------------------------------------------------

        if re.search(
            r"\bClifton\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "Clifton"

        # --------------------------------------------------------------
        # Gulshan-e-Iqbal
        # --------------------------------------------------------------

        if re.search(
            r"\bGulshan(?:-e-Iqbal|\s+e\s+Iqbal)?\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "Gulshan-e-Iqbal"

        # --------------------------------------------------------------
        # Saddar
        # --------------------------------------------------------------

        if re.search(
            r"\bSaddar\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "Saddar"

        return None


    # ------------------------------------------------------------------
    # Bedrooms
    # ------------------------------------------------------------------

    def parse_bedrooms(
        self,
        question: str,
    ) -> int | None:

        text = _normalize_text(question)

        patterns = [
            r"\b(\d+)\s*(?:\+|plus)?\s*bedrooms?\b",
            r"\b(\d+)\s*(?:\+|plus)?\s*br\b",
            r"\b(\d+)\s*(?:\+|plus)?\s*beds?\b",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:
                bedrooms = int(
                    match.group(1)
                )

                if bedrooms < 0:
                    raise ValueError(
                        "bedrooms must be non-negative"
                    )

                return bedrooms

        return None

    # ------------------------------------------------------------------
    # Property type
    # ------------------------------------------------------------------

    def parse_property_type(
        self,
        question: str,
    ) -> str | None:

        text = _normalize_text(question)

        aliases = sorted(
            self.property_type_aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for alias, canonical in aliases:
            if _contains_word(
                text,
                alias,
            ):
                return canonical

        return None

    # ------------------------------------------------------------------
    # Purpose
    # ------------------------------------------------------------------

    def parse_purpose(
        self,
        question: str,
    ) -> str | None:
        """
        Detect ONLY explicit purchase/rental intent.

        Purchase:
            purchase
            purchasing
            buy
            buying
            sale
            for sale
            khareed
            khareedna
            kharid
            kharidna

        Rental:
            rent
            rental
            renting
            lease
            leasing
            kiraya
            kiraye
            kiraye par

        Important:
            Budget does NOT automatically mean Purchase.

        Examples:

            "Lahore mein 3 bedroom apartment 4 crore ke andar chahiye."
                -> None

            "Apartment under 40,000,000 PKR."
                -> None

            "Lahore mein 3 bedroom apartment purchase karna hai."
                -> Purchase

            "Lahore mein 3 bedroom apartment rent par chahiye."
                -> Rental
        """

        text = _normalize_text(question)

        aliases = sorted(
            self.purpose_aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for alias, canonical in aliases:
            if _contains_word(
                text,
                alias,
            ):
                return canonical

        return None

    # ------------------------------------------------------------------
    # Amenities
    # ------------------------------------------------------------------

    def parse_amenities(
        self,
        question: str,
    ) -> list[str]:

        text = _normalize_text(question)

        found: list[str] = []

        aliases = sorted(
            self.amenity_aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for alias, canonical in aliases:
            if _contains_word(
                text,
                alias,
            ):
                if canonical not in found:
                    found.append(canonical)

        return found

    # ------------------------------------------------------------------
    # Complete parse
    # ------------------------------------------------------------------

    def parse(
        self,
        question: str,
    ) -> dict[str, Any]:
        """
        Parse all supported structured filters.

        Unknown values:

            budget        -> None
            city          -> None
            area          -> None
            bedrooms      -> None
            property_type -> None
            purpose       -> None
            amenities     -> []
        """

        question = self._validate_question(
            question
        )

        return {
            "budget": self.parse_budget(
                question
            ),

            "city": self.parse_city(
                question
            ),

            "area": self.parse_area(
                question
            ),

            "bedrooms": self.parse_bedrooms(
                question
            ),

            "property_type": (
                self.parse_property_type(
                    question
                )
            ),

            "purpose": self.parse_purpose(
                question
            ),

            "amenities": self.parse_amenities(
                question
            ),
        }


# ---------------------------------------------------------------------------
# Manual smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    parser = StructuredQueryParser()

    questions = [
        "Lahore mein 3 bedroom apartment 4 crore ke andar chahiye.",
        "3 bedroom rental Lahore mein chahiye.",
        "DHA Phase 6 mein apartment under 4 crore.",
        "DHA Phase 8 Lahore mein 3 bedroom apartment.",
        "Swimming pool aur gym wala apartment Lahore mein.",
        "Bahria Town mein 2 bedroom flat 50 lakh.",
        "Is property mein parking aur security hai?",
        "Gulberg III mein apartment chahiye.",
        "Model Town Lahore mein house chahiye.",
        "Apartment under 40,000,000 PKR.",
        "Lahore mein 3 bedroom apartment purchase karna hai.",
        "Lahore mein 3 bedroom apartment rent par chahiye.",
        "DHA Phase 6 mein house khareedna hai.",
        "Lahore mein 2 bedroom flat kiraye par chahiye.",
    ]

    print("=" * 80)
    print("STRUCTURED QUERY PARSER")
    print("=" * 80)

    for question in questions:

        print("\nQUESTION:")
        print(question)

        print("\nFILTERS:")
        print(
            parser.parse(question)
        )
