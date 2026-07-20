# Titanic Exploratory Data Analysis and Visualization

This repository contains data visualization and exploratory analysis workflows performed on the Titanic dataset using Python, Pandas, Matplotlib, and Seaborn.

## Dataset Structure

The analysis is performed on the standard Titanic dataset located within the directory structure:
```text
Week1/day5/dataset/titanic dataset/Titanic-Dataset.csv
```
## Overview
The workflow executes the following visualization and analytical steps:

1. **Histogram (Age Distribution):** Visualizes passenger age distribution with a KDE curve segmented by passenger class (ClassName).

2. **Bar Chart (Average Fare by Class):** Illustrates average ticket fares across different classes with error bars indicating data spread and consistency.

3. **Box Plot (Fare Distribution):** Highlights median ticket prices, interquartile ranges, and outlier fares across passenger classes.

4. **Correlation Heatmap:** Displays correlation coefficients between numeric variables to reveal relationships such as family size and passenger class impacts.

## Requirements

* Python 3.x
* Pandas
* NumPy
* Matplotlib
* Seaborn

Install the necessary dependencies via terminal:

```bash 
pip install pandas numpy matplotlib seaborn
```

## Running the Notebook
To review and execute the data visualization pipeline interactively, launch Jupyter Notebook or JupyterLab:
```bash
jupyter notebook day5_Pandas.ipynb
```
(Alternatively, open the day5_visualization.ipynb file directly within an IDE configured with Jupyter support, such as VS Code).

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*
