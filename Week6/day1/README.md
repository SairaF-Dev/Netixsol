# AFL Data Foundations — EDA, Feature Engineering & Prediction Targets

This repository/notebook contains a robust, leakage-safe data engineering and exploratory data analysis (EDA) pipeline for Australian Football League (AFL) historical match and player statistics spanning from 1983 to 2025.

---

## Purpose & Scope

The primary objective of this project is to prepare raw historical AFL datasets for predictive modelling and assistant-building. The pipeline executes four core phases:

1. **Data Inventory & Validation** — Catalogs raw tables (`player_rounds_raw.csv`, `team_matches_raw.csv`, `merged_players.csv`), enforces canonical team name normalization across historical rebrands/relocations, establishes a 5-column composite match key, and catches data anomalies (e.g., negative stat entries and exact duplicates).
2. **Prediction Target Definitions** — Formulates clear modelling targets for match outcomes (`match_result_3way`: Home Win, Away Win, Draw) and individual player benchmarks (top disposal-getter, top goal-kicker, and diagnostic composite performance scores).
3. **Exploratory Data Analysis (EDA)** — Investigates structural league changes (team expansions, mergers, COVID-19 schedule shifts), home ground advantages, travel factors, and historical career leaders.
4. **Leakage-Safe Feature Engineering** — Builds rolling form metrics, head-to-head histories, and seasonal ladder ranks while enforcing a strict golden rule: **all predictive features use information available strictly prior to the target match**.

---

## Dataset Schema

* **`player_rounds_raw.csv`**: Granular player statistics on a per-match, round-by-round basis (~274k rows).
* **`team_matches_raw.csv`**: Team-level match performance records (two rows per match: home and away side; ~15.8k rows).
* **`merged_players.csv`**: Seasonal player-level aggregates split by regular season vs. finals (~25k rows).

---

## Key Modelling & Validation Principles

* **No Data Leakage**: Current-match outcomes and statistics are strictly walled off from predictor tables. Lagged features (`player_avg_*`, rolling form windows) are computed using historical shift operations (`.shift(1)`).
* **Strict Time-Based Hold-Out**: Standard random splitting is avoided in favor of a chronological split, holding out the most recent complete season for unbiased final evaluation.
* **Reproducibility**: Random seeds are fixed across operations to ensure deterministic feature generation and dataset assembly.

---

## Getting Started

1. Ensure Python and a Jupyter environment are installed along with standard data science libraries (`pandas`, `numpy`, `matplotlib`, `seaborn`).
2. Place `player_rounds_raw.csv`, `team_matches_raw.csv`, and `merged_players.csv` in the appropriate data directory as referenced by the notebook.
3. Run `AFL_EDA_Feature_Engineering.ipynb` sequentially to generate clean feature tables and validated prediction targets ready for model training.