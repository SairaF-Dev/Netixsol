# AFL Dataset Exploratory Data Analysis (EDA)

This repository contains an Exploratory Data Analysis (EDA) workflow and concept review using Python, Pandas, Matplotlib, and Seaborn on a cleaned Australian Football League (AFL) dataset (`afl_cleaned_dataset.csv`).

---

## Project Overview

The project covers data loading, missing value checks, previewing structure (with over 60 columns including player statistics, team data, match details, player dimensions, and dates), and line charting using statistical visualization libraries.

### Key Dataset Features
* **Player Information:** `player_id`, `first_name`, `last_name`, `born_date`, `debut_date`, `debut_age`, `height`, `weight`
* **Match & Season Stats:** `year`, `team`, `is_finals`, `games_played`, `kicks`, `marks`, `handballs`, `disposals`, `goals`, etc.


---

## Getting Started

### Prerequisites
Make sure you have the required Python libraries installed:
```bash
pip install pandas matplotlib seaborn
```
## Running the Notebook
To review and execute the data processing pipeline interactively, launch Jupyter Notebook or JupyterLab:
```bash 
jupyter notebook afl_data_visualization.ipynb
```
(Alternatively, open the afl_data_visualization.ipynb file directly within an IDE configured with Jupyter support, such as VS Code).

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*
