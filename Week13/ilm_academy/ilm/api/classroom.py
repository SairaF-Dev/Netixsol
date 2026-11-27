"""The teacher's class: what the dashboard shows (Day 5).

    python -m ilm.api.classroom          build and cache data/app/class_week3.json

The class is the FRESH simulated cohort (seed 2027) that the dropout model never trained on,
seen at the week-3 checkpoint (just before the week-4 dropout cliff), exactly as in the Day 2
evaluation:
  - risk: LightGBM trained on the main cohort (settings chosen on validation in Day 2), risk
    levels by capacity (top 10% high, next 20% medium), reason from each student's biggest
    SHAP push, and the matching action
  - mastery: BKT (models/bkt_concept_params.csv) replayed over each student's PUBLIC answers up
    to the checkpoint; the simulator's hidden truth is never read
  - sections: the demo cohort has no real classes, so students are split into sections of 125
    in enrolment order, and the page says so
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from ilm import config

WEEK = 3
SECTION_SIZE = 125
MIN_PRACTISED_SHARE = 0.05      # heatmap: concepts at least 5% of the class has practised
CACHE = config.DATA_DIR / "app" / f"class_week{WEEK}.json"

FEATURE_WORDS = {
    "acc_last10": lambda v: f"{round(v * 10)} of the last 10 answers right",
    "acc_this_week": lambda v: f"{v:.0%} right this week",
    "acc_total": lambda v: f"{v:.0%} right overall",
    "acc_change": lambda v: f"accuracy {'down' if v < 0 else 'up'} {abs(v):.0%} on earlier weeks",
    "wrong_streak": lambda v: f"{int(v)} wrong answers in a row",
    "days_since_last": lambda v: f"no answers for {int(v)} days",
    "empty_week": lambda v: "no answers this week" if v else "answered this week",
    "sessions_this_week": lambda v: f"{int(v)} study session{'s' if int(v) != 1 else ''} this week",
    "sessions_last_week": lambda v: f"{int(v)} session{'s' if int(v) != 1 else ''} last week",
    "answers_this_week": lambda v: f"{int(v)} answers this week",
    "answers_total": lambda v: f"{int(v)} answers so far",
    "active_weeks_share": lambda v: f"active in {v:.0%} of weeks",
    "speed": lambda v: f"takes {v:.1f}x the usual time per question",
    "code_share_this_week": lambda v: f"{v:.0%} of this week's work was coding",
    "week": lambda v: f"week {int(v)} of the course",
}
REASON_LABEL = {"activity": "Inactive", "struggling": "Struggling", "pace": "Pace", "other": "Other"}


def in_words(feature: str, value) -> str | None:
    """A feature value in words; None when there is no value (e.g. accuracy in an empty week),
    so a reason is never just a raw feature name."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return FEATURE_WORDS.get(feature, lambda v: f"{feature.replace('_', ' ')} {v}")(value)


def mastery_table(log: pd.DataFrame, params: pd.DataFrame, students: list[str]) -> pd.DataFrame:
    """P(known) per (student, concept) after replaying the student's public answers."""
    from ilm.tracing.mastery import MasteryTracker
    rows = []
    by_student = dict(tuple(log.sort_values(["student_id", "seq"]).groupby("student_id", sort=False)))
    for sid in students:
        t = MasteryTracker(params)
        h = by_student.get(sid)
        practised = set()
        if h is not None:
            for c, ok in zip(h["concept"], h["correct"]):
                if c in params.index:
                    t.update(c, bool(ok))
                    practised.add(c)
        for c in params.index:
            rows.append({"student_id": sid, "concept": c, "p_known": t.p_known(c),
                         "mastered": t.mastered(c), "practised": c in practised})
    return pd.DataFrame(rows)


def heatmap(m: pd.DataFrame, sections: dict[str, int], order: list[str], names: dict[str, str]) -> dict:
    share = m[m.practised].groupby("concept")["student_id"].nunique() / m["student_id"].nunique()
    cols = [c for c in order if share.get(c, 0) >= MIN_PRACTISED_SHARE]
    m = m[m.concept.isin(cols)].assign(section=m["student_id"].map(sections))
    cell = m.groupby(["section", "concept"])["p_known"].mean().unstack()
    rows = sorted(cell.index)
    return {"concepts": [{"id": c, "name": names[c]} for c in cols],
            "sections": [{"name": f"Section {s}", "students": int((pd.Series(sections) == s).sum()),
                          "values": [round(float(cell.at[s, c]), 3) for c in cols]} for s in rows]}


