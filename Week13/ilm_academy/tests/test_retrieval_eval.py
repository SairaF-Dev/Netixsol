"""The benchmark's scoring maths and its rules (a wrong ruler makes every comparison wrong)."""
from __future__ import annotations

import collections

import pytest

from ilm.content.download import all_lessons
from ilm.content.retrieval_eval import first_hit_rank, load_questions, metrics, rrf


def test_first_hit_rank_counts_from_one_and_accepts_any_relevant_lesson():
    assert first_hit_rank(["a", "b", "c"], ["c"]) == 3
    assert first_hit_rank(["a", "b", "c"], ["x", "b"]) == 2
    assert first_hit_rank(["a", "b"], ["z"]) is None


def test_metrics_by_hand():
    # ranks 1, 2, 4, miss -> hit@1 1/4, hit@5 3/4, mrr (1 + 1/2 + 1/4 + 0) / 4
    m = metrics([1, 2, 4, None])
    assert m == {"n": 4, "hit@1": 0.25, "hit@5": 0.75, "mrr": round(1.75 / 4, 3)}


def test_benchmark_is_balanced_and_well_formed():
    qs = load_questions("all")
    lesson_ids = {l["id"] for l in all_lessons()}
    assert len(qs) >= 40
    assert len({q["q"] for q in qs}) == len(qs)                 # no duplicates
    for q in qs:
        assert q["type"] in ("term", "symptom") and q["split"] in ("dev", "holdout")
        assert q["lessons"] and set(q["lessons"]) <= lesson_ids
    holdout = collections.Counter(q["type"] for q in qs if q["split"] == "holdout")
    assert holdout["term"] == holdout["symptom"]                 # fair final exam
    assert {l for q in qs for l in q["lessons"]} == lesson_ids   # every lesson is tested


def test_holdout_cannot_be_scored_by_accident(monkeypatch):
    import sys
    from ilm.content import retrieval_eval
    monkeypatch.setattr(sys, "argv", ["x", "--split", "holdout"])
    with pytest.raises(SystemExit, match="final exam"):
        retrieval_eval.main()


def test_rrf_rewards_agreement_between_systems():
    # "b" is 2nd in both lists; "a" is 1st in one and missing from the other
    assert rrf([["a", "b", "c"], ["d", "b", "e"]])[0] == "b"
    assert rrf([["a", "b"], ["a", "b"]]) == ["a", "b"]          # identical rankings stay identical
    assert set(rrf([["a"], ["z"]])) == {"a", "z"}               # nothing is lost
