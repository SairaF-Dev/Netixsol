"""BKT: Bayesian Knowledge Tracing (Corbett & Anderson, 1995), fitted with pyBKT.

Each student is in one of two hidden states per skill: knows it / does not know it yet.
Four numbers per skill, learned from data (EM):
  prior    P(already knows it before practising)
  learns   P(learning it from one practice opportunity)
  guesses  P(right answer WITHOUT knowing)
  slips    P(wrong answer DESPITE knowing)
(+ forgets, optional: P(losing it between opportunities); chosen on validation.)

pyBKT's prediction for each answer uses only the earlier answers (checked by
tests/test_tracing.py::test_no_model_sees_the_answer_it_predicts).
Skills never seen in training fall back to the training accuracy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ilm import config

_DEFAULTS = {"user_id": "user_id", "skill_name": "skill", "correct": "correct",
             "order_id": "_order"}


class BKT:
    def __init__(self, forgets: bool = False, num_fits: int = 3, seed: int = config.RANDOM_SEED):
        self.forgets, self.num_fits, self.seed = forgets, num_fits, seed
        self.name = "BKT (pyBKT" + (", with forgetting)" if forgets else ")")

    @staticmethod
    def _prep(df: pd.DataFrame) -> pd.DataFrame:
        d = df[["user_id", "seq", "skill", "correct"]].copy()
        d["skill"] = d["skill"].astype(str)
        d["_order"] = np.arange(len(d))   # df is already in student, seq order
        return d

    def fit(self, train):
        from pyBKT.models import Model
        self.p = float(train["correct"].mean())
        self.skills = set(train["skill"].astype(str))
        self.model = Model(seed=self.seed, num_fits=self.num_fits)
        self.model.fit(data=self._prep(train), defaults=_DEFAULTS, forgets=self.forgets)
        return self

    def predict(self, df):
        d = self._prep(df)
        out = np.full(len(d), self.p)
        known = d["skill"].isin(self.skills).to_numpy()
        if known.any():
            pred = self.model.predict(data=d[known])
            out[known] = pred.loc[d.index[known], "correct_predictions"].to_numpy()
        return out

    def params(self) -> pd.DataFrame:
        return self.model.params().unstack()
