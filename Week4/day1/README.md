# Adult Income Prediction — ML Foundations Baseline

Baseline machine learning workflow to predict whether an individual's annual
income exceeds $50,000, using the UCI Adult (Census Income) dataset.
This project covers problem framing, exploratory data analysis, a
reproducible trainhold-out split, two baseline classifiers, and initial
error analysis — establishing the benchmark that future models must beat.

## Dataset

- Source UCI Machine Learning Repository (via `sklearn.datasets.fetch_openml`, `name=adult`, `version=2`)
- Records 48,842
- Features 14 (demographic + employment)
- Target `class` — binary, `1` = income  $50K, `0` = income ≤ $50K
- Class balance 23.93% positive  76.07% negative (imbalanced)

## Problem Statement

Predict whether an individual earns more than $50,000year, so that
marketing or premium-product outreach can be targeted efficiently —
reducing wasted contact costs for individuals unlikely to qualify.

## Evaluation Metric Precision@top-k

Since outreach budget is limited, only a fixed-size group of top candidates
is contacted rather than everyone above a generic threshold. Precision@top-k
measures accuracy within that selected group — of the k people flagged as
likely high-income, what fraction truly are. This penalizes false positives
(wasted, low-value contacts) directly and extends naturally once a scored
model is introduced.

## Project Workflow
Adult Dataset → Data Cleaning → EDA → Train/Test Split →
Baseline Models → Performance Evaluation → Error Analysis → Future Improvements

## Repository Contents

| File | Description |
|---|---|
| `census_baseline.ipynb` | Full analysis notebook (EDA, splits, baselines, error analysis) |
| `Adult_Income_Baseline_Summary.pdf` | 1-page summary (problem framing → metric → results → error analysis) |
| `README.md` | This file |

## Methodology

1.  **Data Cleaning** — Checked for `'?'` missing indicators (OpenML dataset already uses `NaN`; replacement included as a precaution); target label converted to binary (0/1).
2. **EDA** — shape/dtypes check, missing-value audit, numeric summary, categorical value counts, histograms and bar plots for key features.
3. **Reproducible Split** — stratified 80/20 train/hold-out test split (`random_state=42`); hold-out set untouched until final evaluation. An additional 10% dev split is carved from training for faster iteration.
4. **Baselines**
   - **Majority-class** — always predicts the most frequent class (`≤$50K`)
   - **Rule-based** — predicts `>$50K` when `capital-gain > 0`
5. **Error Analysis** — sampled false positives/negatives to identify patterns and guide next-step feature engineering.

## Baseline Results (hold-out test set, n = 9,769)

| Baseline | Accuracy | Precision | Recall | F1 | ROC AUC | PR AUC |
|---|---|---|---|---|---|---|
| Majority-class | 0.7607 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.2393 |
| Rule-based (`capital-gain > 0`) | 0.7823 | 0.6254 | 0.2250 | 0.3309 | 0.5913 | 0.3262 |

The majority-class baseline reaches ~76% accuracy purely from class imbalance
but identifies zero high-income individuals. The rule-based baseline beats it
on every metric, reaching **62.5% precision** (Precision@k = 526/841) —
the benchmark any real model must clear.

## Key Findings (Error Analysis)

- **False positives:** individuals with nonzero capital-gain who still fall
  in the low-income class — capital-gain alone isn't a sufficient signal.
- **False negatives:** commonly Bachelor's/Master's degree holders in
  professional/managerial roles (Tech-support, Exec-managerial) working
  40–60 hrs/week with **zero** capital-gain — their income comes from
  salary, not investments, which the rule entirely misses.

## Next Steps

1. Handle missing values in `workclass`, `occupation`, `native-country`.
2. One-hot encode categorical features.
3. Log-transform skewed variables (`capital-gain`, `capital-loss`).
4. Engineer combined features from education, occupation, and hours worked.
5. Train stronger models (Logistic Regression, Random Forest, XGBoost) using ranked probability scores.
6. Tune hyperparameters via cross-validation while keeping the hold-out test set untouched.

## How to Run

```bash
pip install pandas numpy scikit-learn matplotlib
jupyter notebook census_baseline.ipynb
```

Run all cells top-to-bottom (`Restart & Run All`) for full reproducibility.

## Tech Stack

Python · pandas · NumPy · scikit-learn · Matplotlib