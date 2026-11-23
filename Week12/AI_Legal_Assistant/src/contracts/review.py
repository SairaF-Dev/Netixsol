"""
Day 4, Task 2: playbook risk review of a contract, exported as a Word file with comments.

Steps for one contract (data/structured/contract/<id>.json, clauses from Day 1):
1. Candidates: for each playbook item (data/playbook/firm_playbook.json), the 3 clauses closest in
   meaning to the item (multilingual-e5-small embeddings, as in Day 2), plus any clause whose title
   names it. Keeps the prompt small even for a 60-page contract.
2. Judgement: Gemini rates each item green / amber / red / missing against the playbook positions,
   names the clause(s), quotes the words it relies on, explains why, and suggests wording.
3. Verification (code): every quote must appear word for word in the clause it names (the Day 2 rule);
   an unverified quote is removed and the finding says so. Legal sources are quoted from the corpus
   (Contract Act, Income Tax Ordinance), never written by the model.
4. Risk score 0-100: each red item adds its weight, amber half of it, a missing required clause counts
   as red; divided by the total weight.
5. Word export: summary, findings table, missing clauses, then the contract with a Word comment on each
   clause that has a finding. Every page is marked "DRAFT - for lawyer review".

Run:  python -m src.contracts.review CONT_SYNTH_001 [--party "Client name"]
"""

import argparse
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from src.rag.verify import quote_found
from src.security.injection import FENCE_RULE, fence
from src.utils.file_utils import load_json

PLAYBOOK = Path("data/playbook/firm_playbook.json")
CONTRACTS = Path("data/structured/contract")
OUT_DIR = Path("evaluations/contract_reviews")
TOP_K = 3
STATUS_ICON = {"green": "✅", "amber": "⚠️", "red": "❌", "missing": "❌"}
DRAFT = "DRAFT — for lawyer review"


class Finding(BaseModel):
    item_id: str
    status: Literal["green", "amber", "red", "missing"]
    clause_ids: List[str]
    quote: str
    reason: str
    suggested_wording: str


class Review(BaseModel):
    findings: List[Finding]


SYSTEM = """You are a senior associate at Khan & Associates, a Pakistani law firm, reviewing a contract for the
firm's client against the firm's playbook. For EVERY playbook item give one finding:
- status: green (meets the green position), amber (negotiate), red (unacceptable), or missing (no clause
  covers it in the candidate clauses shown);
- clause_ids: the clause(s) you relied on (empty if missing);
- quote: words copied exactly from that clause that show the problem or the position (empty if missing);
- reason: one or two plain sentences a client can understand;
- suggested_wording: replacement or new wording for amber, red or missing items (empty for green), based on
  the playbook's suggested wording and adapted to the contract.
Judge from the client's side. Use only the clauses shown; never invent contract text.
""" + FENCE_RULE


@lru_cache(maxsize=1)
def playbook() -> List[Dict]:
    return load_json(PLAYBOOK)["items"]


@lru_cache(maxsize=1)
def _embedder():
    from src.indexing.onnx_models import embedder      # shared with search: one copy in memory
    return embedder()


def load_contract(contract_id: str) -> Dict:
    path = Path(contract_id)
    return load_json(path if path.suffix == ".json" and path.exists() else CONTRACTS / f"{contract_id}.json")


WINDOW, WINDOW_OVERLAP = 300, 50


def windows(contract: Dict) -> List[Dict]:
    """Clauses split into ~300-word windows (long clauses of a 60-page contract would not fit whole)."""
    out = []
    for c in contract["clauses"]:
        words = c["text"].split()
        if not words:
            continue
        starts = range(0, max(1, len(words) - WINDOW_OVERLAP), WINDOW - WINDOW_OVERLAP) if len(words) > WINDOW + WINDOW_OVERLAP else [0]
        for k, s in enumerate(starts):
            out.append({"clause_id": c["clause_id"], "clause_title": c["clause_title"], "part": k + 1,
                        "text": " ".join(words[s:s + WINDOW]) if len(starts) > 1 else c["text"]})
    return out


