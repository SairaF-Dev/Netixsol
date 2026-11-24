"""
Day 5: blind rating of 30 answers.

15 evaluation questions, each answered by two versions of the research pipeline (Day 2 runs, same answer
model, different retrieval):
    naive   - vector search only
    final   - hybrid BM25 + vector search with the multilingual reranker (the app's default, "rerank")
= 30 answers, shuffled. The rater sees the question, the reference answer from the evaluation set and the
answer with its citations, but never which version wrote it. The key (answer -> version) is kept in a
separate file the web app does not serve; it is revealed only after the rater has rated all 30.

Choice of questions (fixed seed, so the set can be rebuilt):
    7 statute and 5 case-law questions, drawn from those where the two versions gave different answers
      (40 of the 100 answers are word-for-word the same; rating identical pairs says nothing about the
      difference), and 3 no-answer questions (drawn from all 20: refusing correctly is the behaviour to rate);
    languages as they come out of the draw.

Rating (per answer, in the web app, page "09 Blind Rating"):
    correctness  correct | partly | wrong | refused       (against the reference answer)
    support      yes | partly | no | none                 (do the cited quotes back the answer?)
    useful       1-5                                       (to a lawyer starting research)
    note         optional

Run:
    python evaluations/blind_rating.py build     -> evaluations/blind_rating_set.json + blind_rating_key.json
    (rate in the web app)
    python evaluations/blind_rating.py report    -> evaluations/blind_rating_report.md (from data/ratings/*.json)
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.blind_rating import SYSTEMS, summarise  # noqa: E402
SET = ROOT / "evaluations" / "blind_rating_set.json"
KEY = ROOT / "evaluations" / "blind_rating_key.json"
RATINGS = ROOT / "data" / "ratings"
REPORT = ROOT / "evaluations" / "blind_rating_report.md"
RESULTS = ROOT / "evaluations" / "blind_rating_results.json"   # for the dashboard
NO_SOURCE = "No sufficient source found"
SEED = 2026
PLAN = {"statute": 7, "case_law": 5, "no_answer": 3}


def _runs():
    out = {}
    for run in SYSTEMS:
        with open(ROOT / "evaluations" / "rag_runs" / f"{run}.jsonl", encoding="utf-8") as f:
            out[run] = {r["id"]: r for r in map(json.loads, f)}
    return out


def _answer(row):
    a = row.get("answer") or {}
    return {"short_answer": a.get("short_answer", ""), "explanation": a.get("explanation", ""),
            "citations": [{"source": f"{c.get('act_or_case', '')}, {c.get('section_or_paragraph', '')}".strip(", "),
                           "quote": c.get("quote", "")} for c in a.get("citations", [])]}


def build() -> None:
    questions = [json.loads(l) for l in open(ROOT / "evaluations" / "rag_eval_set.jsonl", encoding="utf-8")]
    runs = _runs()
    rng = random.Random(SEED)
    differ = lambda q: runs["naive"][q["id"]]["answer"]["short_answer"] != runs["rerank"][q["id"]]["answer"]["short_answer"]
    chosen = []
    for kind, n in PLAN.items():
        pool = [q for q in questions if q["type"] == kind and (kind == "no_answer" or differ(q))]
        chosen += rng.sample(pool, n)

    items, key = [], {}
    for q in chosen:
        gold = q.get("gold") or []
        cite = lambda g: (f"{g['act']}, {g.get('section', '')}" if g.get("act") else
                          f"{g.get('court', '')} {g.get('case_number') or g.get('document_id')}, para {g.get('paragraph', '?')}")
        ref_source = "; ".join(cite(g).strip(", ") for g in gold)
        for run, name in SYSTEMS.items():
            items.append({"question_id": q["id"], "type": q["type"], "language": q["language"], "question": q["question"],
                          "reference": {"answer": q["expected_answer"], "source": ref_source, "quote": q.get("quote", ""),
                                        "no_answer": q["type"] == "no_answer"},
                          "answer": _answer(runs[run][q["id"]]), "_system": name})
    rng.shuffle(items)
    for n, item in enumerate(items, 1):
        item["id"] = f"A{n:02d}"
        key[item["id"]] = item.pop("_system")
    SET.write_text(json.dumps({"about": "Blind rating set: 30 answers, version hidden (key in blind_rating_key.json)",
                               "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    KEY.write_text(json.dumps(key, indent=1), encoding="utf-8")
    kinds = defaultdict(int)
    for q in chosen:
        kinds[(q["type"], q["language"])] += 1
    print(f"{SET.name}: {len(items)} answers from {len(chosen)} questions {dict(kinds)}")


def report() -> None:
    items = json.loads(SET.read_text(encoding="utf-8"))["items"]
    key = json.loads(KEY.read_text(encoding="utf-8"))
    raters = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(RATINGS.glob("*.json"))}
    raters = {u: r for u, r in raters.items() if r}
    if not raters:
        sys.exit("no ratings yet in data/ratings/")
    by_id = {i["id"]: i for i in items}
    lines = ["# Blind rating of 30 answers (Day 5)", "",
             "15 evaluation questions, each answered by two versions of the research pipeline - **naive** (vector "
             "search only) and **final** (hybrid search + reranker, the app's default) - give 30 answers. They were "
             "shuffled and rated in the web app (page 09) without showing which version wrote which; the key was "
             "revealed only after all 30 were rated. Both versions use the same answer model and prompt, so the "
             "difference comes from retrieval. Answers are as generated in the Day 2 runs, before the conclusion "
             "check.", "",
             "Questions: 7 statute and 5 case-law questions drawn (fixed seed) from those where the two versions "
             "answered differently, and 3 questions with no answer in the corpus. *Acceptable* = rated correct, or a "
             "refusal where the corpus has no answer.", ""]
    per_rater = {}
    for user, ratings in raters.items():
        s = summarise(items, key, ratings)
        per_rater[user] = {"rated": len(ratings), "of": len(items), "results": s}
        lines += [f"## Rater: {user} ({len(ratings)} of {len(items)} answers rated)", "",
                  "| | naive | final |", "|---|---|---|"]
        row = lambda label, f: lines.append(f"| {label} | " + " | ".join(f(s[v]) if v in s else "-" for v in ("naive", "final")) + " |")
        row("Acceptable answers", lambda x: f"**{x['acceptable']} / {x['rated']}**")
        row("Correct, questions with an answer", lambda x: f"{x['correct_answerable']} / {x['answerable']}")
        row("Partly correct", lambda x: str(x["correctness"]["partly"]))
        row("Wrong", lambda x: str(x["correctness"]["wrong"]))
        row("Refused", lambda x: str(x["correctness"]["refused"]))
        row("Correct refusal, no-answer questions", lambda x: f"{x['refused_no_answer']} / {x['no_answer']}")
        row("Citations fully support the answer", lambda x: str(x["support"]["yes"]))
        row("Citations partly / do not support", lambda x: f"{x['support']['partly']} / {x['support']['no']}")
        row("Usefulness, mean 1-5 (all)", lambda x: str(x["useful"]))
        row("Usefulness, questions with an answer", lambda x: str(x["useful_answerable"]))
        lines += ["", "| Answer | Question | Type | Language | Version | Correct | Citations | Useful | Note |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for item_id in sorted(ratings):
            it, r = by_id[item_id], ratings[item_id]
            q = it["question"].replace("|", "/")
            lines.append(f"| {item_id} | {q[:70]}{'...' if len(q) > 70 else ''} | {it['type']} | {it['language']} | {key[item_id]} "
                         f"| {r['correctness']} | {r['support']} | {r['useful']} | {r.get('note', '').replace('|', '/')[:80]} |")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    RESULTS.write_text(json.dumps(per_rater, indent=1), encoding="utf-8")
    print(f"{REPORT}: {len(raters)} rater(s)")


if __name__ == "__main__":
    {"build": build, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
