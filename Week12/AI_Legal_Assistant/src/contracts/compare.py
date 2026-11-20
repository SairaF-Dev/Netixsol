"""
Day 4, Task 3: compare two versions of a contract and explain each change's legal impact.

1. Align clauses by content, not by number (numbering often shifts between drafts): title + text
   similarity (rapidfuzz), best pairs first; a pair needs a similarity of at least 55. Clauses left
   unpaired are "removed" (only in the old version) or "added" (only in the new one).
2. Word-level differences inside each changed clause (difflib), shown as deleted / inserted words.
3. Gemini explains every change in plain language for the client: what changed, its legal effect,
   which side it favours and how risky it is, using the firm's playbook positions. The diff itself is
   computed by code, so no change can be invented or missed by the model.
4. Output: JSON, Markdown and a Word redline (deletions red and struck through, insertions blue and
   underlined) with the impact table, marked "DRAFT - for lawyer review".

Run:  python -m src.contracts.compare data/contracts/versions/supply_agreement_v1.json data/contracts/versions/supply_agreement_v2.json
"""

import argparse
import difflib
import json
import re
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel
from rapidfuzz import fuzz

from src.contracts.review import DRAFT, playbook

OUT_DIR = Path("evaluations/contract_comparisons")
MIN_SIMILARITY = 55


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def align(old: List[Dict], new: List[Dict]) -> List[Tuple[Optional[Dict], Optional[Dict]]]:
    scores = []
    for i, a in enumerate(old):
        for j, b in enumerate(new):
            text = fuzz.token_set_ratio(_norm(a["text"]), _norm(b["text"]))
            title = fuzz.token_set_ratio(a["clause_title"], b["clause_title"])
            scores.append((0.75 * text + 0.25 * title, i, j))
    used_old, used_new, pairs = set(), set(), {}
    for score, i, j in sorted(scores, reverse=True):
        if score >= MIN_SIMILARITY and i not in used_old and j not in used_new:
            used_old.add(i); used_new.add(j); pairs[i] = j
    out: List[Tuple[Optional[Dict], Optional[Dict]]] = []
    for i, a in enumerate(old):
        out.append((a, new[pairs[i]] if i in pairs else None))
    out += [(None, b) for j, b in enumerate(new) if j not in used_new]
    return out


def word_diff(old: str, new: str) -> List[Tuple[str, str]]:
    """[(op, text)] with op in equal / delete / insert, on words."""
    a, b = _norm(old).split(), _norm(new).split()
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            ops.append(("equal", " ".join(a[i1:i2])))
        if tag in ("delete", "replace"):
            ops.append(("delete", " ".join(a[i1:i2])))
        if tag in ("insert", "replace"):
            ops.append(("insert", " ".join(b[j1:j2])))
    return ops


def changes(old_contract: Dict, new_contract: Dict) -> List[Dict]:
    out = []
    for a, b in align(old_contract["clauses"], new_contract["clauses"]):
        if a and b and _norm(a["text"]) == _norm(b["text"]) and a["clause_title"] == b["clause_title"]:
            continue
        kind = "changed" if a and b else ("removed" if a else "added")
        out.append({"n": len(out) + 1, "kind": kind,
                    "old_clause": a and f"{a['clause_id']} {a['clause_title']}", "new_clause": b and f"{b['clause_id']} {b['clause_title']}",
                    "old_text": a and _norm(a["text"]), "new_text": b and _norm(b["text"]),
                    "diff": word_diff(a["text"], b["text"]) if a and b else None})
    return out


class Impact(BaseModel):
    n: int
    summary: str
    legal_impact: str
    favours: Literal["Client", "Contractor", "neither"]
    risk: Literal["high", "medium", "low", "none"]
    playbook_item: str


class Impacts(BaseModel):
    impacts: List[Impact]


SYSTEM = """You are a lawyer at Khan & Associates, a Pakistani law firm, explaining a counterparty's changes to a
contract to our client in plain language. For each numbered change give: a one-line summary of what changed; its
legal impact for the client in 1-3 plain sentences (mention Pakistani law where it matters, e.g. Section 27 of the
Contract Act, 1872 on restraint of trade, Section 74 on penalties); which side it favours; a risk level for the
client (high, medium, low, or none for a purely stylistic change); and the matching playbook item id (or "none").
Explain only the changes listed; do not invent others."""


