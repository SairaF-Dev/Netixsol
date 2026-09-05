"""Types shared by the offline dataset and model pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


class InsufficientTrainingData(ValueError):
    """Raised when data cannot support a valid grouped binary model."""


@dataclass(frozen=True)
class TrainingDataset:
    rows: list[dict[str, Any]]
    feature_names: tuple[str, ...]
    features: np.ndarray
    targets: np.ndarray
    groups: np.ndarray

    @property
    def positive_count(self) -> int:
        return int(np.sum(self.targets == 1))

    @property
    def negative_count(self) -> int:
        return int(np.sum(self.targets == 0))