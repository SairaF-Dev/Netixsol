"""LLM question generation + validation (Day 3 Task 4).

    python -m ilm.questions.generate              generate for every concept, validate, report
    python -m ilm.questions.generate --solve      + the independent-solver check (more LLM calls)
    python -m ilm.questions.generate --report     re-validate saved drafts (no generation calls)

Per concept the generator writes an MCQ (every wrong option tied to a misconception), a short
answer and, where the course has coding exercises for the concept, a code question with a
reference solution, a typical buggy solution and tests. It sees the lecture excerpts for the
concept and the existing questions, so it writes NEW ones in the course's own terms.

Every draft goes through gates, cheapest first; the first failure rejects it:
  1. format       the bank's schema (schema.py), concept ids exist, main concept = target
  2. flaws        item-writing flaws: "all/none of the above", the key is clearly the longest
                  option, missing/duplicate misconceptions, an output question that is not
                  machine-checked, a short answer that cannot be auto-graded, code without a buggy
  3. truth        RUN the code (validate.check_truth): an MCQ's key = what the code prints, the
                  solution passes, a do-nothing stub and the buggy solution both FAIL the tests
  4. duplicate    near-copy of a bank question or another draft (token-sequence similarity >= 0.85)
  5. solver       (--solve) a DIFFERENT model answers without the key: a disagreeing MCQ/short
                  answer = ambiguous stem or wrong key; solver code failing the tests = unclear task

Accepted questions go to ilm/questions/generated/generated.yaml with origin "generated". They
are NOT merged into the bank: Day 5 / a human decides, after real students have answered them.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import os
import re
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from ilm import config
from ilm.questions.runner import run_tests
from ilm.questions.schema import Question
from ilm.questions.validate import check_truth, load_bank, normalise_answer

GEN_MODEL = os.getenv("GEN_MODEL", "gemini-3.5-flash-lite")
SOLVER_MODEL = os.getenv("SOLVER_MODEL", "gemini-3.1-flash-lite")     # different from the generator
OUT = config.PROJECT_ROOT / "reports" / "question_gen"          # <run>/{drafts,solver,results}.jsonl
GENERATED_DIR = Path(__file__).with_name("generated")             # <run>.yaml = accepted questions
FIRST_ID = 51                     # generated ids: <concept>-51, -52, ... (bank uses 01-49)
DUP_SIMILAR = 0.85                # max over different bank questions is 0.83 (checked in tests)
SOLVER_BATCH = 10
GATES = ["format", "flaws", "truth", "duplicate", "solver"]
_adapter = TypeAdapter(Question)

GEN_PROMPT = """You write practice questions for an introductory Python course (CS50P-style).

Concept: {name} (id: {cid})
Already learned before this concept: {prereqs}
Lecture excerpts where it is taught:
{sources}

Existing questions on this concept (do NOT repeat or rephrase them):
{existing}

Write {n} NEW questions on this concept, in this order: {types}. Return JSON {{"questions": [...]}}.
Rules for every question:
- "concepts": list of concept ids, the FIRST must be "{cid}"; only add others from: {allowed}
- "difficulty": 1-5 (1 = recall, 5 = hardest in an intro course); "bloom": one of remember,
  understand, apply, analyze, evaluate, create (code questions are apply or higher)
- use only Python taught up to this concept; one clearly correct answer
MCQ: "type": "mcq", "stem", optional "code", 4 "options", "answer" (index of the correct one),
  "misconceptions": {{"<index of EACH wrong option>": "the specific wrong belief behind it"}}.
  If it shows code and asks what it prints, set "check_output": true and make every option an
  exact possible output. No "all/none of the above". Keep options similar in length.
SHORT: "type": "short", "stem", optional "code", "accept": [accepted answers, a word or one line].
  If it asks for the exact output of code, set "check_output": true.
CODE: "type": "code", "stem" (say exactly what the function returns), "function" (its name),
  "solution", "buggy" (a typical WRONG solution a student would write), "tests": 4-6 objects
  {{"call": "function(args)", "expect": "repr() of the right result"}} or {{"call": ..., "raises":
  "ValueError"}}; at least one with "hidden": true and one without; the tests must FAIL the buggy one.

Format example (one of each type, from the existing bank):
{examples}"""

SOLVE_PROMPT = """Answer each Python practice question below. You are a careful student; think,
then answer. Reply JSON {{"answers": [{{"id": "...", "answer": ...}}, ...]}} where answer is:
the option index (0-based integer) for mcq, a short text for short, and complete Python code
defining the function for code.

