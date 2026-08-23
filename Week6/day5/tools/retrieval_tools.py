from functools import lru_cache
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT_PATH = ROOT / "team_snapshots.parquet"
MATCH_PATH = ROOT / "team_matches_home_away_raw.csv"


# ============================================================================
# LOAD SNAPSHOTS
# ============================================================================

if SNAPSHOT_PATH.exists():
    _team_snapshots = pd.read_parquet(SNAPSHOT_PATH)

    VALID_TEAMS = sorted(
        _team_snapshots["team_name"]
        .dropna()
        .unique()
    )
else:
    _team_snapshots = pd.DataFrame()
    VALID_TEAMS = []


# ============================================================================
# LOAD RAW MATCH RESULTS
# ============================================================================

if MATCH_PATH.exists():
    _matches = pd.read_csv(MATCH_PATH)

    _matches["match_date"] = pd.to_datetime(
        _matches["match_date"],
        errors="coerce",
    )

    _matches["team_name"] = (
        _matches["team_name"]
        .astype(str)
        .str.strip()
    )

    _matches["opponent"] = (
        _matches["opponent"]
        .astype(str)
        .str.strip()
    )

    _matches["result"] = (
        _matches["result"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

else:
    _matches = pd.DataFrame()


# ============================================================================
# VALIDATION
# ============================================================================

def _require_snapshot_data():
    if _team_snapshots.empty:
        raise RuntimeError(
            "team_snapshots.parquet is missing."
        )


def _require_match_data():
    if _matches.empty:
        raise RuntimeError(
            "team_matches_home_away_raw.csv is missing."
        )


# ============================================================================
# RECENT FORM
# ============================================================================

def get_team_recent_form(team, n=5):
    """
    Return recent-form snapshots for a team.
    """

    _require_snapshot_data()

    df = (
        _team_snapshots[
            _team_snapshots["team_name"] == team
        ]
        .sort_values("match_date")
        .tail(n)
    )

    if df.empty:
        return {
            "error": f"No recent-form data found for {team}."
        }

    cols = [
        c
        for c in [
            "match_date",
            "opponent",
            "last5_win_rate",
            "last5_avg_score",
            "last5_avg_margin",
            "days_rest",
            "ladder_rank",
            "h2h_win_rate",
        ]
        if c in df.columns
    ]

    records = df[cols].copy()

    records["match_date"] = (
        pd.to_datetime(records["match_date"])
        .dt.strftime("%Y-%m-%d")
    )

    return {
        "team": team,
        "matches": records.to_dict("records"),
    }


# ============================================================================
# ACTUAL LAST RESULTS
# ============================================================================

def get_team_recent_results(team, n=5):
    """
    Return the team's actual last N match results
    from the raw match dataset.
    """

    _require_match_data()

    df = _matches[
        _matches["team_name"].str.lower()
        == team.lower()
    ].copy()

    df = (
        df
        .dropna(subset=["match_date"])
        .sort_values("match_date")
        .tail(n)
        .sort_values("match_date", ascending=False)
    )

    if df.empty:
        return {
            "error": f"No match results found for {team}."
        }

    results = []

    for _, row in df.iterrows():

        results.append(
            {
                "match_date": row["match_date"].strftime(
                    "%Y-%m-%d"
                ),
                "opponent": row["opponent"],
                "result": row["result"],
                "margin": int(row["margin"])
                if pd.notna(row["margin"])
                else None,
                "team_score": int(row["team_score"])
                if pd.notna(row["team_score"])
                else None,
                "opponent_score": int(row["opponent_score"])
                if pd.notna(row["opponent_score"])
                else None,
                "venue": row["venue"]
                if pd.notna(row["venue"])
                else None,
            }
        )

    return {
        "team": team,
        "results": results,
    }


# ============================================================================
# HEAD-TO-HEAD
# ============================================================================

def get_team_h2h_record(team_a, team_b):
    """
    Return the latest available H2H snapshot.
    """

    _require_snapshot_data()

    df = _team_snapshots[
        (
            _team_snapshots["team_name"]
            == team_a
        )
        &
        (
            _team_snapshots["opponent"]
            == team_b
        )
    ].sort_values("match_date")

    if df.empty:
        return {
            "error":
            f"No head-to-head snapshot found for "
            f"{team_a} vs {team_b}."
        }

    row = df.iloc[-1]

    match_date = pd.to_datetime(
        row["match_date"]
    )

    return {
        "team_a": team_a,
        "team_b": team_b,
        "h2h_win_rate": (
            float(row["h2h_win_rate"])
            if pd.notna(row.get("h2h_win_rate"))
            else None
        ),
        "as_of_date": match_date.strftime(
            "%Y-%m-%d"
        ),
    }


# ============================================================================
# PLAYER DATA
# ============================================================================

PLAYER_PATH = ROOT / "afl_players_round_by_round_stats_raw.csv"
PLAYER_METADATA_PATH = ROOT / "merged_players.csv"


if PLAYER_PATH.exists():
    _players = pd.read_csv(
        PLAYER_PATH
    )

else:
    _players = pd.DataFrame()


def _require_player_data():
    if _players.empty:
        raise RuntimeError(
            "afl_players_round_by_round_stats_raw.csv is missing."
        )


@lru_cache(maxsize=1)
def _player_metadata() -> pd.DataFrame:
    """Load the separate, authoritative player-id/name metadata."""
    if not PLAYER_METADATA_PATH.exists():
        return pd.DataFrame(columns=["player_id", "player_name"])

    metadata = pd.read_csv(
        PLAYER_METADATA_PATH,
        usecols=["player_id", "player_name"],
    ).dropna(subset=["player_id", "player_name"])
    metadata["player_id"] = pd.to_numeric(
        metadata["player_id"], errors="coerce"
    )
    metadata = metadata.dropna(subset=["player_id"])
    metadata["player_id"] = metadata["player_id"].astype(int)
    metadata["player_name"] = metadata["player_name"].astype(str).str.strip()
    return metadata.drop_duplicates(subset=["player_id", "player_name"])


def resolve_player_name(player_name: str) -> dict | None:
    """Resolve an exact full player name to its real dataset player_id."""
    query = " ".join((player_name or "").split()).casefold()
    if not query:
        return None

    matches = _player_metadata()[
        _player_metadata()["player_name"].str.casefold() == query
    ]
    if len(matches) != 1:
        return None

    row = matches.iloc[0]
    return {"player_id": int(row["player_id"]), "player_name": row["player_name"]}


def get_player_statistics(
    player_name: str,
    year: int | None = None,
    player_id: int | None = None,
):
    """
    Return historical statistics for an AFL player.

    If year is supplied, only that season is returned.

    Example:
        get_player_statistics("Nick Daicos")
        get_player_statistics("Nick Daicos", 2024)
    """

    _require_player_data()

    resolved = resolve_player_name(player_name)
    if player_id is None and resolved:
        player_id = resolved["player_id"]
    if player_id is None:
        return {
            "error": (
                "I couldn't identify that player in the available AFL "
                "dataset. Please provide the player's full name or team."
            )
        }

    df = _players[_players["player_id"] == int(player_id)].copy()

    if df.empty:
        return {
            "error": (
                f"No player data found for "
                f"{player_name}."
            )
        }

    # ------------------------------------------------------------------------
    # Optional year filter
    # ------------------------------------------------------------------------

    if year is not None:

        year_column = None

        for candidate in (
            "year",
            "season",
        ):

            if candidate in df.columns:
                year_column = candidate
                break

        if year_column is None:
            return {
                "error": (
                    "Player dataset does not contain "
                    "a year/season column."
                )
            }

        df = df[
            pd.to_numeric(
                df[year_column],
                errors="coerce",
            ) == int(year)
        ].copy()

        if df.empty:
            return {
                "error": (
                    f"No statistics found for "
                    f"{player_name} in {year}."
                )
            }

    # ------------------------------------------------------------------------
    # Select useful statistics
    # ------------------------------------------------------------------------

    preferred_columns = [
        "player_id",
        "year",
        "season",
        "match_date",
        "team",
        "opponent",

        # Common AFL statistics
        "disposals",
        "disposal",
        "kicks",
        "handballs",
        "marks",
        "tackles",
        "goals",
        "behinds",
        "clearances",
        "inside_50s",
        "inside_50",
        "contested_possessions",
        "uncontested_possessions",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in df.columns
    ]

    if not available_columns:
        return {
            "error": (
                "No recognized player-statistic "
                "columns were found."
            )
        }

    records = df[
        available_columns
    ].copy()

    # ------------------------------------------------------------------------
    # Convert dates
    # ------------------------------------------------------------------------

    if "match_date" in records.columns:

        records["match_date"] = (
            pd.to_datetime(
                records["match_date"],
                errors="coerce",
            )
            .dt.strftime("%Y-%m-%d")
        )

    # ------------------------------------------------------------------------
    # Remove helper column
    # ------------------------------------------------------------------------

    records = records.where(
        pd.notna(records),
        None,
    )

    # ------------------------------------------------------------------------
    # Return
    # ------------------------------------------------------------------------

    numeric_columns = [
        column for column in ["kicks", "handballs", "disposals", "marks", "tackles", "goals", "behinds", "clearances"]
        if column in records.columns
    ]
    totals = {
        column: int(pd.to_numeric(records[column], errors="coerce").fillna(0).sum())
        for column in numeric_columns
    }

    return {
        "player": resolved["player_name"] if resolved else player_name,
        "player_id": int(player_id),
        "year": year,
        "totals": totals,
        "matches": records.to_dict(
            "records"
        ),
        "match_count": len(records),
    }
