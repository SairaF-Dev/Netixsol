"""Clean text extracted from PDFs so search finds the words students type.

Two real problems found in the MIT slides (2026-11-26):
1. Ligatures: "fi" stored as one glyph "ﬁ", so "deﬁne" != "define".  Fix: Unicode NFKC.
2. Broken "ti" glyph: the font maps "ti" to "S" or "0": "funcSon", "func0on", "itera0ve".

The first version of fix (2) replaced every S/0 between lowercase letters. That also
corrupted camelCase code names: isSorted -> istiorted, maxSize -> maxtiize. So a repair
is now only made when there is independent evidence: the repaired word appears in clean
course text (Whisper transcripts + HTML notes, which never had the font problem) and the
original does not. Measured on lecture 6: 27/31 broken words repaired, 0 camelCase names
damaged. A few rare words stay unrepaired; a wrong "fix" would be worse than none.
"""
from __future__ import annotations

import re
import unicodedata

_TI_INSIDE = re.compile(r"(?<=[a-z])[S0](?=[a-z])")
_WORD = re.compile(r"\b\w*[a-z][S0][a-z]\w*\b")
# At the START of a word the pattern is ambiguous ("Solve" is real), so these few
# observed cases are listed explicitly instead.
_TI_WORD_START = {"Smes": "times", "Sme": "time", "0mes": "times", "0me": "time"}
_BULLETS = re.compile(r"[§◦▪•●]")


def _known(word: str, vocab: set[str]) -> bool:
    w = word.lower()
    return w in vocab or (w.endswith("s") and w[:-1] in vocab)  # accept plurals


def fix_ti_glyph(text: str, vocab: set[str]) -> str:
    """Repair "funcSon" -> "function" only when the repaired word is a known word
    and the original is not. `vocab` = lower-case words from clean course text."""
    def repair(m: re.Match) -> str:
        word = m.group(0)
        fixed = _TI_INSIDE.sub("ti", word)
        return fixed if _known(fixed, vocab) and not _known(word, vocab) else word

    text = _WORD.sub(repair, text)
    return re.sub(r"\b(" + "|".join(_TI_WORD_START) + r")\b",
                  lambda m: _TI_WORD_START[m.group(1)], text)


def clean_pdf_text(text: str, vocab: set[str] | None = None) -> str:
    text = unicodedata.normalize("NFKC", text)  # ﬁ -> fi, non-breaking spaces -> spaces
    if vocab:
        text = fix_ti_glyph(text, vocab)
    text = _BULLETS.sub(" ", text)
    return " ".join(text.split())  # collapse newlines and repeated spaces
