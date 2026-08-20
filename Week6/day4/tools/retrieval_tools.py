"""Structured AFL retrieval tools reused from the Week 6 Day 3 design."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from langchain_core.tools import tool

from .team_resolver import resolve_team


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _find_file(prefix: str) -> Path:
    candidates = list(DATA_DIR.glob(f"{prefix}*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No data file beginning with '{prefix}' in {DATA_DIR}")
    return candidates[0]


def _load_data():
    player_path = _find_file("afl_players_round_by_round_stats_raw")
    team_path = _find_file("team_matches_home_away_raw")

    players = pd.read_csv(player_path, low_memory=False).drop_duplicates()
    teams = pd.read_csv(team_path, low_memory=False)

    for col in ("team_name", "opponent"):
        if col in teams.columns:
            teams[col] = teams[col].astype(str).str.strip()

    teams["team_name"] = teams["team_name"].replace({"W. Bulldogs": "Western Bulldogs"})
    teams["opponent"] = teams["opponent"].replace({"W. Bulldogs": "Western Bulldogs"})

    if "match_date" in players.columns:
        players["match_date"] = pd.to_datetime(players["match_date"])
    if "match_date" in teams.columns:
        teams["match_date"] = pd.to_datetime(teams["match_date"])

    valid_teams = sorted(teams["team_name"].dropna().unique())
    return players, teams, valid_teams


players_raw, teams_raw, VALID_TEAMS = _load_data()


class AFLDataError(Exception):
    pass


def validate_team(name: str) -> str:
    team = resolve_team(name, VALID_TEAMS)
    if not team:
        raise AFLDataError(
            f"'{name}' is not a recognized AFL team. "
            f"Known teams: {', '.join(VALID_TEAMS)}"
        )
    return team


def get_team_recent_form(team_name: str, n: int = 5) -> dict:
    team_name = validate_team(team_name)
    games = (
        teams_raw[teams_raw.team_name == team_name]
        .sort_values("match_date", ascending=False)
        .head(n)
    )
    if games.empty:
        raise AFLDataError(f"No match history found for {team_name}.")

    return {
        "team": team_name,
        "n_games": len(games),
        "results": games[
            ["match_date", "opponent", "result", "team_score"]
        ].assign(
            match_date=lambda d: d.match_date.dt.strftime("%Y-%m-%d")
        ).to_dict(orient="records"),
        "win_rate": round(float((games.result == "W").mean()), 3),
    }


def get_team_h2h_record(team_a: str, team_b: str) -> dict:
    team_a = validate_team(team_a)
    team_b = validate_team(team_b)

    games = teams_raw[
        (teams_raw.team_name == team_a)
        & (teams_raw.opponent == team_b)
    ]

    if games.empty:
        raise AFLDataError(
            f"No recorded matches between {team_a} and {team_b}."
        )

    return {
        "team_a": team_a,
        "team_b": team_b,
        "games_played": len(games),
        f"{team_a}_wins": int((games.result == "W").sum()),
        f"{team_a}_losses": int((games.result == "L").sum()),
        "draws": int((games.result == "D").sum()),
    }


def get_player_recent_games(player_id: int, n: int = 5) -> dict:
    rows = (
        players_raw[players_raw.player_id == player_id]
        .sort_values("match_date", ascending=False)
        .head(n)
    )
    if rows.empty:
        raise AFLDataError(f"No match data found for player_id={player_id}.")

    return {
        "player_id": int(player_id),
        "n_games": len(rows),
        "games": rows[
            ["match_date", "disposals", "goals", "fantasy_points"]
        ].assign(
            match_date=lambda d: d.match_date.dt.strftime("%Y-%m-%d")
        ).to_dict(orient="records"),
    }


@tool
def team_recent_form(team_name: str, n: int = 5) -> str:
    """Get an AFL team's last n match results and recent win rate."""
    try:
        return json.dumps(get_team_recent_form(team_name, n), default=str)
    except AFLDataError as exc:
        return json.dumps({"error": str(exc)})


@tool
def team_h2h_record(team_a: str, team_b: str) -> str:
    """Get the historical head-to-head record between two AFL teams."""
    try:
        return json.dumps(get_team_h2h_record(team_a, team_b), default=str)
    except AFLDataError as exc:
        return json.dumps({"error": str(exc)})


@tool
def player_recent_games(player_id: int, n: int = 5) -> str:
    """Get an AFL player's most recent games and key statistics."""
    try:
        return json.dumps(get_player_recent_games(player_id, n), default=str)
    except AFLDataError as exc:
        return json.dumps({"error": str(exc)})


RETRIEVAL_TOOLS = [
    team_recent_form,
    team_h2h_record,
    player_recent_games,
]
