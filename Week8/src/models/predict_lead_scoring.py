"""
predict_lead_scoring.py
-----------------------
Production inference engine for AI Lead Scoring & Customer Persona Classification.

Features:
1. Loads preprocessing pipeline, trained classifier, and persona clustering models.
2. Accepts raw lead dictionary or pandas DataFrame.
3. Computes conversion probability (0.0 to 1.0).
4. Assigns operational tier (Hot / Warm / Cold) and SLA action.
5. Predicts commercial customer persona (e.g. High-Net-Worth Investor).
6. Produces natural UrduLish explanation matching curriculum specifications (<50ms latency).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from src.features.lead_features import add_lead_features
from src.models.explain_lead_scoring import (
    generate_urdulish_explanation,
    translate_feature_to_urdulish,
)

logger = logging.getLogger(__name__)

PERSONA_NAMES = {
    0: "First-Time Urban Homebuyer",
    1: "High-Net-Worth Investor",
    2: "Budget Renter / Short-Horizon Inquirer",
}


class LeadScorer:
    """Production lead scoring and customer persona prediction service."""

    def __init__(self, models_dir: Path = Path("models")) -> None:
        self.models_dir = Path(models_dir)
        self.pipeline = None
        self.model = None
        self.kmeans = None
        self._is_loaded = False

    def load(self) -> "LeadScorer":
        t0 = time.time()
        self.pipeline = joblib.load(self.models_dir / "lead_preprocessor.joblib")
        self.model = joblib.load(self.models_dir / "lead_scoring_model.joblib")

        kmeans_path = self.models_dir / "lead_persona_kmeans.joblib"
        if kmeans_path.exists():
            self.kmeans = joblib.load(kmeans_path)

        self._is_loaded = True
        logger.info("LeadScorer successfully loaded in %.3fs", time.time() - t0)
        return self

    def score_lead(
        self,
        lead_input: Union[Dict[str, Any], pd.DataFrame],
    ) -> Dict[str, Any]:
        if not self._is_loaded:
            self.load()

        t0 = time.time()

        if isinstance(lead_input, dict):
            df = pd.DataFrame([lead_input])
        else:
            df = lead_input.copy()

        df_feat = add_lead_features(df)
        if "location_frequency" not in df_feat.columns:
            df_feat["location_frequency"] = 0.05
        X_trans = self.pipeline.transform(df_feat)
        prob = float(self.model.predict_proba(X_trans)[0, 1])

        if prob >= 0.65:
            tier = "Hot"
            sla_action = "Call within 1 hour"
            priority_rank = 1
        elif prob >= 0.35:
            tier = "Warm"
            sla_action = "Call within 24 hours"
            priority_rank = 2
        else:
            tier = "Cold"
            sla_action = "Automated email/SMS nurture campaign"
            priority_rank = 3

        persona_id = 0
        persona_label = "Standard Inquirer"
        if self.kmeans is not None:
            try:
                persona_id = int(self.kmeans.predict(X_trans)[0])
                persona_label = PERSONA_NAMES.get(persona_id, f"Persona #{persona_id}")
            except Exception as e:
                logger.warning("Persona prediction note: %s", e)

        pos_factors = []
        neg_factors = []

        visit = df.get("visit_booked", [0])[0] if "visit_booked" in df else 0
        calls = df.get("number_of_calls", [0])[0] if "number_of_calls" in df else 0
        days = df.get("days_since_first_contact", [0])[0] if "days_since_first_contact" in df else 0
        resp = df.get("response_time_minutes", [60])[0] if "response_time_minutes" in df else 60
        match_ratio = df.get("budget_match_ratio", [1.0])[0] if "budget_match_ratio" in df else 1.0

        if visit == 1:
            pos_factors.append("visit already book hai")
        else:
            neg_factors.append("site visit schedule nahi hua")

        if calls >= 2:
            pos_factors.append(f"client ne {int(calls)} dafa call ki")
        elif calls == 0:
            neg_factors.append("client se abhi tak koi phone call nahi hui")

        if match_ratio >= 0.9:
            pos_factors.append("budget market price se match karta hai")
        elif match_ratio < 0.7:
            neg_factors.append("budget market price se kam hai")

        if resp <= 30:
            pos_factors.append("response time bohot fast tha")
        elif resp > 180:
            neg_factors.append("response time delay hua tha")

        if days > 45:
            neg_factors.append(f"pehle rabte ko {int(days)} din guzar chuke hain")

        urdulish_summary = generate_urdulish_explanation(
            lead_data=df.iloc[0].to_dict(),
            top_positive_factors=pos_factors,
            top_negative_factors=neg_factors,
            predicted_probability=prob,
            tier=tier,
        )

        latency_ms = (time.time() - t0) * 1000.0

        return {
            "conversion_probability": round(prob, 4),
            "lead_score_pct": round(prob * 100.0, 1),
            "tier": tier,
            "priority_rank": priority_rank,
            "recommended_sla_action": sla_action,
            "customer_persona": persona_label,
            "persona_cluster_id": persona_id,
            "urdulish_explanation": urdulish_summary,
            "inference_latency_ms": round(latency_ms, 2),
            "model_version": "lgbm_optuna_v1.0",
            "training_label_provenance": "synthetic",
            "crm_validated": False,
        }
