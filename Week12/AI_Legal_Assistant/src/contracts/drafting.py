"""
Day 4, Task 4: drafting agent - case brief, legal notice, contract clauses - with checked sources.

Every document is headed "DRAFT - for lawyer review" and every source in it is checked by code:

* case brief   from a judgment in the corpus. Gemini sees the numbered paragraphs and must cite
               [para N] with a quote; each quote must appear word for word in that paragraph. The list
               of authorities the judgment relies on (precedents, provisions) comes from the knowledge
               graph (data/graph), not from the model.
* legal notice from facts given by the lawyer (sender, recipient, amounts, dates). The legal basis is
               retrieved with the Day 2 pipeline (configuration "rerank") and every citation passes the
               Day 2 verifier (passage retrieved, Act matches, section exists, quote verbatim).
* clauses      from the firm playbook's standard wording for the requested items, adapted to the facts;
               the statutory sources are quoted from the corpus.

A citation that fails its check is removed and the text says "[source removed: not verified]".
Output: Markdown + Word in evaluations/drafts/.

Run:  python -m src.contracts.drafting brief SC_crl.p._207_k_2025
      python -m src.contracts.drafting notice data/contracts/drafting/notice_facts.json
      python -m src.contracts.drafting clauses data/contracts/drafting/clause_request.json
"""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

from src.contracts.review import DRAFT, playbook, source_quotes
from src.rag.answer import Citation, format_sources
from src.rag.verify import quote_found, verify_citation
from src.utils.file_utils import load_json

OUT_DIR = Path("evaluations/drafts")
GRAPH = Path("data/graph")


class ParaCite(BaseModel):
    paragraph: str
    quote: str


class BriefSection(BaseModel):
    heading: str
    text: str
    citations: List[ParaCite]


class Brief(BaseModel):
    title: str
    sections: List[BriefSection]


class DraftSection(BaseModel):
    heading: str
    text: str
    citations: List[Citation]


class Draft(BaseModel):
    title: str
    sections: List[DraftSection]


def _llm():
    from src.llm.gemini_client import GeminiClient
    return GeminiClient()


# ----------------------------------------------------------------------------- case brief
BRIEF_SYSTEM = """You write case briefs for lawyers at a Pakistani law firm from the numbered paragraphs of ONE judgment.
Sections, in order: Facts, Issues, Holding, Reasoning, Outcome. Plain, precise English. Every statement must be
supported: for each section give citations as {paragraph, quote}, the paragraph number exactly as shown and a
quote copied word for word from that paragraph. Use only the judgment; never add law or facts from memory."""


def _authorities(document_id: str) -> Dict[str, List[str]]:
    """Precedents and provisions the judgment relies on, from the knowledge graph."""
    out = {"precedents relied on": [], "precedents cited": [], "provisions referred to": []}
    if not GRAPH.exists():
        return out
    case_key = next((r["key"] for r in csv.DictReader((GRAPH / "nodes_case.csv").open(encoding="utf-8")) if r.get("document_id") == document_id), None)
    act_name = {r["key"]: re.split(r"\s*\(", r.get("name") or r["key"])[0] for r in csv.DictReader((GRAPH / "nodes_act.csv").open(encoding="utf-8"))}
    for edge_type, bucket in (("follows", "precedents relied on"), ("cites", "precedents cited"), ("distinguishes", "precedents cited"),
                              ("refers_to", "provisions referred to"), ("interprets", "provisions referred to")):
        path = GRAPH / f"edges_{edge_type}.csv"
        if case_key and path.exists():
            for r in csv.DictReader(path.open(encoding="utf-8")):
                if r["src"] == case_key:
                    act, _, section = r["dst"].partition("::")
                    label = r["dst"][4:] if r["dst"].startswith("CIT:") else f"{section}, {act_name.get(act, act)}"
                    if label not in out[bucket]:
                        out[bucket].append(label)
    return out


