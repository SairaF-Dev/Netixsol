# AFL Match Context Integration

## Project Overview

This project enriches an AFL Round-by-Round player performance dataset by integrating it with a Team Match dataset. The objective is to add missing match context—such as home/away status, venue, and crowd attendance—and analyze how these factors influence player performance.

The project follows a complete data engineering workflow, including data cleaning, relationship discovery, dataset integration, merge validation, contextual analysis, and visualization.

---

## Objectives

- Clean and prepare both datasets for integration.
- Identify the correct relationship between the datasets.
- Determine an appropriate merge strategy.
- Enrich player records with:
  - Home/Away status
  - Venue
  - Crowd attendance
- Validate the accuracy of the merge.
- Analyze the impact of match context on player fantasy performance.
- Produce a data quality report.

---

## Datasets

### Player Performance Dataset

Contains round-by-round player statistics including:

- Player ID
- Team
- Opponent
- Match Date
- Fantasy Points
- Kicks
- Marks
- Tackles
- Goals
- Handballs
- Other player performance statistics

### Team Match Dataset

Contains team-level match information including:

- Team
- Opponent
- Match Date
- Home/Away
- Venue
- Crowd Attendance
- Match Result
- Margin

---

## Project Workflow

### 1. Data Loading

- Imported required libraries.
- Loaded both datasets using Pandas.

### 2. Data Quality Assessment

Performed an initial assessment by checking:

- Dataset dimensions
- Missing values
- Duplicate records

### 3. Data Cleaning

Cleaning steps included:

- Removed the empty `score` column.
- Removed records with missing `match_date`.
- Filled missing player statistics with zero.
- Removed duplicate player records.
- Standardized text formatting.
- Resolved inconsistent team naming (e.g., **W. Bulldogs → Western Bulldogs**).

### 4. Relationship Discovery

Identified common fields between datasets.

Evaluated:

- Common columns
- Unique value counts
- Single-key uniqueness
- Composite key uniqueness
- Dataset relationship

Selected the composite merge key:

```
team
match_date
opponent
```

The relationship between datasets was determined to be:

> Many Player Records → One Team Match Record

---

## Context Enrichment

Merged the datasets using a **left join** with the composite key and added:

- `home_away`
- `venue`
- `crowd`

Merge validation was strengthened using:

```python
validate='many_to_one'
```

---

## Merge Validation

The merge was validated by checking:

- Record count preservation
- Merge indicator values
- Unmatched records
- Duplicate records introduced by merging

Validation results confirmed:

- No unmatched player records
- No duplicate records introduced
- Player record count remained unchanged

---

## Contextual Analysis

The enriched dataset was analyzed to answer the following questions:

### Home vs Away Performance

Compared average fantasy points for home and away matches.

### Crowd Attendance

Measured the relationship between crowd size and fantasy points using Pearson correlation.

### Venue Performance

Calculated average fantasy points by venue and identified the top-performing venues.

---

## Data Quality Report

The report summarizes:

- Merge keys used
- Challenges encountered
- Data quality issues discovered
- Assumptions made during integration

---

## Visualizations

The project includes visualizations supporting the analysis:

- Home vs Away Average Fantasy Points (Bar Chart)
- Crowd Attendance vs Fantasy Points (Scatter Plot with Trend Line)
- Top Performing Venues (Horizontal Bar Chart)

---

## Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib

---

## Repository Structure

```
day5/
│
├── AFL_Match_Context_Integration.ipynb
├── README.md
│
├── Datasets/
│   ├── afl_players_round_by_round_stats_raw.csv
│   └── team_matches_home_away_raw.csv
│
├── charts/
│   ├── top_5_venues_by_fantasy_points.png
│   ├── home_vs_away.png
│   ├── crowd_size_vs_fantasy_points.png

```

---

## Key Skills Demonstrated

- Data Cleaning
- Data Integration
- Relationship Discovery
- Composite Key Design
- Merge Validation
- Data Quality Assessment
- Feature Enrichment
- Exploratory Data Analysis
- Data Visualization
- Python Programming
- Pandas

---

## Author

**Saira Fatima**