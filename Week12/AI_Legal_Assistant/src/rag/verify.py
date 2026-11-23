"""
Day 2, Task 5: automatic citation verification (code only, no LLM).

Every citation in an answer must pass four checks against the passages the model
was actually given:

  1. source      the citation points to a passage that was retrieved (1..k)
  2. attribution the Act / case named matches the document that passage comes from
  3. reference   the cited section / article / paragraph exists in that document
                 (checked against the structured corpus, not the model's word)
  4. quote       the quoted words appear verbatim in that passage (whitespace,
                 quote marks, footnote marks like "1[" and Urdu letter forms normalised;
                 "..." may join parts that appear in order)

A citation that fails any check is removed. If no citation survives, the answer
becomes "No sufficient source found". A citation that only gives a page (or a
chapter) is not fabricated but cannot be verified at section level; it is
counted as "imprecise" and removed as well, so the user only sees Act+section or
case+paragraph citations. Exception: the Urdu laws are indexed by OCR page (section
numbers do not survive OCR), so for them the page is the reference: it must be the
cited passage's page, and a guessed section (دفعہ) number is removed as unverifiable.
The OCR text has about 1 wrong letter in 3, so the model's clean Urdu quote rarely matches
verbatim: if it matches the page closely (85%+, see urdu_ocr_source_span) the citation is
kept but the quote shown is the source's own OCR text, never the model's wording.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.extraction.urdu_text import normalize_for_search
from src.rag.answer import NO_SOURCE, CitedAnswer, is_refusal
from src.utils.file_utils import load_json

STRUCTURED = Path("data/structured")
_FOOTNOTE = re.compile(r"\d+\[|\]|\[\s*\*[\s*]*\]")
_STOPWORDS = {"the", "of", "and", "act", "ordinance", "court", "pakistan", "high", "supreme", "case",
              "no", "law", "laws", "code", "islamic", "republic", "versus", "petition", "appeal"}


def _norm(text: str) -> str:
    text = normalize_for_search(text)
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'").replace("—", "-").replace("–", "-")
    text = _FOOTNOTE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _words(text: str) -> str:
    """Word sequence used for the verbatim check: same words in the same order, ignoring
    punctuation, spacing and footnote numbers glued to a word ("inquiry1." -> "inquiry")."""
    text = re.sub(r"(?<=[a-z])\d{1,2}(?=[^a-z0-9]|$)", "", _norm(text))
    return " ".join(re.findall(r"[a-z0-9؀-ۿ]+", text))


_URDU_LETTER = re.compile(r"[؀-ۿ]")
MIN_URDU_QUOTE_CHARS = 15


def _urdu_quote_found(parts: List[str], passage: str) -> bool:
    """OCR'd Urdu glues and splits words at random ("کے لیےزرتلافی"), so Urdu quotes are matched
    on the letter sequence with spaces removed; they must still be in order and long enough
    (15+ letters) that a match cannot happen by chance."""
    squash = lambda s: s.replace(" ", "")
    passage_s = squash(passage)
    parts = [squash(p) for p in parts]
    if sum(len(p) for p in parts) < MIN_URDU_QUOTE_CHARS:
        return False
    position = 0
    for part in parts:
        found = passage_s.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


URDU_OCR_MIN_MATCH = 85.0   # measured: real quotes 84-100 on their page, best wrong page <= 59
URDU_OCR_MIN_CHARS = 40


def urdu_ocr_source_span(quote: str, passage: str) -> Optional[Tuple[str, float]]:
    """For an OCR'd Urdu page (about 1 letter in 3 wrong), the model quotes clean Urdu that can
    never match verbatim. If the quote matches the page closely enough to show the model pointed
    at the right text, return that stretch of the SOURCE text (and the match %). The caller shows
    the source text, never the model's wording: a fuzzy match would also accept an added "not",
    so the model's quote itself is not trusted."""
    from rapidfuzz import fuzz

    quote_s = _words(quote).replace(" ", "")
    passage_w = _words(passage)
    keep = [i for i, ch in enumerate(passage_w) if ch != " "]   # squashed index -> spaced index
    passage_s = "".join(passage_w[i] for i in keep)
    if len(quote_s) < URDU_OCR_MIN_CHARS or not passage_s:
        return None
    match = fuzz.partial_ratio_alignment(quote_s, passage_s)
    if match is None or match.score < URDU_OCR_MIN_MATCH or match.dest_end <= match.dest_start:
        return None
    span = passage_w[keep[match.dest_start]:keep[match.dest_end - 1] + 1]
    return span, round(match.score, 1)


