"""Shared helpers for turning per-page PDF text into clean, page-tagged lines."""

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List

# Page furniture common in Pakistan Code and court PDFs.
_FURNITURE = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+$", re.IGNORECASE),
    re.compile(r"^Updated till\b", re.IGNORECASE),
    re.compile(r"^[-–(\[]*\s*\d{1,4}\s*[-–)\]]*$"),          # 12, -2-, (3), [4]
    re.compile(r"^[ivxlcdm]{1,6}$", re.IGNORECASE),           # roman page numbers
    re.compile(r"^Powered by TCPDF", re.IGNORECASE),
]
# A line that is only a number marker, e.g. "1." or "2[3." (footnote prefix).
_NUMBER_ONLY = re.compile(r"^(?:\d+\[)?\s*\d{1,4}[A-Z]{0,4}\.$")


@dataclass
class PageLine:
    text: str
    page: int


def _normalise(line: str) -> str:
    line = line.replace("­", "-").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", line).strip()


def page_lines(pages: Iterable[str], first_page: int = 1, repeat_ratio: float = 0.4) -> List[PageLine]:
    """Split pages into cleaned lines tagged with their 1-based page number.

    Removes page numbers, "Page x of y" stamps and short lines that repeat on many
    pages (running headers/footers), then joins a lone section/paragraph number
    ("12.") with the line that follows it.
    """
    page_list = [[_normalise(line) for line in (text or "").splitlines()] for text in pages]
    page_list = [[line for line in lines if line] for lines in page_list]

    repeated = set()
    if len(page_list) >= 3:
        counts = Counter(line for lines in page_list for line in set(lines) if len(line) <= 80)
        threshold = max(3, int(len(page_list) * repeat_ratio))
        repeated = {line for line, count in counts.items() if count >= threshold}

    out: List[PageLine] = []
    pending_number = None
    for offset, lines in enumerate(page_list):
        page_no = first_page + offset
        for line in lines:
            if line in repeated or any(p.match(line) for p in _FURNITURE):
                continue
            if _NUMBER_ONLY.match(line):
                pending_number = (line, page_no)
                continue
            if pending_number is not None:
                line = f"{pending_number[0]} {line}"
                page_no_for_line = pending_number[1]
                pending_number = None
                out.append(PageLine(line, page_no_for_line))
                continue
            out.append(PageLine(line, page_no))
    return out


def join_lines(lines: Iterable[PageLine]) -> str:
    return " ".join(line.text for line in lines).strip()
