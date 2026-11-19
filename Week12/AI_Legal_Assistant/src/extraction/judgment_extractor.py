"""
Structure extractor for judgments of the Supreme Court of Pakistan and the Lahore
High Court: court, bench, case number, parties, dates, citations, statutes cited,
numbered paragraphs (with pages) and the holding (operative paragraph).

Nothing is invented: fields that cannot be found are left empty / None.
"""

import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

from src.extraction.text_utils import PageLine, page_lines
from src.utils.file_utils import load_json, read_text
from src.utils.logger import setup_logger
from src.utils.schemas import JudgmentDocument, JudgmentParagraph, JudgmentParties

logger = setup_logger("judgment_extractor")

_COURTS = [
    (re.compile(r"SUPREME\s+COURT\s+OF\s+PAKISTAN", re.I), "Supreme Court of Pakistan"),
    (re.compile(r"LAHORE\s+HIGH\s+COURT", re.I), "Lahore High Court"),
    (re.compile(r"HIGH\s+COURT\s+OF\s+SINDH|SINDH\s+HIGH\s+COURT", re.I), "High Court of Sindh"),
    (re.compile(r"ISLAMABAD\s+HIGH\s+COURT", re.I), "Islamabad High Court"),
    (re.compile(r"PESHAWAR\s+HIGH\s+COURT", re.I), "Peshawar High Court"),
]
_CASE_NO = re.compile(
    r"\b((?:Civil|Criminal|Jail|Constitution(?:al)?|Writ|Review|Original|Shariat|Human\s+Rights|Intra\s+Court|"
    r"Suo\s+Motu|C\.?\s?M\.?\s?A|Cr(?:l)?\.?\s?(?:Misc|Revision|Appeal|Petition|Rev)|W\.\s?P|C\.\s?P|C\.\s?A|"
    r"Crl\.\s?A|Crl\.\s?P|I\.?C\.?A|R\.?F\.?A|F\.?A\.?O|C\.?R|Civil\s+Revision|Regular\s+First\s+Appeal|"
    r"Reference|Family\s+Appeal|Tax\s+Reference|Execution)"
    r"[A-Za-z .()]{0,40}?Nos?\.?\s*[\w\-/&,. ]{1,60}?(?:\s+of\s+|/)\s*\d{4})",
    re.I,
)
_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_HEARING = re.compile(r"Date\s+of\s+(?:hearing|the\s+hearing)\s*[:\-]?", re.I)
_DECISION = re.compile(r"Date\s+of\s+(?:decision|announcement|judgment|order)\s*[:\-]?|Decided\s+on\s*[:\-]?", re.I)
_VERSUS = re.compile(r"^(?:versus|vs\.?|v/s\.?|v\.)$", re.I)
_PARTY_MARKER = re.compile(
    r"[.…_ ]*\(?(?:Petitioner|Appellant|Applicant|Complainant|Respondent|Accused)s?\)?(?:\(s\))?"
    r"(?:\s*No\.?\s*\d+)?[.\s]*$", re.I)
# Body headings are printed in capitals; lower-case "judgment" occurs in "(Against judgment ...)".
_BODY_START = re.compile(r"^(?:J\s?U\s?D\s?G\s?E?\s?M\s?E\s?N\s?T|O\s?R\s?D\s?E\s?R|SHORT\s+ORDER)\.?$")
# Header lines that bound the party block (lower-court details, court heading).
_NOT_A_PARTY = re.compile(
    r"\b(?:against|passed|dated|on appeal from|jurisdiction)\b|\bIN THE\b.*\bCOURT\b|"
    r"JUDICIAL DEPARTMENT|JUDGMENT SHEET|ORDER SHEET|HCJDA", re.I)
_PARA = re.compile(r"^(\d{1,3})\.\s+(.*)$")
_AUTHOR = re.compile(r"^([A-Z][A-Za-z .'\-]{3,60}),\s*(?:C\.?J|J|HCJ|ACJ)\.?\s*[—–.\-:]")
_OUTCOME = re.compile(
    r"\b(dismissed|allowed|accepted|disposed of|set aside|leave(?: to appeal)? (?:is )?(?:granted|refused)|"
    r"converted into (?:an )?appeal|acquitted|remanded|remitted|withdrawn|partly allowed|maintained|upheld|"
    r"declared|quashed|struck down|not maintainable|answered)\b", re.I)
