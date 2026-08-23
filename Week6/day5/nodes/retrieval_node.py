from __future__ import annotations

import re

from state import AgentState

from tools.retrieval_tools import (
    VALID_TEAMS,
    get_team_h2h_record,
    get_team_recent_form,
    get_team_recent_results,
    get_player_statistics,
    resolve_player_name,
)

from tools.team_resolver import extract_team_mentions


# ============================================================================
# HELPERS
# ============================================================================

def _extract_year(query: str) -> int | None:
    """
    Extract a 4-digit year from the user's query.

    Example:
        "What about 2024?" -> 2024
        "Nick Daicos stats in 2023" -> 2023
    """

    match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        query,
    )

    if not match:
        return None

    return int(match.group(1))


def _extract_player_name(query: str) -> str | None:
    """
    Extract a player name from an AFL statistics query.

    Examples:
        Patrick Cripps career statistics?
            -> Patrick Cripps

        Patrick Cripps career stats
            -> Patrick Cripps

        Nick Daicos stats in 2024
            -> Nick Daicos

        What are Nick Daicos statistics?
            -> Nick Daicos

        How many disposals did Nick Daicos have?
            -> Nick Daicos
    """

    text = (query or "").strip()

    if not text:
        return None

    # ---------------------------------------------------------------
    # Remove possessive "'s"
    # ---------------------------------------------------------------

    text = re.sub(
        r"'s\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # ---------------------------------------------------------------
    # Remove year
    # ---------------------------------------------------------------

    text = re.sub(
        r"\b(?:19\d{2}|20\d{2})\b",
        "",
        text,
    )

    # ---------------------------------------------------------------
    # Normalize whitespace
    # ---------------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # ---------------------------------------------------------------
    # IMPORTANT:
    #
    # Remove statistic/context words BEFORE extracting the name.
    #
    # This fixes:
    #
    # Patrick Cripps career statistics
    #
    # from becoming:
    #
    # Patrick Cripps career
    # ---------------------------------------------------------------

    statistic_words = (
        r"statistics?|"
        r"stats?|"
        r"performance|"
        r"numbers?|"
        r"career"
    )

    # ---------------------------------------------------------------
    # CASE 1:
    #
    # "How many disposals did Nick Daicos have?"
    # "How many goals did Patrick Cripps score?"
    # ---------------------------------------------------------------

    match = re.search(
        r"\b(?:did|does|do|were|was)\s+"
        r"([A-Za-z][A-Za-z\-']+(?:\s+[A-Za-z][A-Za-z\-']+){1,2})"
        r"\s+(?:have|has|had|score|scored|record|recorded|average)\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        candidate = match.group(1).strip()

        # Remove accidental trailing context words.
        candidate = re.sub(
            rf"\s+\b(?:{statistic_words})\b.*$",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip()

        if len(candidate.split()) >= 2:
            return candidate

    # ---------------------------------------------------------------
    # CASE 2:
    #
    # "statistics of Nick Daicos"
    # "stats for Patrick Cripps"
    # "performance of Nick Daicos"
    # ---------------------------------------------------------------

    match = re.search(
        rf"\b(?:statistics?|stats?|performance|numbers?)"
        r"\s+(?:of|for)\s+"
        r"([A-Za-z][A-Za-z\-']+(?:\s+[A-Za-z][A-Za-z\-']+){1,2})",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        candidate = match.group(1).strip()

        candidate = re.split(
            r"\s+\b(?:in|during|from|for|last|match|game|career|"
            r"statistics?|stats?|performance|numbers?)\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if len(candidate.split()) >= 2:
            return candidate

    # ---------------------------------------------------------------
    # CASE 3:
    #
    # "Patrick Cripps career statistics"
    # "Patrick Cripps career stats"
    # "Nick Daicos statistics"
    # "Nick Daicos performance"
    #
    # This is the IMPORTANT FIX.
    #
    # We explicitly remove everything beginning with:
    # career / stats / statistics / performance / numbers
    # ---------------------------------------------------------------

    candidate = text

    candidate = re.sub(
        rf"\s+\b(?:{statistic_words})\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()

    # ---------------------------------------------------------------
    # Remove common question words from beginning
    # ---------------------------------------------------------------

    candidate = re.sub(
        r"^(?:what\s+are|what\s+were|what\s+is|"
        r"tell\s+me\s+about|show\s+me|give\s+me|"
        r"how\s+about)\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()

    # ---------------------------------------------------------------
    # Remove leading "of" / "for"
    # ---------------------------------------------------------------

    candidate = re.sub(
        r"^(?:of|for)\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()

    # ---------------------------------------------------------------
    # Remove trailing punctuation
    # ---------------------------------------------------------------

    candidate = re.sub(
        r"[?!.,:;]+$",
        "",
        candidate,
    ).strip()

    # ---------------------------------------------------------------
    # Conservative validation.
    #
    # AFL player names normally need at least two words.
    # ---------------------------------------------------------------

    words = candidate.split()

    if 2 <= len(words) <= 3:

        ignored_words = {
            "what",
            "are",
            "were",
            "is",
            "was",
            "about",
            "tell",
            "me",
            "show",
            "give",
            "the",
            "his",
            "her",
            "their",
            "stats",
            "stat",
            "statistics",
            "statistic",
            "performance",
            "numbers",
            "career",
        }

        if not any(
            word.casefold() in ignored_words
            for word in words
        ):
            return candidate

    return None

def _is_player_followup(query: str) -> bool:
    """Recognize pronoun-only player-statistics continuations."""
    return bool(re.fullmatch(
        r"\s*(?:what\s+about\s+(?:his|her|their)\s+(?:stats?|statistics?)|"
        r"how\s+many\s+\w+(?:\s+\w+)?\s+did\s+(?:he|she|they)\s+have)\??\s*",
        query or "",
        flags=re.IGNORECASE,
    ))


def _has_invalid_team_phrase(query: str) -> bool:
    """Reject invented two-word team names before a mascot alias can match."""
    valid_names = {team.casefold() for team in VALID_TEAMS}
    mascots = "Tigers|Blues|Magpies|Bombers|Cats|Dockers|Giants|Hawks|Demons|Saints|Swans|Eagles|Lions|Crows|Power|Bulldogs|Kangaroos|Suns"

    for match in re.finditer(rf"\b([A-Za-z]+[ ]+(?:{mascots}))\b", query):
        candidate = match.group(1).casefold()
        first_word = candidate.split()[0]
        if candidate not in valid_names and first_word not in {"the", "a", "an"}:
            return True

    return False


# ============================================================================
# RETRIEVAL NODE
# ============================================================================

def retrieval_node(state: AgentState) -> AgentState:

    query = state.get(
        "user_query",
        "",
    ).strip()

    query_lower = query.lower()

    # =========================================================================
    # RESOLVE TEAMS
    # =========================================================================

    # =========================================================================
# RESOLVE TEAMS
# =========================================================================

    teams = extract_team_mentions(
        query,
        VALID_TEAMS,
    )

    # -------------------------------------------------------------------------
    # Explicit matchup fallback
    #
    # Supports:
    #   Collingwood vs Richmond
    #   Collingwood vs. Richmond
    #   Collingwood versus Richmond
    #   Collingwood against Richmond
    #
    # This is needed because retrieval queries such as
    # "Collingwood vs Richmond result" should resolve both teams
    # before H2H retrieval is attempted.
    # -------------------------------------------------------------------------

    if len(teams) < 2:

        matchup = re.search(
            r"\b(.+?)\s+(?:vs\.?|versus|against)\s+(.+?)(?:\s+result|\s+results)?$",
            query,
            flags=re.IGNORECASE,
        )

        if matchup:

            left_text = matchup.group(1).strip()
            right_text = matchup.group(2).strip()

            left_teams = extract_team_mentions(
                left_text,
                VALID_TEAMS,
            )

            right_teams = extract_team_mentions(
                right_text,
                VALID_TEAMS,
            )

            if left_teams and right_teams:

                teams = [
                    left_teams[0],
                    right_teams[0],
                ]

    invalid_team_phrase = _has_invalid_team_phrase(query)

    if invalid_team_phrase:
        teams = []

    # =========================================================================
    # YEAR
    # =========================================================================

    year = _extract_year(query)

    # =========================================================================
    # PLAYER NAME
    # =========================================================================
    #
    # IMPORTANT:
    #
    # The raw player dataset does NOT contain player_name.
    #
    # We therefore pass the player name to get_player_statistics(),
    # which will resolve:
    #
    #     player_name
    #          ↓
    #     player_id
    #          ↓
    #     raw player statistics
    #
    # =========================================================================

    player_name = _extract_player_name(query)
    previous_player_name = state.get("player_name")
    previous_player_id = state.get("player_id")

    # A pronoun follow-up must use the resolved player context, not words such
    # as "about his" that happen to resemble a two-word name.
    if _is_player_followup(query) and previous_player_name:
        player_name = previous_player_name

    # =========================================================================
    # PLAYER STATISTICS
    # =========================================================================

    player_stat_triggers = (
        "player statistics",
        "player stats",
        "statistics",
        "stats",
        "statistic",
        "performance",
        "disposals",
        "disposal",
        "kicks",
        "marks",
        "handballs",
        "goals",
        "tackles",
        "clearances",
        "fantasy points",
        "brownlow votes",
        "inside 50",
        "inside 50s",
    )

    is_player_stat_request = any(
            trigger in query_lower
            for trigger in player_stat_triggers
        )
    if (player_name and is_player_stat_request) or (
        state.get("previous_intent") == "retrieval"
        and previous_player_name
        and (year is not None or _is_player_followup(query))
    ):

        if not player_name:
            player_name = previous_player_name
        resolved = resolve_player_name(player_name)
        player_id = resolved["player_id"] if resolved else previous_player_id

        tool_input = {
            "player_name": player_name,
            "player_id": player_id,
        }

        if year is not None:
            tool_input["year"] = year

        result = get_player_statistics(
            player_name=player_name,
            year=year,
            player_id=player_id,
        )

        if isinstance(result, dict) and result.get("error"):

            return {
                **state,

                "tool_name": "player_statistics",

                "tool_input": tool_input,

                "tool_result": result,

                "validation_status": "needs_clarification",

                "validation_error": result["error"],
                "player_name": None,
                "player_id": None,
            }

        return {
            **state,

            "tool_name": "player_statistics",

            "tool_input": tool_input,

            "tools_called":
                state.get("tools_called", [])
                + ["player_statistics"],

            "tool_result": result,

            "validation_status": "valid",
            "player_name": result["player"],
            "player_id": result["player_id"],
        }

    # =========================================================================
    # ACTUAL RECENT RESULTS
    # =========================================================================

    result_triggers = (
        "last 5 results",
        "last five results",
        "recent results",
        "recent matches",
        "last five games",
        "last 5 games",
    )

    if any(
        trigger in query_lower
        for trigger in result_triggers
    ):

        if not teams:

            return {
                **state,

                "tool_name": "team_recent_results",

                "tool_input": None,

                "validation_status": "needs_clarification",

                "validation_error": (
                    "Please specify a recognized AFL team."
                    if invalid_team_phrase
                    else "Please specify an AFL team."
                ),
            }

        team = teams[0]

        tool_input = {
            "team": team,
            "n": 5,
        }

        result = get_team_recent_results(
            team,
            5,
        )

        if isinstance(result, dict) and result.get("error"):

            return {
                **state,

                "tool_name": "team_recent_results",

                "tool_input": tool_input,

                "tool_result": result,

                "validation_status": "needs_clarification",

                "validation_error": result["error"],
            }

        return {
            **state,

            "tool_name": "team_recent_results",

            "tool_input": tool_input,

            "tools_called":
                state.get("tools_called", [])
                + ["team_recent_results"],

            "tool_result": result,

            "validation_status": "valid",
        }

    # =========================================================================
    # RECENT FORM
    # =========================================================================

    form_triggers = (
        "recent form",
        "form",
        "win rate",
        "average score",
        "ladder rank",
    )

    if any(
        trigger in query_lower
        for trigger in form_triggers
    ):

        if not teams:

            # "their" refers to both teams from the immediately preceding
            # head-to-head request; retrieve both instead of guessing one.
            if (
                "their" in query_lower
                and state.get("previous_tool_name") == "team_h2h_record"
                and state.get("team_a")
                and state.get("team_b")
            ):
                team_a = state["team_a"]
                team_b = state["team_b"]
                return {
                    **state,
                    "tool_name": "team_recent_form",
                    "tool_input": {"teams": [team_a, team_b], "n": 5},
                    "tools_called": state.get("tools_called", []) + ["team_recent_form"],
                    "tool_result": {
                        "teams": [
                            get_team_recent_form(team_a, 5),
                            get_team_recent_form(team_b, 5),
                        ],
                    },
                    "validation_status": "valid",
                }

            return {
                **state,

                "tool_name": "team_recent_form",

                "tool_input": None,

                "validation_status": "needs_clarification",

                "validation_error":
                    "Please specify an AFL team.",
            }

        team = teams[0]

        tool_input = {
            "team": team,
            "n": 5,
        }

        result = get_team_recent_form(
            team,
            5,
        )

        if isinstance(result, dict) and result.get("error"):

            return {
                **state,

                "tool_name": "team_recent_form",

                "tool_input": tool_input,

                "tool_result": result,

                "validation_status": "needs_clarification",

                "validation_error": result["error"],
            }

        return {
            **state,

            "tool_name": "team_recent_form",

            "tool_input": tool_input,

            "tools_called":
                state.get("tools_called", [])
                + ["team_recent_form"],

            "tool_result": result,

            "validation_status": "valid",
        }

    # =========================================================================
    # HEAD-TO-HEAD
    # =========================================================================

    if any(
        x in query_lower
        for x in (
            "head-to-head",
            "head to head",
            "h2h",
            "against",
            " vs ",
            " vs. ",
            "versus",
        )
    ):

        if len(teams) >= 2:

            team_a = teams[0]
            team_b = teams[1]

            tool_input = {
                "team_a": team_a,
                "team_b": team_b,
            }

            result = get_team_h2h_record(
                team_a,
                team_b,
            )

            if isinstance(result, dict) and result.get("error"):

                return {
                    **state,

                    "tool_name": "team_h2h_record",

                    "tool_input": tool_input,

                    "tool_result": result,

                    "validation_status":
                        "needs_clarification",

                    "validation_error":
                        result["error"],
                }

            return {
                **state,

                "tool_name": "team_h2h_record",

                "tool_input": tool_input,

                "tools_called":
                    state.get("tools_called", [])
                    + ["team_h2h_record"],

                "tool_result": result,

                "validation_status": "valid",
                "team_a": team_a,
                "team_b": team_b,
            }

        return {
            **state,

            "tool_name": "team_h2h_record",

            "tool_input": {
                "teams_found": teams,
            },

            "validation_status": "needs_clarification",

            "validation_error":
                "I need two identifiable AFL teams "
                "for the head-to-head lookup.",
        }

    # =========================================================================
    # UNSUPPORTED RETRIEVAL
    # =========================================================================

    return {
        **state,

        "tool_name": "retrieval",

        "tool_input": {
            "query": query,
        },

        "validation_status": "needs_clarification",

        "validation_error":
            "I could not safely map this retrieval question "
            "to an available structured lookup. "
            "Please specify the team/player and statistic.",
    }
