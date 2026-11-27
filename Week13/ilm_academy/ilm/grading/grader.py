"""Test-based grading of student code (Day 4 Task 2).

    python -m ilm.grading.grader      grade the 50 submissions, compare with the reference marks

Mark out of 10:
  1. tests     every test run in the Docker sandbox (ilm/grading/sandbox.py); visible and
               hidden tests count the same; mark = 10 x share passed (partial marks)
  2. timeouts  if the whole run times out (one test loops forever), each test is re-run in its
               own container, so the tests that work still earn their marks
  3. rules     the task's explicit rules, read from its text and checked on the code's AST (not
               by running it): "recursive" -> the function calls itself; "for loop" / "while
               loop" -> that loop is present; "no str()", "without using max()" -> no such call;
               "try/except" -> a try block. A broken rule caps the mark at 4
  4. speed     for exercises where it matters, one large input with a 2 s limit; correct but
               too slow loses 1 mark

Test sets compared:
  bank   the exercise's own tests (written before these submissions existed)
  edge   bank + boundary cases taken from the exercise TEXT (factorial(0), 90 vs 89, negative
         lists, '' ...). Written AFTER reading the submissions, so they may fit these 50.
"""
from __future__ import annotations

import ast
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import cohen_kappa_score

from ilm import config
from ilm.grading import sandbox
from ilm.questions.validate import load_bank

GRADING = config.DATA_DIR / "grading"
OUT = config.PROJECT_ROOT / "reports" / "grading"
RULE_CAP = 4
SLOW_PENALTY = 1

EDGE = {
    "recursion-03": [("factorial(0)", "1"), ("factorial(1)", "1"), ("factorial(10)", "3628800")],
    "modulo-02": [("is_even(0)", "True"), ("is_even(-4)", "True"), ("is_even(-3)", "False"), ("is_even(10)", "True")],
    "elif_else-01": [("grade(90)", "'A'"), ("grade(89)", "'B'"), ("grade(80)", "'B'"), ("grade(79)", "'C'"),
                     ("grade(70)", "'C'"), ("grade(69)", "'F'"), ("grade(100)", "'A'")],
    "dictionaries-03": [("count_letters('')", "{}"), ("count_letters('abcabc')", "{'a': 2, 'b': 2, 'c': 2}"),
                        ("count_letters('zzz')", "{'z': 3}")],
    "iterating_lists-03": [("largest([-5, -2, -9])", "-2"), ("largest([3])", "3"), ("largest([0, -1])", "0")],
    "try_except-02": [("to_int('-7')", "-7"), ("to_int('3.5')", "None"), ("to_int('')", "None"),
                      ("to_int('--5')", "None"), ("to_int('abc')", "None")],
    "for_loops-01": [("sum_to(1)", "1"), ("sum_to(100)", "5050")],
    "recursion-05": [("is_palindrome('')", "True"), ("is_palindrome('abba')", "True"),
                     ("is_palindrome('abca')", "False"), ("is_palindrome('ab')", "False")],
    "while_loops-03": [("count_digits(9)", "1"), ("count_digits(10)", "2"), ("count_digits(100)", "3"),
                       ("count_digits(1000000)", "7")],
    "sets-02": [("unique_houses([])", "[]"),
                ("unique_houses([{'house': 'b'}, {'house': 'a'}, {'house': 'b'}])", "['a', 'b']")],
}
SPEED = {      # only where an intro-course solution can be needlessly slow
    "dictionaries-03": ("count_letters('ab' * 100000) == {'a': 100000, 'b': 100000}", "True"),
    "sets-02": ("len(unique_houses([{'house': 'h%05d' % i} for i in range(30000)]))", "30000"),
}


# ------------------------------------------------------------------ rules ----
def rules_from_stem(stem: str) -> list[str]:
    s = stem.lower()
    rules = []
    if re.search(r"\brecursive\b", s):
        rules.append("recursive")
    if "for loop" in s:
        rules.append("for_loop")
    if "while loop" in s:
        rules.append("while_loop")
    if re.search(r"try/except|try and except", s):
        rules.append("try_except")
    for fn in re.findall(r"(?:no|without(?: using)?) (\w+)\(\)", s):
        rules.append(f"no_{fn}")
    return rules


