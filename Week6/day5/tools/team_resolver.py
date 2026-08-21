from __future__ import annotations

import re


def _normalize(text: str) -> str:
    """Normalize text for reliable team-name matching."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# Common AFL aliases.
# Values are the exact canonical names used by the dataset.
TEAM_ALIASES = {
    "adelaide": "Adelaide Crows",
    "crows": "Adelaide Crows",

    "brisbane": "Brisbane Lions",
    "brisbane lions": "Brisbane Lions",
    "lions": "Brisbane Lions",

    "carlton": "Carlton Blues",
    "blues": "Carlton Blues",

    "collingwood": "Collingwood Magpies",
    "collingwood magpies": "Collingwood Magpies",
    "pies": "Collingwood Magpies",
    "magpies": "Collingwood Magpies",

    "essendon": "Essendon Bombers",
    "bombers": "Essendon Bombers",

    "fremantle": "Fremantle Dockers",
    "dockers": "Fremantle Dockers",

    "geelong": "Geelong Cats",
    "geelong cats": "Geelong Cats",
    "cats": "Geelong Cats",

    "gold coast": "Gold Coast Suns",
    "gold coast suns": "Gold Coast Suns",
    "suns": "Gold Coast Suns",

    "gws": "Greater Western Sydney Giants",
    "greater western sydney": "Greater Western Sydney Giants",
    "giants": "Greater Western Sydney Giants",

    "hawthorn": "Hawthorn Hawks",
    "hawks": "Hawthorn Hawks",

    "melbourne": "Melbourne Demons",
    "demons": "Melbourne Demons",

    "north melbourne": "North Melbourne Kangaroos",
    "kangaroos": "North Melbourne Kangaroos",

    "port adelaide": "Port Adelaide Power",
    "power": "Port Adelaide Power",

    "richmond": "Richmond Tigers",
    "richmond tigers": "Richmond Tigers",
    "tigers": "Richmond Tigers",

    "st kilda": "St Kilda Saints",
    "saints": "St Kilda Saints",

    "sydney": "Sydney Swans",
    "swans": "Sydney Swans",

    "west coast": "West Coast Eagles",
    "eagles": "West Coast Eagles",

    "western bulldogs": "Western Bulldogs",
    "bulldogs": "Western Bulldogs",
}


def extract_team_mentions(text: str, valid_teams) -> list[str]:
    """
    Extract team mentions from user text.

    Returns the exact canonical team names used by the dataset.
    """

    if not text:
        return []

    normalized_text = _normalize(text)

    # Build normalized versions of actual dataset names.
    valid_lookup = {
        _normalize(team): team
        for team in valid_teams
    }

    found = []

    # ------------------------------------------------------------
    # 1. Check full official dataset names
    # ------------------------------------------------------------

    for normalized_team, actual_team in sorted(
        valid_lookup.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        pattern = rf"(?<!\w){re.escape(normalized_team)}(?!\w)"

        if re.search(pattern, normalized_text):
            if actual_team not in found:
                found.append(actual_team)

    # ------------------------------------------------------------
    # 2. Check common aliases
    # ------------------------------------------------------------

    for alias, canonical_team in sorted(
        TEAM_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        # Only return aliases that actually exist in the dataset.
        canonical_normalized = _normalize(canonical_team)

        if canonical_normalized not in valid_lookup:
            continue

        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"

        if re.search(pattern, normalized_text):
            actual_team = valid_lookup[canonical_normalized]

            if actual_team not in found:
                found.append(actual_team)

    return found