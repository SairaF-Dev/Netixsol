"""PFA: Performance Factors Analysis (Pavlik, Cen & Koedinger, 2009).

    logit P(correct) = beta_skill + gamma_skill * f(successes) + rho_skill * f(failures)

beta  = how easy the skill is to begin with
gamma = how much each earlier SUCCESS on this skill helps
rho   = how much each earlier FAILURE on this skill changes the odds (failures still teach)
counts are per student AND skill, from EARLIER answers only (evaluate.prior_counts).
f = the raw count (original PFA) or log(1 + count) (later answers add less); chosen on
the validation split, never on test.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.linear_model import LogisticRegression

from ilm.tracing.evaluate import prior_counts


class PFA:
    def __init__(self, C: float = 1.0, transform: str = "log"):
        self.C, self.transform = C, transform
        self.name = f"PFA (C={C}, {transform} counts)"

    def _f(self, x):
        return np.log1p(x) if self.transform == "log" else x

    def _features(self, df):
        c = prior_counts(df, ["user_id", "skill"])
        col = df["skill"].map(self.index)
        known = col.notna().to_numpy()                      # unseen skill: no skill columns
        rows = np.arange(len(df))[known]
        cols = col[known].astype(int).to_numpy()
        k = len(self.index)
        succ = self._f(c["successes"].to_numpy(float))[known]
        fail = self._f(c["failures"].to_numpy(float))[known]
        data = np.concatenate([np.ones(len(rows)), succ, fail])
        return sp.csr_matrix((data, (np.tile(rows, 3), np.concatenate([cols, cols + k, cols + 2 * k]))),
                             shape=(len(df), 3 * k))

    def fit(self, train):
        self.index = {s: i for i, s in enumerate(sorted(train["skill"].unique()))}
        self.lr = LogisticRegression(C=self.C, max_iter=2000)
        self.lr.fit(self._features(train), train["correct"])
        return self

    def predict(self, df):
        return self.lr.predict_proba(self._features(df))[:, 1]

    def skill_weights(self):
        """beta / gamma / rho per skill: readable by a teacher."""
        import pandas as pd
        k, w = len(self.index), self.lr.coef_[0]
        return pd.DataFrame({"beta": w[:k], "gamma": w[k:2 * k], "rho": w[2 * k:]},
                            index=list(self.index))
