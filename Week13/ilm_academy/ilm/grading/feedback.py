"""Feedback on student code (Day 4 Task 3).

    python -m ilm.grading.feedback            feedback for the 50 submissions (no LLM)
    python -m ilm.grading.feedback --llm      + an LLM explanation, gated against leaks

For each submission the student gets:
  1. what failed: VISIBLE tests in full (call, expected, got); HIDDEN tests only as a count and
     what went wrong (crashed with KeyError, wrong value, too slow), never their input or answer:
     showing them would let students hard-code the hidden cases
  2. rules from the task that the code breaks (from the grader's AST check)
  3. code quality: Ruff (bugs, unused names, simplifications), Pylint (warnings, refactors) and
     radon (cyclomatic complexity), filtered to what a beginner should act on
  4. ONE improvement, chosen by priority: make it run > follow the task's rule > fix wrong
     results > speed > quality. One clear next step beats a list of twelve.
  5. a lesson link: the course passage on the exercise's concept, from the course search
     (lesson + video timestamp), restricted to the lessons that teach the concept
  6. (--llm) a short explanation in plain words. It never sees the reference solution or the
     hidden tests, and its reply goes through the tutor's leak checks (passes the tests, near
     copy of the solution, another exercise's answer); a leaking reply is retried once, then
     dropped in favour of the rule-based text.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ilm import config

OUT = config.PROJECT_ROOT / "reports" / "feedback"
BIN = Path(sys.executable).parent

RUFF_RULES = "E,F,B,SIM,C4,RET,PLW,PERF"            # bugs, unused names, simplifications
RUFF_IGNORE = "E501,RET505,RET504"                   # line length; style-only return rules
PYLINT_DISABLE = ("missing-module-docstring,missing-function-docstring,missing-class-docstring,"
                  "invalid-name,too-few-public-methods,consider-using-f-string,unused-import")
CC_WARN = 6                                          # radon: 1-5 simple (A), 6+ worth simplifying

EXCEPTION_HINTS = {
    "KeyError": "looked up a dictionary key that is not there yet",
    "IndexError": "used a position that is outside the list or string",
    "TypeError": "used a value of the wrong type (for example a list where a string was expected)",
    "NameError": "used a name that was never defined",
    "RecursionError": "kept calling itself without reaching a base case",
    "ZeroDivisionError": "divided by zero",
    "ValueError": "got a value it could not convert",
    "AttributeError": "asked a value for something it does not have",
    "TimeoutError": "took too long (is there a loop that never ends?)",
    "SyntaxError": "could not be read by Python (a syntax error)",
    "IndentationError": "could not be read by Python (wrong indentation)",
}
RULE_HINTS = {
    "not recursive": "The task asks for a recursive function: it should call itself on a smaller input.",
    "no for loop": "The task asks for a for loop.",
    "no while loop": "The task asks for a while loop.",
    "no try/except": "The task asks you to use try/except to handle bad input.",
}
def rule_hint(rule: str) -> str:
    m = re.fullmatch(r"uses (\w+)\(\)", rule)
    if m:
        return f"The task says not to use {m.group(1)}(): write that part yourself with a loop."
    return RULE_HINTS.get(rule, f"The task does not allow this: {rule}.")


QUALITY_HINTS = {          # rule code -> beginner wording (anything else uses the tool's own message)
    "E722": "A bare `except:` catches every error, even typing mistakes. Name the error you expect, e.g. `except ValueError:`.",
    "W0702": "A bare `except:` catches every error, even typing mistakes. Name the error you expect, e.g. `except ValueError:`.",
    "SIM103": "You can return the condition directly instead of `if ...: return True else: return False`.",
    "R1703": "You can return the condition directly instead of `if ...: return True else: return False`.",
    "F841": "A variable is given a value but never used.",
    "W0612": "A variable is given a value but never used.",
    "R1705": "After a `return`, the `else:` is not needed.",
    "PLR1714": "Several `==` comparisons with `or` can be one `in` check.",
    "C0200": "Looping with `range(len(...))` can usually loop over the items directly (or use enumerate).",
    "W0107": "An unnecessary `pass` statement.",
}


# ------------------------------------------------------------------ quality tools ----
def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8").stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def quality(code: str, forbidden: set[str] = frozenset()) -> dict:
    """Ruff + Pylint + radon on the student's code. Static only: the code is never run here.
    `forbidden`: functions the task bans (e.g. max): a tip suggesting them is dropped, since
    Pylint happily says "use max()" on an exercise that forbids max()."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "solution.py"
        path.write_text(code, encoding="utf-8")
        issues = []
        try:
            ruff = json.loads(_run([str(BIN / "ruff"), "check", "--output-format", "json", "--select", RUFF_RULES,
                                    "--ignore", RUFF_IGNORE, "--no-cache", str(path)]) or "[]")
        except json.JSONDecodeError:
            ruff = []
        for i in ruff:
            issues.append({"tool": "ruff", "code": i["code"], "line": i["location"]["row"], "message": i["message"]})
        try:
            pyl = json.loads(_run([sys.executable, "-m", "pylint", "--output-format=json", "--score=n",
                                   f"--disable={PYLINT_DISABLE}", str(path)]) or "[]")
        except json.JSONDecodeError:
            pyl = []
        for i in pyl:
            if i["type"] in ("warning", "refactor", "error"):
                issues.append({"tool": "pylint", "code": i["message-id"], "line": i["line"], "message": i["message"]})
        try:
            cc = json.loads(_run([sys.executable, "-m", "radon", "cc", "-j", str(path)]) or "{}")
            blocks = next(iter(cc.values()), []) if cc else []
        except (json.JSONDecodeError, StopIteration):
            blocks = []
    if isinstance(blocks, dict):                    # radon reports a syntax error as a dict
        blocks = []
    syntax = [i for i in issues if i["code"] in ("invalid-syntax", "E0001", "E999")]
    if syntax:                                       # one plain message; style tips are noise here
        i = next((x for x in syntax if x["tool"] == "ruff"), syntax[0])
        msg = re.sub(r"^Parsing failed: ", "", i["message"]).strip("'\"")
        return {"issues": [{**i, "hint": f"Python cannot read line {i['line']}: {msg}."}],
                "max_complexity": 0, "complex": False, "syntax_error": True}
    seen, unique = set(), []
    for i in sorted(issues, key=lambda x: (x["line"], x["tool"])):
        hint = QUALITY_HINTS.get(i["code"], i["message"])
        if any(f"{fn}(" in hint for fn in forbidden):
            continue
        if hint not in seen:                         # ruff and pylint often report the same thing
            seen.add(hint)
            unique.append({**i, "hint": hint})
    worst = max((b["complexity"] for b in blocks), default=0)
    return {"issues": unique, "max_complexity": worst, "complex": worst >= CC_WARN, "syntax_error": False}


