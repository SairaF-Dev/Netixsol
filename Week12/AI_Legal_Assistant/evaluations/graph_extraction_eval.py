"""
Day 3, Task 2: precision / recall of the regex graph extraction on 20 hand-annotated judgments.

Answer key: evaluations/graph_gold_20.json (made without looking at the extractor's output).
Extractor output: data/graph/*.csv (python -m src.graph.regex_extract).

Three link types are scored per judgment, as sets:
  citations   Case -[CITES|FOLLOWS|DISTINGUISHES|OVERRULES]-> precedent, compared as normalised
              law-report citations ("PLD 2016 Supreme Court 358" == "PLD 2016 SC 358")
  provisions  Case -[REFERS_TO|INTERPRETS]-> Section, compared as (act, provision). The extractor's
              Act nodes are mapped onto the answer key's act names by ACT_PATTERNS, so a duplicate
              Act node ("criminal-procedure-code" and "code-of-criminal-procedure") still counts as
              a correct link here; duplicates are reported separately under entity resolution.
  judges      Judge -[SAT_ON]-> Case, compared by normalised name.

Precision = correct extracted links / all extracted links; recall = correct extracted links /
links in the answer key (micro-averaged over the 20 judgments).

Run:  python -m evaluations.graph_extraction_eval
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.graph.entities import canonical_act
from src.graph.regex_extract import norm_citation, norm_name

GOLD = Path("evaluations/graph_gold_20.json")             # development set: errors here guided the fixes
HELDOUT = Path("evaluations/graph_gold_heldout_5.json")   # annotated after the fixes; never used to tune
# First run of the original extractor on the first version of the development key (for the report).
BEFORE_FIXES = {"citations": (1.00, 0.81), "provisions": (0.96, 0.54), "judges": (1.00, 0.93)}
GRAPH = Path("data/graph")
REPORT = Path("evaluations/graph_precision_recall.md")
PRECEDENT_EDGES = ("cites", "follows", "distinguishes", "overrules")
PROVISION_EDGES = ("refers_to", "interprets")

def _read(name: str) -> List[Dict]:
    path = GRAPH / f"{name}.csv"
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def norm_provision(label: str) -> str:
    """'Section 337-D' -> 'SECTION 337D'; 'Order 39 Rule 1' / 'Order XXXIX Rule 1' -> 'ORDER XXXIX RULE 1'."""
    from src.graph.regex_extract import roman

    label = re.sub(r"(?i)\border\s+(\d+)", lambda m: f"Order {roman(m.group(1))}", label)
    return re.sub(r"\s+", " ", label.replace("-", "")).strip().upper()


def norm_cit(citation: str) -> str:
    text = re.sub(r"\(\s*Pak\.?\s*\)", "", citation)              # "PLD 1958 SC (Pak.) 41"
    return re.sub(r"[^A-Z0-9]", "", norm_citation(text).upper())


def _same_judge(name: str, candidates: Set[str]) -> str:
    from rapidfuzz import fuzz

    return next((c for c in candidates if c.split()[:1] == name.split()[:1] and fuzz.ratio(c, name) >= 90), name)


def score(gold: Set, predicted: Set) -> Dict:
    correct = gold & predicted
    return {"gold": len(gold), "predicted": len(predicted), "correct": len(correct),
            "missed": sorted(map(str, gold - predicted)), "wrong": sorted(map(str, predicted - gold))}


def prf(total: Dict) -> Tuple[float, float, float]:
    p = total["correct"] / total["predicted"] if total["predicted"] else 0.0
    r = total["correct"] / total["gold"] if total["gold"] else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def evaluate(gold_path: Path = GOLD) -> Dict:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))["judgments"]
    cases = _read("nodes_case")
    case_key = {row["document_id"]: row["key"] for row in cases if row.get("document_id")}
    case_cit = {row["key"]: (row.get("citation") or row.get("name") or row["key"]) for row in cases}
    act_name = {row["key"]: row.get("name", "") for row in _read("nodes_act")}
    judge_name = {row["key"]: row["name"] for row in _read("nodes_judge")}

    predicted = defaultdict(lambda: {"citations": set(), "provisions": set(), "judges": set()})
    for edge_type in PRECEDENT_EDGES:
        for row in _read(f"edges_{edge_type}"):
            dst = row["dst"]
            raw = dst[4:] if dst.startswith("CIT:") else case_cit.get(dst, dst)
            predicted[row["document_id"]]["citations"].add(norm_cit(raw))
    for edge_type in PROVISION_EDGES:
        for row in _read(f"edges_{edge_type}"):
            act_key, _, label = row["dst"].partition("::")
            predicted[row["document_id"]]["provisions"].add(
                (canonical_act(act_key, act_name.get(act_key, "")), norm_provision(label)))
    doc_of_case = {key: doc for doc, key in case_key.items()}
    for row in _read("edges_sat_on"):
        if row["dst"] in doc_of_case:
            predicted[doc_of_case[row["dst"]]]["judges"].add(norm_name(judge_name.get(row["src"], row["src"])))

    per_doc, totals = {}, {kind: {"gold": 0, "predicted": 0, "correct": 0} for kind in ("citations", "provisions", "judges")}
    for doc_id, item in gold.items():
        wanted = {"citations": {norm_cit(c) for c in item["citations"]},
                  "provisions": {(act, norm_provision(label)) for act, label in item["provisions"]},
                  "judges": {norm_name(j) for j in item["judges"]}}
        # A judge is matched by identity, not spelling: the graph keeps one spelling per judge
        # ("Kakar" for "Kakar" / "Kakkar"), so a predicted name 90%+ similar to a key name counts.
        predicted[doc_id]["judges"] = {_same_judge(name, wanted["judges"]) for name in predicted[doc_id]["judges"]}
        per_doc[doc_id] = {kind: score(wanted[kind], predicted[doc_id][kind]) for kind in wanted}
        for kind, result in per_doc[doc_id].items():
            for field in ("gold", "predicted", "correct"):
                totals[kind][field] += result[field]
    return {"per_doc": per_doc, "totals": totals, "judge_name": judge_name}


def entity_resolution(judge_name: Dict[str, str]) -> Dict:
    """Over the whole graph: Acts split into several nodes, and Judge nodes that are not names."""
    by_act = defaultdict(list)
    for row in _read("nodes_act"):
        act = canonical_act(row["key"], row.get("name", ""))
        if act != row["key"]:
            by_act[act].append(row["key"])
    split_acts = {act: keys for act, keys in by_act.items() if len(keys) > 1}
    from rapidfuzz import fuzz

    is_junk = lambda name: bool(re.search(r"\d|[=|:]|\b(the|of|in|while|and|for)\b", name.lower())) or len(name.split()) > 6
    not_names = [name for name in judge_name.values() if is_junk(name)]
    clean = sorted({key for key, name in judge_name.items() if not is_junk(name)})
    # Spelling variants of one judge ("Akhter" / "Akhtar", "Kakar" / "Kakkar"): near-identical keys.
    variants = [(a, b) for i, a in enumerate(clean) for b in clean[i + 1:]
                if fuzz.ratio(a, b) >= 90 and a.split()[0] == b.split()[0]]
    return {"split_acts": split_acts, "judge_nodes": len(judge_name), "judge_nodes_not_names": sorted(not_names),
            "judge_variants": variants}


KINDS = (("citations", "Precedent citations (CITES / FOLLOWS / ...)"),
         ("provisions", "Statute provisions (REFERS_TO / INTERPRETS)"),
         ("judges", "Judges (SAT_ON)"))


def _errors(result: Dict) -> str:
    errors = []
    for doc_id, kinds in result["per_doc"].items():
        lines = [f"- **{kind}** missed: {', '.join(r['missed'])}" for kind, r in kinds.items() if r["missed"]]
        lines += [f"- **{kind}** wrong: {', '.join(r['wrong'])}" for kind, r in kinds.items() if r["wrong"]]
        if lines:
            errors.append(f"#### {doc_id}\n" + "\n".join(lines))
    return "\n".join(errors) or "none"


def write_report(dev: Dict, held: Dict, res: Dict) -> None:
    rows = []
    for kind, label in KINDS:
        bp, br = BEFORE_FIXES[kind]
        (dp, dr, _), (hp, hr, _) = prf(dev["totals"][kind]), prf(held["totals"][kind])
        rows.append(f"| {label} | {bp:.0%} / {br:.0%} | {dp:.0%} / {dr:.0%} ({dev['totals'][kind]['gold']}) | "
                    f"{hp:.0%} / {hr:.0%} ({held['totals'][kind]['gold']}) |")
    split = "\n".join(f"| {act} | {', '.join(keys)} |" for act, keys in sorted(res["split_acts"].items())) or "| none | |"
    junk = ", ".join(f"`{n}`" for n in res["judge_nodes_not_names"][:8]) or "none"
    variants = "; ".join(f"`{a}` / `{b}`" for a, b in res["judge_variants"]) or "none"
    REPORT.write_text(f"""# Graph extraction: precision and recall (Day 3, Task 2)

