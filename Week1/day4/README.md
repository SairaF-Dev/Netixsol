# Titanic Data Cleaning and Preprocessing

This repository contains data cleaning, handling missing values, datatype fixing, duplicate checks, feature engineering, aggregation, and merging workflows performed on the Titanic dataset.

## Dataset Structure

The analysis is performed on the standard Titanic dataset located within the directory structure:
```text
Week1/day4/dataset/titanic dataset/Titanic-Dataset.csv
```
## Overview

The workflow executes the following data preparation and transformation steps:
1. **Missing Values Identification:** Evaluates and counts missing values across all dataset columns.
2. **Missing Value Handling:** Drops the `Cabin` column due to a high volume of missing data and imputes missing `Age` values using the column mean.
3. **Data Type Correction:** Converts the filled `Age` column format from float to integer type.
4. **Duplicate Verification:** Validates the dataset for duplicate entries to ensure data integrity.
5. **Feature Engineering:** Derives new features including `FamilySize` (combining sibling/spouse and parent/child counts) and `AgeGroup` classifications.
6. **Data Reshaping & Aggregating:** Generates a structured summary table grouped by passenger class (`Pclass`) to evaluate metrics such as survival counts and average age.
7. **Mapping and Merging:** Integrates descriptive text labels (`First`, `Second`, `Third`) with numerical class codes via a left join.

## Requirements

* Python 3.x
* Pandas
* NumPy

Install the necessary dependencies via terminal:
```bash
pip install pandas numpy
```
## Running the Notebook
To review and execute the data processing pipeline interactively, launch Jupyter Notebook or JupyterLab:
```bash 
jupyter notebook day4_pandas_cleaning.ipynb
```
(Alternatively, open the day4_pandas_cleaning.ipynb file directly within an IDE configured with Jupyter support, such as VS Code).

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*
