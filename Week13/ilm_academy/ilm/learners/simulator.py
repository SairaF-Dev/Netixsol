"""Simulated learners for the Ilm Academy Python course.

Why simulate? Real data (ASSISTments) has no dropout labels, is about maths rather than our
course, and never tells us the TRUTH (what a student really knew). A simulator does, so Day 2
can be scored against the truth: did IRT find the planted bad questions? Did the adaptive
engine beat the fixed path?

Why NOT trust it alone? It follows rules we wrote. A model can look great on simulated data
just by rediscovering our rules. Model comparisons are therefore done on REAL data first.

Every student has hidden traits (truth_*): ability, learning rate, speed, slip, motivation.
  knowledge  per concept: known or not. Practice can make it known, faster when its
             prerequisites are known (so the concept graph matters).
  answer     P(correct) = guess + (1 - guess - slip) * sigmoid(a * (ability + BOOST*known - b))
             a, b = the question's hidden discrimination and difficulty. A few questions are
             planted "bad" (a near 0): strong and weak students do equally well on them.
  forgetting a known concept can be forgotten if not practised for a long time.
  dropout    each week: chance rises with recent failures, low motivation and inactivity.
             The base rate is calibrated so ~45% quit before week 4 (the client's number).

Columns starting with truth_ are the ANSWER KEY. They must never be used as model inputs.

Run:  python -m ilm.learners.simulator            (1,000 students + Ali and Sara)
"""
from __future__ import annotations

import argparse
import collections
import json
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ilm import config

# ------------------------------------------------------------------ constants ----
WEEKS = 8
QUESTIONS_PER_SESSION = 8
QUESTIONS_PER_CONCEPT = 3      # fixed path: same number for everyone, mastered or not
MASTERY_BOOST = 2.5            # how much knowing the concept raises the logit
DIFFICULTY_OFFSET = 1.0        # unknown concept + average student = usually wrong
BAD_QUESTION_SHARE = 0.05
FORGET_STABILITY_DAYS = 30.0   # grows with each successful practice
GUESS = {"mcq": None, "short": 0.05, "code": 0.02}  # mcq: 1 / number of options
BASE_SECONDS = {"mcq": 25.0, "short": 45.0, "code": 240.0}
DROPOUT_TARGET = 0.45          # share of students gone before week 4 (client's figure)
DROPOUT_BY_WEEK = 3            # "before week 4" = during weeks 1-3

ALI_STRONG = ["while_loops", "for_loops", "range_function", "break_continue",
              "nested_loops", "iterating_lists"]
ALI_WEAK = ["defining_functions", "parameters", "return_values", "scope",
            "args_kwargs", "lambda_functions", "recursion"]


def public(df: pd.DataFrame) -> pd.DataFrame:
    """What a real platform could observe: everything except the truth_* answer key.
    Day 2 models must be trained on public(...) only."""
    return df[[c for c in df.columns if not c.startswith("truth_")]]


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ------------------------------------------------------------------ course ----
@dataclass
class Course:
    order: list[str]                         # fixed study order of concepts
    prereqs: dict[str, list[str]]
    depth: dict[str, int]
    questions: dict[str, list[str]]          # concept -> question ids (fixed order)
    truth: pd.DataFrame                      # one row per question, indexed by id
    info: dict = field(default_factory=dict)  # same data as plain dicts: fast lookups

    def __post_init__(self):
        self.info = self.truth.to_dict("index")

    @classmethod
    def load(cls, seed: int = config.RANDOM_SEED) -> "Course":
        from ilm.content.download import all_lessons
        from ilm.graph.concept_graph import build_graph, depth_levels, learning_order, load_concepts
        from ilm.questions.validate import load_bank

        g = build_graph(load_concepts())
        order = learning_order(g, {l["id"]: l["order"] for l in all_lessons()})
        questions, rep = load_bank()
        if not rep.ok:
            raise ValueError(f"question bank invalid: {rep.errors[:3]}")
        # Within a concept: one fixed shuffled order, the same for every student. NOT easy
        # first: that made each attempt harder than the last and hid the learning curve
        # (simulated accuracy fell with practice while real students' rose; found 2026-11-26).
        by_concept = collections.defaultdict(list)
        for q in sorted(questions, key=lambda q: q.id):
            by_concept[q.concepts[0]].append(q.id)
        order_rng = np.random.default_rng(seed + 1)
        for ids in by_concept.values():
            order_rng.shuffle(ids)
        return cls(order=order, prereqs={c: list(g.predecessors(c)) for c in g},
                   depth=depth_levels(g), questions=dict(by_concept),
                   truth=question_truth(questions, np.random.default_rng(seed)))