Extractor: regex only (`src/graph/regex_extract.py`). Script: `python -m evaluations.graph_extraction_eval`.
Answer keys were made by Claude (an AI model, not a person) from the judgment text, without looking at the
extractor's output:

* **Development set** (`evaluations/graph_gold_20.json`): 20 judgments (12 Supreme Court, 8 Lahore High
  Court). Its errors were used to improve the extractor, so its scores after the fixes are optimistic.
* **Held-out set** (`evaluations/graph_gold_heldout_5.json`): 5 other judgments, annotated after the fixes
  and never used to change the extractor: the fairer estimate (but small).

Precision / recall (number of links in the answer key in brackets):

| Link type | Before fixes (development) | After fixes (development) | After fixes (held-out) |
|---|---:|---:|---:|
{chr(10).join(rows)}

What the fixes were (all regex / rules, no LLM): law names ending in "Procedure" and containing "of"
("Code of Civil Procedure", "Transfer of Property Act"); "Section 382-B, Cr.P.C." (comma, hyphen);
"Order XVII Rule 3"; sub-clauses inside lists ("337-L (i), (ii), 506"); short names a judgment defines
("the Code", "the Act"); a section without a law named takes the law named last in the same paragraph;
Indian AIR / SCC and "SCP" citations; footnote numbers glued to citations; judge names cleaned of page text;
spelling variants merged.

## Entity resolution (whole graph)

Acts that are still more than one node (the same law written in different ways):

| Act | Nodes |
|---|---|
{split}

Judge nodes: {res['judge_nodes']}; {len(res['judge_nodes_not_names'])} still not a clean name: {junk}.
The same judge split by spelling: {variants}. Merged spellings are kept on the Judge node as `aliases`.

## Remaining errors

### Development set

{_errors(dev)}

### Held-out set

{_errors(held)}
""", encoding="utf-8")


if __name__ == "__main__":
    dev, held = evaluate(GOLD), evaluate(HELDOUT)
    write_report(dev, held, entity_resolution(dev["judge_name"]))
    for name, result in (("development", dev), ("held-out", held)):
        for kind, total in result["totals"].items():
            p, r, f = prf(total)
            print(f"{name:11} {kind:11} gold={total['gold']:4} extracted={total['predicted']:4} correct={total['correct']:4}  P={p:.0%} R={r:.0%} F1={f:.2f}")
    print(f"Wrote {REPORT}")
