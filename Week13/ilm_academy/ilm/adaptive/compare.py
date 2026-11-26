"""Adaptive engine vs the fixed path, on simulated students.

Fair-comparison rules:
  - FRESH students (seed 2026): the engine's BKT and IRT numbers were learned from the
    seed-42 students' answers, so it is not evaluated on the people it learned from.
  - PAIRED: every student goes through every policy with the SAME hidden traits, so a
    difference comes from the policy, not from who happened to enrol.
  - ABLATIONS: the engine with one idea switched off at a time, to see what each adds.
  - Uncertainty: 95% bootstrap interval of the paired difference (students resampled).

Caveat (also in the report): the simulator was written by us. It rewards learning with
prerequisites in place and makes repeated failure push students to drop out, which is
exactly what the engine exploits. A win here is evidence, not proof: Day 5 designs the
real A/B test.

Run:  python -m ilm.adaptive.compare     (needs python -m ilm.tracing.mastery first)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ilm import config
from ilm.adaptive.engine import AdaptiveEngine
from ilm.learners import simulator as sim
from ilm.tracing.mastery import PARAMS_FILE

EVAL_SEED = 2026
N_STUDENTS = 1000


def students(course, n=N_STUDENTS, seed=EVAL_SEED):
    rng = np.random.default_rng(seed)
    return [sim.make_student(i, rng, course) for i in range(n)]


def engine(course, **switches):
    irt = config.REPORTS_DIR / "irt"
    item = pd.read_csv(irt / "question_params_2pl.csv", index_col=0)[["a", "b"]]
    bad = set(pd.read_csv(irt / "flagged_questions.csv", index_col=0).index)
    params = pd.read_csv(PARAMS_FILE, index_col=0)
    return AdaptiveEngine(course.order, course.prereqs, course.questions, params,
                          item_params=item, bad=bad, seed=EVAL_SEED, **switches)


def outcomes(log: pd.DataFrame, people: pd.DataFrame) -> pd.DataFrame:
    hours = log.groupby("student_id")["response_time_sec"].sum() / 3600
    out = people.set_index("student_id")[["truth_known_at_end", "dropped_week", "n_answers"]].copy()
    out["dropped_by_week3"] = (out["dropped_week"].fillna(99) <= 3).astype(int)
    out["dropped_ever"] = out["dropped_week"].notna().astype(int)
    out["hours"] = hours.reindex(out.index).fillna(0)
    out["accuracy"] = log.groupby("student_id")["correct"].mean().reindex(out.index)
    return out.drop(columns="dropped_week")


def paired_ci(diff: np.ndarray, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    means = [rng.choice(diff, len(diff)).mean() for _ in range(n_boot)]
    return float(diff.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    course = sim.Course.load(config.RANDOM_SEED)          # same questions + truth as the history
    base = json.loads((config.PROCESSED_DIR / "simulated" / "summary.json").read_text())["calibrated_drop_base"]
    policies = {
        "fixed path": lambda: sim.FixedPath(course),
        "adaptive (all four ideas)": lambda: engine(course),
        "adaptive without prerequisites": lambda: engine(course, use_prereqs=False),
        "adaptive without ZPD": lambda: engine(course, use_zpd=False),
        "adaptive without bandit": lambda: engine(course, use_bandit=False),
        "adaptive without reviews": lambda: engine(course, use_reviews=False),
    }
    results = {}
    for name, make in policies.items():
        log, people = sim.run_course(students(course), course, make(), EVAL_SEED, base)
        results[name] = outcomes(log, people)
        r = results[name]
        print(f"{name:32s} known {r['truth_known_at_end'].mean():5.1f}  dropped by wk3 "
              f"{r['dropped_by_week3'].mean():.1%}  hours {r['hours'].mean():4.1f}  accuracy {r['accuracy'].mean():.2f}",
              flush=True)

    fixed = results["fixed path"]
    rows = []
    for name, r in results.items():
        row = {"policy": name}
        for m in ("truth_known_at_end", "dropped_by_week3", "dropped_ever", "hours", "n_answers", "accuracy"):
            row[m] = round(float(r[m].mean()), 4)
            if name != "fixed path":
                d, lo, hi = paired_ci((r[m] - fixed[m]).dropna().to_numpy())
                row[f"{m}_vs_fixed"] = [round(d, 4), round(lo, 4), round(hi, 4)]
        rows.append(row)
    out = config.REPORTS_DIR / "adaptive"
    out.mkdir(parents=True, exist_ok=True)
    report = {"students": N_STUDENTS, "eval_seed": EVAL_SEED, "drop_base": base,
              "caveat": "Simulated students; the simulator rewards what the engine does. Evidence, not proof.",
              "policies": rows}
    (out / "comparison.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(rows[1], indent=1))


if __name__ == "__main__":
    main()
