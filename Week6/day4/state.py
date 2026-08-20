from typing import Any, Literal, TypedDict


Intent = Literal["factual", "retrieval", "prediction", "off_topic"]
ValidationStatus = Literal["valid", "invalid", "needs_clarification"]


class AgentState(TypedDict, total=False):
    user_query: str
    conversation_history: list[dict[str, str]]

    intent: Intent
    router_reason: str

    tool_name: str
    tool_input: dict[str, Any]
    tool_result: Any

    validation_status: ValidationStatus
    validation_error: str

    final_response: str

    # ------------------------------------------------------------
    # Pending clarification state
    # ------------------------------------------------------------
    clarification_needed: str
    pending_tool_name: str

    # Saved prediction context
    team_a: str
    team_b: str
    date: str