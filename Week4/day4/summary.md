# Week 4  Day 4: Model Tuning, Regularization & Reproducible Pipelines

## Objective

The objective of this experiment was to improve the supervised learning models developed in previous stages by performing systematic hyperparameter tuning, analyzing model complexity, calibrating prediction probabilities, selecting an appropriate classification threshold, and producing a fully reproducible machine learning pipeline.

The primary optimization metric throughout the tuning process was **Precision**, since the business objective focuses on minimizing false positive predictions while maintaining acceptable overall performance.

---

# 1. Reproducible Machine Learning Pipeline

All experiments were implemented using a fully reproducible Scikit-learn Pipeline that combines:

- Feature Engineering (FunctionTransformer)
- Data Preprocessing
  - Numeric Features
    - Median Imputation
    - Standard Scaling
  - Categorical Features
    - Most Frequent Imputation
    - One-Hot Encoding
- Machine Learning Classifier

Randomness was controlled by assigning `random_state` wherever applicable to ensure consistent experimental results.

---

# 2. Hyperparameter Search

Three candidate models from the previous experiment were optimized using **RandomizedSearchCV** with **Stratified 5-Fold Cross Validation**.

The search optimized **Precision** as the primary evaluation metric while using `n_jobs=-1` for parallel execution.

## Tuned Models

### Logistic Regression

Parameters searched:

- penalty
- C (inverse regularization strength)

Best Parameters

- penalty = l1
- C = 0.001

Best Cross-Validation Precision

**0.7704**

---

### Random Forest

Parameters searched:

- n_estimators
- max_depth
- min_samples_leaf
- max_features

Best Parameters

- n_estimators = 200
- max_depth = 10
- min_samples_leaf = 4
- max_features = log2

Best Cross-Validation Precision

**0.8065**

---

### HistGradientBoosting

Parameters searched:

- learning_rate
- max_iter
- max_depth
- l2_regularization

Best Parameters

- learning_rate = 0.01
- max_iter = 100
- max_depth = 3
- l2_regularization = 0.0

Best Cross-Validation Precision

**0.9710**

HistGradientBoosting achieved the highest cross-validation Precision (0.9710), outperforming Random Forest (0.8065) and Logistic Regression (0.7704). Therefore, it was selected as the final candidate for probability calibration and evaluation on the untouched hold-out test set.

---

# 3. Learning Curve and Model Diagnostics

Learning curves were generated to analyze training and validation performance across different training sizes.

The HistGradientBoosting model showed that:

- Training and validation precision increased as more training data became available.
- The gap between training and validation curves remained relatively small.
- No significant signs of severe overfitting were observed.
- Additional training data may further improve model generalization.

---

## Regularization Analysis

For Logistic Regression, different values of **C** were evaluated.

Observations:

- Very small values of **C** produced stronger regularization.
- Larger values slightly increased training precision but did not improve validation precision.
- Strong regularization reduced model complexity while maintaining stable validation performance.

---

## Tree Complexity Analysis

Random Forest complexity was analyzed using different values of **max_depth**.

Observations:

- Increasing tree depth improved training precision.
- Validation precision decreased for deeper trees.
- This indicates mild overfitting when tree depth becomes too large.
- A depth of **10** provided the best balance between bias and variance.

---

# 4. Probability Calibration

Probability calibration was evaluated using both the Calibration Curve and the Brier Score.

## Brier Score

Before Calibration

**0.1190**

After Calibration

**0.1050**

The lower Brier Score after calibration indicates that the predicted probabilities became better aligned with the observed outcomes, improving probability reliability.

---

# 5. Threshold Selection

Different classification thresholds were evaluated to understand the trade-off between Precision, Recall, and F1-score.

| Threshold | Precision | Recall | F1 |
|-----------|-----------|---------|---------|
|0.30|0.5883|0.7720|0.6678|
|0.40|0.6566|0.6950|0.6753|
|0.50|0.7634|0.5466|0.6371|
|0.60|0.7925|0.5128|0.6227|
|0.70|0.8218|0.4773|0.6039|

As expected:

- Increasing the threshold consistently improved Precision.
- Recall decreased because fewer positive predictions were made.
- Since the business objective prioritizes minimizing false positives, **0.70** was selected as the final operating threshold.

---

# 6. Final Hold-Out Test Performance

The tuned and calibrated HistGradientBoosting pipeline was evaluated on the untouched hold-out test set.

| Metric | Score |
|---------|--------|
|Accuracy|0.8501|
|Precision|0.8218|
|Recall|0.4773|
|F1 Score|0.6039|
|ROC AUC|0.8929|
|PR AUC|0.7568|

These results demonstrate that the final pipeline achieves high precision while maintaining competitive overall predictive performance.

---

# 7. Saved Model

The complete machine learning pipeline, including:

- Feature Engineering
- Preprocessing
- Tuned HistGradientBoosting Classifier

was saved using **Joblib**, allowing the exact pipeline to be reused without rebuilding preprocessing steps.

Example inference:

```python
import joblib

model = joblib.load("final_pipeline.joblib")

prediction = model.predict(new_data)
probability = model.predict_proba(new_data)
```

---

# Conclusion

Hyperparameter tuning significantly improved the candidate models, with HistGradientBoosting delivering the strongest cross-validation performance. Learning curve analysis indicated good generalization without severe overfitting, while calibration reduced the Brier Score from **0.1190** to **0.1050**, producing more reliable probability estimates.

Threshold analysis showed the expected trade-off between Precision and Recall, and a threshold of **0.70** was selected because it maximized Precision, which aligns with the project's business objective of minimizing false positives.

Overall, the final tuned, calibrated, and reproducible pipeline provides a robust solution that is suitable for future deployment and further evaluation in production environments.