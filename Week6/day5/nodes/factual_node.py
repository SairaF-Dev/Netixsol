from state import AgentState

def factual_node(state: AgentState) -> AgentState:
    return {
        **state,
        "tool_name": "direct_factual_answer",
        "tools_called": state.get("tools_called", []) + ["direct_factual_answer"],
        "tool_result": None,
        "validation_status": "valid",
    }
