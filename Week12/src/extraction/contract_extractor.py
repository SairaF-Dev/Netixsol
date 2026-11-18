"""
Structure extractor for contracts (CUAD SEC filings and the synthetic set):
title, type, parties, effective date, governing law, dispute resolution and
top-level clauses with the page each clause starts on.

Fields that cannot be found are left empty / None rather than defaulted.
"""

import re
from pathlib import Path
from typing import Any, List, Optional

from src.extraction.text_utils import PageLine, page_lines
from src.utils.file_utils import load_json, read_text
from src.utils.logger import setup_logger
from src.utils.schemas import ContractClause, ContractDocument

logger = setup_logger("contract_extractor")

_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_DATE = re.compile(
    rf"(?:dated|effective|made(?: and entered into)?|entered into)(?: as)?(?: of| on)?,?\s*(?:this\s+|the\s+)?"
    rf"({_MONTH}\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?{_MONTH},?\s+\d{{4}}|"
    rf"\d{{1,2}}/\d{{1,2}}/\d{{2,4}})",
    re.I,
)
_PARTIES = re.compile(
    r"\bbetween:?\s+(?P<a>[A-Z][^,(;]{2,150}?)\s*[,(;].{0,500}?\band\s+(?P<b>[A-Z][^,(;]{2,150}?)\s*[,(;]",
    re.S,
)
_GOVERNING = re.compile(
    r"\b(?:governed|construed|interpreted|enforced)\b[^.;]{0,120}?\blaws?\s+of\s+(?:the\s+)?"
    r"((?:State|Commonwealth|Province|Republic|People's Republic)\s+of\s+)?"
    r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
)
_ARTICLE = re.compile(r"^(?:ARTICLE|Article)\s+([IVXLC]+|\d{1,2})\b\.?\s*[-:–—]?\s*(.*)$")
_NUMBERED = re.compile(r"^(?:Section\s+|SECTION\s+)?(\d{1,2})\.?\s+([A-Z][A-Za-z ,&/'\-]{2,80}?)(?:\.|:|$)(.*)$")
_TITLE_WORDS = re.compile(r"\b(AGREEMENT|CONTRACT|LICENSE|LEASE|AMENDMENT|PLAN|ARRANGEMENT)\b")


def _roman(value: str) -> int:
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    for current, nxt in zip(value, value[1:] + " "):
        total += -numerals[current] if numerals.get(nxt, 0) > numerals[current] else numerals[current]
    return total


class ContractStructureExtractor:
    """Extracts contract metadata and clauses into structured JSON."""

    def extract_from_pages(
        self,
        pages: List[str],
        doc_id: str,
        title_hint: Optional[str] = None,
        contract_type: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> ContractDocument:
        lines = page_lines(pages)
        head = " ".join(line.text for line in lines[:120])
        full_text = "\n".join(line.text for line in lines)

        title = next(
            (line.text.strip(" .") for line in lines[:40]
             if line.text.isupper() and _TITLE_WORDS.search(line.text) and 8 < len(line.text) < 120),
            None,
        ) or title_hint or "Untitled contract"

        parties: List[str] = []
        match = _PARTIES.search(head)
        if match:
            parties = [re.sub(r"\s+", " ", match.group(name)).strip(" .,") for name in ("a", "b")]

        date = _DATE.search(head)
        governing = _GOVERNING.search(re.sub(r"\s+", " ", full_text))
        governing_law = None
        if governing:
            governing_law = f"Laws of {(governing.group(1) or '')}{governing.group(2)}".strip()

        dispute = None
        arbitration = re.search(r"[^.]{0,200}\barbitrat\w*[^.]{0,200}\.", re.sub(r"\s+", " ", full_text), re.I)
        if arbitration:
            dispute = arbitration.group(0).strip()[:300]

        return ContractDocument(
            document_id=doc_id,
            contract_title=title.title() if title.isupper() else title,
            contract_type=contract_type or "Commercial contract",
            parties=parties,
            effective_date=date.group(1) if date else None,
            governing_law=governing_law,
            dispute_resolution=dispute,
            clauses=self._clauses(lines),
            raw_text=full_text,
            source_file=source_file,
        )

    @staticmethod
    def _clauses(lines: List[PageLine]) -> List[ContractClause]:
        """Top-level clauses: 'ARTICLE IV ...' or '4. Term.' headings with increasing numbers."""
        candidates = []
        for index, line in enumerate(lines):
            article = _ARTICLE.match(line.text)
            if article:
                number = article.group(1)
                value = int(number) if number.isdigit() else _roman(number)
                title = article.group(2).strip() or (lines[index + 1].text if index + 1 < len(lines) else "")
                candidates.append((index, value, f"Article {number}", title.strip(" .")[:120], ""))
                continue
            numbered = _NUMBERED.match(line.text)
            if numbered and len(numbered.group(2).split()) <= 10:
                candidates.append((index, int(numbered.group(1)), f"Clause {numbered.group(1)}",
                                   numbered.group(2).strip(" ."), numbered.group(3).strip()))

        # Prefer the scheme (Article vs numbered) with more headings, then keep increasing numbers.
        articles = [c for c in candidates if c[2].startswith("Article")]
        numbered = [c for c in candidates if c[2].startswith("Clause")]
        chosen = articles if len(articles) >= 3 and len(articles) >= len(numbered) / 3 else numbered
        accepted, last = [], 0
        for candidate in chosen:
            if last < candidate[1] <= last + 3:
                accepted.append(candidate)
                last = candidate[1]
        if len(accepted) < 2:
            return []

        clauses = []
        for position, (index, _, clause_id, title, rest) in enumerate(accepted):
            end = accepted[position + 1][0] if position + 1 < len(accepted) else len(lines)
            body = " ".join([rest] + [line.text for line in lines[index + 1:end]]).strip()
            clauses.append(ContractClause(
                clause_id=clause_id, clause_title=title, text=body, page_number=lines[index].page))
        return clauses

    def extract_from_text(self, text: str, doc_id: str = "CONT_UNKNOWN", **kwargs: Any) -> ContractDocument:
        return self.extract_from_pages(text.split("\f"), doc_id=doc_id, **kwargs)

    def extract_from_file(
        self, file_path: str | Path, doc_id: Optional[str] = None, parser: Any = None, **kwargs: Any
    ) -> ContractDocument:
        path = Path(file_path)
        doc_id = doc_id or path.stem
        if path.suffix == ".json":
            return ContractDocument.model_validate(load_json(path))
        if path.suffix == ".txt":
            return self.extract_from_text(read_text(path), doc_id=doc_id, **kwargs)
        if path.suffix.lower() == ".pdf":
            if parser is None:
                from src.ingestion.pdf_parser import LegalPDFParser
                parser = LegalPDFParser()
            pages = parser.extract_page_texts(path)
            return self.extract_from_pages([p["text"] for p in pages], doc_id=doc_id, source_file=str(path), **kwargs)
        raise ValueError(f"Unsupported file format: {path.suffix}")
