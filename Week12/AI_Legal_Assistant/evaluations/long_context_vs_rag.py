"""
Day 4, Task 5: long-context vs RAG for contract review, on 10 CUAD contracts.

Contracts: 10 from the CUAD test split (src/contracts/cuad_data.py), 3,000-15,000 words, seed 7.
Questions: the same 10 clause types for every contract ("Is there a <type> clause? If yes, quote it.").
Answer key: the CUAD lawyers' labels - a type is present if they marked at least one passage for it.

* long-context  one Gemini request per contract with the whole contract text and all 10 questions.
* RAG           the contract is cut into ~200-word chunks (40-word overlap); for each clause type the 3
                chunks closest to its CUAD description (multilingual-e5-small) are retrieved; one request
                per contract with only those chunks.

Scores: presence accuracy; missed clauses (present but answered "absent"); false alarms; quote check (the
quote is in the contract word for word AND overlaps a passage the lawyers marked for that type); input
size (characters / 4 ~ tokens: the cost driver); time per contract (includes the client's 4 s pacing).

Run:  python -m evaluations.long_context_vs_rag
"""

import json
import random
import re
import time
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

from src.contracts.cuad_data import load, load_cuad, load_types
from src.rag.verify import quote_found

REPORT = Path("evaluations/long_context_vs_rag_report.md")
RUNS = Path("evaluations/rag_runs/long_context_vs_rag.jsonl")
TYPES = ["Governing Law", "Anti-Assignment", "Cap On Liability", "Termination For Convenience", "Exclusivity",
         "Non-Compete", "Audit Rights", "Insurance", "Renewal Term", "Change Of Control"]
N_CONTRACTS, MIN_WORDS, MAX_WORDS, SEED = 10, 3000, 15000, 7
CHUNK, OVERLAP, TOP_K = 200, 40, 3


class TypeAnswer(BaseModel):
    clause_type: str
    present: bool
    quote: str


class ContractAnswers(BaseModel):
    answers: List[TypeAnswer]


SYSTEM = """You review a commercial contract for a lawyer. For each clause type listed, say whether the contract
contains such a clause (present true/false) and, if present, copy the most relevant sentence word for word from the
text given (quote; empty if absent). Use only the text given."""


def pick_contracts() -> List[Dict]:
    test_titles = {r["contract"] for r in load("test")}
    pool = [c for c in load_cuad() if c["title"] in test_titles
            and MIN_WORDS <= len(c["paragraphs"][0]["context"].split()) <= MAX_WORDS]
    random.Random(SEED).shuffle(pool)
    return sorted(pool[:N_CONTRACTS], key=lambda c: c["title"])


def gold(contract: Dict) -> Dict[str, List[str]]:
    out = {t: [] for t in TYPES}
    for qa in contract["paragraphs"][0]["qas"]:
        cat = qa["id"].split("__")[-1]
        if cat in out:
            out[cat] = sorted({a["text"] for a in qa["answers"]})
    return out


def chunks(text: str) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i + CHUNK]) for i in range(0, max(1, len(words) - OVERLAP), CHUNK - OVERLAP)]


def rag_context(text: str, descriptions: Dict[str, str]) -> str:
    from src.contracts.review import _embedder

    parts = chunks(text)
    model = _embedder()
    vecs = model.encode([f"passage: {p}" for p in parts], normalize_embeddings=True)
    blocks = []
    for t in TYPES:
        q = model.encode([f"query: {t}. {descriptions[t]}"], normalize_embeddings=True)[0]
        top = (vecs @ q).argsort()[::-1][:TOP_K]
        blocks.append(f"=== Excerpts for {t} ===\n" + "\n...\n".join(parts[i] for i in sorted(top)))
    return "\n\n".join(blocks)


