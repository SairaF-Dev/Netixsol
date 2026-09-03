from __future__ import annotations

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

    def next_requirement(
        self,
        *,
        intent: str,
        state,
        knowledge,
    ) -> RequirementDecision | None:
        if intent not in self.SEARCH_INTENTS:
            return None

        required = state.required
        preferred = state.preferred
        flexible = getattr(
            state,
            "flexible",
            set(),
        )

        city = self._value(
            "city",
            required,
            preferred,
        )
        area = self._value(
            "area",
            required,
            preferred,
        )
        purpose = self._value(
            "purpose",
            required,
            preferred,
        )
        budget = self._value(
            "budget",
            required,
            preferred,
        )

        # Real-world default order: Purpose -> City -> Budget -> Area.
        # It is slot-driven, not a rigid script: already supplied fields
        # are skipped. Budget comes before area so the verified area list
        # is already relevant to the user's actual affordability.

        # 1. Purpose
        if (
            not purpose
            and "purpose" not in flexible
        ):
            message = (
                "Ji. Ye budget rent ke liye hai ya purchase ke liye?"
                if budget is not None
                else "Aap rent ke liye dekh rahi hain ya purchase ke liye?"
            )
            return RequirementDecision(
                field="purpose",
                message=message,
                pending_action={
                    "type": "collect_requirement",
                    "field": "purpose",
                },
            )

        # 2. City
        if (
            not city
            and not area
            and "city" not in flexible
        ):
            return self._city_decision(
                state=state,
                knowledge=knowledge,
            )

        if (
            area
            and not city
            and "city" not in flexible
        ):
            return self._city_decision(
                state=state,
                knowledge=knowledge,
            )

        # 3. Budget
        if (
            budget is None
            and "budget" not in flexible
        ):
            if self._same_text(purpose, "Rental"):
                message = (
                    "Aapka maximum monthly rental budget kitna hai? "
                    "Agar budget flexible hai to wo bhi bata sakti hain."
                )
            elif self._same_text(purpose, "Purchase"):
                message = (
                    "Aapka maximum purchase budget kitna hai? "
                    "Agar budget flexible hai to wo bhi bata sakti hain."
                )
            else:
                message = (
                    "Aapka approximate maximum budget kitna hai? "
                    "Agar budget flexible hai to wo bhi bata sakti hain."
                )

            return RequirementDecision(
                field="budget",
                message=message,
                pending_action={
                    "type": "collect_requirement",
                    "field": "budget",
                },
            )

        # 4. Area
        # list_areas() receives the current committed filters, so after
        # purpose/city/budget are known it returns only VERIFIED areas
        # that actually have matching inventory.
        if (
            city
            and not area
            and "area" not in flexible
        ):
            return self._area_decision(
                city=city,
                state=state,
                knowledge=knowledge,
            )

        return None

    def _area_decision(
        self,
        *,
        city: str,
        state,
        knowledge,
    ) -> RequirementDecision | None:
        lister = getattr(
            knowledge,
            "list_areas",
            None,
        )

        if not callable(lister):
            return RequirementDecision(
                field="area",
                message=(
                    f"Ji. {city} mein kis area mein dekhna chahti hain? "
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

        try:
            areas = lister(
                city,
                filters=filters,
            )
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

        lines = [
            f"{index}. {area}"
            for index, area
            in enumerate(
                preview,
                start=1,
            )
        ]

        extra_text = (
            "\nAur verified areas bhi available hain; "
            "aap unka naam directly bhi bata sakti hain."
            if has_more
            else ""
        )

        return RequirementDecision(
            field="area",
            message=(
                f"Ji. {city} mein aapke current criteria ke mutabiq "
                "ye kuch verified areas available hain:\n"
                + "\n".join(lines)
                + extra_text
                + "\nAap kis area mein dekhna chahti hain? "
                  "Agar area flexible hai to 'koi bhi area' keh dein."
            ),
            pending_action={
                "type": "choose_verified_area",
                "field": "area",
                "city": city,
                # Numeric choices are intentionally limited to what Sara
                # actually displayed. A named verified area is still
                # resolved normally by Day 2.
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