# ------------------------------------------------------------------ explaining failures ----
def explain_result(t: dict) -> str:
    got = str(t.get("got") or "")
    if got.startswith("TimeoutError") or "timeout" in got.lower() or "killed after" in got.lower():
        return "did not finish in time (is there a loop that never ends?)"
    exc = re.match(r"(\w+(?:Error|Exception))\b", got)
    if exc:
        name = exc.group(1)
        return f"crashed with {name}: it {EXCEPTION_HINTS.get(name, 'raised an error')}"
    if t.get("raises"):
        return f"should raise {t['raises']} but returned a value"
    if got == "None":
        return "returned None: did you print the answer instead of returning it, or miss a return?"
    return "returned a wrong value"


def failures(test_results: list[dict]) -> dict:
    vis = [t for t in test_results if not t["hidden"] and not t["passed"]]
    hid = [t for t in test_results if t["hidden"] and not t["passed"]]
    visible = [{"call": t["call"], "expected": t["expect"] if t["expect"] is not None else f"raises {t['raises']}",
                "got": t["got"], "why": explain_result(t)} for t in vis]
    kinds = {}
    for t in hid:
        why = explain_result(t)
        kinds[why] = kinds.get(why, 0) + 1
    return {"passed": sum(t["passed"] for t in test_results), "total": len(test_results),
            "visible_failed": visible, "hidden_failed": len(hid),
            "hidden_failed_how": [{"how": k, "count": n} for k, n in kinds.items()]}


