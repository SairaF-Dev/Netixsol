"""
Day 3, Task 5: Vector vs Graph vs Hybrid retrieval on multi-hop questions, plus the router.

Question sets
  dev      evaluations/multihop_eval_set.jsonl (30): GraphRAG's rules were developed on these.
  heldout  evaluations/multihop_heldout.jsonl  (10): written afterwards, never used to change them.

Methods
  vector  Day 2 retrieval (configuration "rerank", top 10 passages) -> Gemini lists the answer.
  graph   GraphRAG (src/graph/graphrag.py): local / global Cypher search, text-to-Cypher fallback.
  hybrid  Gemini answers from the graph result (items + evidence sentences) AND the vector passages.
  routed  the router (src/rag/router.py) picks one of the three per question.

Scoring: answers are sets (judges, judgments, provisions, precedents). Each answer item is reduced
to a key: a judgment by its document id, a judge by normalised name (spelling variants match at 90%+),
a provision by its label, a precedent by its normalised citation. Precision / recall / F1 per
question, averaged over questions.

--no-llm (runs without Gemini): graph runs its Cypher paths (text-to-Cypher questions count as
unanswered); vector and hybrid are scored by answer coverage: the share of the answer key that is
present in the retrieved context at all, an upper bound on what an LLM could list from it.

Run:  python -m evaluations.graph_vs_vector --no-llm
      python -m evaluations.graph_vs_vector            (with Gemini)
"""

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Set

from pydantic import BaseModel

from src.graph.regex_extract import citations_in, norm_citation, norm_name
from src.rag.answer import source_label
from src.rag.router import route

SETS = {"dev": Path("evaluations/multihop_eval_set.jsonl"), "heldout": Path("evaluations/multihop_heldout.jsonl")}
RUN_DIR = Path("evaluations/rag_runs")
REPORT = Path("evaluations/graph_vs_vector_report.md")
TOP_K = 10


class ListAnswer(BaseModel):
    items: List[str]
    explanation: str = ""


LIST_SYSTEM = """You answer questions about Pakistani court judgments from the material given, never from memory.
The answer is a list. Write each item exactly as it is identified in the material:
- a judgment: its case number followed by its document id in brackets, e.g. "C.A. 1410/2019 (SC_c.a._1410_2019)";
- a judge: the judge's name without "Justice";
- a provision: e.g. "Section 324", "Article 199", "Order VII Rule 10";
- a precedent: its law-report citation, e.g. "2009 SCMR 230";
- a number, if the question asks how many.
If the material does not contain the answer, return an empty list."""


# ----------------------------------------------------------------------------- scoring
_DOC = re.compile(r"\(((?:SC|LHC)_[^)]+)\)")


def item_key(item: str) -> str:
    text = item.strip()
    doc = _DOC.search(text)
    if doc:
        return "doc:" + doc.group(1).rstrip(".")
    if re.fullmatch(r"\d+", text):
        return "num:" + text
    cits = citations_in(text)
    if cits:
        return "cit:" + re.sub(r"[^A-Z0-9]", "", norm_citation(cits[0]))
    prov = re.match(r"(Section|Article|Order|Rule)\s+(.+)", text, re.I)
    if prov:
        return "prov:" + re.sub(r"[^A-Z0-9]", "", f"{prov.group(1)} {prov.group(2)}".upper())
    return "name:" + norm_name(text.split(":")[0])


def _same(a: str, b: str) -> bool:
    if a == b:
        return True
    if a.startswith("name:") and b.startswith("name:"):
        from rapidfuzz import fuzz
        x, y = a[5:], b[5:]
        return bool(x and y) and (x.replace(" ", "") == y.replace(" ", "") or (x.split()[0] == y.split()[0] and fuzz.ratio(x, y) >= 90))
    return False


