"""A/B test of the adaptive path against the fixed path (Day 5 Task 2).

The design is in reports/ab_test/design.md (the pre-registration). This module holds the parts
a real test runs on, so they are written and checked before any student is enrolled:

  assign()        which arm a new student gets: a hash of the id, stable, no table to leak
  n_per_arm()     students needed per arm for a difference in proportions (and mde() backwards)
  srm()           sample-ratio check: were the arms really split 50/50?
  compare()       difference between arms with a 95% interval (unpaired, as in a real test)
  decide()        the pre-registered decision rule, applied to the results

`python -m ilm.evaluation.ab_test` rehearses the whole test on FRESH simulated students
(seed 2028, never used before), and writes reports/ab_test/rehearsal.json:
  - A/A tests: the fixed path against itself, 1,000 different splits. It should find a
    "difference" about 5% of the time and no more, or the analysis is broken.
  - the A/B test at the planned size, analysed exactly as the real one will be.
  - empirical power: how often a test of this size detects the simulator's effect.
The simulator's effect is not a forecast for real students (it rewards what the engine does),
which is why the sample size is planned for a much smaller effect than the simulator shows.
"""
from __future__ import annotations

import hashlib
import json
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

from ilm import config

Z = NormalDist().inv_cdf
SALT = "ilm-ab-adaptive-v1"         # fixed before launch; a new test gets a new salt

# ---- the pre-registered numbers (design.md section 4); change them only before launch ----
BASELINE_DROPOUT = 0.45             # scenario: 45% drop out before week 4 on the fixed path
MDE = 0.04                          # smallest drop in dropout worth shipping: 45% -> 41%
ALPHA = 0.05                        # two-sided
POWER = 0.80
LOSS = 0.10                         # extra enrolment for accounts that never start, test users etc.
GAIN_MARGIN_SD = 0.20               # learning gain may not be worse by more than 0.2 SD (non-inferiority)
HOURS_GUARDRAIL = 0.20              # study time may not rise by more than 20%
HARM_Z = 2.8                        # interim stop for harm: dropout WORSE with z above this (halfway look)


def assign(student_id: str, salt: str = SALT) -> str:
    """'adaptive' or 'fixed'. A hash, so the same student always gets the same arm, the split
    needs no stored table, and nobody (teacher or engineer) chooses who goes where."""
    h = int(hashlib.sha256(f"{salt}:{student_id}".encode()).hexdigest()[:8], 16)
    return "adaptive" if h % 2 else "fixed"


