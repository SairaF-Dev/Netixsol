from state import AgentState


def factual_node(state: AgentState) -> AgentState:
    """Answer only general AFL factual/rules questions.

    This deliberately does not manufacture dataset-specific statistics.
    """
    return {
        **state,
        "tool_name": "direct_factual_answer",
        "tool_result": None,
        "validation_status": "valid",
    }
