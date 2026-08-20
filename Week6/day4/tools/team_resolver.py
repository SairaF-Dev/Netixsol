"""AFL team-name/alias resolution for the Day 4 graph."""

from __future__ import annotations

import re
from typing import Iterable


TEAM_ALIASES = {
    "adelaide": "Adelaide Crows",
    "crows": "Adelaide Crows",
    "brisbane": "Brisbane Lions",
    "lions": "Brisbane Lions",
    "carlton": "Carlton Blues",
    "blues": "Carlton Blues",
    "collingwood": "Collingwood Magpies",
    "pies": "Collingwood Magpies",
    "magpies": "Collingwood Magpies",
    "essendon": "Essendon Bombers",
    "bombers": "Essendon Bombers",
    "fremantle": "Fremantle Dockers",
    "dockers": "Fremantle Dockers",
    "geelong": "Geelong Cats",
    "cats": "Geelong Cats",
    "gold coast": "Gold Coast Suns",
    "suns": "Gold Coast Suns",
    "gws": "Greater Western Sydney Giants",
    "giants": "Greater Western Sydney Giants",
    "greater western sydney": "Greater Western Sydney Giants",
    "hawthorn": "Hawthorn Hawks",
    "hawks": "Hawthorn Hawks",
    "melbourne": "Melbourne Demons",
    "demons": "Melbourne Demons",
    "north melbourne": "North Melbourne Kangaroos",
    "kangaroos": "North Melbourne Kangaroos",
    "roos": "North Melbourne Kangaroos",
    "port adelaide": "Port Adelaide Power",
    "power": "Port Adelaide Power",
    "richmond": "Richmond Tigers",
    "tigers": "Richmond Tigers",
    "st kilda": "St Kilda Saints",
    "saints": "St Kilda Saints",
    "sydney": "Sydney Swans",
    "swans": "Sydney Swans",
    "west coast": "West Coast Eagles",
    "eagles": "West Coast Eagles",
    "western bulldogs": "Western Bulldogs",
    "bulldogs": "Western Bulldogs",
    "dogs": "Western Bulldogs",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def resolve_team(name: str, valid_teams: Iterable[str]) -> str | None:
    """Resolve an exact dataset team name or a common nickname/alias.

    Returns None rather than guessing when there is no safe match.
    """
    valid = list(valid_teams)
    normalized = normalize(name)

    for team in valid:
        if normalize(team) == normalized:
            return team

    alias_target = TEAM_ALIASES.get(normalized)
    if alias_target and alias_target in valid:
        return alias_target

    # Conservative suffix/substring matching only when it is unique.
    candidates = [
        team for team in valid
        if normalized in normalize(team)
    ]
    if len(candidates) == 1:
        return candidates[0]

    return None


def extract_team_mentions(text: str, valid_teams: Iterable[str]) -> list[str]:
    """Find resolvable team aliases in a query, preserving first occurrence."""
    valid = list(valid_teams)
    normalized_text = normalize(text)
    found: list[str] = []

    aliases = sorted(
        set(list(TEAM_ALIASES.keys()) + [normalize(x) for x in valid]),
        key=len,
        reverse=True,
    )

    for alias in aliases:
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(pattern, normalized_text):
            resolved = resolve_team(alias, valid)
            if resolved and resolved not in found:
                found.append(resolved)

    return found
