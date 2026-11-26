"""Personalised learning path: what to study next, how long it should take, and a short
motivating message in UrduLish (Urdu written in English letters, mixed with English terms).

From a student's answers so far (public data only):
  1. mastery     replay the answers through the BKT tracker (ilm.tracing.mastery)
  2. path        every concept not yet mastered, in course order (prerequisites first);
                 "ready" if its prerequisites are mastered, otherwise "after <prereq>";
                 "quick check" if P(known) >= 0.8 already (likely known, needs a short
                 streak to confirm), else "learn". Needed because 3 answers per concept (the
                 fixed path) rarely prove mastery: Ali truly knew his loops but slipped on
                 1 in 3 answers, so loops were 'likely known', not 'mastered', at week 4.
  3. time        per concept: expected answers to master x the concept's typical seconds per
                 answer x this student's speed
                   expected answers  Monte Carlo under the concept's BKT numbers, starting
                                     from the student's current P(known), until the SAME
                                     mastery rule the engine uses fires (3 in a row, >= 0.95)
                   typical seconds   median answer time on the concept's questions (everyone)
                   speed             median over the student's answers of
                                     (their time / everyone's median time on that question)
  4. message     template chosen from the numbers (strongest and weakest concepts among
                 those answered, quick checks, next step, recent accuracy, time per day) - no LLM, so it can never promise something the plan doesn't say

The time estimate is checked against what simulated students actually needed
(validate_estimates, reports/learning_path/estimate_check.json).

Run:  python -m ilm.adaptive.path    -> reports/learning_path/{ali,sara}.{json,md}, estimate_check.json
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from ilm import config
from ilm.tracing.mastery import MASTERED, STREAK, MasteryTracker

MINUTES_PER_DAY = 30       # the default daily study time the plan is laid out with
MAX_ANSWERS = 60           # Monte Carlo cap: "more than this" is reported as this
N_SIMS = 400
MIN_ANSWERS_FOR_SPEED = 5  # fewer answers than this: assume average speed
CHECK_AT = 0.8             # P(known) from which a concept is a quick check, not a lesson


@dataclass
class Step:
    concept: str
    name: str
    p_known: float
    kind: str                   # "quick check" or "learn"
    status: str                 # "ready" or "after <prerequisite names>"
    lessons: list[str]
    est_answers: float
    est_minutes: float


# ------------------------------------------------------------------ estimates ----
def expected_answers(row: pd.Series, p_known: float, streak: int = 0, n_sims: int = N_SIMS,
                     seed: int = 0) -> float:
    """Mean answers until the mastery rule fires, simulating the BKT model itself.
    Truly-known state starts known with probability p_known; each answer can teach it."""
    rng = np.random.default_rng(seed)
    prior, learns, guess, slip = (float(row[k]) for k in ("prior", "learns", "guesses", "slips"))
    known = rng.random(n_sims) < p_known                      # hidden state of each run
    belief = np.full(n_sims, p_known)                          # what the tracker believes
    run = np.full(n_sims, streak)
    done = np.zeros(n_sims, dtype=bool)
    count = np.zeros(n_sims)
    for _ in range(MAX_ANSWERS):
        active = ~done
        if not active.any():
            break
        right = rng.random(n_sims) < np.where(known, 1 - slip, guess)
        with np.errstate(divide="ignore", invalid="ignore"):   # np.where computes both branches
            post = np.where(right, belief * (1 - slip) / (belief * (1 - slip) + (1 - belief) * guess),
                            belief * slip / (belief * slip + (1 - belief) * (1 - guess)))
        new_belief = post + (1 - post) * learns
        belief = np.where(active, new_belief, belief)
        run = np.where(active, np.where(right, run + 1, 0), run)
        known = known | (active & (rng.random(n_sims) < learns))
        count += active
        done |= (belief >= MASTERED) & (run >= STREAK)
    return float(count.mean())


def question_seconds(log: pd.DataFrame) -> pd.Series:
    """Everyone's median answer time per question."""
    return log.groupby("question_id")["response_time_sec"].median()