def build() -> dict:
    from ilm.adaptive import compare as cmp
    from ilm.analytics import dropout as D
    from ilm.graph.concept_graph import load_concepts
    from ilm.learners import simulator as sim
    from ilm.learners.split import student_split

    sim_dir = config.PROCESSED_DIR / "simulated"
    log = sim.public(pd.read_csv(sim_dir / "interactions.csv.gz"))
    people = pd.read_csv(sim_dir / "students.csv")[["student_id", "dropped_week", "finished_week"]]
    q_sec = log.groupby("question_id")["response_time_sec"].median()
    course = sim.Course.load(config.RANDOM_SEED)
    base = json.loads((sim_dir / "summary.json").read_text())["calibrated_drop_base"]

    # the risk model, as chosen in Day 2 (settings from reports/dropout/report.json)
    chosen = json.loads((config.PROJECT_ROOT / "reports" / "dropout" / "report.json").read_text())["chosen"]
    snaps = D.snapshot(log, people, q_sec)
    train, valid = student_split(snaps, student_col="student_id", test_frac=0.2)
    model = D.fit_lgbm(train, valid, chosen)
    cuts = D.cutoffs(model.predict_proba(valid[D.FEATURES])[:, 1])

    # the class: a fresh cohort the model never saw, at the checkpoint
    t_log, t_people = sim.run_course(cmp.students(course, seed=D.TEST_SEED), course, sim.FixedPath(course),
                                     D.TEST_SEED, base)
    t_log = sim.public(t_log)
    snap = D.snapshot(t_log, t_people[["student_id", "dropped_week", "finished_week"]], q_sec)
    now = snap[snap.week == WEEK].reset_index(drop=True)
    risk = model.predict_proba(now[D.FEATURES])[:, 1]
    sv = D._shap(model, now[D.FEATURES])
    now = now.assign(risk=risk, level=[D.level(s, cuts) for s in risk])

    concepts = load_concepts()
    names = {c["id"]: c["name"] for c in concepts}
    order = [c["id"] for c in concepts]
    params = pd.read_csv(config.MODELS_DIR / "bkt_concept_params.csv", index_col="concept")
    upto = t_log[t_log.week <= WEEK]
    students = now["student_id"].tolist()
    m = mastery_table(upto, params, students)
    enrol = sorted(t_people["student_id"])
    sections = {sid: i // SECTION_SIZE + 1 for i, sid in enumerate(enrol)}
    sections = {s: sections[s] for s in students}

    per_c = m.groupby("concept").agg(p_known=("p_known", "mean"), practised=("practised", "mean"),
                                     mastered=("mastered", "mean"))
    practised_enough = per_c[per_c.practised >= 0.2].sort_values("p_known")
    weakest = [{"id": c, "name": names[c], "known": round(float(r.p_known), 3),
                "mastered": round(float(r.mastered), 3), "practised": round(float(r.practised), 3)}
               for c, r in practised_enough.head(6).iterrows()]
    mastered_per_student = m.groupby("student_id")["mastered"].sum()

    at_risk = []
    for i, r in now.iterrows():
        if r.level == "low":
            continue
        push = sv.loc[i].sort_values(ascending=False)
        kind, top = D.reason(sv.loc[i])
        why = [w for f in push.index[:3] if push[f] > 0 and (w := in_words(f, r[f]))][:2]
        at_risk.append({"student_id": r.student_id, "section": sections[r.student_id], "level": r.level,
                        "risk": round(float(r.risk), 3), "reason": REASON_LABEL.get(kind, "Other"),
                        "why": why, "action": D.ACTION_TEXT[kind], "level_action": D.LEVEL_ACTION[r.level],
                        "answers_total": int(r.answers_total), "days_since_last": int(r.days_since_last),
                        "acc_last10": None if pd.isna(r.acc_last10) else round(float(r.acc_last10), 2),
                        "mastered": int(mastered_per_student.get(r.student_id, 0))})
    at_risk.sort(key=lambda x: -x["risk"])

    out = {
        "cohort": f"fresh simulated cohort (seed {D.TEST_SEED}), fixed course, week {WEEK} checkpoint",
        "week": WEEK, "enrolled": len(t_people), "in_class": len(now),
        "left_before_week": int(((t_people.dropped_week < WEEK) & t_people.dropped_week.notna()).sum()),
        "active_this_week": int((now.answers_this_week > 0).sum()),
        "high": int((now.level == "high").sum()), "medium": int((now.level == "medium").sum()),
        "avg_mastered": round(float(mastered_per_student.mean()), 1), "concepts_total": len(order),
        "weakest": weakest,
        "heatmap": heatmap(m, sections, order, names),
        "section_note": f"Demo cohort: sections are {SECTION_SIZE} students each, in enrolment order.",
        "at_risk": at_risk,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


@lru_cache(maxsize=1)
def load() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return build()


if __name__ == "__main__":
    d = build()
    print({k: v for k, v in d.items() if k not in ("heatmap", "at_risk", "weakest")})
    print("weakest:", [w["name"] for w in d["weakest"]], "| at risk:", len(d["at_risk"]),
          "| heatmap:", len(d["heatmap"]["sections"]), "x", len(d["heatmap"]["concepts"]))