def prf(predicted: List[str], gold: List[str]) -> Dict:
    p_keys, g_keys = list(dict.fromkeys(map(item_key, predicted))), list(dict.fromkeys(map(item_key, gold)))
    hit_p = sum(any(_same(p, g) for g in g_keys) for p in p_keys)
    hit_g = sum(any(_same(g, p) for p in p_keys) for g in g_keys)
    precision = hit_p / len(p_keys) if p_keys else 0.0
    recall = hit_g / len(g_keys) if g_keys else 0.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def coverage(gold: List[str], context: str, doc_ids: Set[str]) -> float:
    """Share of the answer key present anywhere in the retrieved context (no LLM)."""
    flat_text = re.sub(r"[^A-Z0-9]", "", context.upper())
    names = f" {norm_name(context)} "
    found = 0
    for item in gold:
        key = item_key(item)
        kind, value = key.split(":", 1)
        if kind == "doc":
            found += value in doc_ids
        elif kind == "name":
            found += f" {value} " in names
        elif kind in ("cit", "prov"):
            found += value in flat_text
    return found / len(gold) if gold else 0.0


# ----------------------------------------------------------------------------- methods
def passages_text(results: List[Dict]) -> str:
    return "\n\n".join(f"[{i}] {source_label(r)} | document_id: {r['document_id']}\n{r['content'][:2000]}"
                       for i, r in enumerate(results, start=1))


def graph_text(result: Dict) -> str:
    lines = [f"Graph query result ({result['method']} search):"]
    for row, item in zip(result["rows"] or [], result["items"]):
        evidence = row.get("evidence") if isinstance(row, dict) else None
        lines.append(f"- {item}" + (f'\n  evidence: "{evidence[:300]}"' if evidence else ""))
    if len(result["items"]) > len(result["rows"] or []):
        lines += [f"- {item}" for item in result["items"][len(result["rows"] or []):]]
    return "\n".join(lines) if result["items"] else "Graph query result: nothing found."


def run(set_name: str, use_llm: bool) -> List[Dict]:
    from evaluations.rag_evaluation import RETRIEVERS
    from src.graph.graphrag import GraphRAG

    llm = None
    if use_llm:
        from src.llm.gemini_client import GeminiClient
        llm = GeminiClient()
    retriever, rag = RETRIEVERS["rerank"](), GraphRAG(llm=llm)
    records = []
    for item in map(json.loads, SETS[set_name].read_text(encoding="utf-8").splitlines()):
        q, gold = item["question"], item["answer"]
        results = retriever.retrieve(q, top_k=TOP_K)
        context, doc_ids = passages_text(results), {r["document_id"] for r in results}
        graph = rag.answer(q)
        rec = {"id": item["id"], "question": q, "answer": gold, "route": route(q)["mode"],
               "graph_method": graph["method"], "graph_items": graph["items"], "graph_error": graph["error"],
               "cypher": graph["cypher"], "retrieved": sorted(doc_ids)}
        rec["graph"] = prf(graph["items"], gold)
        if use_llm:
            vec = llm.generate_json(f"Question: {q}\n\nMaterial:\n{context}", ListAnswer, system=LIST_SYSTEM, temperature=0.0)
            hyb = llm.generate_json(f"Question: {q}\n\nMaterial:\n{graph_text(graph)}\n\nPassages:\n{context}",
                                    ListAnswer, system=LIST_SYSTEM, temperature=0.0)
            rec.update(vector_items=vec.items, hybrid_items=hyb.items, vector=prf(vec.items, gold), hybrid=prf(hyb.items, gold))
        else:
            graph_hits = prf(graph["items"], gold)["recall"]
            rec["vector"] = {"coverage": coverage(gold, context, doc_ids)}
            covered_by_graph = {item_key(g) for g in gold if any(_same(item_key(g), item_key(p)) for p in graph["items"])}
            rest = [g for g in gold if item_key(g) not in covered_by_graph]
            rest_cov = coverage(rest, context, doc_ids) * len(rest) if rest else 0.0
            rec["hybrid"] = {"coverage": (len(covered_by_graph) + rest_cov) / len(gold) if gold else 0.0}
            rec["graph"]["coverage"] = graph_hits
        rec["routed"] = rec[rec["route"]]
        records.append(rec)
    rag.close()
    return records