def ask(llm, title: str, text: str, descriptions: Dict[str, str]) -> Dict:
    questions = "\n".join(f"- {t}: {descriptions[t]}" for t in TYPES)
    prompt = f"Contract: {title}\n\nCLAUSE TYPES\n{questions}\n\nTEXT\n{text}"
    start = time.time()
    result = llm.generate_json(prompt, ContractAnswers, system=SYSTEM, temperature=0.0)
    seconds = time.time() - start
    answers = {a.clause_type: a for a in result.answers if a.clause_type in TYPES}
    return {"answers": {t: {"present": answers[t].present, "quote": answers[t].quote} if t in answers else {"present": False, "quote": ""}
                        for t in TYPES},
            "input_tokens_est": (len(prompt) + len(SYSTEM)) // 4, "seconds": seconds}


def score(run: Dict, contract_text: str, gold_spans: Dict[str, List[str]]) -> Dict:
    s = {"correct": 0, "missed": 0, "false_alarm": 0, "quote_ok": 0, "present_gold": 0}
    for t in TYPES:
        present, answer = bool(gold_spans[t]), run["answers"][t]
        s["present_gold"] += present
        s["correct"] += answer["present"] == present
        s["missed"] += present and not answer["present"]
        s["false_alarm"] += answer["present"] and not present
        if present and answer["present"] and answer["quote"]:
            q = answer["quote"]
            in_text = quote_found(q, contract_text)
            overlaps = any(quote_found(q, span) or quote_found(span, q) or _overlap(q, span) for span in gold_spans[t])
            s["quote_ok"] += in_text and overlaps
    return s


def _overlap(a: str, b: str) -> bool:
    """At least 8 consecutive words in common."""
    wa, wb = re.findall(r"\w+", a.lower()), " ".join(re.findall(r"\w+", b.lower()))
    return any(" ".join(wa[i:i + 8]) in wb for i in range(max(0, len(wa) - 7)))


def main() -> None:
    from src.llm.gemini_client import GeminiClient

    llm, descriptions = GeminiClient(), load_types()
    rows = []
    for contract in pick_contracts():
        text = re.sub(r"\s+", " ", contract["paragraphs"][0]["context"])
        spans = gold(contract)
        row = {"contract": contract["title"], "words": len(text.split())}
        for method, context in (("long_context", text), ("rag", rag_context(text, descriptions))):
            run = ask(llm, contract["title"], context, descriptions)
            row[method] = {**run, **score(run, text, spans)}
        rows.append(row)
        print(f"{contract['title'][:60]}: LC {row['long_context']['correct']}/10  RAG {row['rag']['correct']}/10", flush=True)
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    RUNS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    write_report(rows)


def write_report(rows: List[Dict]) -> None:
    total = lambda m, k: sum(r[m][k] for r in rows)
    n_q, present = len(rows) * len(TYPES), sum(r["long_context"]["present_gold"] for r in rows)
    lines = ["# Long-context vs RAG for contract review (Day 4, Task 5)", "",
             f"{len(rows)} CUAD test contracts ({min(r['words'] for r in rows):,}-{max(r['words'] for r in rows):,} words), "
             f"10 clause types each = {n_q} questions; {present} of them are present according to the CUAD lawyers. "
             "Model: gemini-3.5-flash-lite. Script: `python -m evaluations.long_context_vs_rag`.", "",
             "| | Long-context (whole contract) | RAG (3 chunks per clause type) |", "|---|---:|---:|"]
    for label, key, fmt in (("Accuracy (present / absent)", "correct", lambda v: f"{v}/{n_q} ({v / n_q:.0%})"),
                            ("Missed clauses (present, answered absent)", "missed", lambda v: f"{v}/{present}"),
                            ("False alarms (absent, answered present)", "false_alarm", lambda v: str(v)),
                            ("Quote real and on the right clause", "quote_ok", lambda v: f"{v}/{present}")):
        lines.append(f"| {label} | {fmt(total('long_context', key))} | {fmt(total('rag', key))} |")
    lines.append(f"| Input per contract (~tokens, average) | {total('long_context', 'input_tokens_est') // len(rows):,} | "
                 f"{total('rag', 'input_tokens_est') // len(rows):,} |")
    lines.append(f"| Time per contract (average) | {total('long_context', 'seconds') / len(rows):.1f} s | {total('rag', 'seconds') / len(rows):.1f} s |")
    lines += ["", "Cost on a paid plan scales with input tokens; the free tier used here costs nothing but limits requests per day. "
              "Time includes the client's 4-second pacing between requests (the same for both).", "",
              "| Contract | Words | Long-context correct | RAG correct |", "|---|---:|---:|---:|"]
    lines += [f"| {r['contract'][:70]} | {r['words']:,} | {r['long_context']['correct']}/10 | {r['rag']['correct']}/10 |" for r in rows]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
