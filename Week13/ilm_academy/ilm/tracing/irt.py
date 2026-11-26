"""IRT: Item Response Theory, 1PL (Rasch) and 2PL.

    P(student s answers question q right) = sigmoid(a_q * (theta_s - b_q))
      theta_s  ability of the student
      b_q      difficulty: the ability at which the chance is 50/50
      a_q      discrimination: how sharply the question separates strong from weak
               1PL gives every question the SAME a.

Fitted by maximum a posteriori (MAP) in two stages (1PL, then 2PL starting from it):
the likelihood of the answers plus gentle priors theta ~ N(0, 1), intercept ~ N(0, 2),
a ~ N(1, 1). Afterwards abilities are rescaled to mean 0, spread 1 (a and b adjusted to
match), because the scale is otherwise arbitrary.
a is NOT forced positive: a NEGATIVE discrimination (strong students do worse) is the
classic sign of a wrong answer key, and we want to see it.

Assumption to remember: ability is fixed. Students who learn during the course break it,
so IRT uses each student's FIRST answer to each question only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from ilm import config

WEAK_A = 0.3   # below this a question barely separates students: review it


class IRT:
    def __init__(self, model: str = "2pl", steps: int = 300, seed: int = config.RANDOM_SEED):
        assert model in ("1pl", "2pl")
        self.model, self.steps, self.seed = model, steps, seed

    def fit(self, df: pd.DataFrame, student: str = "user_id", item: str = "question_id"):
        """df: one row per answer with columns student, item, correct (first answers only)."""
        torch.manual_seed(self.seed)
        self.students = {s: i for i, s in enumerate(df[student].unique())}
        self.items = {q: i for i, q in enumerate(df[item].unique())}
        s = torch.tensor(df[student].map(self.students).to_numpy())
        q = torch.tensor(df[item].map(self.items).to_numpy())
        y = torch.tensor(df["correct"].to_numpy(), dtype=torch.float32)

        # Questions are written as slope * theta + intercept (a, c), then b = -c / a.
        # Fitting (a, b) directly got stuck (found 2026-11-26): a question with a = -1 was
        # fitted as a = +0.33 with b pushed to -5.9, because a could not cross 0 easily.
        theta = torch.zeros(len(self.students), requires_grad=True)
        c = torch.zeros(len(self.items), requires_grad=True)
        a = torch.ones(len(self.items), requires_grad=False)

        def fit_stage(params, use_a_prior):
            opt = torch.optim.LBFGS(params, lr=1, max_iter=self.steps, tolerance_change=1e-7,
                                    line_search_fn="strong_wolfe")

            def closure():
                opt.zero_grad()
                logit = a[q] * theta[s] + c[q]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logit, y, reduction="sum")
                loss = loss + 0.5 * (theta ** 2).sum() + 0.5 * (c ** 2).sum() / 4
                if use_a_prior:
                    loss = loss + 0.5 * ((a - 1) ** 2).sum()
                loss.backward()
                return loss

            prev = None
            for _ in range(20):   # run until it really converges, not a fixed step count
                loss = opt.step(closure).item()
                if prev is not None and abs(prev - loss) < 1e-4 * abs(prev):
                    break
                prev = loss

        fit_stage([theta, c], use_a_prior=False)              # stage 1: 1PL, a = 1
        if self.model == "2pl":                                # stage 2: free slopes, start from 1PL
            a.requires_grad_(True)
            fit_stage([theta, c, a], use_a_prior=True)

        # Fix the scale: a*theta + c is unchanged if theta is rescaled and a, c compensate,
        # so report abilities with mean 0 and spread 1 (the usual IRT convention).
        th, a_, c_ = theta.detach().numpy(), a.detach().numpy(), c.detach().numpy()
        mu, sd = th.mean(), th.std()
        th = (th - mu) / sd
        c_ = c_ + a_ * mu
        a_ = a_ * sd
        with np.errstate(divide="ignore"):
            b_ = np.where(np.abs(a_) > 1e-6, -c_ / a_, np.nan)   # difficulty undefined if a ~ 0
        self.theta = pd.Series(th, index=list(self.students))
        counts = df.groupby(item)["correct"].agg(n="size", p_correct="mean")
        self.item_params = pd.DataFrame({"b": b_, "a": a_, "c": c_},
                                        index=list(self.items)).join(counts)
        return self

    def predict(self, df, student="user_id", item="question_id"):
        th = df[student].map(self.theta).fillna(0).to_numpy()
        p = self.item_params.reindex(df[item])
        return 1 / (1 + np.exp(-(p["a"].fillna(1).to_numpy() * th + p["c"].fillna(0).to_numpy())))

    def flag_bad(self, min_n: int = 50) -> pd.DataFrame:
        """Questions to review. Only questions with enough answers are judged."""
        t = self.item_params[self.item_params["n"] >= min_n].copy()
        # "answer key" needs CLEARLY negative a: noise puts useless questions slightly below 0
        # (two a=-0.1 questions were wrongly sent for answer-key review, 2026-11-26)
        t["reason"] = np.select([t["a"] < -WEAK_A, t["a"] < WEAK_A],
                                ["negative discrimination: check the answer key",
                                 "weak discrimination: does not separate strong from weak"], "")
        return t[t["reason"] != ""].sort_values("a")


def first_answers(df: pd.DataFrame, student: str, item: str) -> pd.DataFrame:
    """IRT assumes fixed ability, so keep each student's first answer to each question."""
    return df.drop_duplicates([student, item], keep="first")


def precision_recall(flagged: set, truth: set) -> dict:
    hit = len(flagged & truth)
    return {"flagged": len(flagged), "planted": len(truth), "found": hit,
            "precision": round(hit / len(flagged), 3) if flagged else None,
            "recall": round(hit / len(truth), 3) if truth else None}
