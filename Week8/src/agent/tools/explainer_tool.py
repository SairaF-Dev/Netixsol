"""
explainer_tool.py
-----------------
LangGraph tool for Model Interpretability and Explanations.
Provides:
- Lead Scoring: TreeSHAP local feature attribution and UrduLish conversion rationale.
- Property Valuation: Explicitly marks price TreeSHAP as pending Task 2/future milestone;
  never fabricates synthetic price explanations or artificial feature values.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import shap

from src.agent.tools.lead_tool import get_lead_scorer
from src.features.lead_features import add_lead_features

logger = logging.getLogger(__name__)

# Shared cached TreeSHAP explainer for lead scoring
_lead_tree_explainer: Optional[shap.TreeExplainer] = None


def get_lead_tree_explainer() -> Optional[shap.TreeExplainer]:
    global _lead_tree_explainer
    if _lead_tree_explainer is None:
        try:
            scorer = get_lead_scorer()
            _lead_tree_explainer = shap.TreeExplainer(scorer.model)
            logger.info("Initialized TreeExplainer for Lead Scorer.")
        except Exception as e:
            logger.warning("Could not initialize TreeExplainer: %s", e)
            _lead_tree_explainer = None
    return _lead_tree_explainer


def explainer_tool(
    target: str = "lead",
    lead_payload: Optional[Dict[str, Any]] = None,
    property_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate model explanations.

    Parameters:
    - target: 'lead' or 'price'
    - lead_payload: Dictionary of lead fields if target == 'lead'
    - property_payload: Dictionary of property fields if target == 'price'

    Returns structured explanation.
    """
    target_clean = target.strip().lower()

    if target_clean == "price":
        # Strictly honest: TreeSHAP price explainer contract
        return {
            "target": "price",
            "explanation_available": False,
            "status": "contract_active_explainer_pending_task2",
            "message": "Property valuation TreeSHAP feature attribution module is currently scheduled for Day 4 Task 2. Model point prediction and quantile range are operational.",
            "top_features": [],
            "urdulish_summary": "Tafseeli feature breakdown model ke aglay marhalay mein dastiyab hoga. Abhi fair price point aur range operational hain.",
        }

    # Otherwise, explain lead
    if not lead_payload:
        return {
            "target": "lead",
            "explanation_available": False,
            "error": "No lead_payload provided for lead explanation.",
        }

    full_payload = {
        "lead_source": lead_payload.get("lead_source", "Call"),
        "preferred_city": lead_payload.get("preferred_city", "Lahore"),
        "preferred_location": lead_payload.get("preferred_location", "Unknown"),
        "property_type": lead_payload.get("property_type", "House"),
        "purpose": lead_payload.get("purpose", "Buy"),
        "budget_pkr": float(lead_payload.get("budget_pkr", 20_000_000.0)),
        "number_of_calls": int(lead_payload.get("number_of_calls", 2)),
        "total_call_duration_min": float(lead_payload.get("total_call_duration_min", 10.0)),
        "response_time_minutes": float(lead_payload.get("response_time_minutes", 15.0)),
        "visit_booked": int(lead_payload.get("visit_booked", 0)),
        "days_since_first_contact": int(lead_payload.get("days_since_first_contact", 2)),
        "follow_up_count": int(lead_payload.get("follow_up_count", 1)),
        "budget_match_ratio": float(lead_payload.get("budget_match_ratio", 1.0)),
        "objection_raised": str(lead_payload.get("objection_raised", "None")),
    }

    try:
        scorer = get_lead_scorer()
        score_res = scorer.score_lead(full_payload)

        df_single = pd.DataFrame([full_payload])
        df_feat = add_lead_features(df_single)
        if "location_frequency" not in df_feat.columns:
            df_feat["location_frequency"] = 0.05
        X_trans = scorer.pipeline.transform(df_feat)

        top_pos: List[Dict[str, Any]] = []
        top_neg: List[Dict[str, Any]] = []

        explainer = get_lead_tree_explainer()
        if explainer is not None:
            shap_vals = explainer(X_trans)
            vals = shap_vals.values
            if len(vals.shape) == 3 and vals.shape[2] == 2:
                class_vals = vals[0, :, 1]
            elif len(vals.shape) == 2:
                class_vals = vals[0, :]
            else:
                class_vals = vals.flatten()

            feat_names = scorer.pipeline.get_feature_names_out()
            feature_impacts = [
                {"feature": str(name), "shap_value": round(float(val), 4)}
                for name, val in zip(feat_names, class_vals)
            ]
            top_pos = [f for f in sorted(feature_impacts, key=lambda x: x["shap_value"], reverse=True) if f["shap_value"] > 0][:5]
            top_neg = [f for f in sorted(feature_impacts, key=lambda x: x["shap_value"]) if f["shap_value"] < 0][:5]

        return {
            "target": "lead",
            "explanation_available": True,
            "conversion_probability": score_res["conversion_probability"],
            "tier": score_res["tier"],
            "top_positive_features": top_pos,
            "top_negative_features": top_neg,
            "urdulish_summary": score_res["urdulish_explanation"],
            "customer_persona": score_res["customer_persona"],
        }
    except Exception as e:
        logger.error("Explainer tool error: %s", e, exc_info=True)
        return {
            "target": "lead",
            "explanation_available": False,
            "error": f"Failed to compute lead explanations: {str(e)}",
        }
