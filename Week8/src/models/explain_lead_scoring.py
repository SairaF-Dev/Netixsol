"""
explain_lead_scoring.py
-----------------------
Explainability and algorithmic fairness engine for lead scoring classification.

Implements:
1. TreeSHAP Global Feature Attribution & Summary Plot
2. TreeSHAP Local Instance Explanation & Waterfall Plot
3. Plain-Language UrduLish Explanation Generator (Domain translation for sales agents)
4. Fairness & Descriptive Subgroup Disparity Audit across Sources, Cities, and Budgets
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)


def compute_shap_explanations(
    model: Any,
    X_sample: np.ndarray,
    feature_names: List[str],
) -> Tuple[shap.Explainer, Any]:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_sample)
    return explainer, shap_values


def generate_shap_plots(
    explainer: shap.Explainer,
    shap_values: Any,
    X_sample: np.ndarray,
    feature_names: List[str],
    sample_index: int = 0,
    output_dir: Path = Path("reports/figures/day3"),
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_plots = []

    fig, ax = plt.subplots(figsize=(9, 7))
    plt.sca(ax)
    vals = shap_values.values
    if len(vals.shape) == 3 and vals.shape[2] == 2:
        vals = vals[:, :, 1]
    shap.summary_plot(vals, X_sample, feature_names=feature_names, show=False, max_display=12)
    plt.title("SHAP Global Feature Importance (Lead Scoring)", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    p1 = output_dir / "fig_d3_shap_summary.png"
    plt.savefig(p1, dpi=300, bbox_inches="tight")
    plt.close()
    saved_plots.append(p1)

    fig, ax = plt.subplots(figsize=(9, 6))
    plt.sca(ax)
    single_val = shap_values[sample_index]
    if len(single_val.shape) == 2 and single_val.shape[1] == 2:
        single_val = single_val[:, 1]
    shap.plots.waterfall(single_val, max_display=10, show=False)
    plt.title(f"SHAP Local Explanation (Lead #{sample_index})", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    p2 = output_dir / "fig_d3_shap_waterfall.png"
    plt.savefig(p2, dpi=300, bbox_inches="tight")
    plt.close()
    saved_plots.append(p2)

    return saved_plots


def generate_urdulish_explanation(
    lead_data: Dict[str, Any],
    top_positive_factors: List[str],
    top_negative_factors: List[str],
    predicted_probability: float,
    tier: str,
) -> str:
    prob_pct = predicted_probability * 100.0

    if tier == "Hot":
        if top_positive_factors:
            reasons_text = ", ".join(top_positive_factors[:3])
        else:
            reasons_text = "client bohot active hai"
        explanation = (
            f"Yeh lead Hot hai (Probability: {prob_pct:.1f}%, Action: Call within 1 hour) kyun ke {reasons_text}. "
            "Client conversion ke bohot qareeb hai."
        )
        return explanation
    elif tier == "Warm":
        if top_positive_factors:
            pos_part = ", ".join(top_positive_factors[:2])
        else:
            pos_part = "kuch dilchaspi hai"
        if top_negative_factors:
            neg_part = ", ".join(top_negative_factors[:1])
        else:
            neg_part = "kuch sawalaat hain"
        explanation = (
            f"Yeh lead Warm hai (Probability: {prob_pct:.1f}%, Action: Call within 24 hours) kyun ke {pos_part}, "
            f"lekin {neg_part}. Agent follow-up se deal close ho sakti hai."
        )
        return explanation
    else:
        if top_negative_factors:
            reasons_text = ", ".join(top_negative_factors[:3])
        else:
            reasons_text = "engagement bohot kam hai"
        explanation = (
            f"Yeh lead Cold hai (Probability: {prob_pct:.1f}%, Action: Automated Nurture) kyun ke {reasons_text}. "
            "Abhi direct call karne ka faida kam hai."
        )
        return explanation


def translate_feature_to_urdulish(feature_name: str, feature_value: Any) -> str:
    fn = feature_name.lower()
    if "visit_booked" in fn:
        if float(feature_value) >= 0.5:
            return "visit already book hai"
        return "site visit schedule nahi hua"
    elif "number_of_calls" in fn or "call" in fn:
        cnt = int(feature_value)
        if cnt > 0:
            return f"client ne {cnt} dafa call ki"
        return "abhi tak koi phone call nahi hui"
    elif "budget_match_ratio" in fn or "budget" in fn:
        if float(feature_value) >= 0.9:
            return "budget market price se match karta hai"
        return "budget thora kam hai"
    elif "response_time" in fn:
        if float(feature_value) <= 30:
            return "response time bohot fast tha"
        return "response time delay hua tha"
    elif "days_since_first_contact" in fn:
        return f"pehle rabte ko {int(feature_value)} din guzar chuke hain"
    elif "engagement_score" in fn:
        return f"engagement score ({float(feature_value):.1f}) acha hai"
    elif "whatsapp" in fn:
        return "inquiry WhatsApp ke zariye aayi hai"
    return f"{feature_name} ka asar hai"


def audit_algorithmic_bias(
    df_test: pd.DataFrame,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, pd.DataFrame]:
    df_audit = df_test.copy()
    df_audit["y_true"] = y_true
    df_audit["y_prob"] = y_prob
    df_audit["y_pred"] = (y_prob >= threshold).astype(int)

    median_budget = df_audit["budget_pkr"].median()
    df_audit["budget_segment"] = np.where(
        df_audit["budget_pkr"] < median_budget,
        f"Lower Budget (<{median_budget / 1_000_000:.1f}M)",
        f"Upper Budget (>={median_budget / 1_000_000:.1f}M)",
    )

    results = {}
    audit_columns = ["lead_source", "preferred_city", "budget_segment"]

    for group_col in audit_columns:
        if group_col not in df_audit.columns:
            continue
        records = []
        for val, grp in df_audit.groupby(group_col):
            cnt = len(grp)
            if cnt < 10:
                continue
            act_rate = grp["y_true"].mean() * 100.0
            pred_rate = grp["y_pred"].mean() * 100.0
            mean_score = grp["y_prob"].mean() * 100.0
            records.append({
                group_col: str(val),
                "Sample_Count": int(cnt),
                "Actual_Conversion_Pct": round(act_rate, 2),
                "Predicted_Positive_Rate_Pct": round(pred_rate, 2),
                "Mean_Predicted_Score_Pct": round(mean_score, 2),
                "Disparity_Ratio": round(pred_rate / max(act_rate, 0.001), 2),
            })
        results[group_col] = pd.DataFrame(records).sort_values("Sample_Count", ascending=False)

    return results