def quote_found(quote: str, passage: str) -> bool:
    passage_w = f" {_words(passage)} "
    parts = [_words(p) for p in re.split(r"\.\.\.|…", quote)]
    parts = [p for p in parts if p]
    if parts and _URDU_LETTER.search(" ".join(parts)):
        return _urdu_quote_found(parts, _words(passage))
    if not parts or sum(len(p.split()) for p in parts) < 4:
        return False
    position = 0
    for part in parts:
        found = passage_w.find(f" {part} ", position)
        if found < 0:
            return False
        position = found + len(part)
    return True


@lru_cache(maxsize=512)
def _document(document_id: str) -> Optional[Dict]:
    for kind in ("statute", "judgment", "contract"):
        path = STRUCTURED / kind / f"{document_id}.json"
        if path.exists():
            return {"kind": kind, **load_json(path)}
    upload = Path("data/web_outputs/uploads") / f"{document_id}.contract.json"   # contracts uploaded in the web app
    if document_id.startswith("UPLOAD_") and upload.exists():
        return {"kind": "contract", **load_json(upload)}
    return None


@lru_cache(maxsize=512)
def _labels(document_id: str) -> Tuple[set, set]:
    """(section/article labels, paragraph numbers) that exist in the structured document."""
    doc = _document(document_id) or {}
    sections = {s["section_number"] for c in doc.get("chapters", []) for s in c["sections"]}
    paragraphs = {str(p["number"]) for p in doc.get("paragraphs", []) if p.get("number")}
    clauses = {c["clause_id"] for c in doc.get("clauses", [])}
    return sections | clauses, paragraphs


_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def parse_reference(text: str) -> Tuple[str, Optional[str]]:
    """'Section 23(1)' -> ('section', 'Section 23'); 'Article 203F(1)' -> ('section', 'Article 203F');
    'para 7' -> ('paragraph', '7'); 'Clause 5' -> ('section', 'Clause 5'); 'page 19' -> ('page', '19')."""
    t = text.translate(_DIGITS).strip()
    low = t.lower()
    order_rule = re.search(r"\border\s+([IVXLC]+|\d+)\s*,?\s*rule\s+(\d+[A-Z]?)", t, re.I)
    if order_rule:
        return "section", f"Order {order_rule.group(1).upper()} Rule {order_rule.group(2).upper()}"
    if re.fullmatch(r"(the\s+)?holding", low):
        return "holding", None
    number = re.search(r"(\d+)\s*-?\s*([A-Za-z]{0,2})(?![a-z])", t)
    if not number:
        return "none", None
    num, suffix = number.group(1), number.group(2).upper()
    if re.search(r"\bpara(graph)?s?\b|پیرا", low):
        return "paragraph", num
    if re.search(r"\bpages?\b|\bp\.\s*\d|صفحہ", low):
        return "page", num
    if re.search(r"\bchapter\b|\bpart\b|\bschedule\b", low) and not re.search(r"\bsection\b|\barticle\b", low):
        return "chapter", num
    if re.search(r"\barticle\b|\bart\.", low):
        return "section", f"Article {num}{suffix}"
    if re.search(r"\bclause\b", low):
        return "section", f"Clause {num}"
    if re.search(r"\bsection\b|\bs\.|\bsec\.|دفعہ|دفعه", low) or re.fullmatch(r"\d+[A-Z]{0,2}", t):
        return "section", f"Section {num}{suffix}"
    return "none", None


def _attribution_ok(named: str, result: Dict) -> bool:
    """The Act / case named in the citation must match the passage's document."""
    meta = result.get("metadata", {})
    doc = _document(result["document_id"]) or {}
    parties = doc.get("parties") or {}
    target = " ".join(str(x) for x in (meta.get("act"), meta.get("court"), meta.get("case_number"),
                                        meta.get("citation"), meta.get("contract_title"),
                                        doc.get("act_name"), doc.get("case_number"), result["document_id"],
                                        parties.get("appellant_or_petitioner"), parties.get("respondent")) if x)
    words = lambda s: {w for w in re.findall(r"[a-z؀-ۿ]{4,}|\d{2,}", _norm(s)) if w not in _STOPWORDS}
    return bool(words(named) & words(target))


@lru_cache(maxsize=1)
def _statute_names() -> Dict[str, str]:
    names = {}
    for path in (STRUCTURED / "statute").glob("*.json"):
        doc = load_json(path)
        if doc.get("language") != "Urdu":
            names[path.stem] = doc["act_name"]
    return names


