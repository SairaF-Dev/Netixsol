from __future__ import annotations

import os

from dataclasses import dataclass
from typing import Any

from .result_presentation import ResultPresentationPolicy


@dataclass
class RequirementDecision:
    """
    A single human-like next step in requirement collection.

    Business/location values are never stored here. They come from the
    verified Day 2 adapter at runtime.
    """

    field: str
    message: str
    pending_action: dict[str, Any] | None = None


class ConversationPolicy:
    """
    Generic requirement-collection policy for Sara.

    Principles:
    - Do not ask again for information already known.
    - Ask one useful question at a time.
    - If a city is known but area is missing, show VERIFIED available
      areas from Day 2 before asking the user to choose.
    - Explicitly flexible fields are not asked again.
    - Property facts never come from this policy.
    Two-Tier Slot-Filling Architecture:
    - Tier 1: Essential slots (Purpose -> City/Area -> Budget).
      Always asked if missing, database result count is irrelevant.
    - Tier 2: Narrowing slots (Bedrooms -> Property Type -> Amenities).
      Only asked when Tier 1 is complete AND matching database count > threshold.
    """

    SEARCH_INTENTS = {
        "property_search",
        "recommendation",
    }

    def __init__(
        self,
        presentation: ResultPresentationPolicy | None = None,
    ):
        self.presentation = (
            presentation
            or ResultPresentationPolicy()
        )

    def is_tier1_complete(self, state) -> bool:
        """Return True when Purpose, City (or Area), and Budget are all known or flexible."""
        required = getattr(state, "required", {})
        preferred = getattr(state, "preferred", {})
        flexible = getattr(state, "flexible", set())

        purpose = self._value("purpose", required, preferred)
        city = self._value("city", required, preferred)
        area = self._value("area", required, preferred)
        budget = self._value("budget", required, preferred)

        has_purpose = bool(purpose) or ("purpose" in flexible)
        has_location = bool(city or area) or ("city" in flexible) or ("area" in flexible)
        has_budget = (budget is not None) or ("budget" in flexible)

        return has_purpose and has_location and has_budget

    def next_tier1_requirement(
        self,
        state: Any = None,
        knowledge: Any = None,
        *,
        intent: str = "property_search",
        **kwargs,
    ) -> RequirementDecision | None:
        state = state or kwargs.get("state")
        knowledge = knowledge or kwargs.get("knowledge")
        intent = intent or kwargs.get("intent", "property_search")
        if intent not in self.SEARCH_INTENTS:
            return None
        """
        Tier 1: Essential slots in priority order:
        1. Purpose (buy / rent)
        2. City / Area
        3. Budget
        4. Area (if city specified, but area not specified and not flexible)
        """
        required = getattr(state, "required", {})
        preferred = getattr(state, "preferred", {})
        flexible = getattr(state, "flexible", set())

        purpose = self._value("purpose", required, preferred)
        city = self._value("city", required, preferred)
        area = self._value("area", required, preferred)
        budget = self._value("budget", required, preferred)

        # 1. Purpose (buy / rent)
        if not purpose and "purpose" not in flexible:
            message = (
                "Ji! Yeh budget rent ke liye hai ya purchase ke liye?"
                if budget is not None
                else "Aap rent par lena chahte hain ya purchase ke liye dekh rahe hain?"
            )
            return RequirementDecision(
                field="purpose",
                message=message,
                pending_action={
                    "type": "collect_requirement",
                    "field": "purpose",
                },
            )

        # 2. City / Area
        if not city and not area and "city" not in flexible and "area" not in flexible:
            return RequirementDecision(
                field="city",
                message="Ji! Pehle batayein aap kis city (jaise Islamabad ya Lahore) mein dekhna chahte hain?",
                pending_action={
                    "type": "collect_requirement",
                    "field": "city",
                },
            )

        if area and not city and "city" not in flexible:
            return self._city_decision(
                state=state,
                knowledge=knowledge,
            )

        # 3. Budget
        if budget is None and "budget" not in flexible:
            if self._same_text(purpose, "Rental"):
                message = (
                    "Aapka maximum monthly rental budget kitna hai? "
                    "Agar budget flexible hai to woh bhi bata sakte hain."
                )
            elif self._same_text(purpose, "Purchase"):
                message = (
                    "Aapka maximum purchase budget kitna hai? "
                    "Agar budget flexible hai to woh bhi bata sakte hain."
                )
            else:
                message = (
                    "Aapka approximate maximum budget kitna hai? "
                    "Agar budget flexible hai to woh bhi bata sakte hain."
                )

            return RequirementDecision(
                field="budget",
                message=message,
                pending_action={
                    "type": "collect_requirement",
                    "field": "budget",
                },
            )

        # 4. Area (if city is known, but specific area is missing and not flexible)
        if city and not area and "area" not in flexible and knowledge is not None:
            area_dec = self._area_decision(
                city=city,
                state=state,
                knowledge=knowledge,
            )
            if area_dec:
                return area_dec

        return None

    def next_narrowing_requirement(
        self,
        *,
        state,
        matching_count: int,
        threshold: int | None = None,
    ) -> RequirementDecision | None:
        """
        Tier 2: Narrowing slots in priority order:
        1. Bedrooms
        2. Property Type
        3. Amenities
        Only asked if matching_count > threshold.
        """
        if threshold is None:
            threshold = int(os.getenv("SARA_RESULTS_CLARIFY_THRESHOLD", 5))

        if matching_count <= threshold:
            return None

        required = getattr(state, "required", {})
        preferred = getattr(state, "preferred", {})
        flexible = getattr(state, "flexible", set())

        property_type = self._value("property_type", required, preferred)
        bedrooms = self._value("bedrooms", required, preferred)
        amenities = self._value("amenities", required, preferred)

        # 1. Bedrooms (only for residential properties, not Plot/Office/Commercial)
        is_bedroom_eligible = True
        if property_type and str(property_type).lower() in ("plot", "commercial", "office"):
            is_bedroom_eligible = False

        if is_bedroom_eligible and bedrooms is None and "bedrooms" not in flexible:
            pt_label = "ghar" if property_type and str(property_type).lower() == "house" else "property"
            return RequirementDecision(
                field="bedrooms",
                message=f"Kitne bedrooms ka {pt_label} dekh rahe hain? (e.g. 2, 3 ya 4 bedrooms)",
                pending_action={
                    "type": "collect_requirement",
                    "field": "bedrooms",
                },
            )

        # 2. Property Type
        if not property_type and "property_type" not in flexible:
            return RequirementDecision(
                field="property_type",
                message="Aap kis property type mein interested hain? (jaise House, Apartment, ya Plot?)",
                pending_action={
                    "type": "collect_requirement",
                    "field": "property_type",
                },
            )

        # 3. Amenities
        if not amenities and "amenities" not in flexible:
            return RequirementDecision(
                field="amenities",
                message="Kya koi specific amenity zaroori hai? (jaise Parking, Security, Lift ya Balcony?)",
                pending_action={
                    "type": "collect_requirement",
                    "field": "amenities",
                },
            )

        return None

    def next_requirement(
        self,
        intent: str = "property_search",
        state: Any = None,
        knowledge: Any = None,
        **kwargs,
    ) -> RequirementDecision | None:
        intent = intent or kwargs.get("intent", "property_search")
        state = state or kwargs.get("state")
        knowledge = knowledge or kwargs.get("knowledge")
        if intent not in self.SEARCH_INTENTS:
            return None
        return self.next_tier1_requirement(state=state, knowledge=knowledge, intent=intent)

    def _area_decision(
        self,
        *,
        city: str,
        state,
        knowledge,
    ) -> RequirementDecision | None:
        matcher = getattr(knowledge, "budget_area_options", None)
        if callable(matcher):
            filters = {**state.preferred, **state.required}
            try:
                result = matcher(city=city, purpose=filters.get("purpose"),
                                 budget=filters.get("budget"),
                                 property_type=filters.get("property_type"))
            except Exception:
                return RequirementDecision("area", "Verified property data abhi access nahi ho raha. Dobara try karein?",
                                           {"type": "collect_requirement", "field": "area"})
            options = result["areas"]
            if not options:
                cheapest = result.get("cheapest")
                if cheapest:
                    message = (f"{city} mein is budget ke andar koi verified area match nahi karta. "
                               f"Sabse sasta available option {cheapest['area']} mein PKR {cheapest['min_price']:,.0f} hai. "
                               "Kya aap budget adjust karna chahenge?")
                else:
                    message = f"{city} mein is purpose aur property type ke liye filhaal verified inventory nahi mili. Kya criteria change karna chahenge?"
                return RequirementDecision("budget", message, {"type": "collect_requirement", "field": "budget"})
            preview, more = self.presentation.preview_choices([row["area"] for row in options])
            label = "budget ke andar" if filters.get("budget") is not None else "available price ranges mein"
            return RequirementDecision("area", f"{city} mein {label} verified options: {', '.join(preview)}. "
                + ("Aur areas bhi available hain. " if more else "")
                + "Kis area mein dekhein? Sab areas ke options bhi dekh sakte hain.",
                {"type": "choose_verified_area", "field": "area", "city": city, "options": [row["area"] for row in options]})
        lister = getattr(
            knowledge,
            "list_available_areas",
            getattr(
                knowledge,
                "list_areas",
                None,
            ),
        )

        if not callable(lister):
            return RequirementDecision(
                field="area",
                message=(
                    f"Ji! {city} mein kis area mein dekhna chahte hain? "
                    "Agar area flexible hai to bata dein."
                ),
                pending_action={
                    "type": "collect_requirement",
                    "field": "area",
                },
            )

        filters = dict(
            state.required
        )

        # list_areas owns city and intentionally ignores old area.
        filters.pop(
            "area",
            None,
        )

        searcher = getattr(knowledge, "search", None)
        if callable(searcher) and filters.get("bedrooms"):
            try:
                exact_matches = searcher(
                    city=city,
                    property_type=filters.get("property_type"),
                    purpose=filters.get("purpose"),
                    budget=filters.get("budget"),
                    bedrooms=filters.get("bedrooms"),
                )
                if not exact_matches:
                    return None
            except Exception:
                pass

        try:
            if hasattr(knowledge, "list_available_areas"):
                areas = lister(
                    city=city,
                    property_type=filters.get("property_type"),
                    purpose=filters.get("purpose"),
                    budget=filters.get("budget"),
                )
            else:
                areas = lister(
                    city,
                    filters=filters,
                )
        except TypeError:
            areas = []
        except Exception:
            areas = []

        if not areas:
            # No area is active yet, so asking the user to "relax area"
            # would be misleading. Let the scoped search execute with the
            # current city/purpose/budget and use grounded no-result recovery
            # to identify which ACTIVE constraint is actually blocking matches.
            return None

        preview, has_more = (
            self.presentation.preview_choices(
                areas
            )
        )

        areas_str = ", ".join(preview)
        extra_note = " aur bhi areas available hain" if has_more else ""

        return RequirementDecision(
            field="area",
            message=(
                f"Ji! {city} mein in areas mein behtareen verified options available hain: {areas_str}{extra_note}. "
                "Aap kis area ke options dekhna chahenge? Agar area flexible hai to bata dein."
            ),
            pending_action={
                "type": "choose_verified_area",
                "field": "area",
                "city": city,
                "options": list(preview),
            },
        )

    def _city_decision(
        self,
        *,
        state,
        knowledge,
    ) -> RequirementDecision:
        lister = getattr(
            knowledge,
            "list_cities",
            None,
        )

        cities: list[str] = []

        if callable(lister):
            filters = dict(
                state.required
            )
            filters.pop(
                "city",
                None,
            )
            filters.pop(
                "area",
                None,
            )

            try:
                cities = lister(
                    filters=filters,
                )
            except Exception:
                cities = []

        if cities:
            preview, has_more = (
                self.presentation.preview_choices(
                    cities
                )
            )

            extra_text = (
                " Aur verified cities bhi available hain."
                if has_more
                else ""
            )

            return RequirementDecision(
                field="city",
                message=(
                    "Ji. Current verified data mein matching options "
                    "in cities mein available hain: "
                    + ", ".join(preview)
                    + "."
                    + extra_text
                    + " Aap kis city mein dekhna chahti hain?"
                ),
                pending_action={
                    "type": "collect_requirement",
                    "field": "city",
                    "options": list(preview),
                },
            )

        return RequirementDecision(
            field="city",
            message=(
                "Aap kis city mein property dekhna chahti hain?"
            ),
            pending_action={
                "type": "collect_requirement",
                "field": "city",
            },
        )

    def _value(
        self,
        key: str,
        required: dict[str, Any],
        preferred: dict[str, Any],
    ) -> Any:
        if key in required:
            return required.get(key)

        return preferred.get(key)

    def _same_text(
        self,
        left: Any,
        right: str,
    ) -> bool:
        if not isinstance(
            left,
            str,
        ):
            return False

        return (
            " ".join(
                left.casefold().split()
            )
            ==
            " ".join(
                right.casefold().split()
            )
        )