# ------------------------------------------------------------------ one improvement ----
def one_improvement(f: dict, rules: list[str], slow: bool | None, q: dict, task_stem: str) -> dict:
    if q.get("syntax_error"):
        return {"kind": "make it run", "text": q["issues"][0]["hint"] + " Fix that first: nothing else can be checked yet."}
    crashes = [v for v in f["visible_failed"] if v["why"].startswith(("crashed", "did not finish"))]
    hidden_crash = [h for h in f["hidden_failed_how"] if h["how"].startswith(("crashed", "did not finish"))]
    never_ends = [x for x in crashes + hidden_crash if "never ends" in x.get("why", x.get("how", ""))]
    if never_ends or (f["passed"] == 0 and (crashes or hidden_crash or f.get("run_error"))):
        # a loop that never ends comes first, even if some tests pass (found on a submission that
        # was first told "use a for loop" while its while loop never stopped)
        x = (never_ends or crashes or hidden_crash or [{"why": str(f.get("run_error"))}])[0]
        what = x.get("why", x.get("how", ""))
        return {"kind": "make it run", "text": f"Your code does not finish its tests: it {what.split(': it ', 1)[-1]}. "
                "Get it running on the example in the task first."}
    if rules:
        all_pass = f["passed"] == f["total"]
        return {"kind": "follow the task", "text": rule_hint(rules[0]) + (
            " Your answers come out right, but the exercise is practising this skill." if all_pass else
            " Some results are also wrong; following the task's method usually fixes them too.")}
    if f["visible_failed"]:
        v = f["visible_failed"][0]
        what = v["why"].replace("returned a wrong value", f"returned {v['got']}").rstrip("?.")
        return {"kind": "fix a wrong result", "text": f"{v['call']} should give {v['expected']}, but your code "
                f"{what}. Trace it by hand with that input."}
    if f["hidden_failed"]:
        how = f["hidden_failed_how"][0]["how"]
        return {"kind": "fix a wrong result", "text": f"{f['hidden_failed']} hidden test(s) failed: your code {how}. "
                "Re-read the task for special cases (the smallest input, boundaries like 'or more', empty input, "
                "negative numbers) and test those yourself."}
    if slow:
        return {"kind": "speed", "text": "It is correct but slow on large inputs: something inside your loop "
                "repeats work for every item. Can you get each answer with one pass?"}
    if q["issues"]:
        return {"kind": "code quality", "text": q["issues"][0]["hint"]}
    if q["complex"]:
        return {"kind": "simplify", "text": f"The logic has many branches (complexity {q['max_complexity']}). "
                "Can some conditions be merged or ordered so fewer checks are needed?"}
    return {"kind": "well done", "text": "All tests pass and the code is clean. Optional: test it on an input "
            "the task did not mention and predict the result first."}


# ------------------------------------------------------------------ lesson link ----
class Lessons:
    """The best course passage for a concept, only from lessons that teach it (cached)."""

    def __init__(self, search=None):
        from ilm.graph.concept_graph import load_concepts
        self.concepts = {c["id"]: c for c in load_concepts()}
        self._search, self._cache = search, {}

    def link(self, concept: str) -> dict | None:
        if concept not in self._cache:
            if self._search is None:
                from ilm.content.search import HybridSearch
                self._search = HybridSearch()
            c = self.concepts[concept]
            taught = set(c.get("taught_in", []))
            hits = self._search.top_chunks(f"{c['name']} python", k=20)
            best = next((h for h in hits if h.lesson_id in taught), hits[0] if hits else None)
            self._cache[concept] = {"title": best.title, "url": best.url, "lesson": best.lesson_id} if best else None
        return self._cache[concept]


# ------------------------------------------------------------------ LLM layer ----
LLM_PROMPT = """You give feedback on a beginner's Python exercise. Facts below come from running
their code; use only these facts. Write 3-5 short sentences: what went wrong in plain words,
why, and the ONE next step. Ask one guiding question. Do NOT write the solution or any code that
solves the exercise; at most quote their own line. Be warm.

Exercise: {stem}
Student's code:
```python
{code}
```
Test results: {passed}/{total} passed. Visible failures: {visible}. Hidden tests failed: {hidden}
(you do not know their inputs; never guess them). Rules broken: {rules}. Too slow: {slow}.
Most important next step (already decided): {improvement}
Reply JSON {{"explanation": "..."}}"""


