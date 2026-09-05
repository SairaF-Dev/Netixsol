"""Train and save the offline LogisticRegression candidate model."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.build_dataset import build_dataset, fetch_interaction_rows
from ml.evaluate_model import evaluate_classifier
from ml.model_types import InsufficientTrainingData, TrainingDataset


def grouped_split(dataset: TrainingDataset, *, random_state: int = 42):
    if len(set(dataset.groups.tolist())) < 2:
        raise InsufficientTrainingData("grouped split requires at least two customers")
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=random_state)
    train_indices, test_indices = next(
        splitter.split(dataset.features, dataset.targets, dataset.groups)
    )
    if set(dataset.targets[train_indices].tolist()) != {0, 1}:
        raise InsufficientTrainingData("training split does not contain both classes")
    if set(dataset.targets[test_indices].tolist()) != {0, 1}:
        raise InsufficientTrainingData("test split does not contain both classes")
    return train_indices, test_indices


def train_candidate(
    dataset: TrainingDataset,
    artifact_path: str | Path,
    *,
    random_state: int = 42,
    synthetic: bool = False,
    data_source: str = "customer_interactions",
) -> dict[str, Any]:
    train_indices, test_indices = grouped_split(dataset, random_state=random_state)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=random_state
        )),
    ])
    model.fit(dataset.features[train_indices], dataset.targets[train_indices])
    metrics = evaluate_classifier(
        model, dataset.features[test_indices], dataset.targets[test_indices]
    )
    classifier = model.named_steps["classifier"]
    coefficients = {
        name: float(value)
        for name, value in zip(dataset.feature_names, classifier.coef_[0])
    }
    artifact = {
        "model": model,
        "model_version": "property_ranker_v1",
        "synthetic": synthetic,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": int(len(train_indices)),
        "test_rows": int(len(test_indices)),
        "positive_count": dataset.positive_count,
        "negative_count": dataset.negative_count,
        "unique_customers": int(len(set(dataset.groups.tolist()))),
        "feature_names": list(dataset.feature_names),
        "metrics": metrics,
        "coefficients": coefficients,
        "training_data_source": data_source,
        "data_source": data_source,
        "label_policy": "rejected=0; liked/shortlisted=1; shown/viewed/appointment events excluded",
        "outcome_precedence": "rejected > liked > shortlisted",
        "split_strategy": "GroupShuffleSplit by customer_id, random_state=42",
    }
    destination = Path(artifact_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, destination)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Sara's offline property preference model")
    parser.add_argument("--artifact", default="ml/models/property_ranker_v1.joblib")
    parser.add_argument("--input", type=Path, help="Development JSON fixture; never writes to PostgreSQL")
    args = parser.parse_args()
    if args.input and "dev" not in str(args.artifact).casefold():
        print("TRAINING NOT RUN: --input requires a development artifact path containing 'dev'")
        return 2
    try:
        if args.input:
            rows = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not all(row.get("synthetic") is True for row in rows):
                raise ValueError("input fixture must be a list of rows marked synthetic=true")
            dataset = build_dataset(rows)
            artifact = train_candidate(
                dataset,
                args.artifact,
                synthetic=True,
                data_source="synthetic_development",
            )
        else:
            dataset = build_dataset(fetch_interaction_rows())
            artifact = train_candidate(dataset, args.artifact)
    except (InsufficientTrainingData, ValueError) as exc:
        print(f"TRAINING NOT RUN: {exc}")
        return 2
    print(f"MODEL SAVED: {args.artifact}")
    print(f"SYNTHETIC: {artifact['synthetic']}")
    print(f"DATASET rows={len(dataset.rows)} positives={dataset.positive_count} negatives={dataset.negative_count}")
    print(f"METRICS: {artifact['metrics']}")
    print(f"COEFFICIENTS: {artifact['coefficients']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())