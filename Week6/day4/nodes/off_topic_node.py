from state import AgentState


def off_topic_node(state: AgentState) -> AgentState:
    return {
        **state,
        "tool_name": "scope_refusal",
        "tool_result": None,
        "validation_status": "valid",
    }
