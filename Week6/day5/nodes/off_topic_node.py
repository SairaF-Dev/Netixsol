from state import AgentState
from guardrails import OFF_TOPIC_RESPONSE

def off_topic_node(state: AgentState) -> AgentState:
    return {
        **state,
        "tool_name": "scope_refusal",
        "tools_called": state.get("tools_called", []) + ["scope_refusal"],
        "tool_result": None,
        "validation_status": "valid",
        "final_response": OFF_TOPIC_RESPONSE,
    }
