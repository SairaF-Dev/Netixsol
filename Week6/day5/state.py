from typing import Any, Literal, TypedDict


Intent = Literal[
    "factual",
    "retrieval",
    "prediction",
    "off_topic",
]


ValidationStatus = Literal[
    "valid",
    "invalid",
    "needs_clarification",
]


class AgentState(TypedDict, total=False):

    # ------------------------------------------------------------------
    # User / conversation
    # ------------------------------------------------------------------

    user_query: str

    conversation_history: list[dict[str, str]]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    intent: Intent

    router_reason: str

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    tool_name: str | None

    tools_called: list[str]

    tool_input: dict[str, Any] | None

    tool_result: Any

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    validation_status: ValidationStatus

    validation_error: str | None

    # ------------------------------------------------------------------
    # Final response
    # ------------------------------------------------------------------

    final_response: str | None

    # ------------------------------------------------------------------
    # Prediction metadata
    # ------------------------------------------------------------------

    prediction_metadata: dict[str, Any]

    # ------------------------------------------------------------------
    # Error / monitoring
    # ------------------------------------------------------------------

    error: str | None

    latency_ms: float

    # ------------------------------------------------------------------
    # Clarification state
    # ------------------------------------------------------------------

    clarification_needed: str | None

    pending_tool_name: str | None

    # ------------------------------------------------------------------
    # Prediction context
    # ------------------------------------------------------------------

    team_a: str | None

    team_b: str | None

    date: str | None

    # ------------------------------------------------------------------
    # Retrieval context
    # ------------------------------------------------------------------

    player_name: str | None

    player_id: int | None

    previous_intent: Intent | None

    previous_tool_name: str | None

    previous_query: str | None

    # ------------------------------------------------------------------
    # Evaluation / monitoring
    # ------------------------------------------------------------------

    request_id: str | None

    node_name: str | None

    success: bool | None
