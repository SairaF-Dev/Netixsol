"""Student-level train/test split (required for Day 2 knowledge tracing).

Every student goes WHOLLY to train or WHOLLY to test. Splitting a student's answers across
both lets a model recognise that student instead of predicting a new one, and the test score
then overstates how it does on next term's students.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ilm import config


def student_split(df: pd.DataFrame, student_col: str = "user_id", test_frac: float = 0.2,
                  seed: int = config.RANDOM_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic: the same seed always gives the same split, whatever the row order."""
    students = np.array(sorted(df[student_col].unique()))
    rng = np.random.default_rng(seed)
    test_ids = set(rng.choice(students, size=round(len(students) * test_frac), replace=False))
    is_test = df[student_col].isin(test_ids)
    return df[~is_test], df[is_test]
