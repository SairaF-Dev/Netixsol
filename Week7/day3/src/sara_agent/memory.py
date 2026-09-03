from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    required: dict[str, Any] = field(default_factory=dict)
    preferred: dict[str, Any] = field(default_factory=dict)
    excluded: dict[str, list[Any]] = field(default_factory=dict)

    # Fields the user has explicitly relaxed/broadened, e.g.
    # "area koi bhi", "budget flexible", or "Islamabad mein aur options".
    # This is conversation state only; it is never sent as a DB filter.
    flexible: set[str] = field(default_factory=set)

    # last_results = only the CURRENTLY DISPLAYED batch. This keeps
    # "option 2" references human and unambiguous.
    last_results: list[dict[str, Any]] = field(default_factory=list)

    # Full ranked candidate pool for progressive "aur options" paging.
    result_pool: list[dict[str, Any]] = field(default_factory=list)
    result_cursor: int = 0

    selected_property: dict[str, Any] | None = None

    last_intent: str | None = None
    pending_action: dict[str, Any] | None = None
    history: list[dict[str, str]] = field(default_factory=list)

    @property
    def preferences(self) -> dict[str, Any]:
        # Backward-compatible hard-filter view.
        return dict(self.required)

    def apply(
        self,
        required: dict[str, Any] | None = None,
        preferred: dict[str, Any] | None = None,
        excluded: dict[str, list[Any]] | None = None,
        relax: list[str] | None = None,
    ) -> None:
        """
        Merge CURRENT-turn constraint changes into memory.

        Important rules:
        1. If the parent location (city) changes and the current turn does
           not explicitly provide an area, clear the old area. An area is
           scoped to its previous city and must not leak into the new city.
        2. If committed search constraints change, invalidate old results,
           selected property and pending property workflow.
        """

        required = required or {}
        preferred = preferred or {}
        excluded = excluded or {}
        relax = relax or []

        before = self._constraint_snapshot()

        # --------------------------------------------------------------
        # 0. Parent/child location consistency
        # --------------------------------------------------------------
        old_city = self.required.get("city")
        new_city = required.get("city")

        current_turn_mentions_area = (
            "area" in required
            or "area" in preferred
            or "area" in excluded
            or "area" in relax
        )

        if (
            new_city is not None
            and old_city is not None
            and not self._equivalent(old_city, new_city)
            and not current_turn_mentions_area
        ):
            # A new hard city invalidates the old city-scoped area.
            self.required.pop("area", None)
            self.preferred.pop("area", None)
            self.excluded.pop("area", None)

        # --------------------------------------------------------------
        # 1. Relax old constraints
        # --------------------------------------------------------------
        for field_name in relax:
            self.required.pop(field_name, None)
            self.preferred.pop(field_name, None)
            self.excluded.pop(field_name, None)

            if isinstance(field_name, str) and field_name.strip():
                self.flexible.add(field_name)

        # --------------------------------------------------------------
        # 2. Apply hard requirements
        # --------------------------------------------------------------
        for key, value in required.items():
            if self._is_empty(value):
                continue

            self.required[key] = value
            self.flexible.discard(key)

            # Hard requirement supersedes an older soft preference.
            self.preferred.pop(key, None)

            # Remove an exact contradictory exclusion.
            self._remove_matching_exclusion(key, value)

        # --------------------------------------------------------------
        # 3. Apply soft preferences
        # --------------------------------------------------------------
        for key, value in preferred.items():
            if self._is_empty(value):
                continue

            self.preferred[key] = value
            self.flexible.discard(key)

            # User explicitly softened this field.
            self.required.pop(key, None)

            self._remove_matching_exclusion(key, value)

        # --------------------------------------------------------------
        # 4. Apply exclusions
        # --------------------------------------------------------------
        for key, values in excluded.items():
            if not isinstance(values, list):
                values = [values]

            cleaned = [
                value
                for value in values
                if not self._is_empty(value)
            ]

            if not cleaned:
                continue

            existing = list(self.excluded.get(key, []))

            for value in cleaned:
                if not self._contains_equivalent(existing, value):
                    existing.append(value)

            self.excluded[key] = existing

            current_required = self.required.get(key)
            if (
                current_required is not None
                and self._matches_any(current_required, cleaned)
            ):
                self.required.pop(key, None)

            current_preferred = self.preferred.get(key)
            if (
                current_preferred is not None
                and self._matches_any(current_preferred, cleaned)
            ):
                self.preferred.pop(key, None)

        after = self._constraint_snapshot()

        # --------------------------------------------------------------
        # 5. Invalidate stale result-dependent state
        # --------------------------------------------------------------
        if before != after:
            self._invalidate_search_results()

    def store_results(
        self,
        results: list[dict[str, Any]],
    ) -> None:
        """
        Backward-compatible exact visible-result storage.

        Used when a factual follow-up filters the CURRENT displayed batch.
        """
        self.result_pool = list(results)
        self.result_cursor = len(self.result_pool)
        self.last_results = list(results)

        if len(self.last_results) == 1:
            self.selected_property = self.last_results[0]
        else:
            self.selected_property = None

    def store_result_pool(
        self,
        results: list[dict[str, Any]],
        batch_size: int,
    ) -> list[dict[str, Any]]:
        """
        Store a full ranked candidate pool and expose only the first
        human-sized batch.
        """

        safe_size = max(
            1,
            int(batch_size),
        )

        self.result_pool = list(results)
        self.result_cursor = 0
        self.selected_property = None

        return self.next_result_batch(
            safe_size
        )

    def next_result_batch(
        self,
        batch_size: int,
    ) -> list[dict[str, Any]]:
        safe_size = max(
            1,
            int(batch_size),
        )

        if (
            not self.result_pool
            or self.result_cursor >= len(self.result_pool)
        ):
            self.last_results = []
            self.selected_property = None
            return []

        start = self.result_cursor
        end = min(
            len(self.result_pool),
            start + safe_size,
        )

        batch = self.result_pool[
            start:end
        ]

        self.result_cursor = end
        self.last_results = list(batch)

        if len(self.last_results) == 1:
            self.selected_property = self.last_results[0]
        else:
            self.selected_property = None

        return list(batch)

    def has_more_results(
        self,
    ) -> bool:
        return (
            bool(self.result_pool)
            and self.result_cursor < len(self.result_pool)
        )

    def remaining_result_count(
        self,
    ) -> int:
        return max(
            0,
            len(self.result_pool)
            - self.result_cursor,
        )

    def select_result(
        self,
        index: int,
    ) -> dict[str, Any] | None:
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
        ):
            return None

        if 0 <= index < len(self.last_results):
            self.selected_property = self.last_results[index]
            return self.selected_property

        return None

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:
        self.history.append(
            {
                "role": role,
                "content": content,
            }
        )
        self.history = self.history[-30:]

    def clear_selection(self) -> None:
        self.selected_property = None

    def clear_results(self) -> None:
        self.last_results.clear()
        self.result_pool.clear()
        self.result_cursor = 0
        self.selected_property = None

    def clear(self) -> None:
        self.required.clear()
        self.preferred.clear()
        self.excluded.clear()
        self.flexible.clear()

        self.last_results.clear()
        self.result_pool.clear()
        self.result_cursor = 0
        self.selected_property = None

        self.last_intent = None
        self.pending_action = None
        self.history.clear()

    def _invalidate_search_results(self) -> None:
        self.last_results.clear()
        self.result_pool.clear()
        self.result_cursor = 0
        self.selected_property = None
        self.pending_action = None

    def _constraint_snapshot(self) -> tuple[Any, Any, Any, Any]:
        return (
            self._freeze(self.required),
            self._freeze(self.preferred),
            self._freeze(self.excluded),
            tuple(sorted(self.flexible)),
        )

    def _remove_matching_exclusion(
        self,
        key: str,
        positive_value: Any,
    ) -> None:
        if key not in self.excluded:
            return

        remaining = [
            value
            for value in self.excluded[key]
            if not self._equivalent(value, positive_value)
        ]

        if remaining:
            self.excluded[key] = remaining
        else:
            self.excluded.pop(key, None)

    def _matches_any(
        self,
        value: Any,
        candidates: list[Any],
    ) -> bool:
        return any(
            self._equivalent(value, candidate)
            for candidate in candidates
        )

    def _contains_equivalent(
        self,
        values: list[Any],
        candidate: Any,
    ) -> bool:
        return any(
            self._equivalent(value, candidate)
            for value in values
        )

    def _equivalent(
        self,
        left: Any,
        right: Any,
    ) -> bool:
        if isinstance(left, str) and isinstance(right, str):
            return self._normalize_text(left) == self._normalize_text(right)

        return left == right

    def _normalize_text(
        self,
        value: str,
    ) -> str:
        return " ".join(value.strip().casefold().split())

    def _is_empty(
        self,
        value: Any,
    ) -> bool:
        return value in (None, "", [])

    def _freeze(
        self,
        value: Any,
    ) -> Any:
        if isinstance(value, dict):
            return tuple(
                sorted(
                    (key, self._freeze(item))
                    for key, item in value.items()
                )
            )

        if isinstance(value, list):
            return tuple(self._freeze(item) for item in value)

        if isinstance(value, tuple):
            return tuple(self._freeze(item) for item in value)

        return value


ConversationMemory = ConversationState
