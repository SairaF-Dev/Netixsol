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
        "h2h_win_rate": row.get(
            "h2h_win_rate"
        ),
        "as_of_date": match_date.strftime(
            "%Y-%m-%d"
        ),
    }