def candidates(contract: Dict, items: List[Dict]) -> Dict[str, List[Dict]]:
    """item id -> the TOP_K windows closest in meaning (+ short clauses whose title names the item)."""
    parts = windows(contract)
    if not parts:
        return {item["id"]: [] for item in items}
    model = _embedder()
    part_vecs = model.encode([f"passage: {p['clause_title']}. {p['text']}" for p in parts], normalize_embeddings=True)
    item_vecs = model.encode([f"query: {i['title']}. {i['green']} {i['red']}" for i in items], normalize_embeddings=True)
    out = {}
    for item, vec in zip(items, item_vecs):
        ranked = [parts[i] for i in (part_vecs @ vec).argsort()[::-1][:TOP_K]]
        words = [w for w in re.findall(r"[a-z]{5,}", item["title"].lower())]
        ranked += [p for p in parts if p not in ranked and p["part"] == 1 and len(p["text"].split()) <= WINDOW
                   and any(w in p["clause_title"].lower() for w in words)]
        out[item["id"]] = ranked
    return out


def _prompt(contract: Dict, cands: Dict[str, List[Dict]], party: str) -> str:
    shown = {}
    for parts in cands.values():
        for p in parts:
            shown[(p["clause_id"], p["part"])] = p
    clause_text = "\n\n".join(f"[{p['clause_id']}] {p['clause_title']}" + (f" (part {p['part']})" if p["part"] > 1 else "") + f"\n{p['text']}"
                              for p in shown.values())
    items = "\n\n".join(
        f"{i['id']} - {i['title']} ({'required' if i['required'] else 'optional'})\n  green: {i['green']}\n  amber: {i['amber']}\n"
        f"  red: {i['red']}\n  suggested wording: {i['suggested_wording']}\n  candidate clauses: {', '.join(dict.fromkeys(c['clause_id'] for c in cands[i['id']])) or 'none'}"
        for i in playbook())
    return (f"Contract: {contract.get('contract_title')} ({contract.get('contract_type')})\nOur client: {party}\n\n"
            f"PLAYBOOK\n{items}\n\nCLAUSES\n{fence(clause_text)}")


def source_quotes(item: Dict) -> List[Dict]:
    """The item's legal sources, quoted from the structured corpus (not from the model)."""
    out = []
    for act_id, label in item.get("sources", []):
        act = load_json(Path("data/structured/statute") / f"{act_id}.json")
        section = next((s for ch in act["chapters"] for s in ch["sections"] if s["section_number"] == label), None)
        if section:
            text = re.sub(r"\s+", " ", section["content"]).strip()
            out.append({"act": act["act_name"], "section": label, "title": section["title"], "page": section.get("page_start"),
                        "quote": text[:400] + ("..." if len(text) > 400 else "")})
    return out


def review_contract(contract_id: str, party: str = "the Client", llm=None) -> Dict:
    from src.llm.gemini_client import GeminiClient

    llm = llm or GeminiClient()
    contract = load_contract(contract_id)
    items = playbook()
    cands = candidates(contract, items)
    result = llm.generate_json(_prompt(contract, cands, party), Review, system=SYSTEM, temperature=0.0)
    by_id = {c["clause_id"]: c for c in contract["clauses"]}
    findings = {}
    for f in result.findings:
        item = next((i for i in items if i["id"] == f.item_id), None)
        if not item or f.item_id in findings:
            continue
        clause_ids = [cid for cid in f.clause_ids if cid in by_id]
        quote_ok = bool(f.quote) and any(quote_found(f.quote, by_id[cid]["text"]) for cid in clause_ids)
        findings[f.item_id] = {
            "item_id": f.item_id, "title": item["title"], "status": f.status, "required": item["required"],
            "weight": item["weight"], "clause_ids": clause_ids,
            "quote": f.quote if quote_ok else "",
            "quote_note": "" if quote_ok or not f.quote else "the model's quote was not found word for word in the clause and was removed",
            "reason": f.reason, "suggested_wording": "" if f.status == "green" else f.suggested_wording,
            "sources": source_quotes(item)}
    for item in items:   # an item the model skipped is reported, not silently dropped
        findings.setdefault(item["id"], {"item_id": item["id"], "title": item["title"], "status": "missing", "required": item["required"],
                                         "weight": item["weight"], "clause_ids": [], "quote": "", "quote_note": "",
                                         "reason": "Not assessed by the model; check manually.", "suggested_wording": item["suggested_wording"],
                                         "sources": source_quotes(item)})
    ordered = [findings[i["id"]] for i in items]
    return {"contract_id": contract_id, "title": contract.get("contract_title"), "type": contract.get("contract_type"),
            "party": party, "risk_score": risk_score(ordered), "findings": ordered,
            "missing": [f["title"] for f in ordered if f["status"] == "missing"]}


