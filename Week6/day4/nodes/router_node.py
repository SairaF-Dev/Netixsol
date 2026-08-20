from state import AgentState
from router import classify_intent


def router_node(state: AgentState) -> AgentState:
    result = classify_intent(state["user_query"])
    return {
        **state,
        "intent": result.intent,
        "router_reason": result.reasoning,
    }