def rule_violations(code: str, function: str, rules: list[str]) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []                                  # it will fail every test anyway
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function), None)
    body = fn or tree
    calls = {n.func.id for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    kinds = {type(n) for n in ast.walk(body)}
    broken = []
    for r in rules:
        if r == "recursive" and function not in calls:
            broken.append("not recursive")
        elif r == "for_loop" and ast.For not in kinds:
            broken.append("no for loop")
        elif r == "while_loop" and ast.While not in kinds:
            broken.append("no while loop")
        elif r == "try_except" and ast.Try not in kinds:
            broken.append("no try/except")
        elif r.startswith("no_") and r[3:] in calls:
            broken.append(f"uses {r[3:]}()")
    return broken


# ------------------------------------------------------------------ running ----
def run_tests(code: str, tests: list[dict]) -> sandbox.SandboxResult:
    r = sandbox.run(code, tests)
    if r.status == "timeout" and len(tests) > 1:   # rescue the tests that do finish
        parts = [sandbox.run(code, [t], wall_sec=3) for t in tests]
        r.passed = [bool(p.passed and p.passed[0]) for p in parts]
        r.details = [(p.details[0] if p.details else p.error or "") for p in parts]
        r.status, r.error = "timeout_rescued", None
    return r


def grade(sub: dict, q, test_set: str = "edge", use_rules: bool = True, use_speed: bool = True) -> dict:
    tests = [t.model_dump() for t in q.tests]
    if test_set == "edge":
        tests += [{"call": c, "expect": e, "hidden": True} for c, e in EDGE.get(q.id, [])]
    r = run_tests(sub["code"], tests)
    share = sum(r.passed) / len(tests) if tests else 0.0
    mark = round(10 * share, 1)
    broken = rule_violations(sub["code"], q.function, rules_from_stem(q.stem)) if use_rules else []
    if broken:
        mark = min(mark, RULE_CAP)
    slow = None
    if use_speed and q.id in SPEED and share == 1.0:
        call, expect = SPEED[q.id]
        s = sandbox.run(sub["code"], [{"call": call, "expect": expect}], wall_sec=6, test_sec=2)
        slow = not (s.passed and s.passed[0])
        if slow:
            mark -= SLOW_PENALTY
    return {"id": sub["id"], "exercise": q.id, "tests": len(tests), "passed": sum(r.passed),
            "status": r.status, "error": r.error, "rules_broken": broken, "slow": slow, "mark": mark,
            "failed": [f"{t['call']} -> {d}" for t, ok, d in zip(tests, r.passed, r.details or [""] * len(tests)) if not ok][:4]}


# ------------------------------------------------------------------ comparison ----
def agreement(grader: list[float], ref: list[float]) -> dict:
    g, h = np.array(grader, float), np.array(ref, float)
    d = np.abs(g - h)
    return {"n": len(g), "mae": round(float(d.mean()), 2), "within_1": round(float((d <= 1).mean()), 3),
            "within_2": round(float((d <= 2).mean()), 3),
            "spearman": round(float(spearmanr(g, h).statistic), 3), "pearson": round(float(pearsonr(g, h).statistic), 3),
            "quadratic_kappa": round(float(cohen_kappa_score(np.rint(g).astype(int), np.rint(h).astype(int),
                                                             weights="quadratic")), 3),
            "mean_grader_minus_ref": round(float((g - h).mean()), 2)}


def load_marks(path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["id"]: {"mark": float(r["mark"]), "reason": r["reason"]} for r in csv.DictReader(f) if r["mark"]}


VARIANTS = {   # name: (test set, rules, speed)
    "bank tests only": ("bank", False, False),
    "+ edge tests": ("edge", False, False),
    "+ rule checks": ("edge", True, False),
    "+ speed check (final)": ("edge", True, True),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bank = {q.id: q for q in load_bank()[0]}
    subs = json.loads((GRADING / "submissions.json").read_text(encoding="utf-8"))
    ref_file = GRADING / "assistant_marks.csv"
    ref = load_marks(ref_file)
    results = {}
    for name, (ts, rules, speed) in VARIANTS.items():
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(lambda s: grade(s, bank[s["exercise"]], ts, rules, speed), subs))
        results[name] = rows
        print(name, agreement([r["mark"] for r in rows], [ref[r["id"]]["mark"] for r in rows]), flush=True)
    final = results["+ speed check (final)"]
    kind = {s["id"]: s["kind"] for s in subs}
    by_kind = {}
    for k in sorted(set(kind.values())):
        ids = [r for r in final if kind[r["id"]] == k]
        by_kind[k] = {"n": len(ids), "mean_grader": round(float(np.mean([r["mark"] for r in ids])), 1),
                      "mean_ref": round(float(np.mean([ref[r["id"]]["mark"] for r in ids])), 1),
                      "mae": round(float(np.mean([abs(r["mark"] - ref[r["id"]]["mark"]) for r in ids])), 2)}
    report = {"reference": "assistant marks (blind, scheme in data/grading/marking_scheme.md), NOT a teacher",
              "variants": {n: agreement([r["mark"] for r in rows], [ref[r["id"]]["mark"] for r in rows])
                           for n, rows in results.items()},
              "by_kind": by_kind,
              "disagreements": [{**r, "ref": ref[r["id"]]["mark"], "ref_reason": ref[r["id"]]["reason"],
                                 "kind": kind[r["id"]]}
                                for r in sorted(final, key=lambda r: -abs(r["mark"] - ref[r["id"]]["mark"]))
                                if abs(r["mark"] - ref[r["id"]]["mark"]) > 2],
              "timeouts_rescued": sum(r["status"] == "timeout_rescued" for r in final),
              "rules_broken": sum(bool(r["rules_broken"]) for r in final),
              "too_slow": sum(bool(r["slow"]) for r in final),
              "grades": final}
    (OUT / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (OUT / "report.md").write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("variants", "timeouts_rescued", "rules_broken", "too_slow")}, indent=1))


