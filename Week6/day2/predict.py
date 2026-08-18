"""
predict.py -- callable prediction functions for the AFL match-winner and top-player models.

These wrap the models trained in the Week 6 Day 2 notebook (afl_prediction_models_week6_day2.ipynb).
Designed to be imported directly as LangChain/LangGraph agent tools on Day 4.

Usage
-----
    from predict import predict_match_winner, predict_top_player

    predict_match_winner('Richmond Tigers', 'Carlton Blues', '2025-06-01')
    -> {'home_team': 'Richmond Tigers', 'away_team': 'Carlton Blues', 'predicted_winner': 'Richmond Tigers',
        'home_win_probability': 0.58, 'as_of_date': '2025-05-24'}

    predict_top_player(team='Richmond Tigers', date='2025-06-01', top_n=5)
    -> [{'player_id': ..., 'predicted_fantasy_points': ...}, ...]

Required files (same directory): match_winner_model.joblib, top_player_model.joblib,
team_snapshots.parquet, player_snapshots.parquet -- all produced by the Day 2 notebook.
"""
import joblib
import pandas as pd
from pathlib import Path

_ARTIFACT_DIR = Path(__file__).parent

_match_model = joblib.load(_ARTIFACT_DIR / 'match_winner_model.joblib')
_top_player_model = joblib.load(_ARTIFACT_DIR / 'top_player_model.joblib')
_team_snapshots = pd.read_parquet(_ARTIFACT_DIR / 'team_snapshots.parquet')
_player_snapshots = pd.read_parquet(_ARTIFACT_DIR / 'player_snapshots.parquet')

VALID_TEAMS = sorted(_team_snapshots['team_name'].unique())
DATA_MIN_DATE = _team_snapshots['match_date'].min()
DATA_MAX_DATE = _team_snapshots['match_date'].max()

_NUMERIC_MATCH_FEATURES = [
    'home_last5_win_rate', 'home_last5_avg_score', 'home_last5_avg_margin', 'home_win_streak',
    'home_days_rest', 'home_ladder_rank', 'home_h2h_win_rate',
    'away_last5_win_rate', 'away_last5_avg_score', 'away_last5_avg_margin', 'away_win_streak',
    'away_days_rest', 'away_ladder_rank', 'away_h2h_win_rate',
]
_PLAYER_FEATURES = ['last5_avg_disposals', 'last5_avg_goals', 'last5_avg_fantasy_points', 'games_played_prior']


class PredictionInputError(ValueError):
    """Raised for invalid team names, players, or out-of-range dates."""


def _validate_team(team_name):
    if team_name not in VALID_TEAMS:
        raise PredictionInputError(
            f"Unknown team '{team_name}'. Valid teams: {', '.join(VALID_TEAMS)}"
        )


def _validate_date(date):
    date = pd.Timestamp(date)
    if date < DATA_MIN_DATE or date > DATA_MAX_DATE + pd.Timedelta(days=365):
        raise PredictionInputError(
            f"Date {date.date()} is well outside the data range "
            f"({DATA_MIN_DATE.date()} to {DATA_MAX_DATE.date()}); prediction would be unreliable."
        )
    return date


def _latest_team_snapshot(team_name, as_of_date):
    hist = _team_snapshots[(_team_snapshots.team_name == team_name) & (_team_snapshots.match_date < as_of_date)]
    if hist.empty:
        raise PredictionInputError(f"No historical data for '{team_name}' before {as_of_date.date()}.")
    return hist.sort_values('match_date').iloc[-1]


def _h2h_snapshot(team_name, opponent_name, as_of_date):
    hist = _team_snapshots[
        (_team_snapshots.team_name == team_name) & (_team_snapshots.opponent == opponent_name)
        & (_team_snapshots.match_date < as_of_date)
    ]
    return hist.sort_values('match_date').iloc[-1]['h2h_win_rate'] if not hist.empty else None


def predict_match_winner(team_a: str, team_b: str, date: str, venue: str = 'unknown') -> dict:
    """
    Predict the winner of a match between team_a (home) and team_b (away) on `date`.

    Parameters
    ----------
    team_a : home team name (must match a known team name -- see VALID_TEAMS)
    team_b : away team name
    date   : ISO date string, e.g. '2025-06-01'
    venue  : optional venue name; defaults to 'unknown' (imputed by the pipeline)

    Returns
    -------
    dict with predicted_winner, home_win_probability, and the as-of date used for form snapshots.

    Raises
    ------
    PredictionInputError on an unknown team or an out-of-range date.
    """
    _validate_team(team_a)
    _validate_team(team_b)
    as_of = _validate_date(date)

    home_snap = _latest_team_snapshot(team_a, as_of)
    away_snap = _latest_team_snapshot(team_b, as_of)
    home_h2h = _h2h_snapshot(team_a, team_b, as_of)

    row = pd.DataFrame([{
        'home_last5_win_rate': home_snap['last5_win_rate'], 'home_last5_avg_score': home_snap['last5_avg_score'],
        'home_last5_avg_margin': home_snap['last5_avg_margin'], 'home_win_streak': 0,
        'home_days_rest': (as_of - home_snap['match_date']).days, 'home_ladder_rank': home_snap['ladder_rank'],
        'home_h2h_win_rate': home_h2h,
        'away_last5_win_rate': away_snap['last5_win_rate'], 'away_last5_avg_score': away_snap['last5_avg_score'],
        'away_last5_avg_margin': away_snap['last5_avg_margin'], 'away_win_streak': 0,
        'away_days_rest': (as_of - away_snap['match_date']).days, 'away_ladder_rank': away_snap['ladder_rank'],
        'away_h2h_win_rate': None,
        'venue': venue,
    }])[_NUMERIC_MATCH_FEATURES + ['venue']]

    proba = float(_match_model.predict_proba(row)[0, 1])
    return {
        'home_team': team_a, 'away_team': team_b,
        'predicted_winner': team_a if proba >= 0.5 else team_b,
        'home_win_probability': round(proba, 3),
        'as_of_date': str(as_of.date()),
    }


def predict_top_player(team: str, date: str, top_n: int = 5) -> list:
    """
    Predict the top-N players by expected fantasy points for `team`'s next match after `date`.

    Parameters
    ----------
    team  : team name (must match a known team name -- see VALID_TEAMS)
    date  : ISO date string
    top_n : how many players to return, ranked by predicted fantasy points

    Returns
    -------
    list of dicts: [{'player_id': ..., 'predicted_fantasy_points': ...}, ...]

    Raises
    ------
    PredictionInputError on an unknown team, out-of-range date, or no recent player data for that team.
    """
    _validate_team(team)
    as_of = _validate_date(date)

    roster = _player_snapshots[(_player_snapshots.team == team) & (_player_snapshots.match_date < as_of)]
    if roster.empty:
        raise PredictionInputError(f"No player history for '{team}' before {as_of.date()}.")

    latest_per_player = roster.sort_values('match_date').groupby('player_id').tail(1).dropna(subset=_PLAYER_FEATURES)
    if latest_per_player.empty:
        raise PredictionInputError(f"No players with complete recent-form data for '{team}' before {as_of.date()}.")

    preds = _top_player_model.predict(latest_per_player[_PLAYER_FEATURES])
    latest_per_player = latest_per_player.assign(predicted_fantasy_points=preds)
    top = latest_per_player.nlargest(top_n, 'predicted_fantasy_points')

    return [
        {'player_id': int(r.player_id), 'predicted_fantasy_points': round(float(r.predicted_fantasy_points), 1)}
        for r in top.itertuples()
    ]