def risk_score(findings: List[Dict]) -> int:
    total = sum(f["weight"] for f in findings)
    points = sum(f["weight"] * (1.0 if f["status"] == "red" or (f["status"] == "missing" and f["required"]) else
                                0.5 if f["status"] == "amber" else 0.0) for f in findings)
    return round(100 * points / total) if total else 0


def risk_band(score: int) -> str:
    return "High" if score >= 50 else "Medium" if score >= 25 else "Low"


# ----------------------------------------------------------------------------- Word export
def export_docx(review: Dict, path: Path) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    contract = load_contract(review["contract_id"])
    doc = Document()
    for section in doc.sections:
        section.header.paragraphs[0].text = DRAFT
        section.header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_heading(f"Contract review: {review['title']}", level=0)
    p = doc.add_paragraph()
    run = p.add_run(DRAFT + ". Prepared by an AI assistant from the firm's playbook; every finding must be checked by a lawyer.")
    run.bold, run.font.color.rgb = True, RGBColor(0xC0, 0x00, 0x00)
    counts = {s: sum(1 for f in review["findings"] if f["status"] == s) for s in ("green", "amber", "red", "missing")}
    doc.add_paragraph(f"Client: {review['party']}    Contract type: {review['type']}")
    doc.add_paragraph(f"Risk score: {review['risk_score']}/100 ({risk_band(review['risk_score'])})    "
                      f"✅ {counts['green']}   ⚠️ {counts['amber']}   ❌ {counts['red']}   missing {counts['missing']}")

    doc.add_heading("Findings", level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    for cell, text in zip(table.rows[0].cells, ("", "Playbook item", "Clause", "Why")):
        cell.text = text
    for f in review["findings"]:
        row = table.add_row().cells
        row[0].text = STATUS_ICON[f["status"]]
        row[1].text = f["title"] + ("" if f["status"] != "missing" else " (missing)")
        row[2].text = ", ".join(f["clause_ids"]) or "-"
        row[3].text = f["reason"]
    if review["missing"]:
        doc.add_heading("Missing clauses", level=1)
        for title in review["missing"]:
            f = next(x for x in review["findings"] if x["title"] == title)
            doc.add_paragraph(f"{title}: proposed wording - {f['suggested_wording']}", style="List Bullet")

    doc.add_heading("Contract text with comments", level=1)
    notes = {}
    for f in review["findings"]:
        for cid in f["clause_ids"]:
            if f["status"] != "green":
                notes.setdefault(cid, []).append(f)
    for clause in contract["clauses"]:
        heading = doc.add_paragraph()
        head_run = heading.add_run(f"{clause['clause_id']}  {clause['clause_title']}")
        head_run.bold = True
        body = doc.add_paragraph(re.sub(r"\s+", " ", clause["text"]).strip())
        body.paragraph_format.space_after = Pt(6)
        for f in notes.get(clause["clause_id"], []):
            text = [f"{STATUS_ICON[f['status']]} {f['title']}: {f['reason']}"]
            if f["quote"]:
                text.append(f"Relied on: \"{f['quote']}\"")
            if f["suggested_wording"]:
                text.append(f"Suggested wording: {f['suggested_wording']}")
            for src in f["sources"]:
                text.append(f"Source: {src['act']}, {src['section']} ({src['title']}), page {src['page']}: \"{src['quote']}\"")
            text.append(DRAFT)
            doc.add_comment(head_run, text="\n".join(text), author="AI review (draft)", initials="AI")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def run(contract_id: str, party: str) -> Path:
    review = review_contract(contract_id, party)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(contract_id).stem
    (OUT_DIR / f"{stem}_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    return export_docx(review, OUT_DIR / f"{stem}_review.docx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("contract_id")
    parser.add_argument("--party", default="the Client")
    args = parser.parse_args()
    print(run(args.contract_id, args.party.replace("_", " ")))
