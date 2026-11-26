"""Parse .srt subtitle files and normalise text for word-error-rate comparison."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


@dataclass
class Cue:
    start: float  # seconds
    end: float
    text: str


def _secs(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[Cue]:
    cues: list[Cue] = []
    # blocks are separated by blank lines; tolerate \r\n and a BOM
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            m = _TIME.search(ln)
            if m:
                g = m.groups()
                text = " ".join(lines[i + 1:]).strip()
                cues.append(Cue(_secs(*g[:4]), _secs(*g[4:]), text))
                break
    return cues


def normalise(text: str) -> str:
    """Lower-case, drop [SOUND] tags and 'SPEAKER:' labels, strip punctuation.

    Both the reference and Whisper output go through this, so WER measures words,
    not formatting differences (commas, capitals) that a student would never notice.
    """
    text = re.sub(r"\[[^\]]*\]", " ", text)                 # [MUSIC PLAYING]
    text = re.sub(r"\b[A-Z][A-Z .'-]{2,}:", " ", text)      # DAVID MALAN:
    text = text.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def text_between(cues: list[Cue], start: float, end: float) -> str:
    """Reference text for cues that start inside [start, end)."""
    return " ".join(c.text for c in cues if start <= c.start < end)