def llm_explanation(fb: dict, q, sub_code: str, ask, bank_by_function: dict) -> dict:
    from ilm.tutor.tutor import leak_reason
    f = fb["tests"]
    prompt = LLM_PROMPT.format(stem=q.stem, code=sub_code, passed=f["passed"], total=f["total"],
                               visible=json.dumps(f["visible_failed"])[:800], hidden=f["hidden_failed_how"],
                               rules=fb["rules_broken"] or "none", slow=bool(fb["slow"]),
                               improvement=fb["one_improvement"]["text"])
    reason = None
    for _ in range(2):
        p = prompt if reason is None else prompt + f"\n\nYOUR LAST REPLY GAVE AWAY THE ANSWER ({reason}). Do not."
        raw = ask(p, temperature=0.3, json_mode=True, max_tokens=600)
        try:
            text = str(json.loads(raw).get("explanation", "")).strip()
        except (json.JSONDecodeError, AttributeError):
            text = ""
        reason = leak_reason(text, q, bank_by_function) if text else "empty"
        hidden_calls = [t["call"] for t in fb["_hidden_calls"]]
        if reason is None and any(c in text for c in hidden_calls):
            reason = "it mentions a hidden test"
        if reason is None:
            return {"text": text, "blocked": False}
    return {"text": None, "blocked": True, "reason": reason}


# ------------------------------------------------------------------ putting it together ----
def feedback(graded: dict, q, sub_code: str, lessons: Lessons | None = None) -> dict:
    from ilm.grading.grader import rules_from_stem
    f = failures(graded["test_results"])
    f["run_error"] = graded.get("run_error")
    qa = quality(sub_code, {r[3:] for r in rules_from_stem(q.stem) if r.startswith("no_")})
    fb = {"id": graded["id"], "exercise": q.id, "mark": graded["mark"], "tests": f,
          "rules_broken": graded["rules_broken"], "slow": graded["slow"], "quality": qa,
          "one_improvement": one_improvement(f, graded["rules_broken"], graded["slow"], qa, q.stem),
          "lesson": lessons.link(q.concepts[0]) if lessons else None,
          "_hidden_calls": [t for t in graded["test_results"] if t["hidden"]]}
    return fb


def render(fb: dict) -> str:
    """What the student sees (markdown). Hidden tests: count and kind only."""
    f = fb["tests"]
    L = [f"**{f['passed']} of {f['total']} tests passed** (mark {fb['mark']}/10)."]
    for v in f["visible_failed"]:
        L.append(f"- `{v['call']}` should give `{v['expected']}`, got `{v['got']}`: it {v['why']}.")
    for h in f["hidden_failed_how"]:
        L.append(f"- {h['count']} hidden test(s): your code {h['how']}.")
    for r in fb["rules_broken"]:
        L.append(f"- Task rule: {rule_hint(r)}")
    if fb["slow"]:
        L.append("- Correct, but too slow on a large input.")
    if fb["quality"]["issues"]:
        L.append("- Code quality: " + "; ".join(i["hint"] for i in fb["quality"]["issues"][:3]))
    L.append(f"\n**Next step:** {fb['one_improvement']['text']}")
    if fb.get("llm"):
        L.append(f"\n{fb['llm']['text']}" if fb["llm"]["text"] else "")
    if fb["lesson"]:
        L.append(f"\n**Rewatch:** [{fb['lesson']['title']}]({fb['lesson']['url']})")
    return "\n".join(x for x in L if x is not None)