def question_truth(questions, rng: np.random.Generator) -> pd.DataFrame:
    """Hidden question parameters. True difficulty follows the author's 1-5 guess, with
    noise: the guess is informative but not exact (Day 3 measures how far off it is)."""
    rows = []
    for q in sorted(questions, key=lambda q: q.id):
        bad = rng.random() < BAD_QUESTION_SHARE
        rows.append({
            "question_id": q.id, "concept": q.concepts[0], "qtype": q.type,
            "author_difficulty": q.difficulty,
            "truth_b": round((q.difficulty - 3) * 0.6 + rng.normal(0, 0.5), 3),
            "truth_a": round(rng.uniform(0.0, 0.15) if bad else rng.lognormal(0.2, 0.25), 3),
            "truth_guess": round(1 / len(q.options) if q.type == "mcq" else GUESS[q.type], 3),
            "truth_bad": bad,
        })
    return pd.DataFrame(rows).set_index("question_id")


# ------------------------------------------------------------------ student ----
@dataclass
class SimStudent:
    student_id: str
    ability: float
    learn_rate: float
    speed: float               # time multiplier: < 1 is fast
    slip: float
    motivation: float
    persona: str = ""
    weak: dict[str, float] = field(default_factory=dict)   # concept -> learn-rate multiplier
    known: set[str] = field(default_factory=set)
    last_seen: dict[str, int] = field(default_factory=dict)
    reps: collections.Counter = field(default_factory=collections.Counter)
    recent: collections.deque = field(default_factory=lambda: collections.deque(maxlen=10))

    def traits(self) -> dict:
        return {"student_id": self.student_id, "persona": self.persona,
                "truth_ability": round(self.ability, 3), "truth_learn_rate": round(self.learn_rate, 3),
                "truth_speed": round(self.speed, 3), "truth_slip": round(self.slip, 3),
                "truth_motivation": round(self.motivation, 3)}

    def answer(self, qid: str, course: Course, day: int, rng: np.random.Generator) -> dict:
        """Answer one question: forget, respond, then maybe learn from the practice."""
        q = course.info[qid]
        c = q["concept"]
        if c in self.known and c in self.last_seen:           # forgetting
            gap = day - self.last_seen[c]
            if rng.random() < 1 - math.exp(-gap / (FORGET_STABILITY_DAYS * (1 + self.reps[c]))):
                self.known.discard(c)
        knew = c in self.known
        logit = q["truth_a"] * (self.ability + MASTERY_BOOST * knew - q["truth_b"] - DIFFICULTY_OFFSET)
        p = q["truth_guess"] + (1 - q["truth_guess"] - self.slip) * sigmoid(logit)
        correct = bool(rng.random() < p)
        seconds = (BASE_SECONDS[q["qtype"]] * self.speed * (1 + 0.15 * (q["truth_b"] + 2))
                   * rng.lognormal(0, 0.3))

        if not knew:                                           # learning from practice
            pre = course.prereqs.get(c, [])
            ready = sum(p_ in self.known for p_ in pre) / len(pre) if pre else 1.0
            p_learn = self.learn_rate * self.weak.get(c, 1.0) * (0.15 + 0.85 * ready)
            if rng.random() < p_learn:
                self.known.add(c)
        elif correct:
            self.reps[c] += 1
        self.last_seen[c] = day
        self.recent.append(correct)
        return {"question_id": qid, "concept": c, "qtype": q["qtype"], "correct": int(correct),
                "response_time_sec": round(seconds, 1), "truth_knew": int(knew), "truth_p_correct": round(p, 3)}


def make_student(i: int, rng: np.random.Generator, course: Course) -> SimStudent:
    ability = rng.normal(0, 1)
    s = SimStudent(
        student_id=f"s{i:04d}", ability=ability,
        learn_rate=float(np.clip(0.30 + 0.08 * ability + rng.normal(0, 0.05), 0.05, 0.7)),
        speed=float(rng.lognormal(0, 0.35)), slip=float(rng.beta(2, 18)),
        motivation=float(rng.normal(0, 1)))
    for c in course.order:   # some students already know the basics
        if rng.random() < sigmoid(ability - 1.0 - 0.6 * course.depth[c]):
            s.known.add(c)
    return s


def personas(course: Course) -> list[SimStudent]:
    """The two students from the Day 2 scenario."""
    def with_ancestors(concepts):
        out, stack = set(), list(concepts)
        while stack:
            c = stack.pop()
            if c not in out:
                out.add(c)
                stack += course.prereqs.get(c, [])
        return out
    ali = SimStudent("ali", ability=0.3, learn_rate=0.35, speed=1.0, slip=0.08, motivation=0.5,
                     persona="Ali: strong in loops, weak in functions",
                     weak={c: 0.3 for c in ALI_WEAK})
    ali.known = with_ancestors(ALI_STRONG) - set(ALI_WEAK)
    sara = SimStudent("sara", ability=0.8, learn_rate=0.4, speed=0.45, slip=0.30, motivation=0.5,
                      persona="Sara: fast but careless")
    return [ali, sara]


