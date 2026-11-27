"""Difficulty calibration, offline: decisions follow the rules and the comparison is sound."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ilm.questions.difficulty import bands, compare, decide, describe, predict
from ilm.questions.validate import load_bank

BANK, _ = load_bank()


def frame(**cols):
    n = len(next(iter(cols.values())))
    base = {"type": ["mcq"] * n, "concept": ["c"] * n, "author": [3] * n, "llm_p_correct": [50.0] * n,
            "llm_why": [""] * n, "b": [0.0] * n, "a": [1.0] * n, "n": [100] * n, "observed_p": [0.5] * n,
            "truth_b": [0.0] * n, "truth_bad": [False] * n}
    base.update(cols)
    t = pd.DataFrame(base, index=[f"q-{i:02d}" for i in range(n)])
    t["llm_hardness"] = 100 - t["llm_p_correct"]
    return t


def test_bands_are_equal_count_and_ordered():
    b = bands(pd.Series(np.linspace(-2, 2, 10)))
    assert b.tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_decisions():
    t = decide(frame(b=list(np.linspace(-2, 2, 10)), author=[1] * 9 + [1],
                     a=[1.0] * 7 + [0.1, -0.4, 1.0], n=[100] * 9 + [10]))
    assert t.loc["q-07", "decision"] == "retire" and "weak" in t.loc["q-07", "reason"]
    assert t.loc["q-08", "decision"] == "retire" and "WORSE" in t.loc["q-08", "reason"]
    assert t.loc["q-09", "decision"] == "unmeasured"                  # 10 answers only
    assert t.loc["q-05", "decision"] == "relabel"                     # author 1, measured level 4
    assert t.loc["q-00", "decision"] == "keep"


def test_comparison_rewards_the_better_ranking_and_skips_planted_bad():
    b = np.linspace(-2, 2, 20)
    t = decide(frame(b=list(b), author=[1, 2, 3, 4, 5] * 4, llm_p_correct=list(100 - 10 * (b + 2)),
                     truth_b=list(b), truth_bad=[False] * 19 + [True]))
    s = compare(t)
    assert s["spearman_with_irt_b"]["llm"] == 1.0 and s["spearman_with_irt_b"]["author"] < 0.5
    assert s["questions_compared"] == 19


def test_prediction_prompt_hides_the_author_label_and_parses_by_id():
    q = BANK[0]
    assert "difficulty" not in describe(q).lower()
    calls = []

    def fake(prompt, **kw):
        calls.append(prompt)
        return json.dumps({"predictions": [{"id": BANK[0].id, "p_correct": "85", "why": "recall"},
                                           {"id": "not-in-batch", "p_correct": 5}]})
    import ilm.questions.difficulty as D
    old = D.PREDICTIONS
    try:
        D.PREDICTIONS = type("P", (), {"write_text": lambda *a, **k: None})()
        out = predict(BANK[:3], fake, {})
    finally:
        D.PREDICTIONS = old
    assert out == {BANK[0].id: {"p_correct": 85.0, "why": "recall"}} and len(calls) == 1