def leaks_hidden(fb: dict, text: str) -> bool:
    """Does the student-facing text reveal a hidden test's input or expected answer?"""
    for t in fb["_hidden_calls"]:
        args = t["call"][t["call"].find("(") + 1:-1]
        if t["call"] in text or (len(args) > 3 and args in text):
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="add the gated LLM explanation")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    from ilm.questions.validate import load_bank
    bank = {q.id: q for q in load_bank()[0]}
    by_fn = {q.function: q for q in bank.values() if q.type == "code"}
    graded = {g["id"]: g for g in json.loads((config.PROJECT_ROOT / "reports" / "grading" / "report.json")
                                             .read_text(encoding="utf-8"))["grades"]}
    subs = json.loads((config.DATA_DIR / "grading" / "submissions.json").read_text(encoding="utf-8"))
    lessons = Lessons()
    ask = None
    if args.llm:
        from ilm import llm
        ask = llm.ask
    rows, pages = [], []
    for s in subs:
        q = bank[s["exercise"]]
        fb = feedback(graded[s["id"]], q, s["code"], lessons)
        if ask:
            fb["llm"] = llm_explanation(fb, q, s["code"], ask, by_fn)
        text = render(fb)
        fb["checks"] = {"hidden_test_leak": leaks_hidden(fb, text),
                        "has_lesson_link": bool(fb["lesson"]), "has_one_improvement": bool(fb["one_improvement"])}
        rows.append({k: v for k, v in fb.items() if k != "_hidden_calls"})
        pages.append(f"## {s['id']} ({q.id})\n\n```python\n{s['code'].rstrip()}\n```\n\n{text}\n")
        print(s["id"], fb["one_improvement"]["kind"], flush=True)
    summary = summarise(rows, subs)
    (OUT / "feedback.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "feedback_pages.md").write_text("# Feedback as students see it\n\n" + "\n".join(pages), encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (OUT / "report.md").write_text(to_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def to_markdown(s: dict) -> str:
    L = ["# Code feedback (Day 4 Task 3)", "",
         f"Feedback for {s['submissions']} submissions; every page is in [feedback_pages.md](feedback_pages.md).", "",
         "| check | result |", "|---|---|",
         f"| hidden test inputs or answers shown to the student | {s['hidden_test_leaks']} |",
         f"| with a lesson + video-timestamp link | {s['with_lesson_link']} / {s['submissions']} |",
         f"| with a code-quality tip (Ruff / Pylint / radon) | {s['with_quality_issue']} |",
         f"| LLM explanations used / blocked as a leak | {s['llm']['used']} / {s['llm']['blocked_as_leak']} |", "",
         "## The one improvement chosen, by kind of submission", "",
         "Priority: make it run > follow the task's rule > fix a wrong result > speed > code quality. "
         "Kinds are the private labels in `ilm/grading/submissions.py`.", "",
         "| improvement | submissions (by kind) |", "|---|---|"]
    for imp, kinds in s["improvement_kind_by_submission_kind"].items():
        L.append(f"| {imp} | " + ", ".join(f"{k} {n}" for k, n in kinds.items()) + " |")
    L += ["", "## Limits", "",
          "- With 1 visible test per exercise, most failures are hidden; the student learns how a hidden "
          "test failed (crashed with KeyError, returned None, wrong value), never its input.",
          "- The tools do not judge readability: s14 (if-chain that overwrites a variable) gets no tip although "
          "a human marked it down for clarity. That is the LLM layer's job, or a teacher's.",
          "- The LLM explanation is gated by the tutor's leak checks (passes the tests, near copy, another "
          "exercise's answer, mentions a hidden test). A leak in plain words would rely on that gate's limits "
          "(see reports/tutor_eval/README.md).",
          "- Lesson links come from the course search on the concept; one link per concept, not per mistake."]
    return "\n".join(L) + "\n"


def summarise(rows: list[dict], subs: list[dict]) -> dict:
    kind = {s["id"]: s["kind"] for s in subs}
    by_imp = {}
    for r in rows:
        by_imp.setdefault(r["one_improvement"]["kind"], []).append(kind[r["id"]])
    return {"submissions": len(rows),
            "hidden_test_leaks": sum(r["checks"]["hidden_test_leak"] for r in rows),
            "with_lesson_link": sum(r["checks"]["has_lesson_link"] for r in rows),
            "with_quality_issue": sum(bool(r["quality"]["issues"]) for r in rows),
            "improvement_kind_by_submission_kind": {k: dict(sorted({x: v.count(x) for x in v}.items()))
                                                    for k, v in sorted(by_imp.items())},
            "llm": {"used": sum(bool(r.get("llm")) for r in rows),
                    "blocked_as_leak": sum(bool(r.get("llm", {}).get("blocked")) for r in rows)}}


if __name__ == "__main__":
    main()
