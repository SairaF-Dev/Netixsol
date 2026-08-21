from state import AgentState

def clarification_node(state: AgentState) -> AgentState:
    return {
        **state,
        "final_response": state.get("validation_error") or
        "I need a little more information before I can answer safely.",
        "validation_status": "needs_clarification",
    }
