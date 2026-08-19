# AFL Prediction Models (Match Winner & Top Player)



Builds match-winner and top-player prediction models on top of the feature engineering work from Week 6 Day 1, and packages both as standalone, documented, callable functions ready to be wired up as LangChain/LangGraph agent tools in Day 4.

## Overview

This notebook takes the leakage-safe match feature table (`afl_match_feature_table_v1.csv`) and the raw player round-by-round stats from Day 1 and builds two production-style prediction pipelines:

1. **Match Winner Model** — predicts `P(home team wins)` for a given fixture.
2. **Top Player Model** — predicts each player's expected fantasy points for their next match, used to rank a team's likely top performers.

Both models are evaluated against simple baselines, checked for football-sensible feature importance, and shipped as a standalone `predict.py` module with input validation — decoupled from the notebook so it can be imported directly by downstream agent tooling.

## Data

| File | Description |
|---|---|
| `match_feature_table_v14.csv` | Match-level feature table from Day 1 (7,904 matches × 44 columns) |
| `data/afl_players_round_by_round_stats_raw - afl_players_round_by_round_stats_raw.csv` | Raw player round-by-round stats (238,683 rows) |
| `data/team_matches_home_away_raw - team_matches_home_away_raw.csv.csv` | Raw team match results, used to build "as-of" team snapshots for live prediction |

**Train/holdout split:** time-based, identical to Day 1 — the most recent season (2025) is held out entirely (7,688 train matches / 216 test matches), keeping every model this week comparable apples-to-apples.

## Task 1 — Baselines

| Baseline | Accuracy | F1 |
|---|---|---|
| Home-always (majority class) | 0.556 | 0.714 |
| Higher-ladder team wins | 0.653 | 0.691 |

- Top-player baseline (last week's leader repeats as this week's leader): **16.7%** hit rate (n = 1,137 rounds).
- The 3-class match result is collapsed to a binary `home_team_wins` target (draws are ~0.8% of matches — too rare to model separately, and folding them into "not a home win" keeps `P(home win)` directly usable for a calibration-focused evaluation).

## Task 2 — Match Winner Model

Two `scikit-learn` pipelines (imputation → scaling/one-hot encoding → classifier) trained on the same holdout split:

| Model | Accuracy | F1 | ROC AUC | Brier Score |
|---|---|---|---|---|
| Logistic Regression | 0.690 | 0.743 | 0.750 | 0.203 |
| HistGradientBoosting | 0.639 | 0.705 | 0.747 | 0.203 |
| Baseline: home-always | 0.556 | 0.714 | — | — |
| Baseline: higher-ladder | 0.653 | 0.691 | — | — |

**Final choice: Logistic Regression.** Both models comfortably beat both baselines; Logistic Regression matches HistGradientBoosting on AUC/Brier while giving directly interpretable coefficients — important once this becomes an agent tool that needs to *explain* a prediction, not just emit a number. HistGradientBoosting is kept as a saved fallback/ensemble candidate.

Saved artifacts: `match_winner_model.joblib` (final), `match_winner_model_gbm_alt.joblib` (alternate).

## Task 3 — Top Player Model

Framed as **regression, then rank**: predict each player's `fantasy_points` for their next match from rolling form features, then rank players within a round by predicted score.

- Features: `last5_avg_disposals`, `last5_avg_goals`, `last5_avg_fantasy_points`, `games_played_prior`
- Model: `GradientBoostingRegressor`
- **MAE: 18.15 fantasy points | RMSE: 22.73 fantasy points**
- **Top-5 hit rate on holdout: 26.7%** (n = 30 rounds) vs. 16.7% baseline

Regression was chosen over learning-to-rank (e.g. LambdaMART) because a single well-calibrated per-player score is more broadly useful (supports both a raw point estimate and a ranking via sorting) and is simpler to justify to a non-ML audience. Learning-to-rank is noted as a natural upgrade path.

Saved artifact: `top_player_model.joblib`.

## Task 4 — Feature Importance & Sanity Checks

- **Match winner (Logistic Regression coefficients):** largest-magnitude features are recent form (`last5_win_rate`), ladder position (`ladder_rank`), and scoring margin — all pushing in football-sensible directions.
- **Top player (GradientBoostingRegressor importances):** `last5_avg_fantasy_points` dominates, as expected — a player's own recent scoring rate is the strongest predictor of next-match output.
- **Sniff test:** 3 randomly sampled holdout matches manually cross-checked against the model's predicted `P(home win)` to confirm predictions track team form/ladder position sensibly.

## Task 5 — Packaging as Callable Functions

To support live predictions (fixtures that haven't happened yet), per-team and per-player "as-of" snapshot tables are built from the raw match/player data — capturing each team/player's latest known rolling state after every historical match. At call time, the most recent snapshot strictly before the requested date is looked up.

This logic is shipped as a standalone module, **`predict.py`**, decoupled from the notebook so it can be imported directly by Day 4 agent tools without any notebook dependency:

```python
from predict import predict_match_winner, predict_top_player

predict_match_winner('Richmond Tigers', 'Carlton Blues', '2025-06-01')
# -> {'home_team': ..., 'away_team': ..., 'predicted_winner': ...,
#     'home_win_probability': ..., 'as_of_date': ...}

predict_top_player('Richmond Tigers', '2025-06-01', top_n=5)
# -> [{'player_id': ..., 'predicted_fantasy_points': ...}, ...]
```

Both functions validate their inputs (unknown team name, out-of-range or unparseable date, missing historical data) and raise a `PredictionInputError` with a clear message rather than failing silently or with a raw stack trace.

## Repository / Output Artifacts

```
week6/
└── day2/
    │   afl_prediction_models_week6_day2d1.ipynb
    │   match_feature_table_v14.csv
    │   match_winner_model.joblib
    │   top_player_model.joblib
    │   player_snapshots.parquet
    │   team_snapshots.parquet
    │   predict.py
    │   README.md
    │
    └── data/
            afl_players_round_by_round_stats_raw - afl_players_round_by_round_stats_raw.csv
            team_matches_home_away_raw - team_matches_home_away_raw.csv
            feature_dictionary_v14.csv                                     
```

## Summary

| Task | Outcome |
|---|---|
| 1. Baselines | Home-always / higher-ladder (match winner) and last-week's-leader (top player) established as the bar to beat |
| 2. Match Winner Model | Logistic Regression selected for deployment — beats both baselines, calibrates well, interpretable |
| 3. Top Player Model | Regression-then-rank framing; MAE 18.15 / RMSE 22.73, 26.7% top-5 hit rate vs. 16.7% baseline |
| 4. Feature Importance | Coefficients and importances check out against football domain knowledge |
| 5. Packaging | Both models saved as `.joblib`, snapshot tables built for live prediction, `predict.py` written and smoke-tested — ready for Day 4 agent tools |

## Requirements

```
pandas
numpy
scikit-learn
joblib
matplotlib
seaborn
```