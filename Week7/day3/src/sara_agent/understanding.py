from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv

from .models import ComparisonRequest, UserUnderstanding
from .edge_case_policy import EdgeCasePolicy


INTENTS = {
    "property_search",
    "property_details",
    "property_selection",
    "recommendation",
    "availability",
    "faq",
    "objection",
    "schedule_visit",
    "reschedule_visit",
    "cancel_visit",
    "greeting",
    "reset",
    "off_topic",
    "unknown",
}

FIELDS = {
    "budget",
    "city",
    "area",
    "bedrooms",
    "property_type",
    "purpose",
    "amenities",
    "investment_goal",
    "developer",
}

REFERENCES = {
    None,
    "selected_property",
    "first_result",
    "second_result",
    "third_result",
    "last_result",
}

COMP_FIELDS = {
    None,
    "price",
    "bedrooms",
    "bathrooms",
    "plot_size",
    "covered_area",
}

COMP_OPS = {
    None,
    "lt",
    "gt",
    "lte",
    "gte",
    "eq",
}


# These are schema vocabulary aliases, not business/property data.
PROPERTY_TYPE_ALIASES = {
    "flat": "Apartment",
    "flats": "Apartment",
    "apartment": "Apartment",
    "apartments": "Apartment",

    "house": "House",
    "houses": "House",
    "home": "House",
    "homes": "House",
    "villa": "House",
    "villas": "House",

    "office": "Office",
    "office space": "Office",

    "shop": "Shop",
    "shops": "Shop",
    "retail shop": "Shop",

    "plot": "Plot",
    "plots": "Plot",
    "residential plot": "Plot",
    "commercial plot": "Plot",
}

PURPOSE_ALIASES = {
    "rent": "Rental",
    "rental": "Rental",
    "kiraya": "Rental",
    "kiraye": "Rental",
    "rent pe": "Rental",
    "rent par": "Rental",

    "purchase": "Purchase",
    "purchasing": "Purchase",
    "buy": "Purchase",
    "buying": "Purchase",
    "khareedna": "Purchase",
    "kharidna": "Purchase",
    "sale": "Purchase",
}


class UnderstandingError(RuntimeError):
    pass