def case_brief(document_id: str, llm=None) -> Dict:
    doc = load_json(Path("data/structured/judgment") / f"{document_id}.json")
    paras = {str(p["number"] if p.get("number") is not None else f"p{i}"): p["text"] for i, p in enumerate(doc["paragraphs"])}
    numbered = "\n\n".join(f"[para {n}] {t[:1800]}" for n, t in paras.items())
    head = f"{doc['court']} | {doc['case_number']} | bench: {', '.join(doc.get('bench', []))}"
    brief = (llm or _llm()).generate_json(f"Judgment: {head}\n\n{numbered}", Brief, system=BRIEF_SYSTEM, temperature=0.0)
    sections, removed = [], 0
    for s in brief.sections:
        kept = []
        for c in s.citations:
            n = c.paragraph.replace("para", "").strip()
            if n in paras and quote_found(c.quote, paras[n]):
                kept.append({"source": f"{doc['case_number']}, para {n}", "quote": c.quote})
            else:
                removed += 1
        text = s.text if kept or not s.citations else s.text + " [source removed: not verified]"
        sections.append({"heading": s.heading, "text": text, "sources": kept})
    return {"kind": "case brief", "title": brief.title, "header": head, "sections": sections,
            "authorities": _authorities(document_id), "removed_citations": removed}


# ----------------------------------------------------------------------------- legal notice
NOTICE_SYSTEM = """You draft legal notices for a Pakistani law firm. Use the facts given and ONLY the numbered source
passages for any law. Sections: Heading (sender, recipient, date, subject), Facts, Breach, Legal basis, Demand,
Consequences, Signature block. For every statement of law give citations (source number, Act, section, a quote
copied word for word from that passage). Do not cite any law that is not in the passages; if the passages do not
support a point, leave the point out. Keep the tone firm and professional."""


def legal_notice(facts: Dict, llm=None, allow=None) -> Dict:
    """allow: access-control filter on retrieved passages (web app); None = no filter."""
    from src.rag.pipeline import _retriever

    retriever = _retriever("rerank")
    results, seen = [], set()
    for query in facts.get("legal_questions", []):
        for r in (retriever.retrieve(query, top_k=4, allow=allow) if allow else retriever.retrieve(query, top_k=4)):
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"]); results.append(r)
    prompt = f"FACTS\n{json.dumps({k: v for k, v in facts.items() if k != 'legal_questions'}, indent=1, ensure_ascii=False)}\n\nSOURCES\n{format_sources(results)}"
    draft = (llm or _llm()).generate_json(prompt, Draft, system=NOTICE_SYSTEM, temperature=0.0)
    return _checked(draft, results, "legal notice")


# "Section 73", "s. 489-F", "Article 199", "Sections 39 and 73"
_LEGAL_REF = re.compile(r"\b(?:sections?|s\.|ss\.|articles?|art\.)\s*(\d+(?:-?[A-Z]{1,2})?(?:\s*(?:,|and|&)\s*\d+(?:-?[A-Z]{1,2})?)*)", re.I)


def _ref_numbers(text: str) -> set:
    return {n.upper().replace("-", "") for m in _LEGAL_REF.finditer(text) for n in re.findall(r"\d+(?:-?[A-Z]{1,2})?", m.group(1), re.I)}


def _unsupported_statements(text: str, allowed: set):
    """Split a section's text into sentences; drop those naming a section / article that no verified source
    supports (red team G1: a fake 'Section 489-Z PPC' planted in the facts reached the notice uncited)."""
    kept, dropped = [], []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        refs = _ref_numbers(sentence)
        (dropped if refs - allowed else kept).append(sentence)
    return " ".join(kept), dropped


def _checked(draft: Draft, results: List[Dict], kind: str) -> Dict:
    sections, removed, verified = [], 0, []
    for s in draft.sections:
        kept = []
        for c in s.citations:
            ok, reason = verify_citation(c, results)
            if ok:
                kept.append({"source": f"{c.act_or_case}, {c.section_or_paragraph}", "quote": c.quote})
            else:
                removed += 1
        verified.append(kept)
    # a legal reference in the text must be one of the notice's verified sources
    allowed = {n for kept in verified for k in kept for n in _ref_numbers(k["source"])}
    unsupported: List[str] = []
    for s, kept in zip(draft.sections, verified):
        text, dropped = _unsupported_statements(s.text, allowed)
        unsupported += dropped
        if dropped:
            text += " [statement removed: it cites a provision not found in the verified sources]"
        if s.citations and not kept:
            text += " [source removed: not verified]"
        sections.append({"heading": s.heading, "text": text.strip(), "sources": kept})
    return {"kind": kind, "title": draft.title, "header": "", "sections": sections, "removed_citations": removed,
            "removed_statements": unsupported, "retrieved": [r["chunk_id"] for r in results]}


