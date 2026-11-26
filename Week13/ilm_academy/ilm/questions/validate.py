"""Load and validate the question bank (ilm/questions/bank/*.yaml).

Checks, in order of how cheap they are:
  1. format      every field present and consistent (schema.py)
  2. references  ids unique, concepts exist in the concept graph
  3. truth       answers are checked by RUNNING code, not trusted:
                   - "what does this print" questions: the snippet's real output = the marked answer
                   - coding questions: the reference solution passes every test
  4. test power  a do-nothing stub and the `buggy` solution must FAIL at least one test
                 (a test nothing can fail grades nothing)
  5. coverage    200+ questions, every concept has 3+, all types / levels used

Run:  python -m ilm.questions.validate
"""
from __future__ import annotations

import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from ilm import config
from ilm.graph.concept_graph import load_concepts
from ilm.questions.runner import run_snippet, run_tests
from ilm.questions.schema import BLOOM, Code, MCQ, Question, Short

BANK_DIR = Path(__file__).with_name("bank")
MIN_TOTAL = 200
MIN_PER_CONCEPT = 3
_adapter = TypeAdapter(Question)


def normalise_answer(text: str) -> str:
    """For GRADING students' short answers: lenient on spacing, case and a final full stop."""
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".")


def normalise_output(text: str) -> str:
    """For CHECKING AUTHORS against real program output: exact, except trailing spaces.
    (Lowercasing here would make "Hello World" equal "hello world" in a .title() question.)"""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_bank(bank_dir: Path = BANK_DIR) -> tuple[list, Report]:
    rep, questions = Report(), []
    for path in sorted(bank_dir.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:  # report and keep checking the other files
            rep.errors.append(f"{path.name}: not valid YAML: {str(e).splitlines()[0]} {getattr(e, 'problem_mark', '')}")
            continue
        for i, item in enumerate(raw.get("questions", [])):
            where = f"{path.name}#{i} ({item.get('id', '?') if isinstance(item, dict) else '?'})"
            try:
                questions.append(_adapter.validate_python(item))
            except ValidationError as e:
                msgs = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
                rep.errors.append(f"{where}: {msgs}")
    return questions, rep


def stub_for(function: str) -> str:
    return f"def {function}(*args, **kwargs):\n    return None\n"


def check_truth(q) -> list[str]:
    """Run the code behind a question. Returns error messages (empty = all good)."""
    errs = []
    if isinstance(q, (MCQ, Short)) and q.check_output:
        out = normalise_output(run_snippet(q.code))
        if isinstance(q, MCQ):
            opts = [normalise_output(o) for o in q.options]
            if opts[q.answer] != out:
                errs.append(f"marked answer {q.options[q.answer]!r} but the code prints {out!r}")
            elif opts.count(out) > 1:
                errs.append("two options match the real output")
        elif out not in {normalise_output(a) for a in q.accept}:
            errs.append(f"accepted answers {q.accept} do not include the real output {out!r}")
    if isinstance(q, Code):
        tests = [t.model_dump() for t in q.tests]
        ref = run_tests(q.solution, tests)
        if not ref.all_passed:
            bad = ref.error or [f"{t['call']} -> {d}" for t, p, d in
                                zip(tests, ref.passed, ref.details) if not p]
            errs.append(f"reference solution fails: {bad}")
        if run_tests(stub_for(q.function), tests).all_passed:
            errs.append("a do-nothing stub passes every test: tests are too weak")
        if q.buggy and run_tests(q.buggy, tests).all_passed:
            errs.append("the buggy solution passes every test: add a test that catches it")
    return [f"{q.id}: {e}" for e in errs]


def coverage(questions, concept_ids: list[str]) -> tuple[dict, Report]:
    rep = Report()
    by_concept = collections.Counter(q.concepts[0] for q in questions)
    summary = {
        "total": len(questions),
        "by_type": dict(collections.Counter(q.type for q in questions)),
        "by_difficulty": {d: sum(q.difficulty == d for q in questions) for d in range(1, 6)},
        "by_bloom": {b: sum(q.bloom == b for q in questions) for b in BLOOM},
        "code_tests": {"visible": sum(not t.hidden for q in questions if q.type == "code" for t in q.tests),
                       "hidden": sum(t.hidden for q in questions if q.type == "code" for t in q.tests)},
        "mcq_auto_checked": sum(q.type == "mcq" and q.check_output for q in questions),
        "short_auto_graded": sum(q.type == "short" and bool(q.accept) for q in questions),
        "short_rubric": sum(q.type == "short" and bool(q.rubric) for q in questions),
        "per_concept": {c: by_concept.get(c, 0) for c in concept_ids},
    }
    if len(questions) < MIN_TOTAL:
        rep.errors.append(f"only {len(questions)} questions, need {MIN_TOTAL}+")
    thin = [c for c in concept_ids if by_concept.get(c, 0) < MIN_PER_CONCEPT]
    if thin:
        rep.errors.append(f"concepts with fewer than {MIN_PER_CONCEPT} questions: {thin}")
    for name, counts in (("type", summary["by_type"]), ("difficulty", summary["by_difficulty"]),
                         ("bloom", summary["by_bloom"])):
        empty = [k for k, v in counts.items() if not v]
        if empty or len(counts) < 3:
            rep.warnings.append(f"{name} levels never used: {empty}")
    return summary, rep


def validate(bank_dir: Path = BANK_DIR, run_code: bool = True) -> tuple[list, dict, Report]:
    questions, rep = load_bank(bank_dir)
    concept_ids = [c["id"] for c in load_concepts()]
    known = set(concept_ids)

    ids = collections.Counter(q.id for q in questions)
    rep.errors += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    stems = collections.Counter(normalise_answer(q.stem + " " + (q.code or "")) for q in questions)
    rep.errors += [f"duplicate question: {s[:60]!r}" for s, n in stems.items() if n > 1]
    for q in questions:
        unknown = [c for c in q.concepts if c not in known]
        if unknown:
            rep.errors.append(f"{q.id}: unknown concepts {unknown}")
        if not q.id.startswith(q.concepts[0] + "-"):
            rep.errors.append(f"{q.id}: id must start with its main concept {q.concepts[0]!r}")

    if run_code:
        with ThreadPoolExecutor(max_workers=8) as pool:  # each check is its own process
            for errs in pool.map(check_truth, questions):
                rep.errors += errs

    summary, cov = coverage(questions, concept_ids)
    rep.errors += cov.errors
    rep.warnings += cov.warnings
    return questions, summary, rep


def main() -> None:
    questions, summary, rep = validate()
    print(json.dumps({k: v for k, v in summary.items() if k != "per_concept"}, indent=1))
    for w in rep.warnings:
        print("WARNING", w)
    for e in rep.errors:
        print("ERROR  ", e)
    out = config.REPORTS_DIR / "question_bank" / "summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({**summary, "errors": rep.errors, "warnings": rep.warnings},
                              indent=1), encoding="utf-8")
    print(f"\n{'VALID' if rep.ok else 'INVALID'}: {len(questions)} questions, "
          f"{len(rep.errors)} errors -> {out}")
    sys.exit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
