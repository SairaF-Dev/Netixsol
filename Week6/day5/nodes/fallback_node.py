from state import AgentState

def fallback_node(state: AgentState) -> AgentState:
    return {
        **state,
        "final_response": (
            "I couldn't satisfy that request with the available AFL tools/data. "
            "I won't guess. Please provide a supported AFL statistic, team/player, "
            "or a prediction type supported by the current models."
        ),
    }
