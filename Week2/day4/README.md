# AFL Player Performance and Analytics Pipeline

## Project Overview
This repository contains a comprehensive data analysis pipeline designed to evaluate Australian Football League (AFL) player performance, consistency, and year-over-year development. Utilizing player metadata, seasonal aggregations, and match-level statistics, the pipeline implements advanced feature engineering, statistical normalization, and trend analysis to support data-driven recruitment and player evaluation.

---

## Datasets
The analysis processes three core data sources:
* **`players_info.csv`**: Contains player biographical information, including physical attributes (height, weight), birth dates, debut dates, and career spans.
* **`seasonal_stats.csv`**: Aggregates comprehensive seasonal performance metrics and averages for every player year.
* **`afl_players_round_by_round_stats_raw.csv`**: Provides granular, round-by-round match-level statistics covering individual match outputs and fantasy scoring.

---

## Core Analytical Framework & Methodology

### 1. Identifying the Top Most Valuable Players
To evaluate overall player value for the latest season, the pipeline constructs a multi-faceted **Performance Index**:
* **Feature Engineering**: Derives advanced performance indicators, including *Goal Conversion* (goals-to-shots ratio), *Disposal Impact* (contested possessions relative to total disposals), *Impact Score* (combining goals, assists, tackles, and clearances per game), and *Turnover Rate* (clanger-to-disposal ratio).
* **Normalization**: Applies **Z-score standardization** across all metrics to eliminate scale discrepancies.
* **Weighted Index**: Combines metrics using a balanced scoring formula—rewarding high fantasy scoring, impact, disposal pressure, and goal conversion, while penalizing high turnover rates. Players with fewer than 15 games played are filtered out to ensure statistical reliability.

### 2. Assessing Player Consistency
To pinpoint dependable week-to-week performers, the pipeline evaluates match-level data:
* **Coefficient of Variation (CV)**: Calculates the ratio of the standard deviation of fantasy points to the mean fantasy points for each player (Std Dev / Mean).
* **Stability Ranking**: Filters for players meeting a minimum threshold of 10 games played, ranking them by lowest variance relative to output.

### 3. Tracking Performance Trends
* **Longitudinal Tracking**: Compares year-over-year performance index shifts to isolate breakout candidates and declining players across consecutive seasons.

---

## Technical Stack & Dependencies
* **Programming Language**: Python 3
* **Data Manipulation & Analysis**: NumPy, Pandas
* **Data Visualization**: Matplotlib, Seaborn

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*
