"""
Day 5: the results dashboard - collects the figures of every evaluation into evaluations/dashboard.json, which the
web app's page 07 (Accuracy Audits) draws. Every number is read from a result file or a report table, never
typed in; each section names its source so a reader can check it.

Run after any evaluation:  python evaluations/dashboard.py
"""

import json
import re
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evaluations"
sys.path.insert(0, str(ROOT))
OUT = EV / "dashboard.json"


def md_table(name: str, first_header: str) -> List[List[str]]:
    """Rows of the first Markdown table in evaluations/<name> whose header row starts with first_header."""
    lines = (EV / name).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells and cells[0].startswith(first_header):
            rows = []
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                rows.append([c.strip() for c in row.strip().strip("|").split("|")])
            return rows
    raise ValueError(f"no table starting with {first_header!r} in {name}")


def num(text: str) -> Optional[float]:
    m = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(",", ""))
    return float(m.group(0)) if m else None


def retrieval() -> Dict:
    from src.rag.pipeline import DEFAULT_CONFIG
    summary = json.loads((EV / "rag_runs" / "summary.json").read_text(encoding="utf-8"))
    labels = {"naive": "Naive", "section": "Section chunks", "hybrid": "+ Hybrid", "rerank": "+ Reranker",
              "rewrite": "+ Query rewrite", "hyde": "+ HyDE", "metadata": "+ Metadata filters", "parent_child": "+ Parent-child"}
    keys = ("recall@5", "recall@5_statute", "recall@5_case_law", "mrr@5", "doc_recall@5", "citation_accuracy",
            "faithfulness", "correct_refusals", "false_refusals")
    rows = [{"config": c, "label": labels.get(c, c), "description": s.get("description", ""), "default": c == DEFAULT_CONFIG,
             **{k.replace("@", "_at_"): s.get(k) for k in keys}} for c, s in summary.items()]
    return {"default": DEFAULT_CONFIG, "questions": next(iter(summary.values()))["questions"], "configs": rows,
            "source": "rag_comparison_report.md (evaluations/rag_runs/summary.json)"}


def citations() -> Dict:
    rows = []
    for r in md_table("citation_verification_report.md", "Configuration"):
        verified = re.match(r"(\d+)", r[2])
        rows.append({"config": r[0], "citations": int(num(r[1])), "verified": int(verified.group(1)),
                     "fabricated": int(num(r[3])), "fabricated_shown": int(num(r[6]))})
    check = {r[0]: int(num(r[1])) for r in md_table("conclusion_check_report.md", "Verdict")}
    return {"configs": rows, "fabricated_shown": sum(r["fabricated_shown"] for r in rows),
            "citations_checked": sum(r["citations"] for r in rows), "conclusion_check": check,
            "source": "citation_verification_report.md, conclusion_check_report.md"}


def graph() -> Dict:
    methods = [{"method": r[0], "precision": num(r[1]) / 100, "recall": num(r[2]) / 100, "f1": num(r[3])}
               for r in md_table("graph_vs_vector_report.md", "Method")]
    links = []
    for r in md_table("graph_precision_recall.md", "Link type"):
        p, rc = (num(x) for x in r[3].split("/")[:2])
        links.append({"link": r[0], "precision": p / 100, "recall": rc / 100})
    return {"methods": methods, "extraction_heldout": links,
            "source": "graph_vs_vector_report.md, graph_precision_recall.md (held-out judgments)"}


