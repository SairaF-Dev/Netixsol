# Feature Engineering, Cross-Validation & Model Comparison

## Project Overview

This project extends the Adult Income Classification problem by introducing feature engineering, robust cross-validation, statistical model comparison, and feature selection. The objective is to improve predictive performance while maintaining a reproducible machine learning workflow with no data leakage.

The target variable predicts whether an individual's annual income exceeds **$50K** using demographic and employment-related attributes from the UCI Adult Census Income dataset.

---

# Objectives

- Create meaningful engineered features.
- Prevent data leakage using a preprocessing pipeline.
- Compare multiple supervised learning models using 5-fold Stratified Cross-Validation.
- Perform statistical comparison between the best models.
- Evaluate feature selection techniques.
- Select the best model and feature set for hyperparameter tuning.

---

# Dataset

- **Dataset:** UCI Adult Census Income
- **Target Variable:** `class`
  - `<=50K`
  - `>50K`

The original hold-out train/test split from the previous stage was reused throughout this project.

---

# Feature Engineering

Six engineered features were created using only information available within each individual record.

| Feature | Description |
|----------|-------------|
| **age_bucket** | Groups age into career-stage categories. |
| **hours_bucket** | Categorizes weekly working hours into part-time, standard, and overtime. |
| **has_capital_gain** | Binary indicator showing whether capital gain is greater than zero. |
| **log_capital_gain** | Log transformation of capital gain to reduce skewness. |
| **higher_education** | Indicates whether education level is Bachelor's degree or above. |
| **edu_hours_interaction** | Interaction feature between education level and weekly working hours. |

Feature engineering was implemented using **FunctionTransformer**, ensuring that transformations occur inside the preprocessing pipeline and preventing information leakage.

---

# Preprocessing Pipeline

The preprocessing pipeline consists of:

### Numeric Features

- Median Imputation
- StandardScaler

### Categorical Features

- Most Frequent Imputation
- OneHotEncoder (`handle_unknown="ignore"`)

The engineered features were added before preprocessing within the same pipeline.

---

# Models Evaluated

Three supervised learning algorithms were compared using identical preprocessing.

- Logistic Regression
- Random Forest Classifier
- HistGradientBoostingClassifier

Evaluation was performed using **5-fold Stratified Cross-Validation**.

---

# Evaluation Metrics

Primary metric:

- Precision

Secondary metrics:

- F1-score
- ROC AUC

Cross-validation performance was reported as:

- Mean
- Standard Deviation

Boxplots were generated for:

- Precision
- F1-score
- ROC AUC

to visualize score distributions across folds.

---

# Statistical Comparison

The two best-performing models were compared using:

- Paired t-test
- Wilcoxon Signed-Rank Test

The statistical analysis was complemented with a practical interpretation of model performance rather than relying solely on p-values.

---

# Feature Selection

Feature selection was evaluated using:

- SelectKBest
- Mutual Information
- k = 30

Performance before and after feature selection was compared using:

- Precision
- Cross-validation training time

The experiment showed that feature selection slightly reduced predictive performance while increasing computational cost.

---

# Key Findings

- HistGradientBoostingClassifier achieved the highest Precision, F1-score, and ROC AUC.
- Engineered features provided meaningful predictive information without introducing data leakage.
- `edu_hours_interaction` and `log_capital_gain` showed the strongest predictive signal among the engineered features.
- Feature selection using SelectKBest did not improve performance or computational efficiency.
- The complete engineered feature set was retained for the next stage of hyperparameter tuning.

---

# Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Scikit-learn
- SciPy

---

# Repository Structure

```
.
├── notebook.ipynb
├── README.md
├── summary.md
```

---

# Future Work

The next phase of the project will focus on:

- Hyperparameter tuning
- Model calibration
- Threshold optimization
- Final evaluation on the untouched hold-out test set

