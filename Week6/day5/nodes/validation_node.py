import json

from state import AgentState


def validation_node(state: AgentState) -> AgentState:
    """
    Validate tool output before formatting.

    Handles:
    - None results
    - empty strings
    - JSON error strings
    - dictionary errors
    - list errors
    - unexpected result types
    """

    result = state.get("tool_result")
    intent = state.get("intent")

    # ================================================================
# 1. NO RESULT
# ================================================================

    if result is None:

        # ------------------------------------------------------------
        # IMPORTANT:
        #
        # A None tool_result is not always an error.
        #
        # For prediction clarification, the prediction node
        # intentionally returns None while waiting for required
        # information such as a date.
        # ------------------------------------------------------------

        if (
            state.get("validation_status")
            == "needs_clarification"
            and state.get("clarification_needed")
        ):

            return {
                **state,
                "validation_status": "needs_clarification",
                "validation_error": state.get(
                    "validation_error"
                ),
                "error": None,
            }

        # ------------------------------------------------------------
        # Genuine missing tool result
        # ------------------------------------------------------------

        error_message = (
            f"No result was returned for intent '{intent}'."
        )

        return {
            **state,
            "validation_status": "needs_clarification",
            "validation_error": error_message,
            "error": error_message,
        }

    # ================================================================
    # 2. STRING
    # ================================================================

    if isinstance(result, str):

        text = result.strip()

        if not text:

            error_message = (
                "Tool returned an empty result."
            )

            return {
                **state,
                "validation_status":
                    "needs_clarification",
                "validation_error":
                    error_message,
                "error":
                    error_message,
            }

        try:
            parsed = json.loads(text)

        except json.JSONDecodeError:

            return {
                **state,
                "validation_status": "valid",
                "validation_error": None,
                "error": None,
            }

        if isinstance(parsed, dict):

            if parsed.get("error"):

                error_message = str(
                    parsed["error"]
                )

                return {
                    **state,
                    "validation_status":
                        "needs_clarification",
                    "validation_error":
                        error_message,
                    "error":
                        error_message,
                }

        return {
            **state,
            "validation_status": "valid",
            "validation_error": None,
            "error": None,
        }

    # ================================================================
    # 3. DICTIONARY
    # ================================================================

    if isinstance(result, dict):

        if result.get("error"):

            error_message = str(
                result["error"]
            )

            return {
                **state,
                "validation_status":
                    "needs_clarification",
                "validation_error":
                    error_message,
                "error":
                    error_message,
            }

        if result.get("unsupported"):

            return {
                **state,
                "validation_status": "valid",
                "validation_error": None,
                "error": None,
            }

        return {
            **state,
            "validation_status": "valid",
            "validation_error": None,
            "error": None,
        }

    # ================================================================
    # 4. LIST
    # ================================================================

    if isinstance(result, list):

        if not result:

            error_message = (
                "Tool returned an empty list."
            )

            return {
                **state,
                "validation_status":
                    "needs_clarification",
                "validation_error":
                    error_message,
                "error":
                    error_message,
            }

        for item in result:

            if isinstance(item, dict):

                if item.get("error"):

                    error_message = str(
                        item["error"]
                    )

                    return {
                        **state,
                        "validation_status":
                            "needs_clarification",
                        "validation_error":
                            error_message,
                        "error":
                            error_message,
                    }

        return {
            **state,
            "validation_status": "valid",
            "validation_error": None,
            "error": None,
        }

    # ================================================================
    # 5. UNEXPECTED TYPE
    # ================================================================

    error_message = (
        "Unexpected tool result type: "
        f"{type(result).__name__}"
    )

    return {
        **state,
        "validation_status":
            "needs_clarification",
        "validation_error":
            error_message,
        "error":
            error_message,
    }