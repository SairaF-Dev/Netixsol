"""Mastery score per concept: BKT's P(student knows the concept), updated after each answer.

The four numbers per concept (prior, learns, guesses, slips) are fitted by pyBKT on the
simulated course's PUBLIC answers. The per-student update is the standard BKT rule:

  1. evidence (Bayes' rule):
       right: P(L | right) = P(L)(1 - slip) / [ P(L)(1 - slip) + (1 - P(L)) guess ]
       wrong: P(L | wrong) = P(L) slip     / [ P(L) slip     + (1 - P(L)) (1 - guess) ]
  2. learning from the practice itself:
       P(L) <- P(L | answer) + (1 - P(L | answer)) * learns

  P(right next time) = P(L)(1 - slip) + (1 - P(L)) guess
  mastery is EARNED when P(L) >= 0.95 (Corbett & Anderson's classic threshold) AND the
  last STREAK answers on the concept were right (ASSISTments skill builders' "3 in a row"),
  and LOST only when P(L) falls below 0.95 again (hysteresis). One slip on a well-known
  concept (0.99 -> ~0.97) keeps it; repeated misses take it away (more of them the longer
  the record of right answers), and it must then be earned again. Without this, 17% of reviews failed (about the slip rate, so mostly slips)
  and each failure sent the student back to relearn the concept and re-locked everything
  built on it: 18% of all adaptive answers were relearning (reports/adaptive/).

Why both: the simulated history has only 3 answers per concept, too few for pyBKT to tell
"learned fast" from "got lucky"; some concepts got learn rates near 1, so P(L) passed 0.95
after one or two right answers while fewer than half of those students truly knew it
(reports/mastery/summary.json). The streak is the evidence the probability alone lacks.

Degenerate parameters (guess + slip >= 1: a right answer would LOWER P(L)) are replaced by
the median of the healthy concepts, and listed in the report.

Run:  python -m ilm.tracing.mastery   (fits the parameters and checks them against the truth)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ilm import config

MASTERED = 0.95
STREAK = 3
PARAMS_FILE = config.MODELS_DIR / "bkt_concept_params.csv"


@dataclass
class MasteryTracker:
    """One student's mastery of every concept. params: DataFrame indexed by concept with
    columns prior, learns, guesses, slips."""
    params: pd.DataFrame
    known: dict[str, float] = field(default_factory=dict)
    streak: dict[str, int] = field(default_factory=dict)      # right answers in a row
    earned: set[str] = field(default_factory=set)             # mastery earned, not yet lost

    def p_known(self, concept: str) -> float:
        return self.known.get(concept, float(self.params.at[concept, "prior"]))

    def p_correct(self, concept: str) -> float:
        p, row = self.p_known(concept), self.params.loc[concept]
        return p * (1 - row["slips"]) + (1 - p) * row["guesses"]

    def update(self, concept: str, correct: bool) -> float:
        p, row = self.p_known(concept), self.params.loc[concept]
        slip, guess = row["slips"], row["guesses"]
        if correct:
            post = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
        else:
            post = p * slip / (p * slip + (1 - p) * (1 - guess))
        self.known[concept] = post + (1 - post) * row["learns"]
        self.streak[concept] = self.streak.get(concept, 0) + 1 if correct else 0
        if self.known[concept] < MASTERED:
            self.earned.discard(concept)
        elif self.streak[concept] >= STREAK:
            self.earned.add(concept)
        return self.known[concept]

    def mastered(self, concept: str) -> bool:
        return concept in self.earned

    def report(self) -> pd.DataFrame:
        rows = [{"concept": c, "p_known": round(self.p_known(c), 3), "mastered": self.mastered(c)}
                for c in self.params.index]
        return pd.DataFrame(rows).set_index("concept")


def trace(log: pd.DataFrame, params: pd.DataFrame, student: str = "student_id") -> pd.DataFrame:
    """Replay every student's answers. Adds p_known_before and p_correct_before for each row
    (what the tracker believed BEFORE seeing that answer)."""
    before_known, before_correct = np.zeros(len(log)), np.zeros(len(log))
    for _, rows in log.groupby(student, sort=False).indices.items():
        t = MasteryTracker(params)
        for i in rows:
            c = log["concept"].iat[i]
            before_known[i], before_correct[i] = t.p_known(c), t.p_correct(c)
            t.update(c, bool(log["correct"].iat[i]))
    return log.assign(p_known_before=before_known, p_correct_before=before_correct)


def fit_params(log: pd.DataFrame) -> pd.DataFrame:
    """pyBKT per concept on public answers (no forgetting: one 'known' state per concept)."""
    from pyBKT.models import Model
    d = log[["student_id", "concept", "correct"]].copy()
    d["_order"] = np.arange(len(d))
    m = Model(seed=config.RANDOM_SEED, num_fits=3, parallel=False)  # see ilm/tracing/bkt.py
    m.fit(data=d, defaults={"user_id": "student_id", "skill_name": "concept",
                            "correct": "correct", "order_id": "_order"})
    p = m.params().reset_index().pivot_table(index="skill", columns="param", values="value")
    return repair_degenerate(p[["prior", "learns", "guesses", "slips"]].rename_axis("concept"))


def degenerate(params: pd.DataFrame) -> pd.Series:
    return params["guesses"] + params["slips"] >= 1


def repair_degenerate(params: pd.DataFrame) -> pd.DataFrame:
    """Concepts where a right answer would lower P(known) get the healthy concepts' median."""
    bad = degenerate(params)
    out = params.copy()
    out.loc[bad] = params.loc[~bad].median().to_numpy()
    out.attrs["repaired"] = sorted(params.index[bad])
    return out


def main() -> None:
    from sklearn.metrics import roc_auc_score
    from ilm.learners.simulator import public
    sim_dir = config.PROCESSED_DIR / "simulated"
    full = pd.read_csv(sim_dir / "interactions.csv.gz").sort_values(["student_id", "seq"])
    log = public(full)                                   # the model never sees truth_*
    params = fit_params(log)
    PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    params.round(4).to_csv(PARAMS_FILE)

    traced = trace(log, params)
    truth = full["truth_knew"].to_numpy()                # used ONLY to score the estimate
    bins = pd.cut(traced["p_known_before"], [0, .2, .4, .6, .8, .95, 1.0], include_lowest=True)
    calib = (pd.DataFrame({"bin": bins, "truth": truth}).groupby("bin", observed=True)["truth"]
             .agg(["mean", "size"]).round(3))
    report = {
        "concepts": len(params),
        "degenerate_replaced_by_median": params.attrs.get("repaired", []),
        "mastery_rule": f"earned: P(known) >= {MASTERED} and last {STREAK} answers right; lost: P(known) < {MASTERED}",
        "note": "3 answers per concept in this history, so the streak rule cannot fire here; "
                "the bins show how far P(known) ALONE can be trusted. The engine's mastery "
                "calls are checked against the truth in reports/adaptive/comparison.json.",
        "auc_p_known_vs_truth_knew": round(float(roc_auc_score(truth, traced["p_known_before"])), 3),
        "auc_p_correct_vs_answer": round(float(roc_auc_score(log["correct"], traced["p_correct_before"])), 3),
        "calibration_share_truly_known_by_p_known_bin": {str(k): v for k, v in calib["mean"].items()},
        "answers_per_bin": {str(k): int(v) for k, v in calib["size"].items()},
    }
    out = config.REPORTS_DIR / "mastery"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