# ------------------------------------------------------------------ the course run ----
class FixedPath:
    """The client's current system: everyone gets the same concepts in the same order,
    QUESTIONS_PER_CONCEPT each, whether they have mastered them or not."""
    name = "fixed"

    def __init__(self, course: Course):
        self.plan = [q for c in course.order
                     for q in (course.questions[c] * QUESTIONS_PER_CONCEPT)[:QUESTIONS_PER_CONCEPT]]
        self.pos: dict[str, int] = collections.defaultdict(int)

    def next_question(self, student: SimStudent) -> str | None:
        i = self.pos[student.student_id]
        if i >= len(self.plan):
            return None
        self.pos[student.student_id] += 1
        return self.plan[i]


def run_course(students: list[SimStudent], course: Course, policy, seed: int,
               drop_base: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate WEEKS weeks. Returns (interactions, students)."""
    rows, people = [], []
    seeds = np.random.SeedSequence(seed).spawn(len(students))   # student i is reproducible
    for s, ss in zip(students, seeds):
        rng = np.random.default_rng(ss)
        seq, dropped, finished = 0, None, None
        for week in range(1, WEEKS + 1):
            n_sessions = int(min(7, rng.poisson(3 * math.exp(0.3 * s.motivation))))
            days = sorted(rng.choice(7, size=n_sessions, replace=False)) if n_sessions else []
            for session, d in enumerate(days):
                day = (week - 1) * 7 + int(d)
                for _ in range(QUESTIONS_PER_SESSION):
                    qid = policy.next_question(s)
                    if qid is None:
                        finished = finished or week
                        break
                    seq += 1
                    rows.append({"student_id": s.student_id, "seq": seq, "week": week, "day": day,
                                 "session": session, **s.answer(qid, course, day, rng)})
            if finished:
                break
            recent = (1 - sum(s.recent) / len(s.recent)) if s.recent else 0.5
            hazard = sigmoid(drop_base + 2.0 * (recent - 0.5) - 0.6 * s.motivation
                             + 1.0 * (n_sessions == 0))
            if rng.random() < hazard:
                dropped = week
                break
        people.append({**s.traits(), "dropped_week": dropped, "finished_week": finished,
                       "n_answers": seq, "truth_known_at_end": len(s.known)})
    return pd.DataFrame(rows), pd.DataFrame(people)


def dropout_rate(people: pd.DataFrame, by_week: int = DROPOUT_BY_WEEK) -> float:
    return float((people["dropped_week"].fillna(99) <= by_week).mean())


def simulate(n: int = 1000, seed: int = config.RANDOM_SEED, drop_base: float = -2.0,
             course: Course | None = None, with_personas: bool = True):
    course = course or Course.load(seed)
    rng = np.random.default_rng(seed)
    students = [make_student(i, rng, course) for i in range(n)]
    if with_personas:
        students += personas(course)
    return run_course(students, course, FixedPath(course), seed, drop_base)


def calibrate_drop_base(course: Course, n: int = 1000, seed: int = config.RANDOM_SEED,
                        target: float = DROPOUT_TARGET, steps: int = 12) -> float:
    """Bisection: the base hazard that makes `target` of students quit by week 3.
    Dropout rises with drop_base, so bisection is safe."""
    lo, hi = -6.0, 2.0
    for _ in range(steps):
        mid = (lo + hi) / 2
        _, people = simulate(n, seed, mid, course, with_personas=False)
        if dropout_rate(people) < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 3)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    a = p.parse_args()
    course = Course.load(a.seed)
    base = calibrate_drop_base(course, a.n, a.seed)
    log, people = simulate(a.n, a.seed, base, course)

    out = config.PROCESSED_DIR / "simulated"
    out.mkdir(parents=True, exist_ok=True)
    log.to_csv(out / "interactions.csv.gz", index=False)
    people.to_csv(out / "students.csv", index=False)
    course.truth.to_csv(out / "questions_truth.csv")
    random_students = people[people["persona"] == ""]
    summary = {
        "students": int(len(random_students)), "personas": people.loc[people["persona"] != "", "student_id"].tolist(),
        "interactions": int(len(log)), "seed": a.seed, "calibrated_drop_base": base,
        "dropout_before_week4": round(dropout_rate(random_students), 3),
        "dropped_by_week": {int(w): int(n) for w, n in random_students["dropped_week"].value_counts().sort_index().items()},
        "finished_course": int(random_students["finished_week"].notna().sum()),
        "overall_accuracy": round(float(log["correct"].mean()), 3),
        "bad_questions_planted": int(course.truth["truth_bad"].sum()),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
