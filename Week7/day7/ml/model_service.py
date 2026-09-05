"""Safe, mode-gated runtime scoring for the development model."""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ml import FEATURE_NAMES
from ml.feature_engineering import engineer_features

logger = logging.getLogger("sara.ml")
VALID_MODES = frozenset({"off", "shadow", "active_dev"})
EXPECTED_MODEL_VERSION = "property_ranker_v1"


class ModelValidationError(ValueError):
    """Raised when a model artifact cannot be used safely."""


class PropertyPreferenceModelService:
    """Load and score the synthetic development artifact only when enabled."""

    def __init__(self, artifact_path: str | Path | None = None, mode: str | None = None):
        configured_mode = (
            mode if mode is not None else os.getenv("SARA_ML_RANKING_MODE", "off")
        ).strip().casefold()
        self.mode = configured_mode if configured_mode in VALID_MODES else "off"
        self.artifact_path = Path(artifact_path or Path(__file__).with_name("models") / "dev_property_ranker_v1.joblib")
        self._artifact: dict[str, Any] | None = None
        self._load_error: str | None = None
        self.last_comparison: list[dict[str, Any]] = []

    def load_model(self) -> dict[str, Any]:
        if self._artifact is not None:
            return self._artifact
        if self._load_error:
            raise ModelValidationError(self._load_error)
        try:
            artifact = joblib.load(self.artifact_path)
            self._validate_artifact(artifact)
            self._artifact = artifact
            logger.info("Development ML model loaded: version=%s", artifact["model_version"])
            return artifact
        except Exception as exc:
            self._load_error = f"development model unavailable: {type(exc).__name__}"
            logger.warning("Development ML model load failed: %s", type(exc).__name__)
            raise ModelValidationError(self._load_error) from exc

    @staticmethod
    def _validate_artifact(artifact: Any) -> None:
        if not isinstance(artifact, dict):
            raise ModelValidationError("artifact is not a metadata dictionary")
        if artifact.get("model_version") != EXPECTED_MODEL_VERSION:
            raise ModelValidationError("unexpected model version")
        if artifact.get("synthetic") is not True:
            raise ModelValidationError("development artifact must be synthetic")
        if artifact.get("data_source") != "synthetic_development":
            raise ModelValidationError("artifact is not synthetic development data")
        if artifact.get("feature_names") != list(FEATURE_NAMES):
            raise ModelValidationError("artifact feature order does not match training")
        model = artifact.get("model")
        if not callable(getattr(model, "predict_proba", None)):
            raise ModelValidationError("artifact model has no predict_proba")

    @staticmethod
    def _model_row(profile: Any, property_data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(profile, dict):
            get = profile.get
        else:
            get = lambda key, default=None: getattr(profile, key, default)
        return {
            "preferred_city": get("city"),
            "preferred_area": get("area"),
            "budget_max": get("budget", get("budget_max")),
            "preferred_bedrooms": get("bedrooms"),
            "preferred_property_type": get("property_type"),
            "preferred_purpose": get("purpose"),
            "preferred_amenities": get("amenities_preferred", get("amenities", [])) or [],
            "city": property_data.get("city"),
            "area": property_data.get("area"),
            "price": property_data.get("price"),
            "bedrooms": property_data.get("bedrooms"),
            "property_type": property_data.get("property_type"),
            "purpose": property_data.get("purpose"),
            "property_amenities": property_data.get("amenities", []) or [],
        }

    def score_property(self, profile: Any, property_data: dict[str, Any]) -> float:
        artifact = self.load_model()
        features = engineer_features(self._model_row(profile, property_data))
        vector = np.asarray([[features[name] for name in FEATURE_NAMES]], dtype=float)
        if not np.isfinite(vector).all():
            raise ModelValidationError("model input contains NaN or infinity")
        probability = float(artifact["model"].predict_proba(vector)[:, 1][0])
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ModelValidationError("model returned an invalid probability")
        return probability

    def _score_candidates(self, profile: Any, candidates: list[dict[str, Any]]) -> list[float]:
        artifact = self.load_model()
        vectors = [
            [engineer_features(self._model_row(profile, candidate))[name] for name in FEATURE_NAMES]
            for candidate in candidates
        ]
        matrix = np.asarray(vectors, dtype=float)
        if not np.isfinite(matrix).all():
            raise ModelValidationError("model input contains NaN or infinity")
        probabilities = np.asarray(artifact["model"].predict_proba(matrix))[:, 1]
        if len(probabilities) != len(candidates) or not np.isfinite(probabilities).all():
            raise ModelValidationError("model returned invalid candidate probabilities")
        if not np.logical_and(probabilities >= 0.0, probabilities <= 1.0).all():
            raise ModelValidationError("model returned an out-of-range probability")
        return [float(probability) for probability in probabilities]

    def rank_properties(self, candidates: list[dict[str, Any]], profile: Any) -> list[dict[str, Any]]:
        """Score verified candidates; active_dev changes order, shadow does not."""
        self.last_comparison = []
        if self.mode == "off" or not candidates or profile is None:
            return candidates
        try:
            probabilities = self._score_candidates(profile, candidates)
            scored_indices = sorted(
                range(len(candidates)),
                key=lambda index: (-probabilities[index], str(candidates[index].get("property_id", ""))),
            )
            ml_positions = {candidate_index: rank for rank, candidate_index in enumerate(scored_indices, start=1)}
            self.last_comparison = [
                {
                    "property_id": candidate.get("property_id"),
                    "deterministic_rank": index + 1,
                    "ml_rank": ml_positions[index],
                    "ml_probability": probabilities[index],
                }
                for index, candidate in enumerate(candidates)
            ]
            if self.mode == "shadow":
                for comparison in self.last_comparison:
                    logger.info(
                        "ML shadow comparison property_id=%s deterministic_rank=%s ml_rank=%s ml_probability=%.6f",
                        comparison["property_id"], comparison["deterministic_rank"],
                        comparison["ml_rank"], comparison["ml_probability"],
                    )
                return candidates
            return [candidates[index] for index in scored_indices]
        except Exception as exc:
            self.last_comparison = []
            logger.warning("ML ranking fallback used: %s", type(exc).__name__)
            return candidates

    def health(self) -> dict[str, Any]:
        result = {"mode": self.mode, "artifact": str(self.artifact_path), "loaded": False, "available": False}
        if self.mode == "off":
            return result
        try:
            artifact = self.load_model()
            result.update({"loaded": True, "available": True, "model_version": artifact["model_version"], "synthetic": artifact["synthetic"]})
        except ModelValidationError as exc:
            result["error"] = str(exc)
        return result