class UserUnderstandingService:
    def __init__(
        self,
        client=None,
        model: str | None = None,
    ):
        load_dotenv()
        self.edge = EdgeCasePolicy()

        self.model = (
            model
            or os.getenv(
                "SARA_LLM_MODEL",
                "openai/gpt-4o-mini",
            )
        )

        self.max_tokens = self._env_int(
            "SARA_NLU_MAX_TOKENS",
            320,
            minimum=120,
            maximum=900,
        )

        self.timeout_seconds = self._env_float(
            "SARA_LLM_TIMEOUT_SECONDS",
            20.0,
            minimum=5.0,
            maximum=120.0,
        )

        self.max_retries = self._env_int(
            "SARA_LLM_MAX_RETRIES",
            1,
            minimum=0,
            maximum=3,
        )

        if client is not None:
            self.client = client
            return

        key = os.getenv("OPENROUTER_API_KEY")

        if not key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured"
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Install dependencies with: "
                "pip install -r requirements.txt"
            ) from exc

        self.client = OpenAI(
            api_key=key,
            base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ),
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )

    def understand(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> UserUnderstanding:
        if not isinstance(message, str):
            raise ValueError("message must be non-empty")

        raw_message = message.strip()
        if not raw_message:
            raise ValueError("message must be non-empty")

        # Repair only generic language/schema typos. Business/location
        # values are never rewritten here.
        semantic_message = self.edge.repair_tokens(raw_message)
        semantic_message = re.sub(
            r"\bpropert\b",
            "property",
            semantic_message,
            flags=re.IGNORECASE,
        )

        deterministic = self._deterministic_understanding(
            message=semantic_message,
            context=context or {},
        )

        if deterministic is not None:
            # Deterministic rich-turn parsing may return before the normal
            # post-LLM repair pipeline. Still apply explicit relaxation
            # language such as "area ka issue nahi" / "area flexible hai".
            deterministic = self._repair_relaxation_understanding(
                result=deterministic,
                raw_message=semantic_message,
            )
            deterministic.raw_message = raw_message
            return deterministic

        payload = {
            "context": self._json_safe(context or {}),
            "current_message": semantic_message,
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": self._system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            )

            content = response.choices[0].message.content or ""
            parsed = self._parse_json(content)

        except Exception as exc:
            fallback = self._deterministic_understanding(
                message=semantic_message,
                context=context or {},
            )

            if fallback is not None:
                fallback = self._repair_relaxation_understanding(
                    result=fallback,
                    raw_message=semantic_message,
                )
                fallback.raw_message = raw_message
                return fallback

            # Provider-safe schema fallback:
            # preserve only explicit schema facts from the CURRENT message.
            # City/area are still verified later by chatbot.py / Day2Adapter.
            schema_fallback = UserUnderstanding(
                intent="unknown",
                raw_message=raw_message,
            )

            schema_fallback = self._repair_explicit_schema_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
            )

            schema_fallback = self._repair_relaxation_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
            )

            schema_fallback = self._repair_budget_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
                context=context or {},
            )

            if (
                schema_fallback.required
                or schema_fallback.preferred
                or schema_fallback.excluded
                or schema_fallback.relax
            ):
                if schema_fallback.intent == "unknown":
                    schema_fallback.intent = "property_search"

                schema_fallback.raw_message = raw_message
                return schema_fallback

            raise UnderstandingError(
                "semantic understanding failed"
            ) from exc

        result = self._validate(parsed, raw_message)

        # Deterministic schema repair protects explicit current-turn values
        # when the LLM omits a clear property type/bedroom/purpose.
        result = self._repair_explicit_schema_understanding(
            result=result,
            raw_message=semantic_message,
        )

        # Location repair remains based on the user's original message;
        # actual city/area validation is later grounded by Day2Adapter.
        result = self._repair_location_understanding(
            result=result,
            raw_message=raw_message,
            context=context or {},
        )

        result = self._repair_correction_understanding(
            result=result,
            raw_message=semantic_message,
            context=context or {},
        )

        result = self._repair_relaxation_understanding(
            result=result,
            raw_message=semantic_message,
        )

        result = self._repair_exact_constraint_comparison(
            result=result,
            raw_message=semantic_message,
        )

        result = self._repair_budget_understanding(
            result=result,
            raw_message=semantic_message,
            context=context or {},
        )

        result.raw_message = raw_message
        return result
        

    def _deterministic_understanding(
        self,
        message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding | None:
        """
        Handle small, schema-level utterances without calling the LLM.

        This is intentionally conservative. It only handles simple
        transaction-purpose follow-ups/corrections such as:

            rent k liye
            rent k liyee
            kiraye ke liye
            purchase k liye
            buy ke liye
            buying ke liye

        Business/property facts are never inferred here.
        """

        if not isinstance(message, str):
            return None

        raw = message.strip()

        if not raw:
            return None

        text = raw.casefold()

        # Normalize common Roman-Urdu spelling noise and punctuation.
        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            return None

        # Keep this fast-path limited to short conversational follow-ups.
        tokens = text.split()

        if len(tokens) > 28:
            return None

        # --------------------------------------------------------------
        # Generic/simple property-search intent
        # --------------------------------------------------------------

        explicit_purpose = self._extract_explicit_purpose(
            text
        )

        investment_request = bool(
            re.search(
                r"\b(?:"
                r"investment\s+(?:ke|k|kay)\s+liye|"
                r"investment\s+option|"
                r"investment\s+property|"
                r"invest\s+(?:karna|krna|karni|krni)|"
                r"invest\s+(?:ke|k|kay)\s+liye"
                r")\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        # In this real-estate agent, an explicit request for an investment
        # property is a recommendation/search for an asset to purchase.
        # This is semantic intent normalization, not a property/business fact.
        if investment_request and explicit_purpose is None:
            explicit_purpose = "Purchase"

        deterministic_intent = (
            "recommendation"
            if investment_request
            else "property_search"
        )

        if self.edge.looks_like_generic_property_request(raw):
            # Use this fast-path only for a genuinely simple property request.
            # Rich turns must continue to semantic NLU so city, area, budget,
            # bedrooms and other explicit current-turn constraints survive.
            has_money = bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|k)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    r"\b(?:budget|max|maximum|under|upto|up to|tak)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            has_location_shape = bool(
                re.search(
                    r"\b(?:phase|sector|block)\s*[a-z0-9-]+\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(r"\b(?:mein|me|main)\b", text)
            )
            has_schema_constraint = bool(
                re.search(
                    r"\b(?:bed|beds|bedroom|bedrooms|bhk|flat|apartment|house|home|villa|plot|office|shop)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )

            if not (has_money or has_location_shape or has_schema_constraint):
                required: dict[str, Any] = {}

                if explicit_purpose:
                    required["purpose"] = explicit_purpose

                return UserUnderstanding(
                    intent=deterministic_intent,
                    required=required,
                    raw_message=raw,
                )

        # A simple explicit property-type request should also work without
        # an LLM, e.g. "apartment chahiye". Keep this conservative so
        # complex multi-constraint turns still go through semantic NLU.
        simple_types = []
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text):
                if canonical not in simple_types:
                    simple_types.append(canonical)

        request_cue = bool(
            re.search(
                r"\b(?:chahiye|dekhni|dekhna|dekh\s+rahi|dekh\s+raha|dikhao|show|find|search)\b",
                text,
            )
        )

        complex_markers = (
            "gym", "parking", "security", "pool", "amenity",
            "developer", "school", "hospital", "installment",
        )

        rich_type_turn = bool(
            explicit_purpose
            or re.search(
                r"\b(?:budget|max|maximum|under|upto|up to|tak)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|k)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b(?:phase|sector|block|mein|me)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b\d{1,2}\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if (
            len(simple_types) == 1
            and request_cue
            and not rich_type_turn
            and not any(marker in text for marker in complex_markers)
            and not re.search(r"\b(?:ya|or|either)\b", text)
        ):
            return UserUnderstanding(
                intent=deterministic_intent,
                required={"property_type": simple_types[0]},
                raw_message=raw,
            )

        # --------------------------------------------------------------
        # Deterministic budget understanding
        # --------------------------------------------------------------
        budget_value = self._extract_budget_amount(
            text
        )

        if budget_value is not None:
            rich_budget_turn = bool(
                explicit_purpose
                or simple_types
                or re.search(
                    r"\b(?:phase|sector|block|mein|me)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    r"\b\d{1,2}\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or (
                    request_cue
                    and len(tokens) >= 5
                )
            )

            # For clear multi-field search turns, preserve the explicit
            # schema facts deterministically. City/area are intentionally
            # NOT guessed here; chatbot.py verifies them against Day 2 data.
            # This keeps ordinary structured requests working even when the
            # external semantic LLM is slow/unavailable.
            if rich_budget_turn:
                soft_markers = (
                    "around",
                    "approx",
                    "approximately",
                    "roughly",
                    "takreeban",
                    "taqreeban",
                    "qareeban",
                    "kareeban",
                    "flexible",
                    "thora upar neeche",
                    "thoda upar neeche",
                    "preferred",
                    "preference",
                )

                is_soft = any(
                    marker in text
                    for marker in soft_markers
                )

                required: dict[str, Any] = {}
                preferred: dict[str, Any] = {}

                if is_soft:
                    preferred["budget"] = budget_value
                else:
                    required["budget"] = budget_value

                if explicit_purpose:
                    required["purpose"] = explicit_purpose

                if len(simple_types) == 1:
                    required["property_type"] = simple_types[0]

                bedroom_values = {
                    int(value)
                    for value in re.findall(
                        r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                        text,
                        flags=re.IGNORECASE,
                    )
                    if int(value) > 0
                }

                if len(bedroom_values) == 1:
                    required["bedrooms"] = next(iter(bedroom_values))

                # If a clear purpose was not present, preserve the budget but
                # let ConversationPolicy ask purpose instead of guessing.
                return UserUnderstanding(
                    intent=deterministic_intent,
                    required=required,
                    preferred=preferred,
                    raw_message=raw,
                )

            soft_markers = (
                "around",
                "approx",
                "approximately",
                "roughly",
                "takreeban",
                "taqreeban",
                "qareeban",
                "kareeban",
                "flexible",
                "thora upar neeche",
                "thoda upar neeche",
                "preferred",
                "preference",
            )

            is_soft = any(
                marker in text
                for marker in soft_markers
            )

            required: dict[str, Any] = {}
            preferred: dict[str, Any] = {}

            if is_soft:
                preferred["budget"] = budget_value
            else:
                required["budget"] = budget_value

            context_required = (
                context.get("required")
                if isinstance(context, dict)
                else {}
            ) or {}

            context_preferred = (
                context.get("preferred")
                if isinstance(context, dict)
                else {}
            ) or {}

            purpose_known = bool(
                context_required.get("purpose")
                or context_preferred.get("purpose")
            )

            return UserUnderstanding(
                intent=deterministic_intent,
                required=required,
                preferred=preferred,
                excluded={},
                relax=[],
                reference_type=None,
                selected_index=None,
                comparison=ComparisonRequest(
                    None,
                    None,
                    None,
                    None,
                ),
                needs_clarification=not purpose_known,
                clarification_reason=(
                    None
                    if purpose_known
                    else "missing_purpose_for_budget"
                ),
                raw_message=raw,
            )

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )

        purpose: str | None = None

        if any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in rental_patterns
        ):
            purpose = "Rental"

        if any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in purchase_patterns
        ):
            # If both purpose families somehow occur, leave it to the
            # semantic layer instead of guessing.
            if purpose is not None:
                return None

            purpose = "Purchase"

        if purpose is None:
            return None

        # Reject obviously complex requests that merely mention rent/buy
        # alongside other new search fields. Those still belong to the LLM.
        complex_field_markers = (
            "bedroom",
            "bedrooms",
            "budget",
            "crore",
            "lakh",
            "city",
            "area",
            "sector",
            "phase",
            "block",
            "apartment",
            "flat",
            "house",
            "plot",
            "office",
            "shop",
            "developer",
            "amenity",
            "gym",
            "parking",
            # A purpose plus a location relation is no longer a purpose-only
            # follow-up. Let semantic NLU preserve the current-turn location.
            " mein ",
            " me ",
        )

        has_location_relation = bool(
            re.search(
                r"\b(?:mein|me)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if (
            has_location_relation
            or any(
                marker in text
                for marker in complex_field_markers
            )
        ):
            # Preserve the explicit purpose deterministically; verified
            # location repair later adds only Day 2-confirmed city/area.
            required = {"purpose": purpose}

            if len(simple_types) == 1:
                required["property_type"] = simple_types[0]

            bedroom_values = {
                int(value)
                for value in re.findall(
                    r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                if int(value) > 0
            }

            if len(bedroom_values) == 1:
                required["bedrooms"] = next(iter(bedroom_values))

            return UserUnderstanding(
                intent=deterministic_intent,
                required=required,
                raw_message=raw,
            )

        return UserUnderstanding(
            intent=deterministic_intent,
            required={
                "purpose": purpose,
            },
            preferred={},
            excluded={},
            relax=[],
            reference_type=None,
            selected_index=None,
            comparison=ComparisonRequest(
                None,
                None,
                None,
                None,
            ),
            needs_clarification=False,
            clarification_reason=None,
            raw_message=raw,
        )

    def _repair_explicit_schema_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """Repair explicit schema values without inventing business facts.

        This layer may recognize canonical property types, exact bedroom
        counts and transaction purpose. It never recognizes a specific
        city/area/property/developer from a hard-coded list.
        """
        normalized = " ".join(raw_message.casefold().split())

        # ---- Property type -------------------------------------------------
        detected_types: list[str] = []
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if re.search(
                rf"\b{re.escape(alias)}\b",
                normalized,
                flags=re.IGNORECASE,
            ):
                if canonical not in detected_types:
                    detected_types.append(canonical)

        if len(detected_types) > 1:
            # "apartment ya house" is a choice, not permission to guess.
            if re.search(r"\b(?:ya|or|either)\b", normalized):
                result.required.pop("property_type", None)
                result.preferred.pop("property_type", None)
                result.needs_clarification = True
                result.clarification_reason = "ambiguous_property_type"

        elif len(detected_types) == 1:
            property_type = detected_types[0]
            # Do not turn explicit negation into a positive filter.
            negative = bool(
                re.search(
                    rf"\b{re.escape(next((a for a,c in PROPERTY_TYPE_ALIASES.items() if c == property_type and re.search(rf'\\b{re.escape(a)}\\b', normalized)), property_type.casefold()))}"
                    rf"\b\s+(?:nahi|nai|nahin|not)\b",
                    normalized,
                    flags=re.IGNORECASE,
                )
            )

            if (
                not negative
                and "property_type" not in result.required
                and "property_type" not in result.preferred
                and "property_type" not in result.excluded
            ):
                result.required["property_type"] = property_type

        # ---- Bedrooms -----------------------------------------------------
        bedroom_values = {
            int(value)
            for value in re.findall(
                r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            if int(value) > 0
        }

        if len(bedroom_values) > 1:
            result.required.pop("bedrooms", None)
            result.preferred.pop("bedrooms", None)
            result.needs_clarification = True
            result.clarification_reason = "ambiguous_bedrooms"
        elif len(bedroom_values) == 1 and "bedrooms" not in result.required:
            result.required["bedrooms"] = next(iter(bedroom_values))

        # ---- Purpose ------------------------------------------------------
        rental = bool(
            re.search(r"\b(?:rent|rental|kiraya|kiraye)\b", normalized)
        )
        purchase = bool(
            re.search(r"\b(?:purchase|purchasing|buy|buying|khareedna|kharidna)\b", normalized)
        )

        if rental and purchase:
            result.required.pop("purpose", None)
            result.preferred.pop("purpose", None)
            result.needs_clarification = True
            result.clarification_reason = "ambiguous_purpose"
        elif rental and "purpose" not in result.required:
            result.required["purpose"] = "Rental"
        elif purchase and "purpose" not in result.required:
            result.required["purpose"] = "Purchase"

        if (
            result.intent == "unknown"
            and (
                result.required
                or result.preferred
                or result.excluded
            )
        ):
            result.intent = "property_search"

        return result

    def _extract_budget_amount(
        self,
        text: str,
    ) -> int | None:
        """
        Parse common PKR budget expressions deterministically.

        Supported examples:
            3 crore
            5 corore   (common typing noise)
            2.5 crore
            1.5 lakh / lac
            150k
            budget 150000

        Money-unit spelling normalization is language handling only;
        it does not introduce any property/business fact.
        """

        if not isinstance(text, str):
            return None

        normalized = " ".join(
            text.casefold()
            .replace(",", "")
            .split()
        )

        if not normalized:
            return None

        has_budget_word = bool(
            re.search(
                r"\b(?:budget|max|maximum|under|upto|up\s+to|tak)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

        crore_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(?:crore|corore|carore|cror|cr)\b",
            normalized,
            flags=re.IGNORECASE,
        )

        if crore_match:
            return int(
                float(crore_match.group(1))
                * 10_000_000
            )

        lakh_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(?:lakh|lac)\b",
            normalized,
            flags=re.IGNORECASE,
        )

        if lakh_match:
            return int(
                float(lakh_match.group(1))
                * 100_000
            )

        k_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*k\b",
            normalized,
            flags=re.IGNORECASE,
        )

        if k_match:
            return int(
                float(k_match.group(1))
                * 1_000
            )

        if has_budget_word:
            number_match = re.search(
                r"\b(\d{4,})\b",
                normalized,
            )

            if number_match:
                return int(
                    number_match.group(1)
                )

        return None

    def _env_int(
        self,
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        raw = os.getenv(
            name
        )

        if raw is None:
            return default

        try:
            value = int(
                raw
            )
        except (
            TypeError,
            ValueError,
        ):
            return default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    def _env_float(
        self,
        name: str,
        default: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:
        raw = os.getenv(
            name
        )

        if raw is None:
            return default

        try:
            value = float(
                raw
            )
        except (
            TypeError,
            ValueError,
        ):
            return default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )
    def _extract_explicit_purpose(
    self,
    text: str,
) -> str | None:

        normalized = text.casefold()

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )
        if any(
            re.search(pattern, normalized)
            for pattern in rental_patterns
        ):
            return "Rental"

        if any(
            re.search(pattern, normalized)
            for pattern in purchase_patterns
        ):
            return "Purchase"

        return None

    def _system_prompt(self) -> str:
        return """
You are the semantic NLU layer for Sara, a Pakistani real-estate
sales assistant.

Return ONLY valid JSON.
Do NOT answer the user.
Do NOT invent property or business facts.

Schema:

{
  "intent": "unknown",
  "required": {},
  "preferred": {},
  "excluded": {},
  "relax": [],
  "reference_type": null,
  "selected_index": null,
  "comparison": {
    "field": null,
    "operator": null,
    "reference": null,
    "value": null
  },
  "needs_clarification": false,
  "clarification_reason": null
}

Allowed intents:

property_search
property_details
property_selection
recommendation
availability
faq
objection
schedule_visit
reschedule_visit
cancel_visit
greeting
reset
off_topic
unknown

Use off_topic when the user's request is clearly outside real estate,
property discovery, property visits, or the supported customer workflow.
Examples include weather, sports, politics, recipes, coding help, jokes,
general trivia, and requests to perform unrelated tasks. Do not use
off_topic for a vague or incomplete property question; use unknown and
request clarification instead.

Allowed filter fields:

budget
city
area
bedrooms
property_type
purpose
amenities
investment_goal
developer


IMPORTANT MEMORY RULE

Extract ONLY changes expressed in the CURRENT message.

Do not copy old city, area, budget, bedrooms or other filters from
conversation context into required/preferred/excluded.

Application memory will merge current-turn changes with previous state.


CONSTRAINT STRENGTH

Use "required" when the user expresses a hard requirement.

Examples:

"Mujhe Lahore mein flat chahiye"

required:
{
  "city": "Lahore",
  "property_type": "Apartment"
}

"Sirf DHA mein"

required:
{
  "area": "DHA"
}

"Maximum 150k"

required:
{
  "budget": 150000
}


Use "preferred" for soft preferences.

Examples:

"DHA preferred hai"

preferred:
{
  "area": "DHA"
}

"Gym ho to acha hai"

preferred:
{
  "amenities": ["Gym"]
}

"Budget around 3 crore hai"

preferred:
{
  "budget": 30000000
}

"Mera budget 3 crore hai"

required:
{
  "budget": 30000000
}

A plain stated budget is normally a HARD maximum budget unless the user
uses soft wording such as around, approximately, takreeban, flexible,
or preferred.


Use "excluded" for things the user does not want.

Examples:

"Bahria nahi chahiye"

excluded:
{
  "area": ["Bahria"]
}

"DHA aur Bahria ke ilawa"

excluded:
{
  "area": ["DHA", "Bahria"]
}

"Apartment nahi chahiye"

excluded:
{
  "property_type": ["Apartment"]
}


Use "relax" when an OLD constraint should be removed entirely.

Examples:

"Area flexible hai"

relax:
["area"]

"Sector koi bhi ho"
"Chahey sector koi b ho"
"Location koi bhi chalegi"

relax:
["area"]

IMPORTANT:
Do NOT extract fake areas such as "sector koi", "area koi", or
"location flexible". These phrases mean the old area constraint is
being relaxed.

"Budget ka issue nahi"

relax:
["budget"]

"Bedrooms koi bhi chalein ge"

relax:
["bedrooms"]


PROPERTY TYPE NORMALIZATION

Normalize ordinary Pakistani real-estate wording into these canonical
property types:

flat / flats / apartment / apartments
-> Apartment

house / home / villa
-> House

office / office space
-> Office

shop / retail shop
-> Shop

plot
-> Plot

If the user explicitly asks for a property type, normally treat it as
required unless they clearly say it is optional/preferred.

Examples:

"Mujhe flat chahiye"

required:
{
  "property_type": "Apartment"
}

"Apartment preferred hai"

preferred:
{
  "property_type": "Apartment"
}

"House nahi chahiye"

excluded:
{
  "property_type": ["House"]
}


PURPOSE NORMALIZATION

rent / rental / kiraya / kiraye pe
-> Rental

buy / purchase / purchasing / khareedna / investment property request
-> Purchase


MONEY NORMALIZATION

Normalize clear PKR expressions.

150k
-> 150000

1.5 lakh
-> 150000

3 crore
-> 30000000

2.5 crore
-> 25000000


LOCATION RULES

Do NOT hard-code actual place names.

Extract whatever city, area, phase, sector, society or location the
user actually mentions.

Examples:

"DHA mein sirf"

required:
{
  "area": "DHA"
}

"DHA Phase 6"

required:
{
  "area": "DHA Phase 6"
}

"Lahore"

required:
{
  "city": "Lahore"
}


INCOMPLETE LOCATION RULE

Do not guess a missing phase, sector, block or identifier.

If the user appears to give an incomplete location such as:

"DHA Phase only"
"Sector mein dikhao"
"Block wala"

and the missing identifier is necessary to understand the intended
location, set:

"needs_clarification": true

and use:

"clarification_reason": "incomplete_location"


REFERENCE RULES

first / pehli
-> selected_index 0

second / dusri
-> selected_index 1

third / teesri
-> selected_index 2

When selecting a numbered result:
intent = property_selection

"iski details"
"uski details"
"this property's details"

If a selected property is clearly available in context:
intent = property_details
reference_type = selected_property

If reference cannot be resolved reliably:
needs_clarification = true
clarification_reason = "ambiguous_reference"


COMPARISON RULES

cheaper / sasti
-> field price, operator lt

more expensive / mehngi
-> field price, operator gt

more bedrooms
-> bedrooms gt

fewer bedrooms
-> bedrooms lt

An exact bedroom request is NOT a comparison.

"3 bedrooms wala dikhao"
-> required {"bedrooms": 3}
-> comparison must be null

"3 bedrooms dikhao chahey sector koi bhi ho"
-> required {"bedrooms": 3}
-> relax ["area"]
-> comparison must be null

larger plot
-> plot_size gt

smaller plot
-> plot_size lt

larger covered area
-> covered_area gt

smaller covered area
-> covered_area lt

comparison.value should normally be null because the verified comparison
value must come from database-backed conversation memory.


OTHER INTENTS

Question about whether selected property is available:
-> availability

Book / schedule / arrange property visit:
-> schedule_visit

Move / change an existing visit:
-> reschedule_visit

Cancel visit:
-> cancel_visit

Investment property / investment option search:
-> recommendation

Price concern, trust concern, location concern, investment-risk/return concern,
builder/developer concern or maintenance concern:
-> objection

General process, company information, brochure or FAQ question:
-> faq


SAFETY RULE

Never invent:

price
availability
ROI
future appreciation
developer reputation
amenities
payment plans
school distance
hospital distance
appointment confirmation
agent information

This layer only understands and structures what the user said.
"""

    def _parse_json(
        self,
        content: str,
    ) -> dict[str, Any]:

        text = content.strip()

        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )

            text = re.sub(
                r"\s*```$",
                "",
                text,
            )

        value = json.loads(
            text
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "expected JSON object"
            )

        return value

    def _validate(
        self,
        p: dict[str, Any],
        raw: str,
    ) -> UserUnderstanding:

        intent = (
            p.get("intent")
            if p.get("intent") in INTENTS
            else "unknown"
        )

        required = self._clean_filter_map(
            p.get("required")
        )

        preferred = self._clean_filter_map(
            p.get("preferred")
        )

        excluded = self._clean_excluded_map(
            p.get("excluded")
        )

        relax = p.get(
            "relax",
            [],
        )

        if not isinstance(
            relax,
            list,
        ):
            relax = []

        relax = [
            field_name
            for field_name in relax
            if field_name in FIELDS
        ]

        ref = p.get(
            "reference_type"
        )

        if ref not in REFERENCES:
            ref = None

        idx = p.get(
            "selected_index"
        )

        if (
            isinstance(idx, bool)
            or not isinstance(idx, int)
        ):
            idx = None

        comparison_raw = p.get(
            "comparison",
            {},
        )

        if not isinstance(
            comparison_raw,
            dict,
        ):
            comparison_raw = {}

        comparison_field = (
            comparison_raw.get("field")
            if comparison_raw.get("field")
            in COMP_FIELDS
            else None
        )

        comparison_operator = (
            comparison_raw.get("operator")
            if comparison_raw.get("operator")
            in COMP_OPS
            else None
        )

        comparison_reference = (
            comparison_raw.get("reference")
            if comparison_raw.get("reference")
            in REFERENCES
            else None
        )

        comparison_value = (
            comparison_raw.get("value")
        )

        if (
            isinstance(
                comparison_value,
                bool,
            )
            or not isinstance(
                comparison_value,
                (int, float),
            )
        ):
            comparison_value = None

        if (
            not comparison_field
            or not comparison_operator
        ):
            comparison_field = None
            comparison_operator = None
            comparison_reference = None
            comparison_value = None

        clarification_reason = (
            p.get(
                "clarification_reason"
            )
        )

        if not isinstance(
            clarification_reason,
            str,
        ):
            clarification_reason = None

        needs_clarification = bool(
            p.get(
                "needs_clarification",
                False,
            )
        )

        # Guard against false-positive incomplete-location decisions.
        # Example: "DHA Phase 5" already contains a concrete phase number.
        # This is generic schema validation; no business/place names are hard-coded.
        if (
            needs_clarification
            and clarification_reason == "incomplete_location"
        ):
            area_value = (
                required.get("area")
                or preferred.get("area")
            )

            if self._has_location_identifier(area_value):
                needs_clarification = False
                clarification_reason = None

        return UserUnderstanding(
            intent=intent,
            required=required,
            preferred=preferred,
            excluded=excluded,
            relax=relax,
            reference_type=ref,
            selected_index=idx,
            comparison=ComparisonRequest(
                comparison_field,
                comparison_operator,
                comparison_reference,
                comparison_value,
            ),
            needs_clarification=needs_clarification,
            clarification_reason=clarification_reason,
            raw_message=raw,
        )

    def _clean_filter_map(
        self,
        raw_map: Any,
    ) -> dict[str, Any]:

        if not isinstance(
            raw_map,
            dict,
        ):
            return {}

        cleaned: dict[str, Any] = {}

        for key, value in raw_map.items():

            if key not in FIELDS:
                continue

            if value in (
                None,
                "",
                [],
            ):
                continue

            value = self._normalize_filter_value(
                key,
                value,
            )

            if value not in (
                None,
                "",
                [],
            ):
                cleaned[key] = value

        return cleaned

    def _clean_excluded_map(
        self,
        raw_map: Any,
    ) -> dict[str, list[Any]]:

        if not isinstance(
            raw_map,
            dict,
        ):
            return {}

        cleaned: dict[
            str,
            list[Any],
        ] = {}

        for key, value in raw_map.items():

            if key not in FIELDS:
                continue

            values = (
                value
                if isinstance(
                    value,
                    list,
                )
                else [value]
            )

            normalized_values = []

            for item in values:

                if item in (
                    None,
                    "",
                ):
                    continue

                item = (
                    self._normalize_filter_value(
                        key,
                        item,
                    )
                )

                if item not in (
                    None,
                    "",
                ):
                    normalized_values.append(
                        item
                    )

            if normalized_values:
                cleaned[key] = (
                    normalized_values
                )

        return cleaned

    def _normalize_filter_value(
        self,
        field_name: str,
        value: Any,
    ) -> Any:

        if field_name == "property_type":
            return self._normalize_property_type(
                value
            )

        if field_name == "purpose":
            return self._normalize_purpose(
                value
            )

        if field_name == "bedrooms":
            if isinstance(
                value,
                bool,
            ):
                return value

            if isinstance(
                value,
                (int, float),
            ):
                return int(value)

        return value

    def _normalize_property_type(
        self,
        value: Any,
    ) -> Any:

        if not isinstance(
            value,
            str,
        ):
            return value

        cleaned = (
            value
            .strip()
            .casefold()
        )

        return PROPERTY_TYPE_ALIASES.get(
            cleaned,
            value.strip(),
        )

    def _normalize_purpose(
        self,
        value: Any,
    ) -> Any:

        if not isinstance(
            value,
            str,
        ):
            return value

        cleaned = (
            value
            .strip()
            .casefold()
        )

        return PURPOSE_ALIASES.get(
            cleaned,
            value.strip(),
        )

    def _has_location_identifier(
        self,
        area: Any,
    ) -> bool:
        """
        Return True when an area expression already contains a concrete
        phase, sector, or block identifier.

        Examples considered complete:
        - "DHA Phase 5"
        - "Phase 6"
        - "Sector F-11"
        - "Block C"

        No actual society/city/developer names are hard-coded here.
        """

        if not isinstance(area, str):
            return False

        text = area.strip()

        if not text:
            return False

        patterns = (
            r"\bphase\s*[-#]?\s*[a-z0-9]+\b",
            r"\bsector\s*[-#]?\s*[a-z0-9]+(?:[-/][a-z0-9]+)?\b",
            r"\bblock\s*[-#]?\s*[a-z0-9]+\b",
        )

        return any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        )


    def _repair_correction_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding:
        """
        Repair short conversational corrections such as:

            "Bahria mein sorry"
            "Gulberg sorry"
            "actually Phase 5"
            "nahi, Sector F-11"

        This does not hard-code business locations. It only detects
        correction language and reuses the location phrase spoken by
        the user in the CURRENT turn.
        """

        if not isinstance(raw_message, str):
            return result

        if not self._looks_like_correction(raw_message):
            return result

        # Purpose corrections must be handled before generic area
        # corrections. Otherwise "purchase k liye" can be mistaken for
        # an area phrase.
        corrected_purpose = self._extract_corrected_purpose(
            raw_message
        )

        if corrected_purpose:
            result.required["purpose"] = corrected_purpose
            result.preferred.pop("purpose", None)
            result.excluded.pop("purpose", None)

            result.relax = [
                field_name
                for field_name in result.relax
                if field_name != "purpose"
            ]

            # Remove any bogus area hallucinated from this purpose-only
            # correction turn.
            bogus_area = result.required.get("area")
            if self._looks_like_purpose_phrase(bogus_area):
                result.required.pop("area", None)

            bogus_area = result.preferred.get("area")
            if self._looks_like_purpose_phrase(bogus_area):
                result.preferred.pop("area", None)

            if "area" in result.excluded:
                result.excluded["area"] = [
                    value
                    for value in result.excluded["area"]
                    if not self._looks_like_purpose_phrase(value)
                ]

                if not result.excluded["area"]:
                    result.excluded.pop("area", None)

            result.intent = "property_search"
            result.needs_clarification = False

            if result.clarification_reason in {
                "missing_purpose_for_budget",
                "incomplete_location",
            }:
                result.clarification_reason = None

            return result

        corrected_area = self._extract_correction_area(raw_message)

        if not corrected_area:
            return result

        # A correction means "replace my previous area with this one".
        result.required["area"] = corrected_area
        result.preferred.pop("area", None)

        # Do not interpret the corrected location as an exclusion.
        if "area" in result.excluded:
            corrected_norm = self._normalize_text(corrected_area)

            kept_area_exclusions = []

            for value in result.excluded["area"]:
                value_norm = self._normalize_text(value)

                same_location = (
                    value_norm == corrected_norm
                    or (
                        value_norm
                        and corrected_norm
                        and (
                            value_norm in corrected_norm
                            or corrected_norm in value_norm
                        )
                    )
                )

                if not same_location:
                    kept_area_exclusions.append(value)

            if kept_area_exclusions:
                result.excluded["area"] = kept_area_exclusions
            else:
                result.excluded.pop("area", None)

        # A correction to area is not a relaxation of the area field.
        result.relax = [
            field_name
            for field_name in result.relax
            if field_name != "area"
        ]

        # If the LLM failed to classify the short correction, treat it
        # as a property search.
        if result.intent == "unknown":
            result.intent = "property_search"

        # A successfully recovered correction is not ambiguous.
        if (
            result.clarification_reason == "incomplete_location"
            and self._has_location_identifier(corrected_area)
        ):
            result.needs_clarification = False
            result.clarification_reason = None

        return result

    def _extract_corrected_purpose(
        self,
        message: str,
    ) -> str | None:
        """Extract Rental/Purchase correction from the current turn."""

        if not isinstance(message, str):
            return None

        text = " ".join(
            message.strip().casefold().split()
        )

        if not text:
            return None

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )

        for pattern in rental_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "Rental"

        for pattern in purchase_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "Purchase"

        return None

    def _looks_like_purpose_phrase(
        self,
        value: Any,
    ) -> bool:
        """Detect bogus area values that are really purpose wording."""

        if not isinstance(value, str):
            return False

        text = " ".join(
            value.strip().casefold().split()
        )

        if not text:
            return False

        purpose_words = (
            "purchase",
            "buy",
            "buying",
            "rent",
            "rental",
            "kiraya",
            "kiraye",
            "khareedna",
            "kharidna",
            "sale",
        )

        return any(
            re.search(
                rf"\b{re.escape(word)}\b",
                text,
                flags=re.IGNORECASE,
            )
            for word in purpose_words
        )

    def _looks_like_correction(
        self,
        message: str,
    ) -> bool:
        if not isinstance(message, str):
            return False

        text = message.casefold()

        markers = (
            "sorry",
            "actually",
            "rather",
            "i mean",
            "mera matlab",
            "matlab",
            "nahi,",
            "nahin,",
            "no,",
        )

        return any(marker in text for marker in markers)

    def _extract_correction_area(
        self,
        message: str,
    ) -> str | None:
        """
        Extract the location phrase from a short correction without
        relying on a hard-coded city/society list.
        """

        if not isinstance(message, str):
            return None

        text = message.strip()
        if not text:
            return None

        # Remove correction discourse markers.
        cleaned = re.sub(
            r"\b("
            r"sorry|actually|rather|"
            r"i\s+mean|mera\s+matlab|matlab|"
            r"no|nahi|nahin"
            r")\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

        # Remove common relation/action words around the location.
        cleaned = re.sub(
            r"\b("
            r"mein|me|main|"
            r"dikhao|dikhayein|dikhaein|show|"
            r"sirf|only|please|pls|"
            r"property|properties|option|options"
            r")\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip(" ,.-")

        # Remove trailing conversational/copula words that are not part
        # of the location itself.
        # Examples:
        #   "bahria tha"  -> "bahria"
        #   "gulberg thi" -> "gulberg"
        #   "phase 5 hai" -> "phase 5"
        cleaned = re.sub(
            r"\s+\b(tha|thi|the|hai|hain|hy|he)\b\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ,.-")

        if not cleaned:
            return None

        # If a concrete phase/sector/block phrase exists, prefer it.
        explicit = self._extract_explicit_area(cleaned)
        if explicit:
            return explicit

        # For short corrections, the remaining current-turn noun phrase
        # is the location candidate. Keep this conservative.
        words = cleaned.split()

        if 1 <= len(words) <= 4:
            return cleaned

        return None

    def _normalize_text(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value).strip().casefold(),
        )


    def _repair_relaxation_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """
        Repair explicit field-relaxation language.

        Examples:
            "area flexible hai"
            "location koi bhi ho"
            "sector koi bhi ho"
            "phase koi b ho"
            "3 bedrooms dikhao chahey sector koi bhi ho"

        These are schema-level language rules only. No city, society,
        phase, or sector names are hard-coded.
        """

        if not isinstance(raw_message, str):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        if not text:
            return result

        area_words = (
            "area",
            "location",
            "sector",
            "phase",
            "block",
        )

        flexible_markers = (
            "flexible",
            "koi bhi",
            "koi b",
            "kuch bhi",
            "any",
            "doesn't matter",
            "does not matter",
            "matter nahi",
            "issue nahi",
            "issue nai",
            "masla nahi",
            "masla nai",
            "problem nahi",
            "problem nai",
            "farq nahi",
            "farak nahi",
            "zaroori nahi",
            "necessary nahi",
        )

        area_relaxed = (
            any(word in text for word in area_words)
            and any(
                marker in text
                for marker in flexible_markers
            )
        )

        if area_relaxed:
            # "sector koi bhi ho" means remove the old area constraint;
            # it must never create a fake area such as "sector koi".
            result.required.pop(
                "area",
                None,
            )
            result.preferred.pop(
                "area",
                None,
            )
            result.excluded.pop(
                "area",
                None,
            )

            if "area" not in result.relax:
                result.relax.append("area")

            if result.clarification_reason == "incomplete_location":
                result.needs_clarification = False
                result.clarification_reason = None

            if result.intent == "unknown":
                result.intent = "property_search"

        return result

    def _repair_exact_constraint_comparison(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """
        Prevent an exact numeric requirement from being hallucinated as
        a relative comparison.

        Example:
            "3 bedrooms wala dikhao"
        means:
            bedrooms == 3

        It does NOT mean:
            bedrooms > selected_property.bedrooms

        A comparison is preserved only when the current message actually
        contains comparative language such as "more", "zyada", "kam",
        "fewer", etc.
        """

        comparison = result.comparison

        if comparison is None:
            return result

        if (
            comparison.field != "bedrooms"
            or "bedrooms" not in result.required
        ):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        comparative_markers = (
            "more bedroom",
            "more bedrooms",
            "extra bedroom",
            "extra bedrooms",
            "zyada bedroom",
            "zyada bedrooms",
            "ziyada bedroom",
            "ziyada bedrooms",
            "zayada bedroom",
            "zayada bedrooms",
            "se zyada",
            "se ziyada",
            "se ziada",
            "fewer bedroom",
            "fewer bedrooms",
            "less bedroom",
            "less bedrooms",
            "kam bedroom",
            "kam bedrooms",
            "se kam",
        )

        has_comparative_language = any(
            marker in text
            for marker in comparative_markers
        )

        if not has_comparative_language:
            result.comparison = ComparisonRequest(
                None,
                None,
                None,
                None,
            )

        return result


    def _repair_budget_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding:
        """
        Make budget semantics deterministic.

        Rules:
        - Plain "mera budget 3 crore hai" -> hard budget ceiling.
        - "around/takreeban 3 crore" -> soft preference.
        - If a budget is supplied but rent vs purchase is still unknown,
          ask for purpose before using that budget across incomparable
          transaction types.
        """

        if not isinstance(raw_message, str):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        budget_value = (
            result.required.get("budget")
            if "budget" in result.required
            else result.preferred.get("budget")
        )

        if budget_value is None:
            return result

        soft_markers = (
            "around",
            "approx",
            "approximately",
            "roughly",
            "takreeban",
            "taqreeban",
            "qareeban",
            "kareeban",
            "flexible",
            "thora upar neeche",
            "thoda upar neeche",
            "preferred",
            "preference",
        )

        is_soft = any(
            marker in text
            for marker in soft_markers
        )

        if is_soft:
            result.preferred["budget"] = budget_value
            result.required.pop("budget", None)
        else:
            # A plain stated budget is a maximum search constraint.
            result.required["budget"] = budget_value
            result.preferred.pop("budget", None)

        # Determine whether purpose is already known either in the current
        # turn or in committed conversation context.
        purpose_known = bool(
            result.required.get("purpose")
            or result.preferred.get("purpose")
            or (
                isinstance(context, dict)
                and (
                    (context.get("required") or {}).get("purpose")
                    or (context.get("preferred") or {}).get("purpose")
                )
            )
        )

        if not purpose_known:
            result.needs_clarification = True
            result.clarification_reason = "missing_purpose_for_budget"

        return result

    def _json_safe(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            Decimal,
        ):
            return float(value)

        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._json_safe(
                    item
                )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._json_safe(
                    item
                )
                for item in value
            ]

        return value
    def _repair_location_understanding(
    self,
    result: UserUnderstanding,
    raw_message: str,
    context: dict[str, Any],
) -> UserUnderstanding:
        """
        Repair obvious LLM inconsistencies for explicit location follow-ups.

        Examples:
            "DHA Phase 6"
            "DHA Phase 5 mein dikhao"
            "Sector F-11 only"
            "Block C mein"

        No actual city/society names are hard-coded.
        """

        explicit_area = self._extract_explicit_area(
            raw_message
        )

        if not explicit_area:
            return result

        # A bare explicit location follow-up should be treated as a
        # hard narrowing constraint unless the user explicitly marks
        # it as a preference.
        if not self._looks_like_soft_preference(
            raw_message
        ):
            result.required["area"] = explicit_area
            result.preferred.pop("area", None)

            # Explicit current-turn area and relax-area are contradictory.
            # The explicit area wins.
            result.relax = [
                field_name
                for field_name in result.relax
                if field_name != "area"
            ]

            # A clear location follow-up is a property search even if
            # the LLM accidentally labels the intent as unknown.
            if result.intent == "unknown":
                result.intent = "property_search"

        # If the raw message contains a concrete identifier,
        # it is not an incomplete location.
        if self._has_location_identifier(
            explicit_area
        ):
            if (
                result.clarification_reason
                == "incomplete_location"
            ):
                result.needs_clarification = False
                result.clarification_reason = None

        return result
    def _extract_explicit_area(
        self,
        message: str,
    ) -> str | None:
        """
        Extract an explicit phase/sector/block location from the CURRENT
        message without hard-coding society or city names.
        """

        if not isinstance(message, str):
            return None

        text = message.strip()
        if not text:
            return None

        # Remove conversational/action words, not real place names.
        cleaned = re.sub(
            r"\b("
            r"mujhe|mujey|mjy|please|pls|"
            r"mein|me|main|"
            r"dikhao|dikhayein|dikhaein|show|"
            r"property|properties|option|options|"
            r"sirf|only"
            r")\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")

        patterns = (
            # Society/name + Phase identifier, e.g. "DHA Phase 5".
            r"\b([A-Za-z][A-Za-z0-9.'-]*(?:\s+[A-Za-z][A-Za-z0-9.'-]*){0,3}"
            r"\s+Phase\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Phase alone, e.g. "Phase 5".
            r"\b(Phase\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Sector, e.g. "Sector F-11".
            r"\b(Sector\s*[-#]?\s*[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)?)\b",

            # Block, e.g. "Block C".
            r"\b(Block\s*[-#]?\s*[A-Za-z0-9]+)\b",
        )

        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split())

        return None

    def _looks_like_soft_preference(
        self,
        message: str,
    ) -> bool:
        """
        Return True only when the user explicitly marks the location
        as optional/soft. A plain location such as "DHA Phase 6"
        remains a hard search constraint.
        """

        if not isinstance(message, str):
            return False

        text = message.casefold()
        markers = (
            "prefer",
            "preferred",
            "preference",
            "ho to acha",
            "ho to achha",
            "ideally",
            "agar ho",
            "flexible",
        )
        return any(marker in text for marker in markers)

        
