"""Configurable training-readiness checks and non-PII data summaries."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ml.build_dataset import NEGATIVE_ACTIONS, POSITIVE_ACTIONS
from ml.model_types import TrainingDataset


def readiness(dataset: TrainingDataset, *, min_rows: int = 50, min_customers: int = 10) -> dict[str, Any]:
    customers = len(set(dataset.groups.tolist()))
    checks = {
        "minimum_rows": len(dataset.rows) >= min_rows,
        "minimum_customers": customers >= min_customers,
        "both_classes": dataset.positive_count > 0 and dataset.negative_count > 0,
    }
    return {
        "training_ready": all(checks.values()),
        "rows": len(dataset.rows),
        "customers": customers,
        "positive_count": dataset.positive_count,
        "negative_count": dataset.negative_count,
        "checks": checks,
    }


def summarize_rows(rows: Iterable[dict[str, Any]], *, synthetic: bool = False) -> dict[str, Any]:
    rows = list(rows)
    outcomes = [row for row in rows if row.get("action") in POSITIVE_ACTIONS | NEGATIVE_ACTIONS]
    positives = sum(row.get("action") in POSITIVE_ACTIONS for row in outcomes)
    negatives = sum(row.get("action") in NEGATIVE_ACTIONS for row in outcomes)
    return {
        "synthetic": synthetic,
        "interactions": len(rows),
        "customers": len({str(row.get("customer_id")) for row in rows}),
        "unique_properties": len({str(row.get("property_id")) for row in rows}),
        "positives": positives,
        "negatives": negatives,
        "class_balance": {"positive": positives, "negative": negatives},
        "snapshot_coverage": sum(bool(row.get("preference_snapshot") and row.get("property_snapshot")) for row in rows),
    }