# Feature Engineering, Cross-Validation & Model Comparison

## Objective

The objective of this experiment was to improve the Adult Income prediction model through principled feature engineering and compare multiple supervised learning algorithms using reliable cross-validation. Six engineered features were created using only current-row information and integrated into the preprocessing pipeline with a `FunctionTransformer` to prevent data leakage. Model selection was based primarily on **Precision**, with **F1-score** and **ROC AUC** used as secondary evaluation metrics. A statistical comparison and feature-selection experiment were also conducted to identify the best model and feature set for the next stage of hyperparameter tuning.

---

# 1. Engineered Feature Summary

Six engineered features were created to capture nonlinear relationships, interaction effects, and transformations that are not directly represented by the original dataset.

| Feature | Purpose | Predictive Signal |
|----------|---------|------------------|
| **age_bucket** | Captures nonlinear relationship between age and income by grouping different career stages. | Peak target mean = **39.4%** (Age 45–54) |
| **hours_bucket** | Distinguishes part-time, standard, and overtime workers. | Overtime target mean = **40.0%** |
| **has_capital_gain** | Binary indicator of investment income. | Mutual Information = **0.0303** |
| **log_capital_gain** | Reduces the skewness of capital gain while preserving predictive information. | Mutual Information = **0.0798** |
| **higher_education** | Indicates whether an individual has a Bachelor's degree or higher. | Mutual Information = **0.0522** |
| **edu_hours_interaction** | Captures the combined effect of education level and weekly working hours. | Mutual Information = **0.0802** |

Overall, all six engineered features demonstrated meaningful predictive signal. The strongest engineered features were **edu_hours_interaction** and **log_capital_gain**, while **age_bucket** and **hours_bucket** revealed clear nonlinear relationships with the target variable that would not be captured by the original continuous features alone.

---

# 2. Cross-Validation Model Comparison

Three supervised learning models were evaluated using **5-fold Stratified Cross-Validation** with identical preprocessing pipelines. Precision was selected as the primary evaluation metric because the business objective favors minimizing false positives when identifying individuals earning more than **$50K**.

| Model | Precision (Mean ± Std) | F1-score (Mean ± Std) | ROC AUC (Mean ± Std) |
|--------|------------------------|-----------------------|----------------------|
| **Logistic Regression** | **0.7444 ± 0.0174** | **0.6753 ± 0.0090** | **0.9137 ± 0.0031** |
| **Random Forest** | **0.7233 ± 0.0111** | **0.6656 ± 0.0084** | **0.9024 ± 0.0053** |
| **HistGradientBoosting** | **0.7789 ± 0.0110** | **0.7090 ± 0.0087** | **0.9276 ± 0.0024** |

### Figures Included

- Precision Boxplot
- F1-score Boxplot
- ROC AUC Boxplot

The cross-validation results showed that **HistGradientBoostingClassifier** achieved the best overall performance, obtaining the highest Precision (**0.7789 ± 0.0110**), F1-score (**0.7090 ± 0.0087**), and ROC AUC (**0.9276 ± 0.0024**). Logistic Regression ranked second and remained a strong, interpretable baseline, while Random Forest produced the lowest scores across all three evaluation metrics. The relatively small standard deviations indicate that all models were reasonably stable across the five cross-validation folds, with HistGradientBoostingClassifier combining both the highest predictive performance and consistent results.

---

# 3. Statistical Comparison

A paired statistical comparison was performed between the two best-performing models: **HistGradientBoostingClassifier** and **Logistic Regression**.

| Statistical Test | Result |
|------------------|--------|
| **Paired t-test** | **p = 0.0018** (Statistically significant) |
| **Wilcoxon Signed-Rank Test** | **W = 0, p = 0.0625** |

The paired t-test indicated a statistically significant difference between the two models, whereas the Wilcoxon Signed-Rank Test narrowly missed the conventional significance threshold. This discrepancy is expected because only five paired observations (one per cross-validation fold) were available, limiting the statistical power of the non-parametric test. Importantly, **W = 0** indicates that HistGradientBoostingClassifier outperformed Logistic Regression in every fold, demonstrating a highly consistent performance advantage.

Since cross-validation fold scores are not completely independent, these statistical tests should be interpreted as supportive rather than definitive evidence. Nevertheless, the statistical analysis, together with the consistent improvements in Precision, F1-score, and ROC AUC, supports selecting **HistGradientBoostingClassifier** as the strongest candidate for further development.

---

# 4. Feature Selection

Feature selection was evaluated using **SelectKBest** with **Mutual Information** as the scoring function (**k = 30**).

Compared with the complete engineered feature set:

- **Precision:** **0.7789 → 0.7714**
- **Cross-validation training time:** **17.96 s → 109.85 s**

The slight reduction in Precision suggests that some discarded features still contained useful predictive information that HistGradientBoostingClassifier was able to exploit effectively. Meanwhile, the increase in overall training time was primarily caused by repeatedly computing Mutual Information during each cross-validation fold, which outweighed any reduction in model training time from using fewer features.

Since **HistGradientBoostingClassifier** is generally robust to weak or redundant features, explicit feature selection provided little additional benefit in this experiment.

**Decision:** Retain the complete engineered feature set for hyperparameter tuning.

---

# 5. Final Recommendation

Based on the cross-validation results, statistical comparison, and feature-selection experiment, **HistGradientBoostingClassifier** is recommended for the next stage of hyperparameter tuning. It achieved the highest Precision (**0.7789 ± 0.0110**), F1-score (**0.7090 ± 0.0087**), and ROC AUC (**0.9276 ± 0.0024**) while maintaining stable performance across all five cross-validation folds.

The six engineered features successfully captured nonlinear patterns, interaction effects, and transformed variables without introducing data leakage. Among them, **edu_hours_interaction** and **log_capital_gain** exhibited the strongest predictive signal, indicating that combining education with working hours and reducing the skewness of capital gain added useful information for classification.

Feature selection using SelectKBest did not improve either predictive performance or computational efficiency. Consequently, the complete engineered feature set will be retained for hyperparameter tuning. The next stage of the project will focus on optimizing **HistGradientBoostingClassifier** through systematic hyperparameter tuning while preserving the established preprocessing and feature engineering pipeline.