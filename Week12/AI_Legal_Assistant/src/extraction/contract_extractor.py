"""
Structure extractor for contracts (CUAD SEC filings and the synthetic set):
title, type, parties, effective date, governing law, dispute resolution and
top-level clauses with the page each clause starts on.

Fields that cannot be found are left empty / None rather than defaulted.
"""

import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

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
_NUMBERED = re.compile(r"^(?:Section\s+|SECTION\s+)?(\d{1,2})(?:\.\s*|\s+)([A-Z][A-Za-z ,;;&/'\-]{2,80}?)(?:\.|:|$)(.*)$")   # U+037E: a Greek question mark some PDFs use for ';'
# 'I. Object of the Agreement': Roman-numbered parts without the word Article
_ROMAN = re.compile(r"^([IVX]{1,5})\.\s+([A-Z][^.]{2,80})$")
LONG_CLAUSE_WORDS = 2500   # longer clauses are split at their sub-clause headings (N.1, N.2, ...)
# '4.1 Term of Agreement': the first sub-clause of clause 4 (used when there is no '4.' heading)
_DECIMAL_FIRST = re.compile(r"^(?:Section\s+|SECTION\s+)?(\d{1,2})\.1\.?\s+([A-Z][^.:]{1,80})")
# '4. Licensee shall ...' or '4. 4.1 Licensee shall ...': a numbered paragraph with no title
_NUMBERED_PARAGRAPH = re.compile(r"^(\d{1,2})\.\s+(?:(\d{1,2}\.\d{1,2})\.?\s*)?(.*)$")
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
    def _candidates(lines: List[PageLine]) -> Tuple[List[tuple], List[tuple], List[tuple]]:
        """Possible clause headings, as (line index, number, clause id, title, text after the title), in three kinds:
        'ARTICLE IV ...'; titled '4. Term.' or decimal '4.1 Term' (first sub-clause stands for clause 4);
        untitled numbered paragraphs '4. Licensee shall ...' (title = the first words)."""
        articles, titled, untitled = [], [], []
        for index, line in enumerate(lines):
            article = _ARTICLE.match(line.text)
            if article:
                number = article.group(1)
                value = int(number) if number.isdigit() else _roman(number)
                title = article.group(2).strip() or (lines[index + 1].text if index + 1 < len(lines) else "")
                articles.append((index, value, f"Article {number}", title.strip(" .")[:120], ""))
                continue
            numbered = _NUMBERED.match(line.text)
            if numbered and len(numbered.group(2).split()) <= 10:
                titled.append((index, int(numbered.group(1)), f"Clause {numbered.group(1)}",
                               numbered.group(2).strip(" ."), numbered.group(3).strip()))
                continue
            decimal = _DECIMAL_FIRST.match(line.text)
            if decimal:
                titled.append((index, int(decimal.group(1)), f"Clause {decimal.group(1)}",
                               decimal.group(2).strip(" .:")[:120], ""))
                continue
            paragraph = _NUMBERED_PARAGRAPH.match(line.text)
            if paragraph:
                rest = paragraph.group(3).strip()
                words = rest.split()
                above = lines[index - 1].text.strip(" .:") if index else ""
                if paragraph.group(2) and len(words) < 3 and 0 < len(above.split()) <= 8:
                    title = above                     # '2. 2.1' with the clause title on the line above
                elif len(rest) > 10:
                    title = " ".join(words[:8]) + ("..." if len(words) > 8 else "")
                else:
                    continue
                untitled.append((index, int(paragraph.group(1)), f"Clause {paragraph.group(1)}", title, rest))
                continue
            roman = _ROMAN.match(line.text)
            if roman:
                articles.append((index, _roman(roman.group(1)), f"Part {roman.group(1)}", roman.group(2).strip(" .")[:120], ""))
        return articles, titled, untitled

    @staticmethod
    def _best_run(candidates: List[tuple], lines: List[PageLine]) -> List[tuple]:
        """Headings numbered 1, 2, 3 ... can appear more than once (a table of contents, then the body;
        numbered lists inside a clause). Build every increasing run - a heading joins the run it continues
        most closely, a 1 or 2 that continues none starts a new run - and keep the run whose clauses
        actually hold text."""
        runs: List[List[tuple]] = []
        previous = None
        for c in sorted(candidates, key=lambda c: c[0]):
            same_as_previous, previous = c[1] == previous, c[1]
            if same_as_previous:   # '1. Definitions' then '1.1 ...': the same clause, not a new run
                continue
            fits = [run for run in runs if 0 < c[1] - run[-1][1] <= 3]
            if fits:
                min(fits, key=lambda run: c[1] - run[-1][1]).append(c)
            elif c[1] <= 2:
                runs.append([c])

        def with_text(run: List[tuple]) -> int:
            ends = [c[0] for c in run[1:]] + [len(lines)]
            return sum(1 for c, end in zip(run, ends)
                       if len(c[4].split()) + sum(len(l.text.split()) for l in lines[c[0] + 1:end]) >= 15)
        return max(runs, key=lambda run: (with_text(run), -run[0][0]), default=[])   # a tie: the earlier run

    @classmethod
    def _clauses(cls, lines: List[PageLine]) -> List[ContractClause]:
        """Top-level clauses: 'ARTICLE IV ...', '4. Term.', '4.1 Term' or numbered paragraphs, increasing numbers."""
        articles, titled, untitled = cls._candidates(lines)
        # Prefer Article headings when there are enough of them, then titled numbers; numbered
        # paragraphs without titles only when the titled headings give fewer than 3 clauses.
        schemes = ([articles] if len(articles) >= 3 and len(articles) >= len(titled) / 3 else []) + [titled, titled + untitled]
        accepted: List[tuple] = []
        for scheme in schemes:
            accepted = cls._best_run(scheme, lines)
            if len(accepted) >= 3:
                break
        if len(accepted) < 2:
            return []

        clauses = []
        for position, (index, number, clause_id, title, rest) in enumerate(accepted):
            end = accepted[position + 1][0] if position + 1 < len(accepted) else len(lines)
            body = " ".join([rest] + [line.text for line in lines[index + 1:end]]).strip()
            parts = cls._sub_clauses(lines, index + 1, end, number) if len(body.split()) > LONG_CLAUSE_WORDS else []
            if not parts:
                clauses.append(ContractClause(
                    clause_id=clause_id, clause_title=title, text=body, page_number=lines[index].page))
                continue
            lead = " ".join([rest] + [line.text for line in lines[index + 1:parts[0][0]]]).strip()
            if len(lead.split()) >= 15:
                clauses.append(ContractClause(clause_id=clause_id, clause_title=title, text=lead, page_number=lines[index].page))
            carry = ""   # a sub-clause that is only a heading ('15.13 Governing Law.') joins the next one
            for k, (start, sub, sub_title, sub_rest) in enumerate(parts):
                stop = parts[k + 1][0] if k + 1 < len(parts) else end
                text = " ".join([carry, sub_rest] + [line.text for line in lines[start + 1:stop]]).strip()
                if len(text.split()) < 15 and k + 1 < len(parts):
                    carry = f"{sub_title}. {text}".strip()
                    continue
                carry = ""
                clauses.append(ContractClause(clause_id=f"{clause_id}.{sub}", clause_title=f"{title}: {sub_title}",
                                              text=text, page_number=lines[start].page))
        return clauses

    @staticmethod
    def _sub_clauses(lines: List[PageLine], start: int, end: int, number: int) -> List[tuple]:
        """A very long clause split at its own sub-clause headings 'N.1 ...', 'N.2 ...' (increasing), so a
        finding can point to 'Clause 3.12' instead of a 20,000-word 'Clause 3'. Needs at least 3 of them."""
        pattern = re.compile(rf"^{number}\.(\d{{1,2}})\.?\s+(\S.*)$")
        parts, last = [], 0
        for i in range(start, end):
            m = pattern.match(lines[i].text)
            if m and last < int(m.group(1)) <= last + 2:
                text = m.group(2).strip()
                head = re.match(r"([A-Z][^.]{1,80}?)\.\s*(.*)$", text)
                if head and len(head.group(1).split()) <= 10:
                    title, rest = head.group(1), head.group(2)
                else:
                    title, rest = " ".join(text.split()[:8]) + ("..." if len(text.split()) > 8 else ""), text
                parts.append((i, int(m.group(1)), title, rest))
                last = int(m.group(1))
        return parts if len(parts) >= 3 else []

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