def concept_seconds(log: pd.DataFrame) -> pd.Series:
    return log.groupby("concept")["response_time_sec"].median()


def speed_factor(history: pd.DataFrame, q_seconds: pd.Series) -> float:
    """> 1: slower than most students, < 1: faster. Median, so one slow answer doesn't swing it."""
    if len(history) < MIN_ANSWERS_FOR_SPEED:
        return 1.0
    ratio = history["response_time_sec"].to_numpy() / q_seconds.reindex(history["question_id"]).to_numpy()
    ratio = ratio[np.isfinite(ratio)]
    return float(np.median(ratio)) if len(ratio) else 1.0


# ------------------------------------------------------------------ the path ----
def build_path(history: pd.DataFrame, course, params: pd.DataFrame, names: dict[str, str],
               lessons: dict[str, list[str]], q_seconds: pd.Series, c_seconds: pd.Series,
               minutes_per_day: int = MINUTES_PER_DAY) -> dict:
    """history: one student's public answers in order (question_id, concept, correct,
    response_time_sec)."""
    tracker = MasteryTracker(params)
    for c, ok in zip(history["concept"], history["correct"]):
        tracker.update(c, bool(ok))
    speed = speed_factor(history, q_seconds)
    mastered = [c for c in course.order if tracker.mastered(c)]
    steps = []
    for c in course.order:
        if tracker.mastered(c):
            continue
        missing = [p for p in course.prereqs.get(c, []) if not tracker.mastered(p)]
        n = expected_answers(params.loc[c], tracker.p_known(c), tracker.streak.get(c, 0),
                             seed=course.order.index(c))
        steps.append(Step(c, names.get(c, c), round(tracker.p_known(c), 3),
                          "quick check" if tracker.p_known(c) >= CHECK_AT else "learn",
                          "ready" if not missing else "after " + ", ".join(names.get(p, p) for p in missing),
                          lessons.get(c, []), round(n, 1),
                          round(n * float(c_seconds.get(c, c_seconds.median())) * speed / 60, 1)))
    total = sum(s.est_minutes for s in steps)
    answered = list(dict.fromkeys(history["concept"]))
    rights = history.groupby("concept")["correct"].sum()
    rank = sorted(answered, key=lambda c: (-round(tracker.p_known(c), 2), -rights.get(c, 0), course.order.index(c)))
    recent = history["correct"].tail(10)
    plan = {
        "answers_so_far": len(history),
        "speed_factor": round(speed, 2),
        "recent_accuracy": round(float(recent.mean()), 2) if len(recent) else None,
        "mastered": [names.get(c, c) for c in mastered],
        "strongest": [names.get(c, c) for c in rank[:2]],
        "weakest": [names.get(c, c) for c in rank[::-1][:2]] if len(rank) >= 4 else [],
        "quick_checks": sum(s.kind == "quick check" for s in steps),
        "quick_check_minutes": round(sum(s.est_minutes for s in steps if s.kind == "quick check")),
        "path": [asdict(s) for s in steps],
        "total_minutes": round(total),
        "minutes_per_day": minutes_per_day,
        "days_at_that_pace": math.ceil(total / minutes_per_day) if steps else 0,
    }
    plan["message"] = urdulish_message(plan, history)
    return plan


# ------------------------------------------------------------------ the message ----
def _minutes(m: float) -> str:
    return f"{m / 60:.1f} ghante" if m >= 90 else f"{max(1, round(m))} minute"