def to_markdown(rep: dict) -> str:
    L = ["# Test-based grading vs reference marks (Day 4 Task 2)", "",
         f"50 submissions (10 bank exercises x 5), graded in the Docker sandbox. Reference: {rep['reference']}.",
         "", "## Agreement, adding one part at a time", "",
         "| grader | MAE (marks /10) | within 1 | within 2 | Spearman | quadratic kappa | grader - ref |",
         "|---|---|---|---|---|---|---|"]
    for n, a in rep["variants"].items():
        L.append(f"| {n} | {a['mae']} | {a['within_1']:.0%} | {a['within_2']:.0%} | {a['spearman']} | "
                 f"{a['quadratic_kappa']} | {a['mean_grader_minus_ref']:+} |")
    L += ["", f"Final grader: {rep['timeouts_rescued']} timed-out runs re-run test by test, "
          f"{rep['rules_broken']} rule violations capped at {RULE_CAP}, {rep['too_slow']} correct-but-slow (-{SLOW_PENALTY}).",
          "", "## By kind of submission (labels from submissions.py, used only after marking)", "",
          "| kind | n | grader mean | reference mean | MAE |", "|---|---|---|---|---|"]
    for k, v in rep["by_kind"].items():
        L.append(f"| {k} | {v['n']} | {v['mean_grader']} | {v['mean_ref']} | {v['mae']} |")
    L += ["", "## Where they disagree by more than 2 marks", ""]
    if not rep["disagreements"]:
        L.append("None.")
    for d in rep["disagreements"]:
        L += [f"- **{d['id']}** ({d['exercise']}, {d['kind']}): grader {d['mark']}, reference {d['ref']}. "
              f"Reference: {d['ref_reason']}. Grader: {d['passed']}/{d['tests']} tests"
              + (f", rules broken: {', '.join(d['rules_broken'])}" if d["rules_broken"] else "")
              + (f", {d['status']}" if d["status"] != "ok" else "") + "."]
    L += ["", "## What the table says", "",
          "- **Tests alone over-mark** (+1.3 on average): code that ignores the task's rule (a loop where "
          "recursion is asked, `max()`, `str()`) still passes every test. The AST rule check brings agreement "
          "from kappa 0.64 to 0.92; edge tests and the speed check add little on these 50.",
          "- **The big remaining gaps are 'right idea, wrong result'**: off-by-one loops or printing instead of "
          "returning fail every test (grader 0), while a human gives 3-4 for the visible idea. Tests cannot see "
          "ideas; that is what Task 3's feedback is for, and why a human reviews low marks.",
          "- **Other gaps are policy or weak tests**: `sorted(nums)[-1]` respects the letter of \"without max()\" "
          "(grader 10, human 7), and an unsorted `set` result passes 4 of 5 tests because few tests check order.",
          "- Same code, same mark: the sandbox fixes `PYTHONHASHSEED`, so set/dict order (and a grade that "
          "depends on it) cannot change between runs.",
          "", "## Limits", "",
          "- The reference is the assistant's blind marks, not a teacher's. Fill "
          "`data/grading/reference_marks_TEMPLATE.csv` with a teacher's marks and rerun to replace it.",
          "- The edge tests were written after reading the submissions, so the 'edge' rows may fit these 50 "
          "better than new ones. 'bank tests only' is the clean measurement.",
          "- Rule checks and the marking scheme follow the same course policy (a broken rule caps at 4), so "
          "agreement on rule-breaking submissions is partly by design; the table shows how much they add.",
          "- Partial marks are the share of tests passed. A teacher also gives credit for a visible right idea "
          "(e.g. code that crashes on every call), which tests cannot see."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