{items}"""


# ------------------------------------------------------------------ generation ----
def _q_json(q) -> dict:
    d = q.model_dump(exclude_none=True, exclude_defaults=False)
    d.pop("origin", None)
    return d


def examples(bank) -> str:
    picks = []
    for t in ("mcq", "short", "code"):
        q = next(x for x in bank if x.type == t and (t != "short" or x.accept)
                 and (t != "mcq" or x.check_output))
        picks.append(_q_json(q))
    return json.dumps(picks, indent=1)


# v1 asked for "one mcq, one short, one code": 84% came back at difficulty 1-2, none at 4-5 and
# none at analyze/evaluate (the bank has 18% at 4-5). v2 gives every question a target, rotating
# over concepts so the set spreads over 1-5 with most at 2-4, like the bank.
TARGET_PLAN = [
    {"mcq": (3, "analyze"), "short": (2, "apply"), "code": (2, "apply")},
    {"mcq": (4, "analyze"), "short": (3, "apply"), "code": (3, "apply")},
    {"mcq": (2, "understand"), "short": (4, "analyze"), "code": (4, "analyze")},
    {"mcq": (5, "evaluate"), "short": (1, "remember"), "code": (5, "create")},
]
BLOOM_HINT = {
    "remember": "recall a fact or name",
    "understand": "explain what something means or does",
    "apply": "use it on a new small case (e.g. the exact output of a short program)",
    "analyze": "trace tricky code, predict an edge case, or find the bug in a given program",
    "evaluate": "judge which of several programs is correct or best, and why",
    "create": "write a function that combines this concept with earlier ones",
}


def describe_targets(types: list[str], plan: dict | None) -> str:
    if plan is None:
        return ", ".join(f"one {t}" for t in types)
    return "; ".join(f"one {t} at difficulty {plan[t][0]} ({plan[t][1]}: {BLOOM_HINT[plan[t][1]]})" for t in types)


def gen_prompt(concept: dict, bank, concepts: dict, chunks, bank_examples: str,
               plan: dict | None = None) -> tuple[str, list[str]]:
    cid = concept["id"]
    mine = [q for q in bank if q.concepts[0] == cid]
    types = ["mcq", "short"] + (["code"] if any(q.type == "code" for q in mine) else [])
    allowed = sorted({cid, *concept.get("prereqs", []), *concept.get("related", [])})
    prompt = GEN_PROMPT.format(
        name=concept["name"], cid=cid,
        prereqs=", ".join(concepts[p]["name"] for p in concept.get("prereqs", [])) or "nothing",
        sources="\n---\n".join(f"({c.title}) {c.text}" for c in chunks),
        existing="\n".join(f"- {q.stem} {q.code or ''}".strip() for q in mine) or "(none)",
        n=len(types), types=describe_targets(types, plan),
        allowed=", ".join(allowed), examples=bank_examples)
    return prompt, types


def generate(concepts: list[dict], bank, ask, search, sink=None, done=frozenset(), all_concepts=None,
             targets: bool = True) -> list[dict]:
    by_id = {c["id"]: c for c in (all_concepts or concepts)}      # prereq names need the full list
    ex = examples(bank)
    drafts = []
    order = {c: i for i, c in enumerate(by_id)}
    for c in concepts:
        if c["id"] in done or not c.get("taught_in"):
            continue
        chunks = search.top_chunks(f"{c['name']} python", k=4)
        plan = TARGET_PLAN[order[c["id"]] % len(TARGET_PLAN)] if targets else None
        prompt, types = gen_prompt(c, bank, by_id, chunks, ex, plan)
        raw = ask(prompt, temperature=0.7, model=GEN_MODEL, max_tokens=8192, json_mode=True)
        try:
            items = json.loads(raw).get("questions", [])
        except (json.JSONDecodeError, AttributeError):
            items = []
        row = {"concept": c["id"], "asked_types": types, "targets": plan, "items": items, "raw_ok": bool(items)}
        drafts.append(row)
        if sink:
            sink(row)
        print(f"{c['id']}: {len(items)} drafts", flush=True)
    return drafts


# ------------------------------------------------------------------ gates ----
def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text.lower())


def similarity(a: str, b: str) -> float:
    """Token SEQUENCE similarity (order and operators count): word sets made `a, b = b, a`
    and `a = b; b = a` look identical and flagged 18 pairs of different bank questions."""
    return difflib.SequenceMatcher(None, _tokens(a), _tokens(b), autojunk=False).ratio()


def text_of(q) -> str:
    return f"{q.stem} {q.code or ''} {' '.join(getattr(q, 'options', []) or [])}"


def normalise_draft(item: dict, concept: str, n: int) -> dict:
    """Light, rule-based clean-up of things the format allows two ways (never content fixes)."""
    d = {k: v for k, v in dict(item).items() if v is not None}
    d["id"] = f"{concept}-{FIRST_ID + n:02d}"
    d["origin"] = "generated"
    if "type" not in d:                            # the fields say it unambiguously
        d["type"] = "code" if "function" in d else "mcq" if "options" in d else "short" if "accept" in d else None
    if isinstance(d.get("misconceptions"), dict):
        d["misconceptions"] = {int(k): v for k, v in d["misconceptions"].items() if str(k).strip().isdigit()}
    for t in d.get("tests", []) or []:
        if isinstance(t, dict) and "expect" in t and not isinstance(t["expect"], str):
            t["expect"] = repr(t["expect"])        # the schema stores expected values as repr text
    return d


def flaws(q, taken_functions: set[str] = frozenset()) -> list[str]:
    out = []
    if q.type == "code" and q.function in taken_functions:
        out.append(f"function name {q.function!r} is already used by another exercise (the tutor finds "
                   "exercises by function name)")
    if q.type == "mcq":
        low = [o.lower() for o in q.options]
        if any("all of the above" in o or "none of the above" in o for o in low):
            out.append("uses all/none of the above")
        lengths = sorted((len(o), i) for i, o in enumerate(q.options))
        if lengths[-1][1] == q.answer and lengths[-1][0] > 1.5 * max(lengths[-2][0], 1) and lengths[-1][0] > 25:
            out.append("the correct option is clearly the longest (guessable)")
        texts = [normalise_answer(m) for m in q.misconceptions.values()]
        if any(len(t) < 8 for t in texts) or len(set(texts)) < len(texts):
            out.append("misconceptions missing, too short or repeated")
    if q.type in ("mcq", "short") and q.code and re.search(r"\bprint", q.stem, re.I) and not q.check_output:
        out.append("asks for program output but check_output is off (key not machine-checked)")
    if q.type == "short" and not q.accept:
        out.append("short answer has no accepted answers (cannot be auto-graded)")
    if q.type == "code" and not q.buggy:
        out.append("code question without a buggy solution (test power cannot be checked)")
    return out


def validate_drafts(drafts: list[dict], bank, concept_ids: set[str]) -> list[dict]:
    """Every draft -> {"concept", "id", "question" (dict), "gate" (first failed gate or None), "why"}."""
    seen = [(q.id, text_of(q)) for q in bank]
    taken = {q.function for q in bank if q.type == "code"}
    results = []
    for row in drafts:
        for n, item in enumerate(row["items"]):
            d = normalise_draft(item, row["concept"], n) if isinstance(item, dict) else {"id": f"{row['concept']}-?"}
            target = (row.get("targets") or {}).get(d.get("type"))
            res = {"concept": row["concept"], "id": d.get("id"), "type": d.get("type"), "question": d,
                   "target": list(target) if target else None, "gate": None, "why": []}
            results.append(res)
            try:
                q = _adapter.validate_python(d)
            except ValidationError as e:
                res["gate"], res["why"] = "format", [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()][:3]
                continue
            unknown = [c for c in q.concepts if c not in concept_ids]
            if unknown or q.concepts[0] != row["concept"]:
                res["gate"], res["why"] = "format", [f"concepts {q.concepts} (target {row['concept']})"]
                continue
            if (f := flaws(q, taken)):
                res["gate"], res["why"] = "flaws", f
                continue
            if (errs := check_truth(q)):
                res["gate"], res["why"] = "truth", [e.split(": ", 1)[-1] for e in errs]
                continue
            near = max(((similarity(text_of(q), t), i) for i, t in seen), default=(0, None))
            if near[0] >= DUP_SIMILAR:
                res["gate"], res["why"] = "duplicate", [f"{near[0]:.2f} similar to {near[1]}"]
                continue
            seen.append((q.id, text_of(q)))
            if q.type == "code":
                taken.add(q.function)
    return results


# ------------------------------------------------------------------ solver gate ----
def solver_items(qs: list[dict]) -> str:
    parts = []
    for d in qs:
        s = f"[{d['id']}] ({d['type']}) {d['stem']}"
        if d.get("code"):
            s += f"\n```python\n{d['code']}\n```"
        if d["type"] == "mcq":
            s += "\n" + "\n".join(f"  {i}: {o}" for i, o in enumerate(d["options"]))
        if d["type"] == "code":
            s += f"\nDefine the function {d['function']}."
        parts.append(s)
    return "\n\n".join(parts)


def solver_verdict(d: dict, answer) -> str | None:
    """None = the independent solver agrees with the key; else the reason it does not."""
    if answer is None:
        return "solver gave no answer"
    if d["type"] == "mcq":
        try:
            return None if int(answer) == d["answer"] else (
                f"solver chose {answer} ({d['options'][int(answer)]!r}), key is {d['answer']}: ambiguous or wrong key")
        except (TypeError, ValueError, IndexError):
            return f"solver answer {answer!r} is not an option"
    if d["type"] == "short":
        ok = {normalise_answer(str(a)) for a in d.get("accept", [])}
        return None if normalise_answer(str(answer)) in ok else (
            f"solver answered {answer!r}, accepted {d.get('accept')}: accept list too narrow or stem unclear")
    code = re.sub(r"^```(?:python)?\s*|```\s*$", "", str(answer).strip(), flags=re.M)
    run = run_tests(code, d["tests"])
    return None if run.all_passed else "solver's code fails the tests: task unclear or tests check unstated behaviour"


def solve(results: list[dict], ask, sink=None, done=frozenset()) -> dict[str, dict]:
    todo = [r["question"] for r in results if r["gate"] is None and r["id"] not in done]
    out = {}
    for i in range(0, len(todo), SOLVER_BATCH):
        batch = todo[i:i + SOLVER_BATCH]
        raw = ask(SOLVE_PROMPT.format(items=solver_items(batch)), temperature=0, model=SOLVER_MODEL,
                  max_tokens=8192, json_mode=True)
        try:
            answers = {a.get("id"): a.get("answer") for a in json.loads(raw).get("answers", [])}
        except (json.JSONDecodeError, AttributeError):
            answers = {}
        for d in batch:
            row = {"id": d["id"], "answer": answers.get(d["id"]), "verdict": solver_verdict(d, answers.get(d["id"]))}
            out[d["id"]] = row
            if sink:
                sink(row)
        print(f"solved {i + len(batch)}/{len(todo)}", flush=True)
    return out


def apply_solver(results: list[dict], solved: dict[str, dict]) -> None:
    for r in results:
        s = solved.get(r["id"])
        if r["gate"] is None and s and s["verdict"]:
            r["gate"], r["why"] = "solver", [s["verdict"]]


# ------------------------------------------------------------------ report ----
def summarise(drafts: list[dict], results: list[dict], solver_ran: bool) -> dict:
    asked = sum(len(d["asked_types"]) for d in drafts)
    by_gate = collections.Counter(r["gate"] for r in results)
    accepted = [r for r in results if r["gate"] is None]
    by_type = {t: {"generated": sum(r["type"] == t for r in results),
                   "accepted": sum(r["type"] == t for r in accepted)} for t in ("mcq", "short", "code")}
    funnel, left = [], len(results)
    for g in GATES:
        if g == "solver" and not solver_ran:
            break
        left -= by_gate.get(g, 0)
        funnel.append({"gate": g, "rejected": by_gate.get(g, 0), "still_in": left})
    digits = re.compile(r"\d+")
    reasons = collections.Counter(r["gate"] + ": " + digits.sub("#", r["why"][0])[:90]
                                  for r in results if r["gate"])
    def spread(qs):
        n = max(len(qs), 1)
        return {"difficulty": {d: round(sum(q["difficulty"] == d for q in qs) / n, 2) for d in range(1, 6)},
                "bloom": {b: round(sum(q["bloom"] == b for q in qs) / n, 2) for b in BLOOM_HINT}}
    on_target = [r for r in accepted if r.get("target")]
    return {"generator": GEN_MODEL, "solver": SOLVER_MODEL if solver_ran else "not run",
            "accepted_spread": spread([r["question"] for r in accepted]),
            "on_target_difficulty": round(sum(r["question"]["difficulty"] == r["target"][0] for r in on_target)
                                          / len(on_target), 2) if on_target else None,
            "concepts": len(drafts), "asked": asked, "generated": len(results),
            "accepted": len(accepted), "acceptance_rate": round(len(accepted) / max(len(results), 1), 3),
            "acceptance_rate_of_asked": round(len(accepted) / max(asked, 1), 3),
            "by_type": by_type, "funnel": funnel, "top_reasons": reasons.most_common(12)}


def to_markdown(s: dict, results: list[dict]) -> str:
    L = ["# Generated questions: validation report", "",
         f"Generator `{s['generator']}`, independent solver `{s['solver']}`. {s['concepts']} concepts, "
         f"{s['asked']} questions asked for, {s['generated']} returned.", "",
         f"**Accepted: {s['accepted']} of {s['generated']} = {100 * s['acceptance_rate']:.0f}%** "
         f"({100 * s['acceptance_rate_of_asked']:.0f}% of the {s['asked']} asked for).", "",
         "## Funnel (gates in order; the first failure rejects)", "", "| gate | rejected | still in |", "|---|---|---|",
         f"| generated | | {s['generated']} |"]
    L += [f"| {f['gate']} | {f['rejected']} | {f['still_in']} |" for f in s["funnel"]]
    L += ["", "## By type", "", "| type | generated | accepted | rate |", "|---|---|---|---|"]
    for t, v in s["by_type"].items():
        L.append(f"| {t} | {v['generated']} | {v['accepted']} | {100 * v['accepted'] / max(v['generated'], 1):.0f}% |")
    L += ["", "## Most common rejection reasons", "", "| count | reason |", "|---|---|"]
    L += [f"| {n} | {r} |" for r, n in s["top_reasons"]]
    L += ["", "## Examples of rejected drafts", ""]
    shown = set()
    for r in results:
        if r["gate"] and r["gate"] not in shown:
            shown.add(r["gate"])
            q = r["question"]
            L += [f"### {r['id']} ({r['type']}): rejected at **{r['gate']}**", f"- why: {'; '.join(r['why'])}",
                  f"- stem: {q.get('stem', '')}", ""]
    return "\n".join(L) + "\n"


def write_accepted(results: list[dict], path: Path) -> int:
    acc = [r["question"] for r in results if r["gate"] is None]
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ("# GENERATED by ilm.questions.generate: passed every validation gate, NOT yet reviewed or\n"
            "# answered by real students. Not part of the bank (load_bank reads bank/ only).\n")
    path.write_text(head + yaml.safe_dump({"questions": acc}, sort_keys=False, allow_unicode=True,
                                          width=100), encoding="utf-8")
    return len(acc)


# ------------------------------------------------------------------ main ----
def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _appender(p: Path):
    def sink(row):
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return sink


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--solve", action="store_true", help="run the independent-solver gate")
    ap.add_argument("--report", action="store_true", help="no generation; re-validate saved drafts")
    ap.add_argument("--concepts", nargs="*", help="only these concept ids")
    ap.add_argument("--run", default="v2", help="v1 = plain prompt (no targets), v2 = difficulty/Bloom targets")
    args = ap.parse_args(argv)
    out = OUT / args.run
    out.mkdir(parents=True, exist_ok=True)
    drafts_file, solved_file = out / "drafts.jsonl", out / "solver.jsonl"
    from ilm.graph.concept_graph import load_concepts
    concepts = load_concepts()
    if args.concepts:
        concepts = [c for c in concepts if c["id"] in args.concepts]
    bank, _ = load_bank()
    drafts = _read_jsonl(drafts_file)
    if not args.report:
        from ilm import llm
        from ilm.content.search import HybridSearch
        drafts += generate(concepts, bank, llm.ask, HybridSearch(), sink=_appender(drafts_file),
                           all_concepts=load_concepts(), done={d["concept"] for d in drafts},
                           targets=args.run != "v1")
    results = validate_drafts(drafts, bank, {c["id"] for c in load_concepts()})
    solved = {s["id"]: s for s in _read_jsonl(solved_file)}
    if args.solve:
        from ilm import llm
        solved.update(solve(results, llm.ask, sink=_appender(solved_file), done=set(solved)))
    apply_solver(results, solved)
    s = summarise(drafts, results, solver_ran=bool(solved))
    (out / "report.json").write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "report.md").write_text(to_markdown(s, results), encoding="utf-8")
    (out / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
                                       encoding="utf-8")
    n = write_accepted(results, GENERATED_DIR / f"{args.run}.yaml")
    print(json.dumps({k: s[k] for k in ("generated", "accepted", "acceptance_rate", "funnel", "accepted_spread",
                                        "on_target_difficulty")}, indent=1),
          f"\n{n} accepted -> {GENERATED_DIR / (args.run + '.yaml')}")


if __name__ == "__main__":
    main()
