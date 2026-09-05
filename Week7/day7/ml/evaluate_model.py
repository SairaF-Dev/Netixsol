"""Evaluation helpers for the offline candidate model."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(model: Any, features: np.ndarray, targets: np.ndarray) -> dict[str, Any]:
    predictions = model.predict(features)
    result: dict[str, Any] = {
        "rows": int(len(targets)),
        "positive_count": int(np.sum(targets == 1)),
        "negative_count": int(np.sum(targets == 0)),
        "accuracy": float(accuracy_score(targets, predictions)),
        "precision": float(precision_score(targets, predictions, zero_division=0)),
        "recall": float(recall_score(targets, predictions, zero_division=0)),
        "f1": float(f1_score(targets, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(targets, predictions, labels=[0, 1]).tolist(),
    }
    result["roc_auc"] = (
        float(roc_auc_score(targets, model.predict_proba(features)[:, 1]))
        if len(set(targets.tolist())) == 2
        else None
    )
    return result