_CITATION = re.compile(
    r"\b(?:PLD|PLJ|PCr\.?\s?LJ|KLR|NLR|CLC)\s+\d{4}\s+(?:SC|FSC|Lah(?:ore)?|Kar(?:achi)?|Pesh(?:awar)?|"
    r"Quetta|Bal(?:ochistan)?|Isl(?:amabad)?|Sindh|Supreme\s+Court|SC\s*\(AJ&K\)|AJ&K|GB)\s+\d+\b"
    r"|\b\d{4}\s+(?:SCMR|CLC|YLR|MLD|PCr\.?\s?LJ|PLC(?:\s*\(C\.?S\.?\))?|PTD|CLD|YLR\s*N|CLC\s*N|MLD\s*N|"
    r"PCr\.?\s?LJ\s*N|GBLR|SCR|PLD)\s+\d+\b",
    re.I,
)
_STATUTE_REF = re.compile(
    r"\b(?:[Ss]ections?|[Aa]rticles?|[Ss]\.|Art\.|Order|Rule)\s+[\dA-Z]+(?:\s*\([\w ]+\))*"
    r"(?:\s*(?:,|and|&|to|read with)\s*[\dA-Z]+(?:\s*\([\w ]+\))*){0,4}"
    r"\s*(?:of\s+(?:the\s+)?)?"
    r"(PPC|P\.P\.C\.?|Cr\.?\s?P\.?\s?C\.?|C\.?\s?P\.?\s?C\.?|Constitution(?: of the Islamic Republic of Pakistan)?(?:,? 1973)?|"
    r"Qanun-e-Shahadat(?: Order)?(?:,? 1984)?|Q\.?S\.?O\.?|(?:[A-Z][A-Za-z()'\-]*\s+){1,8}"
    r"(?:Act|Ordinance|Order|Code|Rules|Regulations)(?:,?\s*\d{4})?)"
)


