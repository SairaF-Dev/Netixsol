"""
Structure extractor for statutes: Act -> Chapter/Part/Order -> Section/Article/Rule.

Works on the real Pakistan Code / National Assembly PDFs. Section headings appear
in several layouts ("1. Short title.—(1) ...", "30. Power to order discovery. The
Court ...", or the number and title on separate lines), so candidates are found
with a permissive pattern and then filtered:

* numbers must increase (a reset to 1 starts a new run, e.g. each CPC Order);
* runs whose headings have almost no text between them are tables of contents
  and are dropped.
"""

import re
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from src.extraction.text_utils import PageLine, page_lines
from src.utils.file_utils import load_json, read_text
from src.utils.logger import setup_logger
from src.utils.schemas import ChapterItem, SectionItem, StatuteDocument

logger = setup_logger("statute_extractor")

_HEADING = re.compile(r"^(?:\d+\[)?\s*\[?(\d{1,4})([A-Z]{0,4})\.\s+\[?([A-Z“\"].*)$")
_TITLE_END = re.compile(
    r"\.\s*(?:—|–|-{1,2}|_{1,})"   # ".—" ".–" ".-" ".__"
    r"|:\s*(?:—|–|-{1,2}|_{1,})?"  # ":" ":—"
    r"|\.\s+(?=[A-Z(“\"])"              # ". Every suit ..."
)
_DIVISION = re.compile(r"^(CHAPTER|PART|ORDER)\s+([IVXLC]+[A-Z]?|\d+[A-Z]?)\b\.?\s*[–—:-]?\s*(.*)$")
_SCHEDULE = re.compile(r"^(?:THE\s+)?([A-Z]+\s+)?SCHEDULE\b", re.IGNORECASE)
_DOT_LEADER =re.compile(r"\.{4,}|…{2,}")
_SUBSECTION = re.compile(r"^(?:\d+\[)?\(\d+[A-Z]?\)")
_ACT_NUMBER = re.compile(r"\(\s*((?:ACT|Act|ORDINANCE|Ordinance|P\.O\.|President's Order)\s+No\.?\s*[^)]{1,40})\)")
_YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")
# Amendment footnotes printed at the foot of Pakistan Code pages.
_FOOTNOTE = re.compile(
    r"^\d{1,3}\s*(?:Subs\.|Ins\.|Added|Omitted|Renumbered|New\s|Rep\.|The words|Vide|Inserted|"
    r"Substituted|Amended|Proviso|Clause|Sub-section|Explanation|Section|Article)",
    re.IGNORECASE,
)


def _is_successor(prev: Optional[Dict[str, Any]], event: Dict[str, Any]) -> bool:
    """True if event is the natural next heading after prev (n -> n+1, 2 -> 2A, 2A -> 2B)."""
    if prev is None:
        return event["num"] == 1
    if event["num"] == prev["num"]:
        return event["suffix"] > prev["suffix"]
    return event["num"] == prev["num"] + 1


def _split_title(rest: str) -> Optional[tuple]:
    """Split heading text into (title, body). None if it does not look like a heading."""
    if _DOT_LEADER.search(rest):
        return None
    match = _TITLE_END.search(rest)
    if match:
        title, body = rest[: match.start()], rest[match.end():]
    else:
        title, body = rest, ""
        if rest.rstrip().endswith((",", ";")) or len(rest) > 160:
            return None
    title = title.strip(" .[]")
    if not title or len(title.split()) > 30:
        return None
    return title, body.strip()