def n_per_arm(p0: float = BASELINE_DROPOUT, mde: float = MDE, alpha: float = ALPHA, power: float = POWER) -> int:
    """Students per arm to detect a change of `mde` in a proportion (normal approximation)."""
    p1 = p0 - mde
    za, zb = Z(1 - alpha / 2), Z(power)
    n = (za * math.sqrt(2 * p0 * (1 - p0)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / mde ** 2
    return math.ceil(n)


def mde(n: int, p0: float = BASELINE_DROPOUT, alpha: float = ALPHA, power: float = POWER) -> float:
    """Smallest change detectable with n students per arm (the inverse of n_per_arm)."""
    lo, hi = 1e-4, p0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if n_per_arm(p0, mid, alpha, power) > n else (lo, mid)
    return round(hi, 4)


def enrolment_needed() -> int:
    return math.ceil(2 * n_per_arm() * (1 + LOSS))


def srm(n_a: int, n_b: int) -> float:
    """p-value that a 50/50 split produced these counts. Below 0.001: stop and find the bug
    (a broken assignment, one arm's sign-ups failing...) before reading any result."""
    n = n_a + n_b
    z = (n_a - n / 2) / math.sqrt(n / 4)
    return 2 * (1 - NormalDist().cdf(abs(z)))


def compare(a: pd.Series, b: pd.Series) -> dict:
    """Mean of arm b minus arm a, with a 95% interval (unpooled standard error; for 0/1 values
    this is the usual difference in proportions)."""
    a, b = a.dropna(), b.dropna()
    d = b.mean() - a.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = d / se if se else 0.0
    return {"fixed": round(float(a.mean()), 4), "adaptive": round(float(b.mean()), 4), "diff": round(float(d), 4),
            "low": round(float(d - 1.96 * se), 4), "high": round(float(d + 1.96 * se), 4),
            "z": round(float(z), 2), "p": round(2 * (1 - NormalDist().cdf(abs(z))), 4)}


def balance(a: pd.Series, b: pd.Series) -> float:
    """Standardised mean difference of a pre-test covariate. Above 0.1 = the arms differ at the start."""
    sd = math.sqrt((a.var() + b.var()) / 2)
    return round(float((b.mean() - a.mean()) / sd), 3) if sd else 0.0


def analyse(df: pd.DataFrame) -> dict:
    """df: one row per student with arm, pretest, dropped_by_week4, gain, hours, hours_per_concept.
    Every metric is analysed for every student who was assigned (intention to treat)."""
    f, a = df[df.arm == "fixed"], df[df.arm == "adaptive"]
    out = {"n_fixed": len(f), "n_adaptive": len(a), "srm_p": round(srm(len(f), len(a)), 4),
           "pretest_balance_smd": balance(f.pretest, a.pretest)}
    for m in ("dropped_by_week4", "gain", "hours", "hours_per_concept", "dropped_ever"):
        if m in df:
            out[m] = compare(f[m], a[m])
    out["gain_margin"] = round(GAIN_MARGIN_SD * float(f.gain.std()), 3)
    return out


def decide(r: dict) -> dict:
    """The pre-registered rule (design.md section 7). Returns the decision and why."""
    why = []
    if r["srm_p"] < 0.001:
        return {"decision": "invalid: fix the split and rerun", "why": [f"sample ratio p = {r['srm_p']}"]}
    drop, gain, hours = r["dropped_by_week4"], r["gain"], r["hours"]
    fewer_drop = drop["high"] < 0
    gain_ok = gain["low"] > -r["gain_margin"]
    hours_ok = hours["high"] <= HOURS_GUARDRAIL * hours["fixed"]
    why.append(f"week-4 dropout {drop['diff']:+.1%} [{drop['low']:+.1%}, {drop['high']:+.1%}]: "
               + ("lower, the interval excludes 0" if fewer_drop else "not shown to be lower"))
    why.append(f"learning gain {gain['diff']:+.2f} [{gain['low']:+.2f}, {gain['high']:+.2f}] vs margin "
               f"-{r['gain_margin']:.2f}: " + ("not worse" if gain_ok else "may be worse than the margin allows"))
    why.append(f"study hours {hours['diff']:+.2f} [{hours['low']:+.2f}, {hours['high']:+.2f}] vs guardrail "
               f"+{HOURS_GUARDRAIL * hours['fixed']:.2f}: " + ("ok" if hours_ok else "too much extra work"))
    if fewer_drop and gain_ok and hours_ok:
        decision = "ship the adaptive path"
    elif fewer_drop and not gain_ok:
        decision = "do not ship as is: students stay but learn less; tune the pace and test again"
    elif drop["low"] > 0:
        decision = "do not ship: dropout is higher"
    else:
        decision = "keep the fixed path: no clear benefit"
    return {"decision": decision, "why": why}


# ------------------------------------------------------------------ rehearsal ----
REHEARSAL_SEED = 2028               # fresh: not the training (42), development (2026) or confirmation (2027) group


def simulate(n: int, seed: int = REHEARSAL_SEED) -> pd.DataFrame:
    """Both policies on the SAME n fresh students (the simulator allows it, real life does not).
    One row per student with the outcome under each policy, so any split can be tried later."""
    from ilm.adaptive.compare import engine, outcomes, students
    from ilm.learners import simulator as sim
    course = sim.Course.load(config.RANDOM_SEED)
    base = json.loads((config.PROCESSED_DIR / "simulated" / "summary.json").read_text())["calibrated_drop_base"]
    frames = {}
    for arm, make in (("fixed", lambda: sim.FixedPath(course)), ("adaptive", lambda: engine(course, seed))):
        group = students(course, n=n, seed=seed)
        pre = pd.Series({s.student_id: len(s.known) for s in group}, name="pretest")
        log, people = sim.run_course(group, course, make(), seed, base)
        o = outcomes(log, people).join(pre)
        o["gain"] = o["truth_known_at_end"] - o["pretest"]
        o["hours_per_concept"] = o["hours"] / o["gain"].where(o["gain"] > 0)
        frames[arm] = o.rename(columns={"dropped_by_week3": "dropped_by_week4"})   # by week 3 = before week 4
        print(f"simulated {arm}: {len(o)} students", flush=True)
    both = frames["fixed"].add_suffix("_fixed").join(frames["adaptive"].add_suffix("_adaptive"))
    both.index = both.index.astype(str)
    return both


METRICS = ("dropped_by_week4", "gain", "hours", "hours_per_concept", "dropped_ever")


def experiment(both: pd.DataFrame, salt: str, aa: bool = False) -> pd.DataFrame:
    """One randomised experiment: each student is seen under the arm the hash gives them only.
    aa=True: both 'arms' get the fixed path (an A/A test)."""
    arm = pd.Series([assign(i, salt) for i in both.index], index=both.index)
    rows = pd.DataFrame({"arm": arm, "pretest": both["pretest_fixed"]})
    treated = (arm == "adaptive") if not aa else pd.Series(False, index=both.index)
    for m in METRICS:
        rows[m] = np.where(treated, both[f"{m}_adaptive"], both[f"{m}_fixed"])
    return rows


def rehearse(n_students: int | None = None, aa_runs: int = 1000, power_runs: int = 500) -> dict:
    n_arm = n_per_arm()
    n = n_students or 2 * n_arm
    both = simulate(n)
    paired = {m: round(float((both[f"{m}_adaptive"] - both[f"{m}_fixed"]).mean()), 4) for m in METRICS}

    aa_hits, aa_srm = 0, 0
    for k in range(aa_runs):
        r = analyse(experiment(both, f"aa-{k}", aa=True))
        aa_hits += r["dropped_by_week4"]["p"] < ALPHA
        aa_srm += r["srm_p"] < 0.001

    main = analyse(experiment(both, SALT))

    # power at the planned size, and at the size needed for the simulator's own effect
    rng = np.random.default_rng(0)
    def power_at(per_arm: int) -> float:
        hits = 0
        for k in range(power_runs):
            sample = both.iloc[rng.choice(len(both), size=min(2 * per_arm, len(both)), replace=False)]
            hits += analyse(experiment(sample, f"pw-{k}"))["dropped_by_week4"]["high"] < 0
        return round(hits / power_runs, 3)

    return {
        "design": {"baseline_dropout": BASELINE_DROPOUT, "mde": MDE, "alpha": ALPHA, "power": POWER,
                   "n_per_arm": n_arm, "enrol_with_loss": enrolment_needed(),
                   "mde_table": {str(k): mde(k) for k in (500, 1000, 2000, 2500, 4000)},
                   "n_table": {f"{d:.0%}": n_per_arm(mde=d) for d in (0.03, 0.04, 0.05, 0.08, 0.11)}},
        "rehearsal": {"seed": REHEARSAL_SEED, "students": len(both),
                      "simulated_dropout_fixed": round(float(both["dropped_by_week4_fixed"].mean()), 3),
                      "note": "fresh simulated students; the simulator rewards what the engine does"},
        "paired_truth": paired,
        "aa": {"runs": aa_runs, "false_positive_rate": round(aa_hits / aa_runs, 3), "srm_alarms": aa_srm},
        "ab": main,
        "decision": decide(main),
        "empirical_power": {"planned_size": {"per_arm": n_arm, "detects_drop": power_at(n_arm)},
                            "small_test": {"per_arm": 500, "detects_drop": power_at(500)}},
    }


def main() -> None:
    out = config.REPORTS_DIR / "ab_test"
    out.mkdir(parents=True, exist_ok=True)
    report = rehearse()
    (out / "rehearsal.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("design", "aa", "decision", "empirical_power")}, indent=1))


if __name__ == "__main__":
    main()
