"""Small bridge to existing Sara understanding, memory and presentation policies.

No LLM response generation or property retrieval lives here.
"""
from sara_agent.understanding import UserUnderstandingService
from sara_agent.memory import ConversationState
from sara_agent.query_planner import QueryPlanner
from sara_agent.conversation_policy import ConversationPolicy
from sara_agent.result_presentation import ResultPresentationPolicy
from sara_agent.natural_speech import NaturalSpeechPolicy


def resolve_property_reference(understanding, order, selected=None):
    explicit = getattr(understanding, "interaction_property_id", None)
    if explicit:
        return explicit if explicit in order else None
    index = getattr(understanding, "selected_index", None)
    if isinstance(index, int) and not isinstance(index, bool):
        return order[index] if 0 <= index < len(order) else None
    reference = getattr(understanding, "reference_type", None)
    positions = {"first_result": 0, "second_result": 1, "third_result": 2}
    if reference in positions:
        index = positions[reference]
        return order[index] if index < len(order) else None
    if reference == "last_result" and order:
        return order[-1]
    if reference == "selected_property":
        if selected in order:
            return selected
        if len(order) == 1:
            return order[0]
    return None


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
        service = self.understanding or UserUnderstandingService(deterministic_first=False)
        return service.understand(message, context=context)

    def hydrate(self, preferences, saved):
        fields = ("city", "area", "bedrooms", "property_type", "purpose", "amenities")
        required = {key: getattr(preferences, key) for key in fields
                    if preferences and getattr(preferences, key, None) not in (None, [])}
        if preferences and preferences.budget_max is not None:
            required["budget"] = preferences.budget_max
        return ConversationState(required=required, excluded=saved.get("excluded", {}), flexible=set(saved.get("flexible", [])),
                                 pending_action=saved.get("pending_action"))