def _iso_date(match: re.Match) -> str:
    day, month, year = (int(g) for g in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def _find_date_after(lines: List[PageLine], pattern: re.Pattern, limit: int = 120) -> Optional[str]:
    for index, line in enumerate(lines[:limit]):
        if pattern.search(line.text):
            window = line.text[pattern.search(line.text).end():] + " " + " ".join(
                l.text for l in lines[index + 1:index + 3])
            date = _DATE.search(window)
            if date:
                return _iso_date(date)
    return None


class JudgmentStructureExtractor:
    """Extracts judicial metadata, parties, citations, paragraphs and the holding."""

    def extract_from_pages(
        self,
        pages: List[str],
        doc_id: str,
        court_hint: Optional[str] = None,
        case_number_hint: Optional[str] = None,
        neutral_citation: Optional[str] = None,
        pages_needing_ocr: Optional[List[int]] = None,
        source_file: Optional[str] = None,
    ) -> JudgmentDocument:
        """Extract a judgment.

        case_number_hint: reliable case number (e.g. from the court's file name).
        neutral_citation: e.g. "2026 LHC 8304" for Lahore High Court files.
        """
        lines = page_lines(pages)
        head = lines[:150]
        head_text = "\n".join(line.text for line in head)

        # The court the file was downloaded from (hint) wins: the header often also names
        # the lower court ("against the judgment of the Peshawar High Court").
        court = court_hint or next((name for pattern, name in _COURTS if pattern.search(head_text[:3000])), None)
        court = court or "Unknown court"

        # The case number from the court's file name (passed as a hint by the
        # pipeline) is reliable; header text often also lists lower-court numbers.
        case_match = _CASE_NO.search(head_text)
        case_number = case_number_hint or (
            re.sub(r"\s+", " ", case_match.group(1)).strip(" .,") if case_match else "Unknown")

        body_index = self._body_start(lines)
        petitioner, respondent = self._parties(lines[: body_index or 80])
        bench = self._bench(lines[: body_index or 80])
        if not bench:
            # High Court judgments name the author at the start of the text ("NAME, J.-").
            author = next((m.group(1) for line in lines[:200] if (m := _AUTHOR.match(line.text))), None)
            if author:
                bench = [author.title() if author.isupper() else author]

        date_of_hearing = _find_date_after(lines, _HEARING)
        date_of_decision = _find_date_after(lines, _DECISION, limit=len(lines))
        date = date_of_decision or date_of_hearing or ""
        year_source = date or case_number
        # Whole 4-digit token only, so "No.12069 of 2010" gives 2010, not 2069.
        year_match = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", year_source)

        paragraphs = self._paragraphs(lines[body_index:] if body_index is not None else lines)
        holding, holding_page, outcome = self._holding(paragraphs)

        full_text = "\n".join(line.text for line in lines)
        citations = list(dict.fromkeys(re.sub(r"\s+", " ", c) for c in _CITATION.findall(full_text)))
        if neutral_citation:
            citations.insert(0, neutral_citation)
        statutes = list(dict.fromkeys(
            re.sub(r"\s+", " ", m.group(0)).strip() for m in _STATUTE_REF.finditer(full_text)
        ))[:40]

        return JudgmentDocument(
            document_id=doc_id,
            case_number=case_number,
            court=court,
            year=int(year_match.group(0)) if year_match else None,
            date_of_judgment=date_of_decision or "",
            date_of_hearing=date_of_hearing,
            bench=bench,
            parties=JudgmentParties(appellant_or_petitioner=petitioner, respondent=respondent),
            citations=citations,
            matter_id=self.matter_id(
                court, case_number if case_number != "Unknown" else (neutral_citation or doc_id)),
            legal_topics=[],
            statutes_cited=statutes,
            issues=[],
            holding=holding,
            outcome=outcome,
            full_text=full_text,
            paragraphs=paragraphs,
            holding_page=holding_page,
            source_file=source_file,
            pages_needing_ocr=pages_needing_ocr or [],
        )

    @staticmethod
    def matter_id(court: str, case_number: str) -> str:
        """Stable ID for the case (several PDFs can belong to one matter)."""
        prefix = {"Supreme Court of Pakistan": "SC", "Lahore High Court": "LHC"}.get(court, "CT")
        key = re.sub(r"[^A-Za-z0-9]+", "-", case_number).strip("-").upper()
        return f"{prefix}:{key}"

    @staticmethod
    def _body_start(lines: List[PageLine]) -> Optional[int]:
        for index, line in enumerate(lines[:200]):
            if _BODY_START.match(line.text.strip(" :")):
                return index + 1
            if _AUTHOR.match(line.text):
                return index
        return None

    @staticmethod
    def _clean_party(texts: List[str]) -> str:
        text = " ".join(t for t in texts if not t.startswith(("(Against", "[in ", "(On appeal", "(Appeal")))
        text = _PARTY_MARKER.sub("", text)
        text = re.sub(r"\s+", " ", text).strip(" .,;:…")
        return text[:300] or "Unknown"

    def _parties(self, lines: List[PageLine]) -> Tuple[str, str]:
        texts = [line.text for line in lines]
        for index, text in enumerate(texts):
            inline = re.match(r"^(?:\d+\.\s+)?(.{3,200}?)\s+(?:Vs\.?|Versus|V/S|v\.)\s+(.{3,200})$", text, re.I)
            if inline and not _VERSUS.match(text) and not _NOT_A_PARTY.search(text):
                return self._clean_party([inline.group(1)]), self._clean_party([inline.group(2)])
            if not _VERSUS.match(text.strip(" .")):
                continue
            before: List[str] = []
            for prev in reversed(texts[max(0, index - 12):index]):
                if _PARTY_MARKER.fullmatch(prev) or re.fullmatch(r"\[in .*\]", prev):
                    continue  # "…Petitioner(s)" marker or "[in CP 70-K/2023]" note
                if (_CASE_NO.search(prev) or _NOT_A_PARTY.search(prev) or "justice" in prev.lower()
                        or prev.startswith(("(Against", "[Against", "Present", "PRESENT", "Bench", "&", "…."))):
                    break
                before.insert(0, prev)
            after: List[str] = []
            for nxt in texts[index + 1:index + 14]:
                if nxt.lower().startswith(("for the", "date of", "in attendance", "present", "and")) or _BODY_START.match(nxt):
                    break
                after.append(nxt)
                if re.search(r"Respondents?(?:\(s\))?[.\s]*$", nxt):
                    break
            return self._clean_party(before), self._clean_party(after)
        return "Unknown", "Unknown"

    @staticmethod
    def _bench(lines: List[PageLine]) -> List[str]:
        names = []
        for line in lines:
            lower = line.text.lower()
            if "justice" in lower and len(line.text) < 120 and not lower.startswith(("for ", "before", "(")):
                name = re.sub(r"^(?:PRESENT|Present|Bench)\s*:?\s*", "", line.text).strip(" ,.")
                name = re.sub(r"^(?:Mr\.|Mrs\.|Ms\.|Miss)\s*", "", name, flags=re.I)
                if name.isupper():
                    name = name.title().replace("Cj", "CJ").replace("Hcj", "HCJ")
                names.append(name)
        return list(dict.fromkeys(names))[:9]

    @staticmethod
    def _paragraphs(lines: List[PageLine]) -> List[JudgmentParagraph]:
        paragraphs: List[JudgmentParagraph] = []
        current: Optional[dict] = None
        expected = 1
        for line in lines:
            match = _PARA.match(line.text)
            if match and int(match.group(1)) in (expected, expected + 1):
                if current:
                    paragraphs.append(JudgmentParagraph(**current))
                current = {"number": match.group(1), "text": match.group(2), "page": line.page}
                expected = int(match.group(1)) + 1
                continue
            if current is None:
                # Opening paragraph is usually unnumbered ("NAME, J.- ...").
                current = {"number": None, "text": line.text, "page": line.page}
                continue
            current["text"] += " " + line.text
        if current:
            paragraphs.append(JudgmentParagraph(**current))
        return [p for p in paragraphs if p.text.strip()]

    @staticmethod
    def _holding(paragraphs: List[JudgmentParagraph]) -> Tuple[str, Optional[int], Optional[str]]:
        for paragraph in reversed(paragraphs[-6:]):
            # Signature blocks and "Approved for reporting" trail the operative text.
            text = re.split(r"\(\s*[A-Z][A-Z .]{3,}\)|\bJUDGE\b|Approved for [Rr]eporting|Announced in", paragraph.text)[0]
            outcome = _OUTCOME.search(text)
            if outcome:
                return text.strip(), paragraph.page, outcome.group(1).lower()
        if paragraphs:
            last = paragraphs[-1]
            return last.text.strip()[:1500], last.page, None
        return "", None, None

    def extract_from_text(self, text: str, doc_id: str = "JUD_UNKNOWN", **kwargs: Any) -> JudgmentDocument:
        return self.extract_from_pages(text.split("\f"), doc_id=doc_id, **kwargs)

    def extract_from_file(
        self, file_path: str | Path, doc_id: Optional[str] = None, parser: Any = None, **kwargs: Any
    ) -> JudgmentDocument:
        path = Path(file_path)
        doc_id = doc_id or path.stem
        if path.suffix == ".json":
            return JudgmentDocument.model_validate(load_json(path))
        if path.suffix == ".txt":
            return self.extract_from_text(read_text(path), doc_id=doc_id, **kwargs)
        if path.suffix.lower() == ".pdf":
            if parser is None:
                from src.ingestion.pdf_parser import LegalPDFParser
                parser = LegalPDFParser()
            pages = parser.extract_page_texts(path)
            return self.extract_from_pages(
                [p["text"] for p in pages], doc_id=doc_id,
                pages_needing_ocr=[p["page_number"] for p in pages if p["needs_ocr"]],
                source_file=str(path), **kwargs,
            )
        raise ValueError(f"Unsupported file format: {path.suffix}")
