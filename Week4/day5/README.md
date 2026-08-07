# Adult Census Income Prediction — Machine Learning Capstone

## Project Overview

This capstone project develops an end-to-end machine learning solution for predicting whether an individual's annual income exceeds **$50,000** using the **UCI Adult Census Income Dataset**.

The project builds upon previous experiments involving baseline models, preprocessing, feature engineering, hyperparameter tuning, calibration, and model evaluation. It extends the workflow by incorporating ensemble learning, class imbalance handling, model interpretability, fairness evaluation, and deployment preparation.

The final solution emphasizes **high Precision**, making it suitable for business scenarios where minimizing false positive predictions is more important than maximizing Recall.

---

# Business Objective

The objective of this project is to identify individuals who are most likely to earn more than **$50K per year**.

Potential business applications include:

- Targeted marketing campaigns
- Customer segmentation
- Financial product recommendations
- Credit risk screening

Since contacting an incorrect customer is costly, **Precision** was selected as the primary evaluation metric.

---

# Dataset

**Dataset:** UCI Adult Census Income Dataset

**Target Variable**

- **0** → Income ≤ $50K
- **1** → Income > $50K

### Dataset Size

- Total Samples: **48,842**
- Training Set: **39,073**
- Testing Set: **9,769**

### Original Features

- Age
- Workclass
- Education
- Education Number
- Marital Status
- Occupation
- Relationship
- Race
- Sex
- Capital Gain
- Capital Loss
- Hours per Week
- Native Country
- Final Weight (fnlwgt)

---

# Feature Engineering

Six additional features were created to improve predictive performance.

| Engineered Feature | Description |
|-------------------|-------------|
| age_bucket | Age grouped into ranges |
| hours_bucket | Working hours grouped into categories |
| has_capital_gain | Indicates whether capital gain exists |
| log_capital_gain | Log-transformed capital gain |
| higher_education | Education level ≥ 13 |
| edu_hours_interaction | Education × Working Hours interaction |

---

# Data Preprocessing

The preprocessing pipeline includes:

### Numerical Features

- Median Imputation
- Standard Scaling

### Categorical Features

- Missing value imputation
- One-Hot Encoding
- Unknown category handling (`handle_unknown="ignore"`)

All preprocessing steps are integrated into a reusable Scikit-Learn pipeline.

---

# Models Evaluated

Three ensemble learning models were compared.

| Model | Purpose |
|--------|----------|
| Random Forest | Bagging Ensemble |
| HistGradientBoosting | Gradient Boosting |
| Stacking Classifier | Ensemble of Logistic Regression and Random Forest |

---

# Hold-Out Test Results

| Model | Accuracy | Precision | Recall | F1 Score | ROC AUC | PR AUC |
|--------|----------|-----------|---------|----------|---------|---------|
| Random Forest | 0.8573 | 0.8168 | 0.5205 | 0.6358 | 0.9115 | 0.7920 |
| HistGradientBoosting | **0.8164** | **0.9875** | 0.2357 | 0.3805 | 0.8929 | 0.7497 |
| Stacking | 0.8587 | 0.7795 | **0.5714** | **0.6594** | **0.9120** | **0.7945** |

---

# Selected Model

The final production model is:

## HistGradientBoostingClassifier

### Hyperparameters

```python
learning_rate = 0.01
max_depth = 3
max_iter = 100
l2_regularization = 0
```

### Why This Model?

Although the Stacking classifier achieved the highest Recall and F1-score, HistGradientBoosting produced the highest Precision (**98.75%**), making it the most suitable model for the project's business objective.

---

# Class Imbalance Handling

The training data contains moderate class imbalance.

| Class | Percentage |
|--------|------------|
| Income ≤50K | 76.07% |
| Income >50K | 23.93% |

Three imbalance handling strategies were evaluated.

- Class Weight
- Random Oversampling
- SMOTE

Among them, **SMOTE** achieved the highest cross-validation Precision and the most stable performance.

---

# Model Interpretability

To improve transparency, two interpretability techniques were applied.

## Permutation Importance

Most influential features:

- Capital Gain
- Marital Status
- Capital Loss
- Education Number
- Education-Hours Interaction

## SHAP

Global and local SHAP explanations were generated to understand:

- Feature contributions
- Individual predictions
- False Positives
- False Negatives
- True Positives

---

# Fairness Evaluation

Model performance was evaluated across demographic groups.

### Precision by Sex

| Sex | Precision |
|------|-----------|
| Female | 0.9896 |
| Male | 0.9870 |

### Precision by Race

| Race | Precision |
|------|-----------|
| White | 0.9880 |
| Black | 1.0000 |
| Asian-Pac-Islander | 0.9412 |
| Other | 1.0000 |
| Amer-Indian-Eskimo | 1.0000 |

No major disparity was observed using Precision, although additional fairness metrics should be monitored in production.

---

# Deployment

The final deployment artifact is a complete Scikit-Learn pipeline containing:

- Feature Engineering
- Preprocessing
- HistGradientBoosting Classifier

The pipeline was saved as:

```
final_income_prediction_model.joblib
```

The deployment pipeline supports:

- Input validation
- Custom prediction threshold
- SHAP explanations
- Robust handling of unseen categorical values
- Automatic preprocessing during inference


---

# Technologies Used

- Python
- Pandas
- NumPy
- Scikit-Learn
- Imbalanced-Learn
- SHAP
- Joblib
- Matplotlib
- Seaborn

---

# Key Findings

- HistGradientBoosting achieved **98.75% Precision** on the hold-out test set.
- Capital Gain is the strongest predictor of high income.
- SHAP explanations improved model transparency.
- Fairness evaluation showed consistent Precision across demographic groups.
- The deployment pipeline successfully handles missing inputs and unseen categorical values.

---

# Future Improvements

Potential future enhancements include:

- Hyperparameter optimization using Bayesian Optimization
- Threshold optimization based on business cost
- Probability calibration
- Additional fairness metrics (Equal Opportunity, Demographic Parity)
- Drift detection for production monitoring
- Continuous model retraining using newly collected data
- Deployment as a REST API using FastAPI or Flask