# ----------------------------------------------------------------------------- contract clauses
CLAUSE_SYSTEM = """You draft contract clauses for a Pakistani law firm. Start from the firm's standard wording given for
each item and adapt it to the deal facts (party names, amounts, periods). Keep the firm's position; do not weaken it.
Return one section per item: heading = item title, text = the clause, citations = empty list."""


def clauses(request: Dict, llm=None) -> Dict:
    items = [i for i in playbook() if i["id"] in request["items"]]
    standard = "\n\n".join(f"{i['title']} (id {i['id']})\nfirm position: {i['green']}\nstandard wording: {i['suggested_wording']}" for i in items)
    prompt = f"DEAL FACTS\n{json.dumps(request.get('facts', {}), indent=1, ensure_ascii=False)}\n\nITEMS\n{standard}"
    draft = (llm or _llm()).generate_json(prompt, Draft, system=CLAUSE_SYSTEM, temperature=0.0)
    sections = []
    from rapidfuzz import fuzz

    for position, s in enumerate(draft.sections):
        # pair each drafted clause with its playbook item by heading (position only as a fallback)
        item = max(items, key=lambda i: fuzz.token_set_ratio(i["title"], s.heading)) if items else None
        if item is None or fuzz.token_set_ratio(item["title"], s.heading) < 60:
            item = items[min(position, len(items) - 1)]
        srcs = [{"source": f"{q['act']}, {q['section']} ({q['title']}), page {q['page']}", "quote": q["quote"]} for q in source_quotes(item)]
        srcs.insert(0, {"source": f"Firm playbook: {item['title']} (standard wording)", "quote": item["suggested_wording"]})
        sections.append({"heading": s.heading, "text": s.text, "sources": srcs})
    return {"kind": "contract clauses", "title": request.get("title", "Draft clauses"), "header": "", "sections": sections, "removed_citations": 0}


# ----------------------------------------------------------------------------- export
def to_markdown(doc: Dict) -> str:
    lines = [f"> **{DRAFT}**", "", f"# {doc['title']}", ""]
    if doc.get("header"):
        lines += [doc["header"], ""]
    for s in doc["sections"]:
        lines += [f"## {s['heading']}", "", s["text"], ""]
        lines += [f"- *{src['source']}*: \"{src['quote']}\"" for src in s["sources"]]
        lines.append("")
    for bucket, values in (doc.get("authorities") or {}).items():
        if values:
            lines += [f"**Authorities ({bucket}, from the knowledge graph):** " + "; ".join(values), ""]
    lines.append(f"*{doc['removed_citations']} citation(s) removed by verification. {DRAFT}.*")
    return "\n".join(lines)


def to_docx(doc: Dict, path: Path) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import RGBColor

    d = Document()
    d.sections[0].header.paragraphs[0].text = DRAFT
    d.sections[0].header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    warn = d.add_paragraph().add_run(DRAFT)
    warn.bold, warn.font.color.rgb = True, RGBColor(0xC0, 0x00, 0x00)
    d.add_heading(doc["title"], level=0)
    if doc.get("header"):
        d.add_paragraph(doc["header"])
    for s in doc["sections"]:
        d.add_heading(s["heading"], level=1)
        d.add_paragraph(s["text"])
        for src in s["sources"]:
            p = d.add_paragraph(style="List Bullet")
            p.add_run(f"{src['source']}: ").italic = True
            p.add_run(f"\"{src['quote']}\"")
    for bucket, values in (doc.get("authorities") or {}).items():
        if values:
            d.add_paragraph(f"Authorities ({bucket}, from the knowledge graph): " + "; ".join(values))
    d.add_paragraph(f"{doc['removed_citations']} citation(s) removed by verification. {DRAFT}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    d.save(path)
    return path


def save(doc: Dict, stem: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{stem}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / f"{stem}.md").write_text(to_markdown(doc), encoding="utf-8")
    return to_docx(doc, OUT_DIR / f"{stem}.docx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["brief", "notice", "clauses"])
    parser.add_argument("source", help="judgment document id, or a JSON file of facts / clause request")
    args = parser.parse_args()
    if args.kind == "brief":
        print(save(case_brief(args.source), f"brief_{args.source}"))
    else:
        data = json.loads(Path(args.source).read_text(encoding="utf-8"))
        result = legal_notice(data) if args.kind == "notice" else clauses(data)
        print(save(result, f"{args.kind}_{Path(args.source).stem}"))