def urdulish_message(plan: dict, history: pd.DataFrame, name: str | None = None) -> str:
    """Short, specific, honest: every number in it comes from the plan."""
    hi = f"{name}, " if name else ""
    steps = plan["path"]
    if not steps:
        return f"{hi}MashaAllah! Saare concepts master ho gaye. Ab revision karte raho taake yaad rahe."
    ready = [s for s in steps if s["status"] == "ready"]
    nxt = next((s for s in ready if s["kind"] == "learn"), ready[0] if ready else steps[0])
    lines = []
    if not len(history):
        lines.append(f"{hi}Ilm Academy mein khush aamdeed! Shuru karte hain {nxt['name']} se.")
    else:
        lines.append(f"{hi}{' aur '.join(plan['strongest'])} pe tumhari grip zabardast hai, shabaash!")
        if plan["weakest"]:
            lines.append(f"{' aur '.join(plan['weakest'])} pe thodi aur practice chahiye, "
                         "aur hum wahi saath mil kar karenge.")
    acc = plan["recent_accuracy"]
    if acc is not None and acc < 0.5:
        lines.append("Pichle kuch sawaal mushkil lage? Ye bilkul normal hai, ghalti hi se seekhte hain.")
    if plan["quick_checks"] and len(history):
        lines.append(f"{plan['quick_checks']} concept{'s' if plan['quick_checks'] > 1 else ''} tum shayad pehle se jaante ho: un ka quick check "
                     f"(taqreeban {_minutes(plan['quick_check_minutes'])}).")
    if len(history):
        lines.append(f"Agla naya concept: {nxt['name']} (taqreeban {_minutes(nxt['est_minutes'])}).")
    lines.append(f"Roz sirf {plan['minutes_per_day']} minute do, aur poora course "
                 f"{plan['days_at_that_pace']} din mein complete. Chalo, shuru karein!")
    return " ".join(lines)


# ------------------------------------------------------------------ checking the estimate ----
def validate_estimates(log: pd.DataFrame, course, params: pd.DataFrame, q_seconds: pd.Series,
                       c_seconds: pd.Series, max_students: int = 300) -> dict:
    """For each (student, concept) the adaptive engine taught to mastery: the estimate made
    just BEFORE the first answer on that concept (using only earlier answers) vs the time the
    student actually spent until mastery was earned."""
    rows = []
    for sid, h in list(log.groupby("student_id", sort=False))[:max_students]:
        h = h.reset_index(drop=True)
        tracker = MasteryTracker(params)
        start: dict[str, tuple[int, float]] = {}
        spent: dict[str, float] = {}
        for i, (c, ok, t) in enumerate(zip(h["concept"], h["correct"], h["response_time_sec"])):
            if c not in start and not tracker.mastered(c):
                n = expected_answers(params.loc[c], tracker.p_known(c), tracker.streak.get(c, 0),
                                     n_sims=200, seed=i)
                est = n * float(c_seconds.get(c, c_seconds.median())) * speed_factor(h.iloc[:i], q_seconds) / 60
                start[c] = (i, est)
                spent[c] = 0.0
            if c in spent:
                spent[c] += t / 60
            tracker.update(c, bool(ok))
            if c in spent and tracker.mastered(c):
                rows.append({"student_id": sid, "concept": c, "est": start[c][1], "actual": spent.pop(c)})
    d = pd.DataFrame(rows)
    ratio = d["actual"] / d["est"]
    return {
        "pairs": len(d), "students": int(d["student_id"].nunique()),
        "median_estimate_min": round(float(d["est"].median()), 1),
        "median_actual_min": round(float(d["actual"].median()), 1),
        "median_actual_over_estimate": round(float(ratio.median()), 2),
        "share_within_x2": round(float(((ratio >= 0.5) & (ratio <= 2)).mean()), 3),
        "spearman": round(float(d["est"].corr(d["actual"], method="spearman")), 3),
        "note": "Only concepts that reached mastery: students who quit mid-concept have no actual time.",
    }


