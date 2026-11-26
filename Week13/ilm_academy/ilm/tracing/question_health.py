"""Question bank health: fit IRT to the simulated answers and find the bad questions.

IRT sees only the PUBLIC data (simulator.public): who answered which question, right or
wrong. The answer key (truth_bad, truth_b, truth_a) is used only afterwards, to score how
well IRT found the planted bad questions.

Run:  python -m ilm.tracing.question_health   -> reports/irt/
"""
from __future__ import annotations

import json

import pandas as pd

from ilm import config
from ilm.learners.simulator import public
from ilm.tracing.irt import IRT, first_answers, precision_recall

SIM = config.PROCESSED_DIR / "simulated"


def main() -> None:
    log = public(pd.read_csv(SIM / "interactions.csv.gz"))
    truth = pd.read_csv(SIM / "questions_truth.csv").set_index("question_id")
    data = first_answers(log, "student_id", "question_id")

    results = {}
    for kind in ("1pl", "2pl"):
        m = IRT(kind).fit(data, student="student_id")
        results[kind] = m
    m2 = results["2pl"]
    params = m2.item_params.join(truth[["concept", "author_difficulty", "truth_b", "truth_a", "truth_bad"]])
    flags = m2.flag_bad()
    planted = set(truth.index[truth["truth_bad"]])
    judged = set(params.index[params["n"] >= 50])

    report = {
        "answers_used": len(data), "students": int(data["student_id"].nunique()),
        "questions": int(data["question_id"].nunique()),
        "questions_with_50plus_answers": len(judged),
        "bad_question_detection": precision_recall(set(flags.index), planted & judged),
        "planted_but_never_asked": sorted(planted - set(params.index)),
        "questions_never_asked_by_fixed_path": int(len(truth) - len(params)),
        "difficulty_recovery_spearman": round(params["b"].corr(params["truth_b"], method="spearman"), 3),
        "discrimination_recovery_spearman": round(params["a"].corr(params["truth_a"], method="spearman"), 3),
        "author_guess_vs_irt_difficulty_spearman":
            round(params["author_difficulty"].corr(params["b"], method="spearman"), 3),
    }
    out = config.REPORTS_DIR / "irt"
    out.mkdir(parents=True, exist_ok=True)
    params.round(3).to_csv(out / "question_params_2pl.csv")
    flags.join(truth[["truth_bad"]]).round(3).to_csv(out / "flagged_questions.csv")
    (out / "summary.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    print(flags.join(truth[["truth_bad"]])[["n", "p_correct", "a", "reason", "truth_bad"]].round(2).to_string())


if __name__ == "__main__":
    main()
