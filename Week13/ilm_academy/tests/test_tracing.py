"""Knowledge-tracing protocol: metrics, counts, and the rule that no model sees the answer
it is predicting."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ilm.tracing import evaluate as ev
from ilm.tracing.pfa import PFA


def _toy(n_students=40, n_answers=12, seed=0):
    """Students whose accuracy depends on skill and improves with practice."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_students):
        ability = rng.normal()
        for t in range(n_answers):
            skill = ["a", "b", "c"][t % 3]
            p = 1 / (1 + np.exp(-(ability + 0.3 * (t // 3) - (skill == "c"))))
            rows.append({"user_id": u, "seq": t + 1, "skill": skill, "correct": int(rng.random() < p)})
    return pd.DataFrame(rows)


def test_metrics_by_hand():
    m = ev.metrics([1, 0, 1, 0], [0.9, 0.2, 0.4, 0.6])
    # pairs (right, wrong): (.9,.2) ok (.9,.6) ok (.4,.2) ok (.4,.6) wrong -> AUC 3/4
    assert m["auc"] == 0.75 and m["accuracy"] == 0.5
    assert m["rmse"] == pytest.approx(np.sqrt((0.01 + 0.04 + 0.36 + 0.36) / 4), abs=1e-4)


def test_prior_counts_exclude_the_current_answer():
    df = pd.DataFrame({"user_id": [1, 1, 1, 2], "skill": ["a", "a", "b", "a"], "correct": [1, 0, 1, 1]})
    c = ev.prior_counts(df, ["user_id", "skill"])
    assert c["successes"].tolist() == [0, 1, 0, 0] and c["failures"].tolist() == [0, 0, 0, 0]
    c = ev.prior_counts(df, ["user_id"])
    assert c["successes"].tolist() == [0, 1, 1, 0] and c["failures"].tolist() == [0, 0, 1, 0]


@pytest.mark.parametrize("model", [ev.GlobalMean(), ev.SkillMean(), ev.StudentSoFar(), PFA()],
                         ids=lambda m: m.name)
def test_no_model_sees_the_answer_it_predicts(model):
    df = _toy()
    model.fit(df)
    for row in (0, 5, 11, 200):
        assert ev.future_blind(model, df, row), f"{model.name} changed its prediction at row {row}"


def test_the_future_blind_check_catches_a_cheating_model():
    class Cheater:
        name = "cheater"
        def fit(self, train): return self
        def predict(self, df): return df["correct"].to_numpy() * 0.8 + 0.1
    assert not ev.future_blind(Cheater(), _toy(), 5)


def test_split_is_student_level_and_valid_comes_from_train():
    train, valid, test = ev.load_splits(_toy(n_students=100))
    ids = [set(x["user_id"]) for x in (train, valid, test)]
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])
    assert len(ids[2]) == 20 and len(ids[1]) == 16


def test_pfa_learns_that_practice_helps_and_beats_baselines():
    train, _, test = ev.load_splits(_toy(n_students=300, n_answers=15))
    pfa = PFA().fit(train)
    assert (pfa.skill_weights()["gamma"] > 0).all()        # earlier successes raise the odds
    auc = {m.name: ev.score(m, train, test)["auc"] for m in (ev.SkillMean(), pfa)}
    assert auc[pfa.name] > auc["baseline: skill mean"]
