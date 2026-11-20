"""
How well does the conclusion check (src/rag/conclusion_check.py) catch wrong conclusions, and how often
does it raise a false alarm?

Input: the 79 answered questions of the Day 2 run with query rewriting (evaluations/rag_runs/rewrite.jsonl),
each with its exact five retrieved passages (rebuilt from their chunk ids) and the answer Gemini gave.
The check is run once on each (one Gemini call per answer; the answers themselves are not regenerated).

Every flagged answer, and a sample of passed ones, was then read by hand against the question's expected
answer (evaluations/rag_eval_set.jsonl) and its passages: evaluations/conclusion_check_review.json holds
those judgements ("right" = the flag points to a real problem; "wrong" = false alarm).

Run:  python -m evaluations.conclusion_check_eval          (check + report)
      python -m evaluations.conclusion_check_eval --report (report only, from saved verdicts)
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.rag.answer import CitedAnswer

RUN = Path("evaluations/rag_runs/rewrite.jsonl")
EVAL_SET = Path("evaluations/rag_eval_set.jsonl")
OUT = Path("evaluations/rag_runs/conclusion_check_rewrite.jsonl")
REVIEW = Path("evaluations/conclusion_check_review.json")
REPORT = Path("evaluations/conclusion_check_report.md")


def run() -> None:
    from src.rag.advanced import INDEX_DIR, MemoryDenseIndex
    from src.rag.conclusion_check import check_conclusion
    from src.llm.gemini_client import GeminiClient

    chunks = MemoryDenseIndex(INDEX_DIR / "vstore_legal.sqlite3").by_id
    questions = {q["id"]: q for q in map(json.loads, EVAL_SET.read_text(encoding="utf-8").splitlines())}
    llm = GeminiClient()
    rows = [r for r in map(json.loads, RUN.read_text(encoding="utf-8").splitlines()) if not r["refused"]]
    with OUT.open("w", encoding="utf-8") as out:
        for n, row in enumerate(rows, 1):
            results = [chunks[r["chunk_id"]] for r in row["retrieved"]]
            answer = CitedAnswer.model_validate(row["answer"])
            verdict = check_conclusion(llm, questions[row["id"]]["question"], answer, results)
            out.write(json.dumps({"id": row["id"], "type": row["type"], "language": row["language"],
                                  "citation_correct": row.get("citation_correct"), **verdict.model_dump()}, ensure_ascii=False) + "\n")
            print(f"  {n}/{len(rows)} {row['id']}: {verdict.verdict}", flush=True)


def report() -> None:
    verdicts = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines()]
    questions = {q["id"]: q for q in map(json.loads, EVAL_SET.read_text(encoding="utf-8").splitlines())}
    answers = {r["id"]: r["answer"] for r in map(json.loads, RUN.read_text(encoding="utf-8").splitlines())}
    review = json.loads(REVIEW.read_text(encoding="utf-8")) if REVIEW.exists() else {}
    labels = review.get("labels", {})
    counts = Counter(v["verdict"] for v in verdicts)
    flagged = [v for v in verdicts if v["verdict"] != "supported"]
    judged = [v for v in flagged if v["id"] in labels]
    right = sum(1 for v in judged if labels[v["id"]]["flag"] == "right")
    passed_judged = [v for v in verdicts if v["verdict"] == "supported" and v["id"] in labels]
    missed = sum(1 for v in passed_judged if labels[v["id"]]["flag"] == "missed")
    lines = ["# Conclusion check: does the answer's conclusion follow from its sources?", "",
             "The citation verifier proves each quote exists; this check asks whether the conclusion drawn from it is "
             "right (same legal issue, no retrieved passage contradicting or limiting it, not overstated). Run on the "
             f"{len(verdicts)} answered questions of the Day 2 query-rewriting run, with the same passages and answers "
             "(one extra Gemini call each). Script: `python -m evaluations.conclusion_check_eval`.", "",
             "| Verdict | Answers |", "|---|---:|",
             *[f"| {k} | {counts.get(k, 0)} |" for k in ("supported", "partly", "not_supported")], ""]
    if judged:
        lines += [f"Every flagged answer was read by hand against the expected answer and the passages "
                  f"({review.get('reviewer', '')}): **{right} of {len(judged)} flags point to a real problem**, "
                  f"{len(judged) - right} are false alarms.", ""]
    if passed_judged:
        lines += [f"A sample of {len(passed_judged)} answers the check passed was read the same way: "
                  f"{missed} had a problem the check missed.", ""]
    lines += ["| Question | Type | Verdict | The check's reason | Hand review |", "|---|---|---|---|---|"]
    for v in flagged:
        q = questions[v["id"]]["question"].replace("|", "/")
        label = labels.get(v["id"], {})
        lines.append(f"| {v['id']}: {q[:110]} | {v['type']} | {v['verdict']} | {v['issue'].replace('|', '/')} | "
                     f"{label.get('flag', 'not reviewed')}: {label.get('note', '')} |")
    lines += ["", "Example caught outside this set (Day 2 demo, Urdu): asked whether a court can award *more* than the "
              "penalty amount fixed in a contract, the model answered yes, citing a real Specific Relief Act passage "
              "about enforcing the contract itself. The check rejected it (\"the passages discuss specific performance "
              "despite a penalty clause, but do not address damages exceeding the amount\"); the redraft answered "
              "\"No sufficient source found\", which is right for the passages retrieved."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(dict(counts), f"flags reviewed {len(judged)}, right {right}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    if not parser.parse_args().report:
        run()
    report()