def explain(change_list: List[Dict], client: str, llm=None) -> Dict[int, Dict]:
    from src.llm.gemini_client import GeminiClient

    llm = llm or GeminiClient()
    positions = "\n".join(f"- {i['id']} ({i['title']}): green = {i['green']} red = {i['red']}" for i in playbook())
    body = "\n\n".join(
        f"{c['n']}. {c['kind'].upper()} {c['new_clause'] or c['old_clause']}\n   OLD: {c['old_text'] or '(not in old version)'}\n"
        f"   NEW: {c['new_text'] or '(deleted)'}" for c in change_list)
    result = llm.generate_json(f"Our client: {client}\n\nPLAYBOOK\n{positions}\n\nCHANGES\n{body}", Impacts, system=SYSTEM, temperature=0.0)
    return {i.n: i.model_dump() for i in result.impacts}


def compare(old_path: Path, new_path: Path, client: str = "the Client", llm=None) -> Dict:
    old, new = json.loads(old_path.read_text(encoding="utf-8")), json.loads(new_path.read_text(encoding="utf-8"))
    change_list = changes(old, new)
    impacts = explain(change_list, client, llm) if change_list else {}
    for c in change_list:
        c["impact"] = impacts.get(c["n"])
    return {"old": old["contract_title"], "new": new["contract_title"], "client": client,
            "unchanged": len(old["clauses"]) - sum(1 for c in change_list if c["kind"] != "added"), "changes": change_list}


def to_markdown(result: Dict) -> str:
    lines = [f"# Contract comparison ({DRAFT})", "", f"Old: {result['old']}  ", f"New: {result['new']}  ",
             f"Client: {result['client']}. {len(result['changes'])} changes, {result['unchanged']} clauses unchanged.", "",
             "| # | Clause | Change | Risk | Favours | Legal impact |", "|---|---|---|---|---|---|"]
    for c in result["changes"]:
        imp = c["impact"] or {}
        lines.append(f"| {c['n']} | {c['new_clause'] or c['old_clause']} | {c['kind']}: {imp.get('summary', '')} | "
                     f"{imp.get('risk', '?')} | {imp.get('favours', '?')} | {imp.get('legal_impact', 'not explained')} |")
    lines += ["", "## Redline (deleted ~~struck~~, inserted **bold**)", ""]
    for c in result["changes"]:
        lines.append(f"**{c['n']}. {c['new_clause'] or c['old_clause']}** ({c['kind']})  ")
        if c["diff"]:
            lines.append(" ".join(f"~~{t}~~" if op == "delete" else f"**{t}**" if op == "insert" else t for op, t in c["diff"]))
        else:
            lines.append(f"~~{c['old_text']}~~" if c["kind"] == "removed" else f"**{c['new_text']}**")
        lines.append("")
    return "\n".join(lines)


def to_docx(result: Dict, path: Path) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import RGBColor

    doc = Document()
    doc.sections[0].header.paragraphs[0].text = DRAFT
    doc.sections[0].header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_heading("Contract comparison", level=0)
    doc.add_paragraph(f"Old: {result['old']}\nNew: {result['new']}\nClient: {result['client']}")
    doc.add_paragraph(f"{len(result['changes'])} changes; {result['unchanged']} clauses unchanged. {DRAFT}.")
    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    for cell, text in zip(table.rows[0].cells, ("#", "Clause", "Risk", "Favours", "Legal impact")):
        cell.text = text
    for c in result["changes"]:
        imp = c["impact"] or {}
        row = table.add_row().cells
        row[0].text, row[1].text = str(c["n"]), f"{c['new_clause'] or c['old_clause']} ({c['kind']})"
        row[2].text, row[3].text = imp.get("risk", "?"), imp.get("favours", "?")
        row[4].text = f"{imp.get('summary', '')} {imp.get('legal_impact', '')}".strip()
    doc.add_heading("Redline", level=1)
    for c in result["changes"]:
        doc.add_paragraph().add_run(f"{c['n']}. {c['new_clause'] or c['old_clause']} ({c['kind']})").bold = True
        para = doc.add_paragraph()
        ops = c["diff"] or ([("delete", c["old_text"])] if c["kind"] == "removed" else [("insert", c["new_text"])])
        for op, text in ops:
            run = para.add_run(text + " ")
            if op == "delete":
                run.font.strike, run.font.color.rgb = True, RGBColor(0xC0, 0x00, 0x00)
            elif op == "insert":
                run.font.underline, run.font.color.rgb = True, RGBColor(0x00, 0x32, 0xA0)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("--client", default="Pak Telecom Enterprises (Pvt) Ltd (the Client)")
    args = parser.parse_args()
    result = compare(Path(args.old), Path(args.new), args.client)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(args.new).stem
    (OUT_DIR / f"{stem}_comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / f"{stem}_comparison.md").write_text(to_markdown(result), encoding="utf-8")
    print(to_docx(result, OUT_DIR / f"{stem}_comparison.docx"))
