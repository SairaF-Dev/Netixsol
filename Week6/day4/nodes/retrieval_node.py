from state import AgentState
from tools.retrieval_tools import (
    get_team_h2h_record,
    get_team_recent_form,
)


def retrieval_node(state: AgentState) -> AgentState:
    """A deterministic retrieval node for the common Day 4 test paths.

    The router decides retrieval; this node resolves a small set of explicit
    retrieval intents instead of giving a generic agent arbitrary tool freedom.
    """
    query = state["user_query"].lower()
    result = None
    tool_name = ""

    # Team recent-form path.
    for trigger in ("recent form", "last 5", "last five", "recent results"):
        if trigger in query:
            from tools.retrieval_tools import VALID_TEAMS
            from tools.team_resolver import extract_team_mentions

            teams = extract_team_mentions(state["user_query"], VALID_TEAMS)
            if teams:
                result = get_team_recent_form(teams[0], 5)
                tool_name = "team_recent_form"
                break

    # Head-to-head path.
    if result is None and any(
        x in query for x in ("head-to-head", "head to head", "h2h", "against")
    ):
        from tools.retrieval_tools import VALID_TEAMS
        from tools.team_resolver import extract_team_mentions

        teams = extract_team_mentions(state["user_query"], VALID_TEAMS)
        if len(teams) >= 2:
            result = get_team_h2h_record(teams[0], teams[1])
            tool_name = "team_h2h_record"
        else:
            return {
                **state,
                "tool_name": "team_h2h_record",
                "validation_status": "needs_clarification",
                "validation_error": "I need two identifiable AFL teams for the head-to-head lookup.",
            }

    if result is None:
        return {
            **state,
            "tool_name": "retrieval",
            "validation_status": "needs_clarification",
            "validation_error": (
                "I could not safely map this retrieval question to an available "
                "structured lookup. Please specify the team/player and statistic."
            ),
        }

    return {
        **state,
        "tool_name": tool_name,
        "tool_result": result,
    }
