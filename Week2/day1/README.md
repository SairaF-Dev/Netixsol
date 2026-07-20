# AFL Player Data Cleaning, Validation, and Integration Pipeline

This repository contains a complete Python-based data cleaning, validation, and merging pipeline for Australian Football League (AFL) datasets. The project processes raw player information and seasonal performance statistics, resolves data quality issues, harmonizes key structures, and generates analysis-ready datasets.

---

## **Project Overview**
Raw data extracted from sports information platforms frequently contains inconsistencies, mixed data types, structural formatting anomalies, and missing entries. This project implements a rigorous data preprocessing workflow using **Pandas** and **NumPy** to ensure high data integrity before exploratory data analysis or machine learning modeling.



## **Key Deliverables**
* **`days1_afl_data_cleaning_and_validation.ipynb`**: The master Jupyter Notebook containing all end-to-end cleaning, transformation, validation, and export steps.
* **`players_info.csv`**: The cleaned and standardized player biographical dataset.
* **`seasonal_stats.csv`**: The cleaned seasonal performance dataset with imputed numerical metrics.
* **`merged_players.csv`**: The final integrated dataset synthesized via an inner join on unique player identifiers.



## **Data Quality Assessment & Cleaning Pipeline**

### **1. Player Information Dataset (`player_info_df`)**
* **Initial Shape:** 2,848 rows × 16 columns
* **Issues Addressed:**
  * **Unessential Metadata:** Dropped high-volume missing text/URL columns (`profile_pic`, `player_common_names`) that do not impact performance analysis.
  * **Missing Team Data:** Imputed 94 missing team entries with `'Unknown'` to preserve baseline demographic counts.
  * **Date Formatting:** Converted unstandardized raw date strings (`born_date`, `debut_date`, `last_date`) into standard datetime objects using `pd.to_datetime`.
  * **Duplicates:** Removed 5 identical duplicate rows.
* **Final Shape:** 2,843 rows × 14 columns

### **2. Seasonal Statistics Dataset (`player_seasonal_stats_df`)**
* **Initial Shape:** 15,880 rows × 54 columns
* **Issues Addressed:**
  * **Missing Performance Metrics:** Imputed missing values across 45 float-type performance metric columns with `0.0`, reflecting unrecorded instances or non-participation during specific game blocks.
  * **Mixed Key Formatting (`player_id`):** Cleaned mixed-format identifiers containing string prefixes (e.g., stripping `'ID_'`) and cast the entire column type to `int64`.
  * **Duplicates:** Removed 6 duplicate records.
* **Final Shape:** 15,874 rows × 54 columns



## **Data Integration & Validation Summary**
* **Merge Operation:** Executed an inner join between `player_seasonal_stats_df` (using `player_id`) and `player_info_df` (using `id`).
* **Final Merged Shape:** 15,523 rows × 68 columns
* **Validation Metrics:**
  * **Orphan Seasonal Stats (Unmatched IDs):** 222 records
  * **Profiles with No Seasonal Stats:** 1,068 records
  * **Total Null Values Post-Cleaning:** 0



## **How to Run the Code**
1. Ensure the raw CSV files (`afl_players_info_raw.csv` and `afl_players_seasonal_stats_raw.csv`) are placed in your working directory or Google Colab environment.
2. Open and run the Jupyter Notebook:
   ```bash
   jupyter notebook day1_afl_data_cleaning_and_validation.ipynb

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*


   
