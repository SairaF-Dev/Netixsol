# Week 4  Day 4: Model Tuning, Regularization & Reproducible Pipelines

## Overview

This project extends the supervised learning models developed in previous stages by applying systematic hyperparameter tuning, regularization, probability calibration, threshold optimization, and reproducible machine learning pipelines.

The Adult Census Income dataset is used to predict whether an individual's annual income exceeds **$50K**. The primary optimization metric is **Precision**, since reducing false positive predictions is the project's business objective.

---

# Project Objectives

- Build fully reproducible Scikit-learn pipelines.
- Tune multiple supervised learning models using RandomizedSearchCV.
- Compare candidate models using cross-validation.
- Diagnose overfitting and underfitting using learning curves.
- Analyze the effects of regularization and tree complexity.
- Improve probability estimates through calibration.
- Select an appropriate decision threshold based on business requirements.
- Evaluate the final tuned model on an untouched hold-out test set.
- Save the complete trained pipeline for future inference.

---

# Dataset

**Dataset:** Adult (Census Income) Dataset

**Prediction Target:**

- <=50K → 0
- >50K → 1

---

# Models Evaluated

The following supervised learning models were tuned and compared:

- Logistic Regression
- Random Forest
- HistGradientBoosting Classifier

---

# Hyperparameter Search

RandomizedSearchCV was used with:

- Stratified 5-Fold Cross Validation
- Precision as the optimization metric
- Parallel execution (`n_jobs=-1`)
- Controlled randomness using `random_state`

### Best Cross-Validation Precision

| Model | Precision |
|--------|-----------|
| Logistic Regression | **0.7704** |
| Random Forest | **0.8065** |
| HistGradientBoosting | **0.9710** |

HistGradientBoosting achieved the highest cross-validation Precision (0.9710), outperforming Random Forest (0.8065) and Logistic Regression (0.7704). Therefore, it was selected as the final candidate for probability calibration and evaluation on the untouched hold-out test set.

---

# Model Diagnostics

The notebook includes:

- Learning Curves
- Logistic Regression Regularization Analysis
- Random Forest Tree Depth Analysis
- Calibration Curve
- Confusion Matrix
- Threshold Analysis

These diagnostics were used to evaluate model complexity, identify potential overfitting, and improve probability estimates.

---

# Probability Calibration

Calibration was evaluated using:

- Calibration Curve
- Brier Score

| Stage | Brier Score |
|--------|-------------|
| Before Calibration | **0.1190** |
| After Calibration | **0.1050** |

A lower Brier Score after calibration indicates improved probability estimation.

---

# Threshold Selection

Several classification thresholds were evaluated.

| Threshold | Precision | Recall | F1 |
|-----------|-----------|---------|---------|
|0.30|0.5883|0.7720|0.6678|
|0.40|0.6566|0.6950|0.6753|
|0.50|0.7634|0.5466|0.6371|
|0.60|0.7925|0.5128|0.6227|
|0.70|0.8218|0.4773|0.6039|

A threshold of **0.70** was selected because it produced the highest Precision, which aligns with the project's objective of minimizing false positives.

---

# Final Hold-Out Test Results

| Metric | Score |
|---------|--------|
| Accuracy | **0.8501** |
| Precision | **0.8218** |
| Recall | **0.4773** |
| F1 Score | **0.6039** |
| ROC AUC | **0.8929** |
| PR AUC | **0.7568** |

---

# Project Structure

```
week4_day4_model_tuning_pipelines.ipynb
README.md
tuning_report.md
final_pipeline.joblib
```

---

# Requirements

- Python 3.x
- NumPy
- Pandas
- Matplotlib
- Scikit-learn
- Joblib

---

# Reproducing the Results

1. Clone the repository.
2. Install all required Python libraries.
3. Open the notebook.
4. Run every cell from top to bottom.
5. The notebook will:
   - Build preprocessing pipelines
   - Perform hyperparameter tuning
   - Generate learning curves
   - Apply probability calibration
   - Evaluate multiple thresholds
   - Produce final evaluation metrics
   - Save the trained pipeline

---

# Loading the Saved Model

```python
import joblib

model = joblib.load("final_pipeline.joblib")

prediction = model.predict(new_data)

probability = model.predict_proba(new_data)
```

---

# Key Takeaways

- Fully reproducible Scikit-learn pipelines were implemented.
- Three candidate models were systematically tuned.
- HistGradientBoosting achieved the best cross-validation precision.
- Learning curve analysis showed good generalization with minimal overfitting.
- Probability calibration improved the Brier Score.
- Threshold tuning demonstrated the trade-off between Precision and Recall.
- The final calibrated pipeline achieved strong predictive performance on the untouched hold-out test set.
- The trained pipeline was saved for future deployment and inference.

