"""Teacher extras (Day 5): question bank health, tutor safety, and the founder's Impact page.

Every number comes from a report in reports/ (each written by a re-runnable script) or from
the app's own logs; each section says where. Nothing here is estimated on the fly except the
teacher-hours calculator, whose assumptions are shown and adjustable on the page.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache

import pandas as pd

from ilm import config
from ilm.api import service

R = config.PROJECT_ROOT / "reports"
QUESTION_DECISIONS = ["Retire", "Relabel", "Keep"]


def _json(*parts) -> dict:
    return json.loads(R.joinpath(*parts).read_text(encoding="utf-8"))


def _ab_test() -> dict | None:
    """The A/B test design and its rehearsal on simulated students (ilm/evaluation/ab_test.py)."""
    if not (R / "ab_test" / "rehearsal.json").exists():
        return None
    r = _json("ab_test", "rehearsal.json")
    d, ab = r["design"], r["ab"]
    pick = lambda m: {k: ab[m][k] for k in ("diff", "low", "high")}
    return {"n_per_arm": d["n_per_arm"], "enrol": d["enrol_with_loss"], "mde": d["mde"], "baseline": d["baseline_dropout"],
            "rehearsal": {"students": r["rehearsal"]["students"], "dropout": pick("dropped_by_week4"),
                          "gain": pick("gain"), "gain_margin": ab["gain_margin"],
                          "aa_false_positive": r["aa"]["false_positive_rate"], "decision": r["decision"]["decision"]}}


# ------------------------------------------------------------------ question bank ----
def _qdb():
    con = service._db()
    con.execute("CREATE TABLE IF NOT EXISTS question_decisions (question TEXT PRIMARY KEY, decision TEXT, "
                "level INTEGER, teacher TEXT, at REAL)")
    return con


def decide_question(qid: str, decision: str, level: int | None, teacher: str) -> dict:
    if qid not in service.bank():
        raise KeyError(qid)
    if decision not in QUESTION_DECISIONS:
        raise ValueError("Unknown decision.")
    if decision == "Relabel" and not (level and 1 <= level <= 5):
        raise ValueError("Relabel needs a level from 1 to 5.")
    with service._db_lock, _qdb() as con:
        con.execute("INSERT OR REPLACE INTO question_decisions VALUES (?, ?, ?, ?, ?)",
                    (qid, decision, level if decision == "Relabel" else None, teacher, time.time()))
    return {"question": qid, "decision": decision, "level": level}


@lru_cache(maxsize=1)
def _difficulty() -> tuple[pd.DataFrame, dict]:
    return pd.read_csv(R / "difficulty" / "questions.csv"), _json("difficulty", "report.json")


def question_health() -> dict:
    df, rep = _difficulty()
    with service._db_lock, _qdb() as con:
        decided = {r[0]: {"decision": r[1], "level": r[2]} for r in
                   con.execute("SELECT question, decision, level FROM question_decisions").fetchall()}
    bank = service.bank()
    names = {c: v["name"] for c, v in service.concepts().items()}

    def row(r) -> dict:
        q = bank.get(r.id)
        return {"id": r.id, "type": r.type, "concept": names.get(r.concept, r.concept), "stem": q.stem if q else "",
                "code_line": (q.code or "").strip().splitlines()[0][:80] if q and q.code else None,
                "author_level": int(r.author), "measured_level": None if pd.isna(r.measured_level) else int(r.measured_level),
                "discrimination": None if pd.isna(r.a) else round(float(r.a), 2),
                "share_right": None if pd.isna(r.observed_p) else round(float(r.observed_p), 2),
                "answers": None if pd.isna(r.n) else int(r.n), "reason": r.reason if isinstance(r.reason, str) else "",
                "decision": decided.get(r.id)}

    gen = _json("question_gen", "v2", "report.json")
    counts = df["decision"].value_counts().to_dict()
    return {
        "total": int(len(df)), "counts": {k: int(v) for k, v in counts.items()},
        "retire": [row(r) for r in df[df.decision == "retire"].sort_values("a").itertuples()],
        "relabel": [row(r) for r in df[df.decision == "relabel"].itertuples()],
        "difficulty_agreement": {"author": rep["spearman_with_irt_b"]["author"], "llm": rep["spearman_with_irt_b"]["llm"]},
        "generated": {"asked": gen["asked"], "accepted": gen["accepted"], "rate": gen["acceptance_rate"],
                      "funnel": gen["funnel"], "spread": gen["accepted_spread"]["difficulty"]},
        "source": "reports/difficulty (IRT on simulated answers; python -m ilm.questions.difficulty) and "
                  "reports/question_gen/v2 (python -m ilm.questions.generate)",
        "caveat": "Measured difficulty comes from simulated students whose true difficulty was built from the "
                  "author's guess, so agreement favours the author. Real answers will settle it.",
    }


# ------------------------------------------------------------------ tutor safety ----
def tutor_safety() -> dict:
    runs = []
    for run, cases, label in [("run1", "main", "Original tutor, 50 test conversations"),
                              ("run2", "main", "After the leak fixes, same 50"),
                              ("run2", "heldout", "After the leak fixes, 12 unseen exercises"),
                              ("run3", "heldout2", "Latest tutor, 12 more unseen exercises")]:
        p = R / "tutor_eval" / run / cases / "report.json"
        if not p.exists():
            continue
        h = json.loads(p.read_text(encoding="utf-8"))["headline"]
        runs.append({"label": label, "exercise_turns": h["exercise_turns"],
                     "leaks": round(h["leak_rate_auto_only"] * h["exercise_turns"]),
                     "jailbreaks_resisted": h.get("jailbreak_resisted"), "fallbacks": h.get("fixed_fallback"),
                     "correct": h.get("correct"), "pedagogy": h.get("pedagogy"), "tone": h.get("tone")})
    judge = json.loads((R / "tutor_eval" / "run1" / "main" / "report.json").read_text(encoding="utf-8"))["headline"]
    live = {"questions": 0, "hints": 0, "by_rung": {}, "urdulish_share": None, "blocked": 0, "not_in_course": 0, "students": 0}
    with service._db_lock, service._db() as con:
        has = con.execute("SELECT name FROM sqlite_master WHERE name = 'tutor_log'").fetchone()
        if has:
            rows = con.execute("SELECT username, kind, level, language, grounded, leak_blocked FROM tutor_log").fetchall()
            if rows:
                # count what the student got: a question routed to the hint ladder ("write X for
                # me") is a hint, so hints and the per-rung counts always add up
                live = {"questions": sum(r[2] is None for r in rows), "hints": sum(r[2] is not None for r in rows),
                        "by_rung": {str(k): sum(r[2] == k for r in rows) for k in (1, 2, 3, 4)},
                        "urdulish_share": round(sum(r[3] == "urdulish" for r in rows) / len(rows), 2),
                        "blocked": sum(bool(r[5]) for r in rows), "not_in_course": sum(not r[4] for r in rows),
                        "students": len({r[0] for r in rows})}
    return {"evaluation": runs, "judge_caught_code_leaks": judge.get("judge_caught_code_leaks"),
            "live": live, "source": "reports/tutor_eval (python -m ilm.tutor.evaluate); live counts from the app's "
            "tutor log (metadata only: no student text is stored)"}


# ------------------------------------------------------------------ impact ----
def impact() -> dict:
    a = _json("adaptive", "comparison_seed2027.json")
    pol = {p["policy"]: p for p in a["policies"]}
    fixed, adaptive = pol["fixed path"], pol["adaptive (all four ideas)"]

    def ci(key):
        d, lo, hi = adaptive[f"{key}_vs_fixed"]
        return {"diff": d, "low": lo, "high": hi}

    drop = _json("dropout", "report.json")
    grading = _json("grading", "report.json")
    final = grading["variants"]["+ speed check (final)"]
    tests_only = grading["variants"]["bank tests only"]
    attacks = _json("sandbox", "attack_report.json")
    plag = _json("plagiarism", "report.json")["base_rate"]
    lgbm = drop["test_results"]["LightGBM"]
    return {
        "adaptive": {"students": a["students"], "caveat": a["caveat"],
                     "fixed": {"dropped_by_week3": fixed["dropped_by_week3"], "dropped_ever": fixed["dropped_ever"],
                               "concepts_known": fixed["truth_known_at_end"], "hours": fixed["hours"]},
                     "adaptive": {"dropped_by_week3": adaptive["dropped_by_week3"], "dropped_ever": adaptive["dropped_ever"],
                                  "concepts_known": adaptive["truth_known_at_end"], "hours": adaptive["hours"]},
                     "diff": {"dropped_by_week3": ci("dropped_by_week3"), "dropped_ever": ci("dropped_ever"),
                              "concepts_known": ci("truth_known_at_end"), "hours": ci("hours")}},
        # all four, because the simple baseline is slightly ahead of LightGBM and both sit at the
        # ceiling of what the data can show (only the simulator's hidden motivation does better)
        "dropout_model": {"lightgbm": lgbm["pr_auc"],
                          "baseline": drop["test_results"]["baseline (logistic, 3 signals)"]["pr_auc"],
                          "ceiling_observable": drop["best_possible_pr_auc"]["rule_observable_part_only"],
                          "ceiling_hidden": drop["best_possible_pr_auc"]["rule_with_hidden_motivation"],
                          "base_rate": lgbm["base_rate"]},
        "grading": {"kappa_final": final["quadratic_kappa"], "kappa_tests_only": tests_only["quadratic_kappa"],
                    "mae": final["mae"], "within_2": final["within_2"],
                    "reference": "blind assistant marks, not a teacher (data/grading/marking_scheme.md)"},
        "review_share": round(sum(1 for g in grading["grades"] if g["mark"] < 4) / len(grading["grades"]), 2),
        "sandbox": {"attacks": attacks["attacks"], "contained": attacks["contained"]},
        "plagiarism": {"false_alarm_rate": plag["false_alarm_rate_per_honest_pair"],
                       "by_class": plag["threshold_flags_by_class_size"]},
        "tutor": tutor_safety()["evaluation"],
        "ab_test": _ab_test(),
        "sources": {"ab_test": "reports/ab_test/design.md (pre-registration), rehearsal.json","adaptive": "reports/adaptive/comparison_seed2027.json (fresh cohort, paired bootstrap 95% CI)",
                    "dropout": "reports/dropout/report.json", "grading": "reports/grading/report.json",
                    "sandbox": "reports/sandbox/attack_report.json", "plagiarism": "reports/plagiarism/report.json"},
    }
