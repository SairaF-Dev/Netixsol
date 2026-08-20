import json
from state import AgentState


def validation_node(state: AgentState) -> AgentState:
    if state.get("validation_status") == "needs_clarification":
        return state

    result = state.get("tool_result")

    if result is None and state.get("intent") == "retrieval":
        return {
            **state,
            "validation_status": "invalid",
            "validation_error": "Retrieval returned no result.",
        }

    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = result

        if isinstance(parsed, dict) and parsed.get("error"):
            return {
                **state,
                "validation_status": "needs_clarification",
                "validation_error": parsed["error"],
            }

    if isinstance(result, dict) and result.get("error"):
        return {
            **state,
            "validation_status": "needs_clarification",
            "validation_error": result["error"],
        }

    return {
        **state,
        "validation_status": "valid",
    }
