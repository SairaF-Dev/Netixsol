"""
Inference Script
Adult Census Income Prediction

Loads the trained model, validates inputs,
predicts income class, and explains predictions
using SHAP.
"""

import joblib
import pandas as pd
import shap

# -------------------------------------------------------
# Load Model
# -------------------------------------------------------

model = joblib.load("final_income_prediction_model.joblib")

# -------------------------------------------------------
# SHAP Explainer
# -------------------------------------------------------

explainer = shap.Explainer(
    model.named_steps["classifier"]
)

# -------------------------------------------------------
# Required Columns
# -------------------------------------------------------

required_columns = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country"
]

# -------------------------------------------------------
# Input Validation
# -------------------------------------------------------

def validate_input(df):

    missing = set(required_columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    return True


# -------------------------------------------------------
# Prediction Function
# -------------------------------------------------------

def predict_income(input_data, threshold=0.70):

    if isinstance(input_data, dict):
        input_data = pd.DataFrame([input_data])

    validate_input(input_data)

    probability = model.predict_proba(input_data)[:, 1][0]

    prediction = int(probability >= threshold)

    # Feature engineering
    engineered = (
        model.named_steps["preprocessor"]
        .named_steps["feature_engineering"]
        .transform(input_data)
    )

    # Preprocessing
    processed = (
        model.named_steps["preprocessor"]
        .named_steps["column_transform"]
        .transform(engineered)
    )

    # SHAP values
    sv = explainer(processed)

    feature_names = (
        model.named_steps["preprocessor"]
        .named_steps["column_transform"]
        .get_feature_names_out()
    )

    contributions = pd.DataFrame({
        "Feature": feature_names,
        "Contribution": sv.values[0]
    })

    top_features = (
        contributions
        .assign(abs_value=contributions["Contribution"].abs())
        .sort_values("abs_value", ascending=False)
        .head(3)
        .drop(columns="abs_value")
    )

    return {
        "Probability": round(float(probability), 4),
        "Predicted Class": prediction,
        "Top Features": top_features
    }


# -------------------------------------------------------
# Basic Tests
# -------------------------------------------------------

if __name__ == "__main__":

    # Example input
    sample = pd.DataFrame([{
        "age": 39,
        "workclass": "State-gov",
        "fnlwgt": 77516,
        "education": "Bachelors",
        "education-num": 13,
        "marital-status": "Never-married",
        "occupation": "Adm-clerical",
        "relationship": "Not-in-family",
        "race": "White",
        "sex": "Male",
        "capital-gain": 2174,
        "capital-loss": 0,
        "hours-per-week": 40,
        "native-country": "United-States"
    }])

    print("=" * 50)
    print("Prediction Test")
    print("=" * 50)

    result = predict_income(sample)

    print(result)

    print("\n")

    print("=" * 50)
    print("Missing Column Test")
    print("=" * 50)

    try:

        bad_sample = sample.drop(columns=["age"])

        predict_income(bad_sample)

    except ValueError as e:

        print(e)

    print("\n")

    print("=" * 50)
    print("Unseen Category Test")
    print("=" * 50)

    unseen = sample.copy()

    unseen["workclass"] = "MyNewCompany"

    print(predict_income(unseen))