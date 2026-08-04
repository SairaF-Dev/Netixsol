# Adult Income Prediction  ML Foundations 

Progressive machine learning workflow to predict whether an individual's
annual income exceeds **$50,000**, using the UCI **Adult (Census Income)**
dataset. Built across two days: Day 1 establishes problem framing and
baseline benchmarks; Day 2 introduces real supervised models with
leak-free preprocessing pipelines.

## Dataset

- **Source:** UCI Machine Learning Repository (via `sklearn.datasets.fetch_openml`, `name="adult"`, `version=2`)
- **Records:** 48,842 | **Features:** 14 | **Target:** `class` (`1` = >$50K, `0` = ≤$50K)
- **Class balance:** 23.93% positive / 76.07% negative (imbalanced)
- **Hold-out test set:** stratified 20% split, `random_state=42`, untouched until final evaluation (n = 9,769)

## Problem Statement & Metric

Predict whether an individual earns more than $50,000/year, so marketing
outreach can be targeted efficiently and wasted contact costs minimized.
Primary metric: **Precision@top-k** — since outreach budget is limited to
a fixed-size group of top candidates, precision within that selected
group directly reflects the cost of a false positive.

## Repository Contents

```
Week4/
├── day1/
│   ├── census_baseline.ipynb              — EDA, reproducible train/test split, two baselines
│   ├── Adult_Income_Baseline_Summary.pdf   — 1-page summary
│   └── README.md
└── day2/
    ├── week4_day2_supervised_learning.ipynb — preprocessing pipeline, LogReg & Decision Tree, evaluation, interpretability
    ├── Day2_Preprocessing_Model_Writeup.pdf — 2-page write-up (preprocessing choices + model comparison)
    ├── preprocessor.pkl
    ├── logreg_full_pipeline.pkl
    ├── tree_full_pipeline.pkl                — saved pipelines for reuse on Day 3
    └── README.md
```

## Day 1:  Problem Framing & Baselines

- **Majority-class baseline** (always predicts ≤$50K) and **rule-based baseline** (`capital-gain > 0`) evaluated on the hold-out test set.
- Rule-based baseline reached **62.5% precision** (Precision@k = 526/841) — the benchmark for real models to beat.
- Error analysis: false positives had nonzero capital-gain but low income; false negatives were salaried professionals (Bachelor's/Master's, Exec-managerial/Tech-support) with zero capital-gain — the rule alone misses salary-driven high earners.

## Day 2: Preprocessing, Models & Evaluation

### Preprocessing (`ColumnTransformer`)

| Feature type | Steps | Reasoning |
|---|---|---|
| Numeric (6) | `SimpleImputer(median)` → `StandardScaler` | capital-gain/loss are heavily right-skewed (mean ≫ median, max=99,999); median avoids outlier distortion |
| Categorical (8) | `SimpleImputer(constant, "Missing")` → `OneHotEncoder(handle_unknown="ignore")` | Missing `workclass` records work fewer hours/week (31.8 vs. 40.4) and have lower capital-gain — a systematic pattern, not random. Confirmed **100% of `workclass` NaNs are also `occupation` NaNs** (2,799/2,799), so most-frequent imputation would fabricate employment details for the same group twice |

### Models

Two pipelines (`preprocessor` + estimator), fit on training data only:

1. **Logistic Regression** (`solver="liblinear"`, `random_state=42`)
2. **Decision Tree Classifier** (`random_state=42`, unconstrained)

### Results (hold-out test set, n = 9,769)

| Model | Accuracy | Precision | Recall | F1 | ROC AUC | PR AUC |
|---|---|---|---|---|---|---|
| Day1: Majority Baseline | 0.7607 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.2393 |
| Day1: Rule Baseline | 0.7823 | 0.6254 | 0.2250 | 0.3309 | 0.5913 | 0.3262 |
| **Logistic Regression** | **0.8542** | **0.7428** | 0.5979 | **0.6626** | **0.9058** | **0.7671** |
| Decision Tree | 0.8186 | 0.6185 | **0.6317** | 0.6251 | 0.7546 | 0.4789 |

- **Logistic Regression:** no overfitting (train 0.8535 vs. test 0.8542, gap = -0.0007).
- **Decision Tree:** grew to depth 68, 99.99% train accuracy vs. 81.86% test, an 18-point gap confirming severe overfitting. Top splits (`marital-status`, `capital-gain`, `education-num`) were nonetheless intuitive.
- **Errors:** false negatives outnumber false positives for both models (LogReg: 940 vs. 484), favoring Logistic Regression under the Precision@top-k objective.

### Interpretability

- **Logistic Regression coefficients:** top positive drivers — capital-gain, married status, Exec-managerial occupation, education-num (all intuitive). Several native-country categories appeared among top coefficients despite tiny subgroup sizes (28–127 people), likely reflecting instability rather than real signal.
- **Fairness note:** `sex_Female` carries a strongly negative coefficient (-1.03), reflecting a real gender income gap in the 1994 Census data flagged for awareness if this model informs real decisions.

## Model Selected for Day 3

**Logistic Regression** leads on nearly every metric, shows no overfitting, and is directly interpretable. The Decision Tree's logic is sound but overfit; a **pruned** version (`max_depth`, `min_samples_leaf`) will be tested on Day 3 to see if it can capture nonlinear interactions the linear model cannot.

## Next Steps (Day 3)

1. Prune the Decision Tree to address overfitting.
2. Log-transform `capital-gain`/`capital-loss` before scaling.
3. A/B test the "Missing"-category imputation strategy against most-frequent to quantify its actual impact (well-justified for workclass/occupation; reasoned by analogy only for native-country).
4. Reload the saved `preprocessor.pkl` and wrap it into new model pipelines without modification.

## How to Run

```bash
pip install pandas numpy scikit-learn matplotlib joblib
jupyter notebook census_baseline.ipynb
jupyter notebook week4_day2_supervised_learning.ipynb
```

Run all cells top-to-bottom (`Restart & Run All`) for full reproducibility.

## Tech Stack

Python · pandas · NumPy · scikit-learn · Matplotlib · joblib

