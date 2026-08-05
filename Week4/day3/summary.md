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
| **log_capital_gain** | Reduces skewness of capital gain while preserving predictive information. | Mutual Information = **0.0798** |
| **higher_education** | Indicates Bachelor's degree or higher. | Mutual Information = **0.0522** |
| **edu_hours_interaction** | Captures the combined effect of education level and weekly working hours. | Mutual Information = **0.0802** |

Overall, all engineered features demonstrated meaningful predictive signal. The strongest engineered features were **edu_hours_interaction** and **log_capital_gain**, while **age_bucket** and **hours_bucket** revealed clear nonlinear relationships with the target variable that would not be captured by the original continuous features alone.

---

# 2. Cross-Validation Model Comparison

Three supervised learning models were evaluated using **5-fold Stratified Cross-Validation** with identical preprocessing pipelines. Precision was selected as the primary evaluation metric because the business objective favors minimizing false positives when identifying individuals earning more than \$50K.

| Model | Precision (Mean ± Std) | F1-score (Mean ± Std) | ROC AUC (Mean ± Std) |
|--------|------------------------|-----------------------|----------------------|
| Logistic Regression | **(Insert your result)** | **(Insert your result)** | **(Insert your result)** |
| Random Forest | **(Insert your result)** | **(Insert your result)** | **(Insert your result)** |
| HistGradientBoosting | **(Insert your result)** | **(Insert your result)** | **(Insert your result)** |

**Figures included in notebook**

- Precision Boxplot
- F1-score Boxplot
- ROC AUC Boxplot

The cross-validation results consistently showed that **HistGradientBoostingClassifier** achieved the highest average Precision, F1-score, and ROC AUC across the five folds while maintaining relatively stable performance. Logistic Regression remained a strong and interpretable baseline, whereas Random Forest produced lower overall performance and greater variability across folds.

---

# 3. Statistical Comparison

A paired statistical comparison was performed between the two best-performing models: **HistGradientBoostingClassifier** and **Logistic Regression**.

- **Paired t-test:** Significant difference (**p = 0.0018**)
- **Wilcoxon Signed-Rank Test:** p = **0.0625**

Although the Wilcoxon test narrowly missed the conventional 0.05 significance threshold, this is expected with only five paired observations. The statistic **W = 0** indicates that HistGradientBoostingClassifier outperformed Logistic Regression in every cross-validation fold. Since cross-validation fold scores are not completely independent, these statistical results should be interpreted as supportive rather than definitive evidence. Nevertheless, both the statistical comparison and the practical improvement in Precision, F1-score, and ROC AUC support selecting HistGradientBoostingClassifier as the strongest candidate for further development.

---

# 4. Feature Selection

Feature selection was evaluated using **SelectKBest** with **Mutual Information** as the scoring function (**k = 30**).

Compared with the complete engineered feature set:

- Precision decreased from **0.7789** to **0.7714**   
- Cross-validation training time increased from **17.79 s** to **109.85 s**

The reduction in Precision suggests that some discarded features still contributed useful predictive information, while the increased training time was primarily caused by repeatedly computing Mutual Information during each cross-validation fold. Since **HistGradientBoostingClassifier** is generally robust to weak or redundant features, explicit feature selection provided little additional benefit in this experiment.

**Decision:** Retain the complete engineered feature set for hyperparameter tuning.

---

# 5. Final Recommendation

Based on the cross-validation results, statistical comparison, and feature-selection experiment, **HistGradientBoostingClassifier** is recommended for the next stage of hyperparameter tuning. It achieved the strongest overall performance across all evaluation metrics while maintaining consistent results across the validation folds.

The six engineered features successfully captured nonlinear patterns, interaction effects, and transformed variables without introducing data leakage. Feature selection did not improve either predictive performance or computational efficiency; therefore, the complete engineered feature set will be retained. Future work will focus on optimizing HistGradientBoostingClassifier through hyperparameter tuning while continuing to use the established preprocessing and feature engineering pipeline.