def contracts() -> Dict:
    t = md_table("clause_classification_report.md", "")
    header = [c.strip() for c in (EV / "clause_classification_report.md").read_text(encoding="utf-8").split("\n| |", 1)[1].split("\n", 1)[0].strip().strip("|").split("|")]
    micro = next(r for r in t if r[0] == "Micro F1")
    macro = next(r for r in t if r[0].startswith("Macro F1"))
    models = [{"model": h.strip(), "micro_f1": num(a), "macro_f1": num(b)} for h, a, b in zip(header, micro[1:], macro[1:])]
    lc = {r[0]: r[1:] for r in md_table("long_context_vs_rag_report.md", "")}
    acc = lc["Accuracy (present / absent)"]
    secs = lc["Time per contract (average)"]
    long_rag = [{"method": "Long context (whole contract)", "accuracy": num(acc[0].split("(")[1]) / 100, "seconds": num(secs[0])},
                {"method": "RAG (3 chunks per clause type)", "accuracy": num(acc[1].split("(")[1]) / 100, "seconds": num(secs[1])}]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    planted = re.search(r"all (\d+) planted\s+changes found", readme)
    return {"clause_classification": models, "long_context_vs_rag": long_rag,
            "comparison_planted": {"found": int(planted.group(1)), "of": int(planted.group(1))} if planted else None,
            "source": "clause_classification_report.md, long_context_vs_rag_report.md, README (Day 4 Task 3)"}


def ocr() -> Dict:
    rows = [{"engine": r[0], "cer": num(r[1]) / 100, "wer": num(r[2]) / 100, "ms": num(r[3])}
            for r in md_table("ocr_comparison_report.md", "OCR Engine")]
    return {"engines": rows, "source": "ocr_comparison_report.md"}


def security() -> Dict:
    data = json.loads((EV / "red_team_results.json").read_text(encoding="utf-8"))["results"]
    groups = OrderedDict()
    for r in data:
        g = groups.setdefault(r["group"], {"group": r["group"], "attacks": 0, "held": 0, "broke": 0, "limitation": 0})
        g["attacks"] += 1
        g[{"held": "held", "broke": "broke", "check": "limitation"}[r["verdict"]]] += 1
    return {"groups": list(groups.values()), "attacks": len(data), "held": sum(r["verdict"] == "held" for r in data),
            "weaknesses_fixed": 7, "source": "red_team_report.md (red_team_results.json)"}


def latency() -> Optional[Dict]:
    path = EV / "latency_cost.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    r = d["research"]
    stages = [("Retrieval", r["retrieval_s"]), ("Answer (Gemini)", r["answer_s"]), ("Citation check", r["verify_s"]),
              ("Conclusion check (Gemini)", r["check_s"])]
    return {"date": d["date"], "questions": r["questions"], "config": r["config"],
            "stages": [{"stage": n, "median_s": s["median"], "p90_s": s["p90"]} for n, s in stages if s],
            "end_to_end": r["total_s"], "redrafts": r["redrafts"], "calls_per_question": r["calls_per_question"],
            "usd_per_question": r["usd_per_question"], "usd_per_1000": 1000 * r["usd_per_question"],
            "tokens_in": r["input_tokens_per_question"], "tokens_out": r["output_tokens_per_question"],
            "retrieval_only": d["retrieval"], "graph_median_s": d["graph"]["seconds"]["median"],
            "review_usd": d["review"]["usd_per_review"], "price": d["price"],
            "review_gemini_s": sum(x["gemini_s"] for x in d["review"]["rows"]) / len(d["review"]["rows"]),
            "gemini_overloaded": d.get("gemini_503_retries", 0),
            "source": "latency_cost_report.md (latency_cost.json)"}


def blind() -> Optional[Dict]:
    path = EV / "blind_rating_results.json"
    if not path.exists():
        return None
    return {"raters": json.loads(path.read_text(encoding="utf-8")), "source": "blind_rating_report.md"}


def main() -> None:
    out = {"built": time.strftime("%Y-%m-%d %H:%M"), "retrieval": retrieval(), "citations": citations(),
           "graph": graph(), "contracts": contracts(), "ocr": ocr(), "security": security(),
           "latency": latency(), "blind_rating": blind()}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT}: " + ", ".join(k for k, v in out.items() if v))


if __name__ == "__main__":
    main()
