"""Small bridge to existing Sara understanding, memory and presentation policies.

No LLM response generation or property retrieval lives here.
"""
from dataclasses import dataclass
import re
from typing import Literal, Any

from sara_agent.understanding import UserUnderstandingService
from sara_agent.memory import ConversationState
from sara_agent.query_planner import QueryPlanner
from sara_agent.conversation_policy import ConversationPolicy
from sara_agent.result_presentation import ResultPresentationPolicy
from sara_agent.natural_speech import NaturalSpeechPolicy


@dataclass(frozen=True)
class PropertyResolutionResult:
    status: Literal["resolved", "ambiguous", "no_match"]
    value: Any = None  # str for resolved, list[str] for ambiguous, None for no_match

    def __bool__(self):
        return self.status == "resolved" and bool(self.value)

    def __eq__(self, other):
        if isinstance(other, PropertyResolutionResult):
            return self.status == other.status and self.value == other.value
        if other is None:
            return self.status == "no_match" or self.value is None
        if isinstance(other, str):
            return self.status == "resolved" and self.value == other
        return False


def resolve_property_reference(
    understanding,
    order,
    selected=None,
    shown_properties_map: dict[str, str] | None = None,
    raw_message: str | None = None,
) -> PropertyResolutionResult:
    if order is None:
        order = []

    explicit = getattr(understanding, "interaction_property_id", None)
    if explicit:
        if explicit in order:
            return PropertyResolutionResult("resolved", explicit)
        return PropertyResolutionResult("no_match", None)

    index = getattr(understanding, "selected_index", None)
    if isinstance(index, int) and not isinstance(index, bool):
        if 0 <= index < len(order):
            return PropertyResolutionResult("resolved", order[index])
        return PropertyResolutionResult("no_match", None)

    reference = getattr(understanding, "reference_type", None)
    positions = {"first_result": 0, "second_result": 1, "third_result": 2}
    if reference in positions:
        pos_idx = positions[reference]
        if pos_idx < len(order):
            return PropertyResolutionResult("resolved", order[pos_idx])
        return PropertyResolutionResult("no_match", None)

    if reference == "last_result" and order:
        return PropertyResolutionResult("resolved", order[-1])

    # Name-based matching if shown_properties_map and raw_message are available
    if shown_properties_map and raw_message:
        raw_lower = raw_message.casefold()
        matched = []
        for pid in order:
            name = shown_properties_map.get(pid)
            if not name:
                continue
            name_lower = name.casefold()
            if name_lower in raw_lower:
                matched.append(pid)
            else:
                name_words = [
                    w for w in re.split(r"\s+", name_lower)
                    if len(w) > 2 and w not in {
                        "the", "and", "for", "with", "apartments", "apartment",
                        "house", "villas", "villa", "plot", "plots", "phase"
                    }
                ]
                if name_words and all(re.search(r"\b" + re.escape(w) + r"\b", raw_lower) for w in name_words):
                    matched.append(pid)
        if len(matched) == 1:
            return PropertyResolutionResult("resolved", matched[0])
        elif len(matched) > 1:
            exact_matches = [pid for pid in matched if shown_properties_map.get(pid, "").casefold() in raw_lower]
            if len(exact_matches) == 1:
                return PropertyResolutionResult("resolved", exact_matches[0])
            return PropertyResolutionResult("ambiguous", matched)

    if reference == "selected_property":
        if selected in order:
            return PropertyResolutionResult("resolved", selected)
        if len(order) == 1:
            return PropertyResolutionResult("resolved", order[0])

    return PropertyResolutionResult("no_match", None)


class SaraService:
    def __init__(self, understanding=None):
        self.understanding = understanding
        self.planner = QueryPlanner()
        self.presentation = ResultPresentationPolicy(mode="chat")
        self.policy = ConversationPolicy(self.presentation)
        self.speech = NaturalSpeechPolicy()

    def understand(self, message, context):
        # Lazy construction avoids requiring an LLM key at API startup.
        # The Day 3 chatbot repairs partial deterministic extraction using its
        # own verified-location pass. This adapter needs complete structured NLU.
        if self.understanding is None:
            self.understanding = UserUnderstandingService(deterministic_first=True)
        return self.understanding.understand(message, context=context)

    def hydrate(self, preferences, saved):
        fields = ("city", "area", "bedrooms", "property_type", "purpose", "amenities")
        required = {key: getattr(preferences, key) for key in fields
                    if preferences and getattr(preferences, key, None) not in (None, [])}
        if preferences and preferences.budget_max is not None:
            required["budget"] = preferences.budget_max
        return ConversationState(required=required, excluded=saved.get("excluded", {}), flexible=set(saved.get("flexible", [])),
                                 pending_action=saved.get("pending_action"))
