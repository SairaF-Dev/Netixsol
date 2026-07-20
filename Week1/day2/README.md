# Sensor Data Analysis with NumPy

This repository demonstrates how to generate synthetic multi-sensor time-series data, compute rolling statistics, normalize data using Z-scores, and detect statistical outliers using **NumPy**.

## Overview

The script performs four main data science operations:
1. **Synthetic Data Generation:** Creates a simulated dataset representing 100 time-step readings across 3 independent sensors drawn from a normal distribution.
2. **Rolling Statistics:** Computes a sliding window mean over a specified window size (5 readings) to track trends over time.
3. **Data Normalization:** Standardizes the dataset using the Z-score formula across each sensor channel.
4. **Outlier Detection:** Flags readings that deviate beyond 2 standard deviations from the mean using boolean masking.

## Requirements

* Python 3.x
* NumPy

Install NumPy if you haven't already:
```bash
pip install numpy
```
Running the Script
Execute the script directly in your terminal or Python environment:
day2_numpy_outliers.py

*Author: Saira Fatima | DevSquad ’26 Internship at NetixSol*

