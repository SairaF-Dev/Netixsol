"""
Day 2, Task 5: run the citation verifier over saved RAG runs (no LLM calls).

For each configuration in evaluations/rag_runs/<config>.jsonl the retrieved passages
are reloaded by chunk id, every citation is checked (src/rag/verify.py) and the
report evaluations/citation_verification_report.md shows, before verification:
how many citations were verified, fabricated (wrong source / attribution /
reference / quote) or imprecise (page or chapter only); and after verification:
fabricated citations shown to the user (always 0, they are removed), answers
turned into "No sufficient source found", and citation accuracy on the kept citations.

Run:  python -m evaluations.verify_citations [config ...]
"""

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

from tabulate import tabulate

from evaluations.rag_evaluation import DESCRIPTIONS, RUN_DIR, citation_correct, load_eval_set
from src.rag.answer import CitedAnswer, is_refusal
from src.rag.verify import verify_answer

REPORT = Path("evaluations/citation_verification_report.md")
DETAILS = RUN_DIR / "citation_checks.jsonl"


def _content_lookup(config: str):
    if config == "parent_child":
        from src.rag.parent_child_index import load_parents
        parents = load_parents()
        return lambda cid: parents.get(cid)
    path = Path("data/indices") / ("vstore_naive_fixed.sqlite3" if config == "naive" else "vstore_legal.sqlite3")
    con = sqlite3.connect(str(path))

    def get(cid):
        row = con.execute("SELECT chunk_id, document_id, content, metadata_json FROM legal_chunks WHERE chunk_id=?",
                          (cid,)).fetchone()
        return row and {"chunk_id": row[0], "document_id": row[1], "content": row[2], "metadata": json.loads(row[3])}
    return get


def verify_run(config: str, items: Dict[str, Dict]) -> Dict:
    lookup = _content_lookup(config)
    records = [json.loads(l) for l in (RUN_DIR / f"{config}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [r for r in records if r.get("answer") and r["id"] in items]
    reasons, details = Counter(), []
    answered = refused_after = correct_after = answerable = 0
    total = verified = 0
    for record in records:
        item = items[record["id"]]
        results = [lookup(r["chunk_id"]) or {"chunk_id": r["chunk_id"], "document_id": r["document_id"],
                                             "content": "", "metadata": {}} for r in record["retrieved"]]
        answer = CitedAnswer.model_validate(record["answer"])
        checked, report = verify_answer(answer, results)
        for entry in report:
            total += 1
            verified += entry["verified"]
            if not entry["verified"]:
                reasons[entry["reason"].split(":")[0]] += 1
            details.append({"config": config, "id": record["id"], **entry})
        if not is_refusal(answer):
            answered += 1
            refused_after += is_refusal(checked)
        if item["gold"]:
            answerable += 1
            correct_after += citation_correct(checked, results, item)
    fabricated = sum(n for reason, n in reasons.items() if reason not in ("imprecise", "unverifiable"))
    return {"config": config, "answers": len(records), "answered": answered, "citations": total,
            "verified": verified, "fabricated": fabricated,
            "imprecise": reasons.get("imprecise", 0) + reasons.get("unverifiable", 0),
            "by_reason": dict(reasons), "turned_into_refusal": refused_after,
            "citation_accuracy_after": correct_after / answerable if answerable else None, "details": details}


def main(configs: List[str]) -> None:
    items = {i["id"]: i for i in load_eval_set(reviewed_only=True)}
    runs = [verify_run(c, items) for c in configs if (RUN_DIR / f"{c}.jsonl").exists()]
    runs = [r for r in runs if r["answers"]]
    with DETAILS.open("w", encoding="utf-8") as handle:
        for run in runs:
            for entry in run.pop("details"):
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    pct = lambda n, d: f"{n} ({100 * n / d:.0f}%)" if d else "0"
    rows = [[DESCRIPTIONS.get(r["config"], r["config"]), r["citations"], pct(r["verified"], r["citations"]),
             pct(r["fabricated"], r["citations"]), pct(r["imprecise"], r["citations"]),
             ", ".join(f"{k} {v}" for k, v in sorted(r["by_reason"].items())) or "-",
             "0", r["turned_into_refusal"],
             "-" if r["citation_accuracy_after"] is None else f"{100 * r['citation_accuracy_after']:.0f}%"]
            for r in runs]
    table = tabulate(rows, tablefmt="github", headers=[
        "Configuration", "Citations", "Verified", "Fabricated", "Imprecise or unverifiable",
        "Failed checks", "Fabricated shown to user", "Answers turned into refusal", "Citation accuracy after"])
    REPORT.write_text(f"""# Citation Verification (Day 2, Task 5)

Every citation in the Gemini answers was checked by code (no LLM), against the passages the
model was given and the structured corpus:

1. **source**: the passage number exists among the retrieved passages;
2. **attribution**: the Act / case named matches that passage's document;
3. **reference**: the cited section / article / paragraph exists in that document;
4. **quote**: the quoted words appear verbatim in that passage (whitespace, quote marks,
   footnote marks and Urdu letter forms normalised).

A citation failing any check is removed; an answer left without citations becomes
"No sufficient source found". Citations giving only a page or chapter are counted as
imprecise, and section numbers cited from Urdu OCR pages (which carry none) as
unverifiable; neither counts as fabricated, but both are removed. Questions: the reviewed evaluation set.
Per-citation results: `{DETAILS}`.

{table}
""", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main(sys.argv[1:] or list(DESCRIPTIONS))