def _named_statute(named: str) -> Optional[str]:
    """Corpus statute whose name matches the Act named in a citation (e.g. 'Contract Act, 1872')."""
    words = lambda s: {w for w in re.findall(r"[a-z]{4,}", _norm(s)) if w not in _STOPWORDS}
    wanted = words(named)
    best = max(((len(wanted & words(name)) / max(1, len(words(name))), doc_id)
                for doc_id, name in _statute_names().items()), default=(0, None))
    return best[1] if best[0] >= 0.6 else None


def _statute_quoted_in_passage(citation, result: Dict) -> Tuple[bool, str]:
    """A judgment passage may quote a statute: accept 'Contract Act, Section 23' if that section
    exists in the corpus statute and the quote is in the passage or in that section."""
    doc_id = _named_statute(citation.act_or_case)
    kind, label = parse_reference(citation.section_or_paragraph)
    if not doc_id or kind != "section":
        return False, "attribution: named Act/case does not match the passage's document"
    sections, _ = _labels(doc_id)
    if label not in sections:
        return False, f"reference: {label} does not exist in {doc_id}"
    doc = _document(doc_id)
    section_text = next((" ".join([s["content"]] + s["subsections"]) for c in doc["chapters"]
                         for s in c["sections"] if s["section_number"] == label), "")
    if quote_found(citation.quote, result["content"]) or quote_found(citation.quote, section_text):
        return True, "ok (statute quoted in the passage)"
    return False, "quote: not found verbatim in the cited passage"


def verify_citation(citation, results: List[Dict]) -> Tuple[bool, str]:
    if not 1 <= citation.source <= len(results):
        return False, "source: passage number was not retrieved"
    result = results[citation.source - 1]
    if not _attribution_ok(citation.act_or_case, result):
        return _statute_quoted_in_passage(citation, result)
    kind, label = parse_reference(citation.section_or_paragraph)
    if kind == "holding":
        if (_document(result["document_id"]) or {}).get("kind") != "judgment":
            return False, "reference: only a judgment has a holding"
        return (True, "ok") if quote_found(citation.quote, result["content"]) else (
            False, "quote: not found verbatim in the cited passage")
    sections, paragraphs = _labels(result["document_id"])
    is_urdu_law = (_document(result["document_id"]) or {}).get("language") == "Urdu"
    if kind == "page" and is_urdu_law:
        # Urdu laws are indexed by OCR page (no section numbers survive OCR), so the page is the
        # most precise reference that can be checked: it must be the passage's page.
        page = str(result.get("metadata", {}).get("page", "")).translate(_DIGITS)
        if label != page:
            return False, f"reference: page {label} is not the cited passage's page ({page or 'unknown'})"
        if quote_found(citation.quote, result["content"]):
            return True, "ok (Urdu law, page-level)"
        span = urdu_ocr_source_span(citation.quote, result["content"])
        if span:
            return True, f"ok (Urdu OCR page, {span[1]:.0f}% match: source text shown instead of the model's quote)"
        return False, "quote: not found in the cited passage"
    if kind in ("page", "chapter", "none"):
        return False, f"imprecise: cites a {kind}, not a section or paragraph"
    if kind == "section":
        if is_urdu_law:
            return False, "unverifiable: Urdu law pages (OCR) carry no section numbers; cite the page"
        if not sections:
            return False, "reference: document has no section structure to verify against"
        if label not in sections:
            return False, f"reference: {label} does not exist in {result['document_id']}"
    if kind == "paragraph" and label not in paragraphs:
        return False, f"reference: para {label} does not exist in {result['document_id']}"
    if not quote_found(citation.quote, result["content"]):
        return False, "quote: not found verbatim in the cited passage"
    return True, "ok"


def verify_answer(answer: CitedAnswer, results: List[Dict]) -> Tuple[CitedAnswer, List[Dict]]:
    """Return the answer with only verified citations (or the refusal) and a per-citation report."""
    if is_refusal(answer):
        return answer, []
    report, kept = [], []
    for citation in answer.citations:
        ok, reason = verify_citation(citation, results)
        if ok and "source text shown" in reason:
            # never show the model's wording for a fuzzy (OCR) match: replace it by the source's own text
            span, _ = urdu_ocr_source_span(citation.quote, results[citation.source - 1]["content"])
            citation = citation.model_copy(update={"quote": span})
        report.append({**citation.model_dump(), "verified": ok, "reason": reason})
        if ok:
            kept.append(citation)
    if not kept:
        return CitedAnswer(short_answer=NO_SOURCE), report
    return CitedAnswer(short_answer=answer.short_answer, explanation=answer.explanation, citations=kept), report
