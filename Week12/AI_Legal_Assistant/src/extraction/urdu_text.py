"""
Cleanup and normalisation of EasyOCR output for the Pakistan Code Urdu laws.

EasyOCR's Urdu model often emits Arabic letter forms (ي ك ه ة) and Arabic-Indic
digits (٠-٩) where Urdu uses ی ک ہ and ۰-۹, and it reads the faint
"THE PAKISTAN CODE" watermark as broken Latin words (PAKIS, PASTAN, COD...).
`clean_urdu_ocr` fixes both; `normalize_for_search` additionally maps all digits
to ASCII and drops Urdu punctuation so queries and documents tokenise the same way.

The ه -> ہ mapping is a simplification: where the page has the aspirate ھ
(e.g. تھا) and OCR produced ه, the result is ہ, which is still a common
OCR-style spelling and keeps the word searchable.
"""

import re
from difflib import SequenceMatcher

_LETTERS = str.maketrans({
    "ي": "ی",  # ي Arabic yeh       -> ی Farsi/Urdu yeh
    "ى": "ی",  # ى alef maksura     -> ی
    "ك": "ک",  # ك Arabic kaf       -> ک keheh
    "ه": "ہ",  # ه Arabic heh       -> ہ heh goal
    "ة": "ہ",  # ة teh marbuta      -> ہ
    "أ": "ا",  # أ                  -> ا
    "إ": "ا",  # إ                  -> ا
})
_ARABIC_INDIC_TO_URDU = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")
_ALL_DIGITS_TO_ASCII = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_WATERMARK_WORDS = ("THE", "PAKISTAN", "CODE")
_LATIN_UPPER = re.compile(r"\b[A-Z]{3,}\b")
_JUNK_CHARS = re.compile(r"[~|<>^`]")
_PAGE_NUMBER_LINE = re.compile(r"^\s*[\d٠-٩۰-۹]{1,4}\s*$")
_URDU_PUNCT = re.compile(r"[،؛؟۔]")


def _is_watermark(token: str) -> bool:
    """Uppercase Latin token that looks like a piece of 'THE PAKISTAN CODE'."""
    if any(token in word for word in _WATERMARK_WORDS) or "PAKISTAN" in token or "CODE" in token:
        return True
    return any(SequenceMatcher(None, token, word).ratio() >= 0.7 for word in _WATERMARK_WORDS)


def normalize_urdu_letters(text: str) -> str:
    """Arabic letter forms -> Urdu forms; Arabic-Indic digits -> Urdu digits."""
    return text.translate(_LETTERS).translate(_ARABIC_INDIC_TO_URDU)


def clean_urdu_ocr(text: str) -> str:
    """Normalise letters/digits, remove the watermark, junk symbols and page-number lines."""
    text = normalize_urdu_letters(text)
    text = _LATIN_UPPER.sub(lambda m: "" if _is_watermark(m.group(0)) else m.group(0), text)
    text = _JUNK_CHARS.sub(" ", text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line and not _PAGE_NUMBER_LINE.match(line):
            lines.append(line)
    return "\n".join(lines)


def normalize_for_search(text: str) -> str:
    """Normalisation shared by documents and queries in the keyword index."""
    text = normalize_urdu_letters(text).translate(_ALL_DIGITS_TO_ASCII)
    return _URDU_PUNCT.sub(" ", text)


def urdu_year(text: str) -> int | None:
    """First 4-digit year (1800-2099) in any digit script, e.g. '... ۱۹۷۳ء' -> 1973."""
    match = re.search(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)", text.translate(_ALL_DIGITS_TO_ASCII))
    return int(match.group(1)) if match else None