class StatuteStructureExtractor:
    """Extracts the Act/Chapter/Section hierarchy from statute PDFs."""

    def extract_from_pages(
        self,
        pages: List[str],
        doc_id: str,
        act_name: Optional[str] = None,
        pages_needing_ocr: Optional[List[int]] = None,
        source_file: Optional[str] = None,
    ) -> StatuteDocument:
        lines = page_lines(pages)
        act_name = act_name or self._detect_act_name(lines) or "Unknown Act"
        is_constitution = "constitution" in act_name.lower()
        year_match = _YEAR.search(act_name)

        # 1. Find heading candidates and divisions (chapter/part/order/schedule).
        events: List[Dict[str, Any]] = []
        for index, line in enumerate(lines):
            division = _DIVISION.match(line.text)
            if division and line.text.split()[0].isupper():
                title = division.group(3).strip(" .:-_")
                if not title and index + 1 < len(lines) and len(lines[index + 1].text) < 80:
                    title = lines[index + 1].text.strip(" .")
                events.append({"kind": "division", "index": index, "label": division.group(1).title(),
                               "number": division.group(2), "title": title})
                continue
            if _SCHEDULE.match(line.text) and line.text.isupper() and len(line.text) < 60:
                events.append({"kind": "division", "index": index, "label": "Schedule",
                               "number": line.text.title(), "title": line.text.title()})
                continue
            heading = _HEADING.match(line.text)
            if heading:
                split = _split_title(heading.group(3))
                if split:
                    events.append({"kind": "section", "index": index, "num": int(heading.group(1)),
                                   "suffix": heading.group(2), "title": split[0], "body": split[1]})

        # 2. Keep sections whose numbers increase; a reset to 1 starts a new run.
        #    A jump (e.g. "11." from a footnote marker before "1.") is skipped when
        #    the expected next number turns up shortly afterwards.
        sections = [e for e in events if e["kind"] == "section"]
        runs: List[List[Dict[str, Any]]] = []
        previous = None
        for position, event in enumerate(sections):
            num, suffix = event["num"], event["suffix"]
            if previous is None or num == 1 and not suffix:
                if previous is None and num > 3:
                    continue
                # A "1." inside a section (a numbered list) is not a new run if the
                # current sequence continues shortly afterwards.
                division_between = any(
                    e["kind"] == "division" and previous["index"] < e["index"] < event["index"] for e in events
                ) if previous is not None else True
                if not division_between and any(
                    _is_successor(previous, later) for later in sections[position + 1: position + 40]
                ):
                    continue
                runs.append([event])
            elif (num == previous["num"] and suffix > previous["suffix"]) or previous["num"] < num <= previous["num"] + 25:
                if not _is_successor(previous, event) and any(
                    _is_successor(previous, later) for later in sections[position + 1: position + 40]
                ):
                    continue
                runs[-1].append(event)
            else:
                continue
            previous = event

        # 3. Drop table-of-contents runs (headings with almost no text between them).
        kept = set()
        kept_runs = []
        for run in runs:
            gaps = [nxt["index"] - cur["index"] for cur, nxt in zip(run, run[1:])]
            body_chars = [len(event["body"]) for event in run]
            if len(run) == 1 or (gaps and median(gaps) > 1.5) or median(body_chars) > 40:
                kept.update(id(event) for event in run)
                kept_runs.append(run)
        # The longest kept run is the Act's own section/article sequence; later
        # restarted runs are Orders (CPC) or schedule/annex items.
        main_run = {id(event) for event in max(kept_runs, key=len)} if kept_runs else set()
        first_section = min((e["index"] for e in events if id(e) in kept), default=len(lines))
        # Divisions listed in a table of contents (before the first body section)
        # are ignored, except the CHAPTER/PART heading right before that section.
        lead = [e for e in events if e["kind"] == "division" and e["index"] < first_section
                and e["label"] in ("Chapter", "Part")]
        accepted = [
            e for e in events
            if id(e) in kept
            or (e["kind"] == "division" and e["index"] >= first_section)
            or (lead and e is lead[-1])
        ]

        # 4. Assemble chapters and sections in document order.
        chapters: List[Dict[str, Any]] = []
        current_chapter = None
        current_order = None
        current_schedule = None
        preamble_end = len(lines)
        boundaries = [e["index"] for e in accepted] + [len(lines)]
        for position, event in enumerate(accepted):
            end = boundaries[position + 1]
            if event["kind"] == "division":
                if event["label"] == "Order":
                    current_order = event["number"]
                elif event["label"] == "Schedule":
                    current_order, current_schedule = None, event["title"]
                chapter_number = event["title"] if event["label"] == "Schedule" else f"{event['label']} {event['number']}"
                current_chapter = {"chapter_number": chapter_number,
                                   "chapter_title": event["title"] or event["label"], "sections": []}
                chapters.append(current_chapter)
                continue
            preamble_end = min(preamble_end, event["index"])
            if current_chapter is None:
                current_chapter = {"chapter_number": "General", "chapter_title": "General Provisions", "sections": []}
                chapters.append(current_chapter)
            number = f"{event['num']}{event['suffix']}"
            if id(event) in main_run:
                label = f"{'Article' if is_constitution else 'Section'} {number}"
            elif current_order:
                label = f"Order {current_order} Rule {number}"
            else:
                label = f"{current_schedule or current_chapter['chapter_number']} item {number}"
            body_lines = [event["body"]] if event["body"] else []
            body_lines += [line.text for line in lines[event["index"] + 1:end] if not _FOOTNOTE.match(line.text)]
            content, subsections = self._split_subsections(body_lines)
            current_chapter["sections"].append({
                "section_number": label, "title": event["title"], "content": content,
                "subsections": subsections, "page_start": lines[event["index"]].page,
            })

        chapter_models = [
            ChapterItem(
                chapter_number=ch["chapter_number"],
                chapter_title=ch["chapter_title"],
                sections=[SectionItem(**section) for section in ch["sections"]],
            )
            for ch in chapters
            if ch["sections"]
        ]
        return StatuteDocument(
            document_id=doc_id,
            act_name=act_name,
            act_number=self._detect_act_number(lines),
            year=int(year_match.group(1)) if year_match else 0,
            preamble=self._detect_preamble(lines[:preamble_end]),
            chapters=chapter_models,
            raw_text="\n".join(line.text for line in lines),
            source_file=source_file,
            pages_needing_ocr=pages_needing_ocr or [],
        )

    @staticmethod
    def _split_subsections(body_lines: List[str]) -> tuple:
        content: List[str] = []
        subsections: List[str] = []
        for text in body_lines:
            if _SUBSECTION.match(text):
                subsections.append(text)
            elif subsections:
                subsections[-1] += " " + text
            else:
                content.append(text)
        return " ".join(content).strip(), [s.strip() for s in subsections]

    @staticmethod
    def _detect_act_name(lines: List[PageLine]) -> Optional[str]:
        for line in lines[:40]:
            text = line.text.strip(" .")
            if text.isupper() and re.search(r"\b(ACT|ORDINANCE|CODE|CONSTITUTION|ORDER)\b", text) and len(text) < 120:
                return text.title()
        return None

    @staticmethod
    def _detect_act_number(lines: List[PageLine]) -> Optional[str]:
        for line in lines[:400]:
            match = _ACT_NUMBER.search(line.text)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _detect_preamble(lines: List[PageLine]) -> str:
        text = " ".join(line.text for line in lines)
        start = re.search(r"\bWHEREAS\b", text)
        if not start:
            return ""
        return text[start.start(): start.start() + 1500].strip()

    def extract_from_text(self, text: str, doc_id: str = "STAT_UNKNOWN", act_name: Optional[str] = None) -> StatuteDocument:
        """Extract from plain text; form feeds (\\f) separate pages if present."""
        return self.extract_from_pages(text.split("\f"), doc_id=doc_id, act_name=act_name)

    def extract_from_file(
        self, file_path: str | Path, doc_id: Optional[str] = None, act_name: Optional[str] = None, parser: Any = None
    ) -> StatuteDocument:
        path = Path(file_path)
        doc_id = doc_id or path.stem
        if path.suffix == ".json":
            return StatuteDocument.model_validate(load_json(path))
        if path.suffix == ".txt":
            return self.extract_from_text(read_text(path), doc_id=doc_id, act_name=act_name)
        if path.suffix.lower() == ".pdf":
            if parser is None:
                from src.ingestion.pdf_parser import LegalPDFParser
                parser = LegalPDFParser()
            pages = parser.extract_page_texts(path)
            return self.extract_from_pages(
                [p["text"] for p in pages], doc_id=doc_id, act_name=act_name,
                pages_needing_ocr=[p["page_number"] for p in pages if p["needs_ocr"]],
                source_file=str(path),
            )
        raise ValueError(f"Unsupported file format: {path.suffix}")
