from state import AgentState

from tools.retrieval_tools import (
    VALID_TEAMS,
    get_team_h2h_record,
    get_team_recent_form,
    get_team_recent_results,
)

from tools.team_resolver import extract_team_mentions


def retrieval_node(state: AgentState) -> AgentState:

    query = state["user_query"].lower()

    # ------------------------------------------------------------------
    # Resolve teams
    # ------------------------------------------------------------------

    teams = extract_team_mentions(
        state["user_query"],
        VALID_TEAMS,
    )

    # ------------------------------------------------------------------
    # ACTUAL RECENT RESULTS
    # ------------------------------------------------------------------

    result_triggers = (
        "last 5 results",
        "last five results",
        "recent results",
        "recent matches",
        "last five games",
        "last 5 games",
    )

    if any(
        trigger in query
        for trigger in result_triggers
    ):

        if not teams:

            return {
                **state,
                "tool_name": "team_recent_results",
                "validation_status": "needs_clarification",
                "validation_error":
                    "Please specify an AFL team.",
            }

        team = teams[0]

        result = get_team_recent_results(
            team,
            5,
        )

        if isinstance(result, dict) and result.get("error"):

            return {
                **state,
                "tool_name": "team_recent_results",
                "validation_status": "needs_clarification",
                "validation_error": result["error"],
            }

        return {
            **state,
            "tool_name": "team_recent_results",
            "tools_called":
                state.get("tools_called", [])
                + ["team_recent_results"],
            "tool_result": result,
        }

    # ------------------------------------------------------------------
    # RECENT FORM
    # ------------------------------------------------------------------

    form_triggers = (
        "recent form",
        "form",
        "win rate",
        "average score",
        "ladder rank",
    )

    if any(
        trigger in query
        for trigger in form_triggers
    ):

        if teams:

            result = get_team_recent_form(
                teams[0],
                5,
            )

            return {
                **state,
                "tool_name": "team_recent_form",
                "tools_called":
                    state.get("tools_called", [])
                    + ["team_recent_form"],
                "tool_result": result,
            }

    # ------------------------------------------------------------------
    # HEAD-TO-HEAD
    # ------------------------------------------------------------------

    if any(
        x in query
        for x in (
            "head-to-head",
            "head to head",
            "h2h",
            "against",
        )
    ):

        if len(teams) >= 2:

            result = get_team_h2h_record(
                teams[0],
                teams[1],
            )

            return {
                **state,
                "tool_name": "team_h2h_record",
                "tools_called":
                    state.get("tools_called", [])
                    + ["team_h2h_record"],
                "tool_result": result,
            }

        return {
            **state,
            "tool_name": "team_h2h_record",
            "validation_status": "needs_clarification",
            "validation_error":
                "I need two identifiable AFL teams "
                "for the head-to-head lookup.",
        }

    # ------------------------------------------------------------------
    # Unsupported retrieval
    # ------------------------------------------------------------------

    return {
        **state,
        "tool_name": "retrieval",
        "validation_status": "needs_clarification",
        "validation_error":
            "I could not safely map this retrieval question "
            "to an available structured lookup. "
            "Please specify the team/player and statistic.",
    }