def summarize(records: List[Dict], use_llm: bool) -> Dict[str, Dict[str, float]]:
    fields = ("precision", "recall", "f1") if use_llm else ("coverage",)
    out = {}
    for method in ("vector", "graph", "hybrid", "routed"):
        out[method] = {f: mean(r[method].get(f, 0.0) for r in records) for f in fields}
        if not use_llm and method == "graph":
            out[method].update({f: mean(r["graph"][f] for r in records) for f in ("precision", "recall", "f1")})
    for scope in ("local", "global"):
        pass
    return out


def write_report(all_runs: Dict[str, List[Dict]], use_llm: bool) -> None:
    lines = ["# Vector vs Graph vs Hybrid on multi-hop questions (Day 3, Task 5)", "",
             "Questions: `evaluations/multihop_eval_set.jsonl` (30, development: GraphRAG's rules were built on them) and "
             "`evaluations/multihop_heldout.jsonl` (10, held-out: written afterwards). Answers are sets; scores are averaged "
             "over questions. Script: `python -m evaluations.graph_vs_vector`.", ""]
    if not use_llm:
        lines += ["Mode `--no-llm` (no Gemini calls): **graph** is scored as an answer (precision / recall / F1 of the items "
                  "its Cypher query returns; the 1 question that needs text-to-Cypher counts as unanswered). **vector** and "
                  "**hybrid** are scored by *answer coverage*: the share of the answer key present anywhere in the retrieved "
                  "context (vector: top 10 passages; hybrid: graph result + those passages). Coverage is an upper bound on "
                  "what an LLM could list, not an answer score.", ""]
    for name, records in all_runs.items():
        s = summarize(records, use_llm)
        lines += [f"## {name} set ({len(records)} questions)", ""]
        if use_llm:
            lines += ["| Method | Precision | Recall | F1 |", "|---|---:|---:|---:|"]
            lines += [f"| {m} | {v['precision']:.0%} | {v['recall']:.0%} | {v['f1']:.2f} |" for m, v in s.items()]
        else:
            g = s["graph"]
            lines += ["| Method | Answer score (P / R / F1) | Answer coverage in context |", "|---|---:|---:|",
                      f"| vector (top {TOP_K} passages) | needs Gemini | {s['vector']['coverage']:.0%} |",
                      f"| graph (Cypher, no LLM) | {g['precision']:.0%} / {g['recall']:.0%} / {g['f1']:.2f} | {g['coverage']:.0%} |",
                      f"| hybrid (graph + passages) | needs Gemini | {s['hybrid']['coverage']:.0%} |",
                      f"| routed | | {s['routed']['coverage']:.0%} |"]
        routes = {}
        for r in records:
            routes[r["route"]] = routes.get(r["route"], 0) + 1
        lines += ["", f"Router choices: {routes}.", "", "| Question | Route | Graph path | Graph F1 | Vector coverage |",
                  "|---|---|---|---:|---:|"]
        for r in records:
            vec = r["vector"].get("f1", r["vector"].get("coverage", 0))
            lines.append(f"| {r['id']}: {r['question'][:90]} | {r['route']} | {r['graph_method']} | {r['graph']['f1']:.2f} | {vec:.0%} |")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()
    use_llm = not args.no_llm
    runs = {}
    for name in SETS:
        runs[name] = run(name, use_llm)
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        with (RUN_DIR / f"graph_vs_vector_{name}{'' if use_llm else '_nollm'}.jsonl").open("w", encoding="utf-8") as handle:
            for rec in runs[name]:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(name, json.dumps(summarize(runs[name], use_llm)))
    write_report(runs, use_llm)
    print(f"Wrote {REPORT}")
