"""Validation-gated candidate training, model promotion, and rollback."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from src.features.property_features import HuberPropertyPreprocessor
from src.mlops.monitoring import DATA_DIR, MODELS_DIR, evaluate_mape
from src.models.train_huber import RENT_HUBER_PARAMS, SALE_HUBER_PARAMS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROLLBACK_DIR = MODELS_DIR / "rollback"
REPORT_DIR = PROJECT_ROOT / "reports" / "day5"
logger = logging.getLogger(__name__)


def _artifact_names(purpose: str) -> tuple[str, str]:
    value = purpose.casefold()
    if value not in {"sale", "for sale", "rent", "for rent"}:
        raise ValueError("purpose must be sale or rent.")
    prefix = "sale" if value in {"sale", "for sale"} else "rent"
    return f"{prefix}_model_huber.joblib", f"{prefix}_preprocessor_huber.joblib"


def promote_artifacts(
    candidate_model: Path,
    candidate_preprocessor: Path,
    active_model: Path,
    active_preprocessor: Path,
    rollback_root: Path = ROLLBACK_DIR,
) -> Path:
    """Back up the active pair, then atomically replace each artifact with rollback on error."""
    for path in (candidate_model, candidate_preprocessor, active_model, active_preprocessor):
        if not path.is_file():
            raise FileNotFoundError(f"Model promotion artifact is missing: {path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = rollback_root / stamp
    backup.mkdir(parents=True, exist_ok=False)
    active_paths = [active_model, active_preprocessor]
    candidate_paths = [candidate_model, candidate_preprocessor]
    for path in active_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Active model artifact is missing: {path}")
        shutil.copy2(path, backup / path.name)

    replaced: list[Path] = []
    try:
        for candidate, active in zip(candidate_paths, active_paths):
            staged = active.with_name(f".{active.name}.{stamp}.staged")
            shutil.copy2(candidate, staged)
            staged.replace(active)
            replaced.append(active)
    except Exception:
        for active in replaced:
            shutil.copy2(backup / active.name, active)
        for active in active_paths:
            staged = active.with_name(f".{active.name}.{stamp}.staged")
            if staged.exists():
                staged.unlink()
        raise
    return backup


def rollback_artifacts(backup_dir: Path, purpose: str, models_dir: Path = MODELS_DIR) -> None:
    names = _artifact_names(purpose)
    model_dest, prep_dest = (models_dir / name for name in names)
    source_paths = [backup_dir / name for name in names]
    missing = [str(path) for path in source_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Rollback backup is incomplete: {', '.join(missing)}")
    missing_active = [str(path) for path in (model_dest, prep_dest) if not path.is_file()]
    if missing_active:
        raise FileNotFoundError(f"Active model pair is incomplete: {', '.join(missing_active)}")

    staging = []
    old_files: dict[Path, Path] = {}
    try:
        for destination in (model_dest, prep_dest):
            backup = destination.with_name(f".{destination.name}.pre-rollback")
            if destination.exists():
                shutil.copy2(destination, backup)
                old_files[destination] = backup
        for source, destination in zip(source_paths, (model_dest, prep_dest)):
            staged = destination.with_name(f".{destination.name}.rollback")
            shutil.copy2(source, staged)
            staging.append((staged, destination))
        for staged, destination in staging:
            staged.replace(destination)
    except Exception:
        for staged, destination in staging:
            if staged.exists():
                staged.unlink()
            old = old_files.get(destination)
            if old is not None and old.exists():
                old.replace(destination)
        raise
    finally:
        for old in old_files.values():
            if old.exists():
                old.unlink()


def train_candidate(purpose: str, train_path: Path, validation_path: Path) -> dict[str, Any]:
    """Fit a candidate on the train split and compare with the active model on validation."""
    _artifact_names(purpose)
    prefix = "sale" if purpose.casefold() in {"sale", "for sale"} else "rent"
    train = pd.read_csv(train_path, low_memory=False)
    validation = pd.read_csv(validation_path, low_memory=False)
    if train.empty or validation.empty or "price" not in train or "price" not in validation:
        raise ValueError("Training and validation CSVs must be non-empty and contain a price column.")

    preprocessor = HuberPropertyPreprocessor(random_state=42)
    x_train = preprocessor.fit_transform(train)
    x_validation = preprocessor.transform(validation)
    params = SALE_HUBER_PARAMS if prefix == "sale" else RENT_HUBER_PARAMS
    candidate = lgb.LGBMRegressor(**params)
    candidate.fit(x_train, np.log1p(train["price"].to_numpy(dtype=float)))

    active_model_path = MODELS_DIR / f"{prefix}_model_huber.joblib"
    active_prep_path = MODELS_DIR / f"{prefix}_preprocessor_huber.joblib"
    active_model = joblib.load(active_model_path)
    active_preprocessor = joblib.load(active_prep_path)
    incumbent_mape = evaluate_mape(active_model, active_preprocessor, validation)
    candidate_mape = evaluate_mape(candidate, preprocessor, validation)
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "For Sale" if prefix == "sale" else "For Rent",
        "training_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "incumbent_validation_mape_percent": round(incumbent_mape, 4),
        "candidate_validation_mape_percent": round(candidate_mape, 4),
        "promoted": False,
        "rollback_backup": None,
        "decision": "candidate did not improve validation MAPE",
    }

    if candidate_mape < incumbent_mape:
        candidate_dir = MODELS_DIR / "candidates"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_model_path = candidate_dir / f"{prefix}_model_candidate.joblib"
        candidate_prep_path = candidate_dir / f"{prefix}_preprocessor_candidate.joblib"
        joblib.dump(candidate, candidate_model_path)
        joblib.dump(preprocessor, candidate_prep_path)
        backup = promote_artifacts(
            candidate_model_path,
            candidate_prep_path,
            active_model_path,
            active_prep_path,
        )
        report.update({
            "promoted": True,
            "rollback_backup": str(backup),
            "decision": "candidate improved validation MAPE",
        })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"retraining_{prefix}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", choices=("sale", "rent"), required=True)
    parser.add_argument("--train", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--rollback", type=Path, help="Restore the specified saved rollback directory.")
    args = parser.parse_args()
    prefix = "sale" if args.purpose == "sale" else "rent"
    if args.rollback:
        rollback_artifacts(args.rollback, args.purpose)
        print(f"Restored {prefix} model and preprocessor from {args.rollback}")
        return 0

    report = train_candidate(
        args.purpose,
        args.train or DATA_DIR / f"prop_{prefix}_train.csv",
        args.validation or DATA_DIR / f"prop_{prefix}_val.csv",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    raise SystemExit(main())
