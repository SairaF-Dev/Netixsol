"""
Day 3, Task 2 (LLM part): check the relationship types the regex step guessed from cue words.

Regex types a link from words in the sentence ("relied", "distinguish", "overrul", "meaning of"), which
cannot tell who is speaking or what the word is about: "counsel relied upon X", "Not APPROVED for
reporting", "review lies where the decision is per incuriam". Gemini reads the evidence sentence of
every regex-typed link (FOLLOWS, DISTINGUISHES, OVERRULES, INTERPRETS) and gives the type, 10 links
per request:

  precedent links  FOLLOWS | DISTINGUISHES | OVERRULES | CITES (neutral, or relied on by counsel /
                   the court below)
  provision links  INTERPRETS | REFERS_TO

Results go to data/graph/llm_relation_checks.jsonl; src.graph.regex_extract applies them when it
writes the graph (method "regex+llm"), so re-running the extraction keeps them. Links typed CITES /
REFERS_TO by regex are not re-checked: this step fixes wrong types, it does not look for missed ones.

Accuracy is measured on 34 hand-labelled links (evaluations/relation_gold_sample.json).

Run:  python -m src.graph.llm_relation_check          (then: python -m src.graph.regex_extract)
      python -m src.graph.llm_relation_check --score  (accuracy on the hand-labelled sample)
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Literal

from pydantic import BaseModel

GRAPH = Path("data/graph")
CHECKS = GRAPH / "llm_relation_checks.jsonl"
GOLD = Path("evaluations/relation_gold_sample.json")
BATCH = 10
PRECEDENT_TYPES = ("FOLLOWS", "DISTINGUISHES", "OVERRULES")
PROVISION_TYPES = ("INTERPRETS",)

SYSTEM = """You classify how a Pakistani court judgment treats a cited precedent or statutory provision,
using only the sentence given. Decide what THIS court does, not what counsel argued, not what the court
below did, and not what the precedent itself did to other cases.
For a precedent (law-report citation):
  FOLLOWS        this court relies on it, quotes it with approval or applies its rule
  DISTINGUISHES  this court says it does not apply to this case (different facts or issue)
  OVERRULES      this court declares it wrongly decided or no longer good law
  CITES          a neutral mention, a citation in a list or footnote without treatment, or a case relied
                 on only by counsel or by the court below
For a provision:
  INTERPRETS     this court explains or decides the meaning or scope of the provision
  REFERS_TO      the provision is only mentioned or applied (charges, procedure, counsel's argument,
                 quoted statute text)
Give a short reason (under 20 words) for each link."""


class Verdict(BaseModel):
    n: int
    label: Literal["FOLLOWS", "DISTINGUISHES", "OVERRULES", "CITES", "INTERPRETS", "REFERS_TO"]
    reason: str


class Verdicts(BaseModel):
    verdicts: List[Verdict]


def edge_id(edge: Dict) -> str:
    return f"{edge['type']}|{edge['src']}|{edge['dst']}|{edge.get('paragraph', '')}"


def _target(edge: Dict) -> str:
    dst = edge["dst"]
    return dst[4:] if dst.startswith("CIT:") else dst.split("::")[-1]


def typed_edges() -> List[Dict]:
    edges = []
    for edge_type in PRECEDENT_TYPES + PROVISION_TYPES:
        with (GRAPH / f"edges_{edge_type.lower()}.csv").open(encoding="utf-8") as handle:
            edges += [dict(row, type=edge_type) for row in csv.DictReader(handle)]
    return edges


def _prompt(batch: List[Dict]) -> str:
    lines = []
    for n, edge in enumerate(batch, start=1):
        kind = "provision" if edge["type"] in PROVISION_TYPES else "precedent"
        lines.append(f"{n}. {kind}: {_target(edge)}\n   sentence: \"{edge['sentence'][:600]}\"")
    return "Classify each link.\n\n" + "\n\n".join(lines)


def classify(edges: List[Dict], llm) -> Dict[str, Dict]:
    """edge id -> {label, reason}; one request per BATCH edges (cached, so re-runs are free)."""
    out = {}
    for start in range(0, len(edges), BATCH):
        batch = edges[start:start + BATCH]
        result = llm.generate_json(_prompt(batch), Verdicts, system=SYSTEM, temperature=0.0)
        by_n = {v.n: v for v in result.verdicts}
        for n, edge in enumerate(batch, start=1):
            verdict = by_n.get(n)
            allowed = ("INTERPRETS", "REFERS_TO") if edge["type"] in PROVISION_TYPES else ("FOLLOWS", "DISTINGUISHES", "OVERRULES", "CITES")
            if verdict and verdict.label in allowed:
                out[edge_id(edge)] = {"label": verdict.label, "reason": verdict.reason}
        print(f"  {min(start + BATCH, len(edges))}/{len(edges)} links checked")
    return out


def run() -> None:
    from src.llm.gemini_client import GeminiClient

    edges = typed_edges()
    verdicts = classify(edges, GeminiClient())
    with CHECKS.open("w", encoding="utf-8") as handle:
        for edge in edges:
            v = verdicts.get(edge_id(edge))
            if v:
                handle.write(json.dumps({"id": edge_id(edge), "regex": edge["type"], "llm": v["label"], "reason": v["reason"],
                                         "sentence": edge["sentence"][:300]}, ensure_ascii=False) + "\n")
    changed = sum(1 for e in edges if verdicts.get(edge_id(e), {}).get("label", e["type"]) != e["type"])
    print(f"{len(verdicts)} of {len(edges)} links checked, {changed} retyped -> {CHECKS}")


def load_checks() -> Dict[str, str]:
    if not CHECKS.exists():
        return {}
    return {r["id"]: r["llm"] for r in map(json.loads, CHECKS.read_text(encoding="utf-8").splitlines())}


def score() -> None:
    """Regex vs LLM type accuracy on the hand-labelled sample."""
    gold = json.loads(GOLD.read_text(encoding="utf-8"))["edges"]
    from src.llm.gemini_client import GeminiClient

    llm_labels = classify([{**g, "type": g["type"]} for g in gold], GeminiClient())
    regex_ok = sum(g["type"] == g["gold"] for g in gold)
    llm_ok = sum(llm_labels.get(edge_id(g), {}).get("label") == g["gold"] for g in gold)
    print(f"regex type correct: {regex_ok}/{len(gold)}   LLM type correct: {llm_ok}/{len(gold)}")
    for g in gold:
        got = llm_labels.get(edge_id(g), {}).get("label")
        if got != g["gold"]:
            print(f"  #{g['n']} regex {g['type']} / LLM {got} / hand {g['gold']}: {g['why']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    score() if args.score else run()
