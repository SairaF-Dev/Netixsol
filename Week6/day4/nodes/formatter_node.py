from __future__ import annotations

import json

from state import AgentState


def _parse_result(result):
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    return result


def formatter_node(state: AgentState) -> AgentState:
    intent = state.get("intent")
    result = _parse_result(state.get("tool_result"))

    if intent == "off_topic":
        response = (
            "I can only help with AFL-related questions. "
            "You can ask me about an AFL team, player, match, statistic, or rule."
        )
        return {**state, "final_response": response}

    if intent == "factual":
        # The factual branch is intentionally conservative.
        response = (
            "I can answer general AFL rules, history, and competition-structure "
            "questions. For dataset-specific statistics, I need to use a retrieval tool."
        )
        return {**state, "final_response": response}

    if intent == "retrieval":
        response = (
            "According to the available AFL dataset:\n"
            f"{json.dumps(result, indent=2, default=str)}"
        )
        return {**state, "final_response": response}

    if intent == "prediction":
        if not result:
            response = (
                "I couldn't produce a prediction from the available models. "
                "I won't guess."
            )
            return {**state, "final_response": response}

        if isinstance(result, dict) and "predicted_winner" in result:
            probability = float(result["home_win_probability"])
            winner = result["predicted_winner"]
            home = result["home_team"]
            away = result["away_team"]

            confidence = probability if winner == home else 1 - probability

            response = (
                f"Model prediction: **{winner}** has a "
                f"{confidence:.1%} predicted probability of winning "
                f"against {away if winner == home else home}.\n\n"
                f"Grounding: the model used recent-form, scoring/margin, "
                f"rest, ladder-position and head-to-head inputs from the "
                f"available historical snapshots (as of {result['as_of_date']}).\n\n"
                "This is a probabilistic model output, not a certainty."
            )
            return {**state, "final_response": response}

        if isinstance(result, dict) and "predictions" in result:
            rows = result["predictions"]
            lines = [
                f"- Player ID {row['player_id']}: "
                f"{row['predicted_fantasy_points']} predicted fantasy points"
                for row in rows
            ]
            response = (
                f"Top-player prediction for **{result['team']}**:\n"
                + "\n".join(lines)
                + "\n\nThis is a probabilistic/model-based ranking, not a certainty."
            )
            return {**state, "final_response": response}

        response = (
            "The prediction model returned a result, but it is not in a supported "
            "response format. I won't invent a prediction."
        )
        return {**state, "final_response": response}

    return {
        **state,
        "final_response": "I couldn't determine how to answer that safely.",
    }
