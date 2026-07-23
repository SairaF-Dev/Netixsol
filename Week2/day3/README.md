# AFL Player Exploratory Data Analysis (EDA)

## Project Overview
This project performs an in-depth Exploratory Data Analysis (EDA) on cleaned and merged AFL player datasets spanning multiple decades. The analysis translates raw player metrics, demographics, and match statistics into actionable business and sports-analytics insights.

---

## Repository Contents
* **`EDA_AFL.ipynb`**: The main Jupyter Notebook containing all python code, data manipulations, visualizations, observations, and business insights.
* **`merged_players.csv`**: The primary merged dataset containing player profiles, yearly match statistics, physical attributes, and career spans.
* **`charts/`**: Directory containing all exported high-resolution visualizations (`.png` files) generated during the EDA process.

---

## Key Analysis Areas
1. **Match Volume by Team:** Identifying which franchises have played the highest cumulative matches.
2. **Player Age Distribution:** Analyzing career lifespan peaks using `last_age`.
3. **Team Roster Sizing:** Evaluating unique player counts across team histories via `player_teams`.
4. **Physical Variations:** Comparing weight and height distributions across different clubs.
5. **Fantasy Performance:** Determining teams with the highest average fantasy points.
6. **Goal Scoring Elite:** Identifying the Top 15 goal scorers in the dataset.
7. **Temporal Coverage:** Tracking record availability across seasons.

---


## Getting Started

### Prerequisites
Make sure you have the required Python libraries installed:
```bash
pip install numpy pandas matplotlib seaborn
```
## Running the Notebook
To review and execute the data processing pipeline interactively, launch Jupyter Notebook or JupyterLab:
```bash 
jupyter notebook EDA_AFL.ipynb
```
(Alternatively, open the EDA_AFL.ipynb file directly within an IDE configured with Jupyter support, such as VS Code).

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*