# ------------------------------------------------------------------ run ----
def _course_lookup():
    from ilm.content.download import all_lessons
    from ilm.graph.concept_graph import load_concepts
    titles = {l["id"]: l["title"] for l in all_lessons()}
    concepts = load_concepts()
    names = {c["id"]: c["name"] for c in concepts}
    lessons = {c["id"]: [f"{l}: {titles.get(l, l)}" for l in c.get("taught_in", [])] for c in concepts}
    return names, lessons


def to_markdown(who: str, persona: str, plan: dict, upto_week: int) -> str:
    lines = [f"# Learning path: {who}", "", f"*{persona}. Planned from the public answers of weeks 1-{upto_week} "
             f"({plan['answers_so_far']} answers); speed factor {plan['speed_factor']} (1 = typical).*", "",
             f"> {plan['message']}", "",
             f"**Mastered ({len(plan['mastered'])}):** {', '.join(plan['mastered']) or 'none yet'}", "",
             f"**Strongest:** {', '.join(plan['strongest'])}. **Weakest:** {', '.join(plan['weakest']) or '-'}.", "",
             f"**Still to do:** {len(plan['path'])} concepts ({plan['quick_checks']} quick checks), about {plan['total_minutes'] / 60:.1f} hours "
             f"= {plan['days_at_that_pace']} days at {plan['minutes_per_day']} min/day.", "",
             "| # | concept | P(known) now | kind | status | est. answers | est. minutes | lesson |",
             "|---|---|---|---|---|---|---|---|"]
    for i, s in enumerate(plan["path"][:15], 1):
        lines.append(f"| {i} | {s['name']} | {s['p_known']:.2f} | {s['kind']} | {s['status']} | {s['est_answers']} | "
                     f"{s['est_minutes']} | {'; '.join(s['lessons'])} |")
    if len(plan["path"]) > 15:
        lines.append(f"| ... | {len(plan['path']) - 15} more in the JSON | | | | | | |")
    return "\n".join(lines) + "\n"


def main() -> None:
    from ilm.adaptive import compare as cmp
    from ilm.learners import simulator as sim
    from ilm.tracing.mastery import PARAMS_FILE

    course = sim.Course.load(config.RANDOM_SEED)
    params = pd.read_csv(PARAMS_FILE, index_col=0)
    names, lessons = _course_lookup()
    sim_dir = config.PROCESSED_DIR / "simulated"
    log = sim.public(pd.read_csv(sim_dir / "interactions.csv.gz")).sort_values(["student_id", "seq"])
    q_sec, c_sec = question_seconds(log), concept_seconds(log)
    personas = pd.read_csv(sim_dir / "students.csv").set_index("student_id")["persona"]

    out = config.REPORTS_DIR / "learning_path"
    out.mkdir(parents=True, exist_ok=True)
    upto = 4                                   # a "week-4 check-in" on the fixed course
    for who in ("ali", "sara"):
        h = log[(log.student_id == who) & (log.week <= upto)]
        plan = build_path(h, course, params, names, lessons, q_sec, c_sec)
        plan["message"] = urdulish_message(plan, h, name=who.capitalize())
        (out / f"{who}.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
        (out / f"{who}.md").write_text(to_markdown(who.capitalize(), personas[who], plan, upto), encoding="utf-8")
        print(who, plan["message"], f"| {len(plan['path'])} concepts, {plan['total_minutes']} min", flush=True)

    # is the time estimate any good? check it on adaptive-engine runs (fresh students)
    base = json.loads((sim_dir / "summary.json").read_text())["calibrated_drop_base"]
    group = cmp.students(course, n=300, seed=cmp.EVAL_SEED)
    adaptive_log, _ = sim.run_course(group, course, cmp.engine(course, cmp.EVAL_SEED), cmp.EVAL_SEED, base)
    check = validate_estimates(sim.public(adaptive_log), course, params, q_sec, c_sec)
    (out / "estimate_check.json").write_text(json.dumps(check, indent=1), encoding="utf-8")
    print(json.dumps(check, indent=1))


if __name__ == "__main__":
    main()
