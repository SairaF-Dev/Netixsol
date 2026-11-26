"""Knowledge tracing: the shared protocol every model is scored with.

Task: for each answer, predict P(correct) using ONLY that student's EARLIER answers.
Split: student-level (ilm.learners.split). Test students are never seen in training.
Tuning: only on a validation split carved out of the TRAINING students. The test set is
scored once per model, at the end.
Metrics: AUC, accuracy (threshold 0.5), RMSE.

A model is any object with
    fit(train: DataFrame) -> self
    predict(df: DataFrame) -> np.ndarray      # one probability per row of df
where df has columns user_id, seq, skill, correct (rows of one student in seq order).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ilm import config
from ilm.learners.split import student_split

COLUMNS = ["user_id", "seq", "skill", "correct"]


def load_splits(df: pd.DataFrame, seed: int = config.RANDOM_SEED):
    """train / valid / test, all student-level. valid comes out of train (for tuning)."""
    df = df.sort_values(["user_id", "seq"]).reset_index(drop=True)
    train_all, test = student_split(df, "user_id", 0.2, seed)
    train, valid = student_split(train_all, "user_id", 0.2, seed + 1)
    return train, valid, test


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 0, 1)
    return {"auc": round(float(roc_auc_score(y, p)), 4),
            "accuracy": round(float(((p >= 0.5) == (y == 1)).mean()), 4),
            "rmse": round(float(np.sqrt(((y - p) ** 2).mean())), 4),
            "n": int(len(y))}


def prior_counts(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Successes and failures BEFORE each row, per group (e.g. student, or student+skill).
    The current row is excluded: that is what keeps a model blind to the answer it predicts."""
    g = df.groupby(by)["correct"]
    succ = g.cumsum() - df["correct"]
    attempts = g.cumcount()
    return pd.DataFrame({"successes": succ, "failures": attempts - succ}, index=df.index)


# ------------------------------------------------------------------ baselines ----
class GlobalMean:
    """Same probability for everyone: the training accuracy. AUC is 0.5 by construction."""
    name = "baseline: global mean"

    def fit(self, train):
        self.p = float(train["correct"].mean())
        return self

    def predict(self, df):
        return np.full(len(df), self.p)


class SkillMean:
    """Each skill's training accuracy: knows which skills are hard, nothing about the student."""
    name = "baseline: skill mean"

    def fit(self, train):
        self.p = float(train["correct"].mean())
        self.by_skill = train.groupby("skill")["correct"].mean()
        return self

    def predict(self, df):
        return df["skill"].map(self.by_skill).fillna(self.p).to_numpy()


class StudentSoFar:
    """The student's accuracy so far (all skills), pulled towards the skill mean when there
    is little history: (successes + m * skill_mean) / (attempts + m)."""
    name = "baseline: student so far"

    def __init__(self, m: float = 5.0):
        self.m = m

    def fit(self, train):
        self.skill = SkillMean().fit(train)
        return self

    def predict(self, df):
        c = prior_counts(df, ["user_id"])
        prior = self.skill.predict(df)
        attempts = c["successes"] + c["failures"]
        return ((c["successes"] + self.m * prior) / (attempts + self.m)).to_numpy()


def score(model, train, test) -> dict:
    model.fit(train)
    return {"model": model.name, **metrics(test["correct"], model.predict(test))}


def future_blind(model, df: pd.DataFrame, row: int) -> bool:
    """Flip the answer at `row` (and nothing else). A model that only uses earlier answers
    gives exactly the same predictions for that row and every row before it."""
    before = model.predict(df)
    flipped = df.copy()
    flipped.loc[flipped.index[row], "correct"] = 1 - flipped["correct"].iloc[row]
    after = model.predict(flipped)
    student = df["user_id"].iloc[row]
    same_student_upto = (df["user_id"] == student).to_numpy() & (np.arange(len(df)) <= row)
    return bool(np.allclose(before[same_student_upto], after[same_student_upto]))
