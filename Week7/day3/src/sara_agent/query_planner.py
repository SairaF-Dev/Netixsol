from __future__ import annotations

from decimal import Decimal
from typing import Any

from .memory import ConversationState
from .models import QueryPlan, UserUnderstanding


class QueryPlanner:
    """Turn current understanding into a deterministic verified-data plan.

    Clarification turns may still contain safe information (for example a
    budget while purpose is missing). Only the ambiguous field is withheld
    from committed memory; unrelated explicit constraints are preserved.
    """

    _AMBIGUOUS_FIELDS_BY_REASON = {
        "selected_area_not_available": {"area"},
        "ambiguous_location_fragment": {"area"},
        "incomplete_location": {"area"},
        "ambiguous_property_type": {"property_type"},
        "ambiguous_bedrooms": {"bedrooms"},
        "ambiguous_purpose": {"purpose"},
        "unverified_location": {"city", "area"},
    }

    def build_plan(
        self,
        u: UserUnderstanding,
        state: ConversationState,
    ) -> QueryPlan:
        required = dict(u.required)
        preferred = dict(u.preferred)
        excluded = {
            key: list(values)
            for key, values in u.excluded.items()
        }
        relax = list(u.relax)

        if u.needs_clarification:
            ambiguous = self._AMBIGUOUS_FIELDS_BY_REASON.get(
                u.clarification_reason,
                set(),
            )

            for field_name in ambiguous:
                required.pop(field_name, None)
                preferred.pop(field_name, None)
                excluded.pop(field_name, None)
                relax = [
                    item
                    for item in relax
                    if item != field_name
                ]

        state.apply(
            required,
            preferred,
            excluded,
            relax,
        )

        if u.selected_index is not None:
            if state.select_result(u.selected_index) is None:
                return self._plan(
                    state,
                    needs_clarification=True,
                    clarification_reason="selected_result_not_available",
                )

        if u.needs_clarification:
            return self._plan(
                state,
                needs_clarification=True,
                clarification_reason=u.clarification_reason,
            )

        if u.comparison.field and u.comparison.operator:
            ref = self._resolve_reference(u, state)

            if ref is None:
                return self._plan(
                    state,
                    needs_clarification=True,
                    clarification_reason="missing_comparison_reference",
                )

            value = ref.get(u.comparison.field)

            if (
                isinstance(value, bool)
                or not isinstance(
                    value,
                    (int, float, Decimal),
                )
            ):
                return self._plan(
                    state,
                    selected_property=ref,
                    needs_clarification=True,
                    clarification_reason="missing_verified_comparison_value",
                )

            return self._plan(
                state,
                comparison_field=u.comparison.field,
                comparison_operator=u.comparison.operator,
                comparison_value=value,
                selected_property=ref,
            )

        return self._plan(
            state,
            selected_property=state.selected_property,
        )

    def _plan(
        self,
        state: ConversationState,
        **kwargs: Any,
    ) -> QueryPlan:
        return QueryPlan(
            required=dict(state.required),
            preferred=dict(state.preferred),
            excluded={
                key: list(values)
                for key, values in state.excluded.items()
            },
            **kwargs,
        )

    def _resolve_reference(
        self,
        u: UserUnderstanding,
        state: ConversationState,
    ) -> dict[str, Any] | None:
        ref = (
            u.comparison.reference
            or u.reference_type
        )

        if ref == "selected_property":
            return state.selected_property

        mapping = {
            "first_result": 0,
            "second_result": 1,
            "third_result": 2,
        }

        if ref in mapping:
            index = mapping[ref]
            if index < len(state.last_results):
                return state.last_results[index]
            return None

        if ref == "last_result":
            return (
                state.last_results[-1]
                if state.last_results
                else None
            )

        return state.selected_property
