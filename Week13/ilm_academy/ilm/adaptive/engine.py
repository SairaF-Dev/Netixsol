"""Adaptive engine: decides what each student practises next.

Four ideas, each a switch so their effect can be measured separately (ablation):
  prerequisites  a concept unlocks only when all its prerequisites are mastered
  zpd            pick questions the student has a 60-80% predicted chance of answering:
                 hard enough to learn from, easy enough not to frustrate
  bandit         Thompson sampling over concepts: each concept has a Beta(wins, losses)
                 belief about "practising this now produces learning"; sample from each,
                 practise the highest sample. Mostly picks what works, sometimes explores.
  reviews        spaced repetition: a mastered concept comes back after 1, 3, 7, 14, 30 days

The engine sees only what a real platform sees: question ids, right/wrong, the day.
Its knowledge of the student is BKT mastery (ilm.tracing.mastery); its knowledge of
the questions is IRT difficulty fitted on historical answers, and the bad-question list.
"""
from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ilm import config
from ilm.tracing.mastery import MASTERED, MasteryTracker

ZPD = (0.60, 0.80)
REVIEW_DAYS = (1, 3, 7, 14, 30)
WINDOW = 3            # look at the next 3 unlocked concepts in course order, not all of them
LEARNING_STEP = 0.05  # bandit "win": mastery rose by at least this much after the answer


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


@dataclass
class _Student:
    tracker: MasteryTracker
    last_seen: dict = field(default_factory=dict)          # concept -> day
    review_level: collections.Counter = field(default_factory=collections.Counter)
    asked: collections.Counter = field(default_factory=collections.Counter)
    pending: tuple | None = None                            # (concept, mode)


class AdaptiveEngine:
    def __init__(self, order: list[str], prereqs: dict[str, list[str]],
                 questions: dict[str, list[str]], bkt_params: pd.DataFrame,
                 item_params: pd.DataFrame | None = None, bad: set[str] | None = None,
                 use_prereqs: bool = True, use_zpd: bool = True, use_bandit: bool = True,
                 use_reviews: bool = True, seed: int = config.RANDOM_SEED, name: str = "adaptive"):
        self.order, self.prereqs, self.params = order, prereqs, bkt_params
        self.use = {"prereqs": use_prereqs, "zpd": use_zpd, "bandit": use_bandit, "reviews": use_reviews}
        self.name = name
        self.rng = np.random.default_rng(seed)
        bad = bad or set()
        self.questions = {c: [q for q in qs if q not in bad] or qs for c, qs in questions.items()}
        self.concept_of = {q: c for c, qs in questions.items() for q in qs}
        # question difficulty relative to its concept (IRT); unknown questions count as average
        self.shift: dict[str, float] = {}
        if item_params is not None:
            ip = item_params.join(pd.Series(self.concept_of, name="concept"), how="inner")
            mean_b = ip.groupby("concept")["b"].mean()
            for q, row in ip.iterrows():
                if np.isfinite(row["b"]) and np.isfinite(row["a"]):
                    self.shift[q] = max(row["a"], 0.1) * (row["b"] - mean_b[row["concept"]])
        self.wins = collections.Counter()     # bandit, shared by all students
        self.losses = collections.Counter()
        self.students: dict[str, _Student] = {}

    # ---------------------------------------------------------------- beliefs ----
    def _st(self, sid: str) -> _Student:
        if sid not in self.students:
            self.students[sid] = _Student(MasteryTracker(self.params))
        return self.students[sid]

    def predicted(self, sid: str, q: str) -> float:
        """P(right) for this student on this question: concept mastery, shifted by the
        question's difficulty relative to its concept."""
        p = self._st(sid).tracker.p_correct(self.concept_of[q])
        return 1 / (1 + math.exp(-(_logit(p) - self.shift.get(q, 0.0))))

    def mastered(self, sid: str, c: str) -> bool:
        return self._st(sid).tracker.p_known(c) >= MASTERED

    def unlocked(self, sid: str, c: str) -> bool:
        return not self.use["prereqs"] or all(self.mastered(sid, p) for p in self.prereqs.get(c, []))

    def frontier(self, sid: str) -> list[str]:
        """Concepts to learn next: not mastered, unlocked, in course order."""
        return [c for c in self.order if not self.mastered(sid, c) and self.unlocked(sid, c)][:WINDOW]

    def due_reviews(self, sid: str, day: int) -> list[str]:
        if not self.use["reviews"]:
            return []
        st = self._st(sid)
        due = []
        for c, last in st.last_seen.items():
            level = min(st.review_level[c], len(REVIEW_DAYS) - 1)
            overdue = day - last - REVIEW_DAYS[level]
            if self.mastered(sid, c) and overdue >= 0:
                due.append((overdue, c))
        return [c for _, c in sorted(due, reverse=True)]

    # ---------------------------------------------------------------- choosing ----
    def _pick_question(self, sid: str, c: str) -> str:
        st = self._st(sid)
        qs = self.questions[c]
        if not self.use["zpd"]:
            return min(qs, key=lambda q: (st.asked[q], qs.index(q)))
        target = sum(ZPD) / 2
        return min(qs, key=lambda q: (st.asked[q], abs(self.predicted(sid, q) - target)))

    def _in_zpd(self, sid: str, c: str) -> bool:
        lo, hi = ZPD
        return any(lo <= self.predicted(sid, q) <= hi for q in self.questions[c])

    def next_question(self, sid: str, day: int = 0) -> str | None:
        st = self._st(sid)
        reviews = self.due_reviews(sid, day)
        if reviews:
            c, mode = reviews[0], "review"
        else:
            front = self.frontier(sid)
            if not front:
                return None                                   # everything mastered
            if self.use["zpd"]:                               # prefer concepts with a ZPD question
                front = [c for c in front if self._in_zpd(sid, c)] or front
            if self.use["bandit"]:
                samples = {c: self.rng.beta(1 + self.wins[c], 1 + self.losses[c]) for c in front}
                c = max(front, key=samples.get)
            else:
                c = front[0]
            mode = "learn"
        q = self._pick_question(sid, c)
        st.pending = (c, mode)
        return q

    def observe(self, sid: str, q: str, correct: bool, day: int) -> None:
        st = self._st(sid)
        c = self.concept_of[q]
        before = st.tracker.p_known(c)
        after = st.tracker.update(c, correct)
        mode = st.pending[1] if st.pending and st.pending[0] == c else "learn"
        if mode == "learn":
            (self.wins if after - before >= LEARNING_STEP else self.losses)[c] += 1
        else:                                                  # review: grow or reset the gap
            st.review_level[c] = st.review_level[c] + 1 if correct else 0
        st.last_seen[c] = day
        st.asked[q] += 1
        st.pending = None
