from state import AgentState


def clarification_node(state: AgentState) -> AgentState:
    """
    Ask the user for missing information while preserving
    the pending prediction context.
    """

    validation_error = state.get("validation_error")

    return {
        **state,
        "final_response": (
            validation_error
            or "I need a little more information before I can answer safely."
        ),
        "validation_status": "needs_clarification",
    }