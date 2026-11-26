"""Turn transcripts, notes and slides into chunks: one idea each, with a link back.

Every chunk keeps WHERE it came from (lesson, timestamp / page / section, link),
because the Day 3 tutor must cite "Lecture 6 at 1:46", not just answer.

Sizes (why): ~60-90 s of speech or ~150-250 words is one idea. Smaller loses context
("it calls itself": what does?); bigger buries the answer and makes the link vague.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

import pymupdf
from bs4 import BeautifulSoup

from ilm.content.download import lesson_files, lesson_path
from ilm.content.text_clean import clean_pdf_text
from ilm.content.transcribe import transcript_path

# transcript chunk limits
MAX_SECONDS = 75
MAX_WORDS = 220
# notes sections longer than this are split
NOTES_MAX_WORDS = 260
# slide pages with fewer words than this are merged into one "slide outline" chunk
SLIDE_MIN_WORDS = 25


@dataclass
class Chunk:
    id: str
    lesson_id: str
    course_id: str
    source: str          # transcript | notes | slides
    title: str           # human-readable label shown in citations
    text: str
    url: str             # where a student can see it (YouTube ?t=, notes #anchor, PDF #page=)
    license: str
    start_sec: float | None = None
    end_sec: float | None = None
    page: int | None = None
    section: str | None = None

    def metadata(self) -> dict:
        """Chroma metadata must be str/int/float/bool: drop the Nones."""
        return {k: v for k, v in asdict(self).items() if v is not None and k not in ("id", "text")}


def _mmss(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- transcripts ----
def transcript_chunks(lesson: dict) -> list[Chunk]:
    """Group Whisper segments into ~75 s windows. The last segment of each chunk is
    repeated at the start of the next (overlap), so an idea cut at a border survives."""
    path = transcript_path(lesson["id"])
    if not path.exists():
        return []
    segs = json.loads(path.read_text(encoding="utf-8"))["segments"]
    course = lesson["course"]
    chunks: list[Chunk] = []
    current: list[dict] = []

    def flush():
        start, end = current[0]["start"], current[-1]["end"]
        text = " ".join(s["text"] for s in current)
        chunks.append(Chunk(
            id=f"{lesson['id']}:transcript:{len(chunks):04d}", lesson_id=lesson["id"],
            course_id=course["id"], source="transcript",
            title=f"{lesson['title']} (video {_mmss(start)})", text=text,
            url=f"https://youtu.be/{lesson['youtube']}?t={int(start)}",
            license=course["license"], start_sec=start, end_sec=end))

    for seg in segs:
        current.append(seg)
        words = sum(len(s["text"].split()) for s in current)
        if current[-1]["end"] - current[0]["start"] >= MAX_SECONDS or words >= MAX_WORDS:
            flush()
            current = [current[-1]]  # overlap: carry the last segment forward
    if len(current) > 1 or (current and not chunks):
        flush()
    return chunks


# ---------------------------------------------------------------------- notes ----
def _split_words(text: str, max_words: int) -> list[str]:
    """Split long text into near-equal parts on sentence ends, each <= ~max_words."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    sentences = re.split(r"(?<=[.!?:])\s+", text)
    parts, cur = [], []
    for s in sentences:
        if cur and len(" ".join(cur + [s]).split()) > max_words:
            parts.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        parts.append(" ".join(cur))
    return parts


def notes_chunks(lesson: dict) -> list[Chunk]:
    """CS50P notes: one chunk per <h2> section (long sections split), linked by anchor.
    MIT's "notes" file is the official transcript PDF: it is the answer key for Whisper,
    not course content to index twice, so it is skipped."""
    if not lesson_files(lesson)["notes"]["name"].endswith(".html"):
        return []
    path = lesson_path(lesson, "notes")
    if not path.exists():
        return []
    course = lesson["course"]
    main = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser").find("main")
    # Syntax highlighting wraps every token in its own <span>. Joining tokens with " "
    # turned `square(2)` into `square ( 2 )` and `__name__` into `_ _name_ _`.
    # So flatten each code element to its exact text first (pre blocks keep newlines).
    for code in main.find_all(["pre", "code"]):
        if code.find_parent(["pre", "code"]) is None:  # outermost only
            code.replace_with(f" {code.get_text('')} ")
    base_url = lesson_files(lesson)["notes"]["url"]
    chunks: list[Chunk] = []
    for h2 in main.find_all("h2"):
        heading = h2.get_text(" ", strip=True)
        if heading.lower() in ("summing up", "congratulations!", "this was cs50!"):
            continue  # recap/outro sections repeat content or contain none
        parts = []
        for sib in h2.find_next_siblings():
            if sib.name in ("h1", "h2"):
                break
            parts.append(sib.get_text(" ", strip=True))
        body = " ".join(" ".join(parts).split())
        if not body:
            continue
        for k, piece in enumerate(_split_words(body, NOTES_MAX_WORDS)):
            chunks.append(Chunk(
                id=f"{lesson['id']}:notes:{len(chunks):04d}", lesson_id=lesson["id"],
                course_id=course["id"], source="notes",
                title=f"{lesson['title']} notes: {heading}" + (f" (part {k + 1})" if k else ""),
                text=f"{heading}. {piece}", url=f"{base_url}#{h2.get('id', '')}",
                license=course["license"], section=heading))
    return chunks


# --------------------------------------------------------------------- slides ----
_SLIDE_FOOTER = re.compile(r"6\.0001 LECTURE \d+")


def course_vocabulary() -> set[str]:
    """Lower-case words from clean course text (Whisper transcripts + HTML notes).
    Used as evidence when repairing broken PDF text (see text_clean.fix_ti_glyph)."""
    from ilm import config
    from ilm.content.download import all_lessons
    words: set[str] = set()
    for p in (config.PROCESSED_DIR / "transcripts").glob("*.json"):
        if ".first" in p.name:
            continue  # partial benchmark runs
        for s in json.loads(p.read_text(encoding="utf-8"))["segments"]:
            words.update(re.findall(r"[a-z]+", s["text"].lower()))
    for lesson in all_lessons():
        notes = lesson_path(lesson, "notes")
        if notes.suffix == ".html" and notes.exists():
            text = BeautifulSoup(notes.read_text(encoding="utf-8"), "html.parser").get_text()
            words.update(re.findall(r"[a-z]+", text.lower()))
    return words


def slide_chunks(lesson: dict, vocab: set[str] | None = None) -> list[Chunk]:
    """Text-rich pages become their own chunk; sparse pages (CS50P slides are mostly a
    single keyword) are merged into one 'slide outline' chunk so they can't win a search
    on a bare keyword. `vocab` enables the evidence-checked "ti" repair."""
    path = lesson_path(lesson, "slides")
    if not path.exists():
        return []
    if vocab is None:
        vocab = course_vocabulary()
    course = lesson["course"]
    url = lesson_files(lesson)["slides"]["url"]
    chunks: list[Chunk] = []
    sparse: list[str] = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = clean_pdf_text(_SLIDE_FOOTER.sub(" ", page.get_text()), vocab)
            text = re.sub(r"\s\d{1,3}$", "", text)  # trailing page number
            if len(text.split()) >= SLIDE_MIN_WORDS:
                chunks.append(Chunk(
                    id=f"{lesson['id']}:slides:{len(chunks):04d}", lesson_id=lesson["id"],
                    course_id=course["id"], source="slides",
                    title=f"{lesson['title']} slides p.{i}", text=text,
                    url=f"{url}#page={i}", license=course["license"], page=i))
            elif text and text not in sparse:
                sparse.append(text)
    if sparse:
        chunks.append(Chunk(
            id=f"{lesson['id']}:slides:outline", lesson_id=lesson["id"], course_id=course["id"],
            source="slides", title=f"{lesson['title']} slide outline",
            text=f"{lesson['title']} slide outline: " + "; ".join(sparse),
            url=url, license=course["license"]))
    return chunks


def lesson_chunks(lesson: dict, vocab: set[str] | None = None) -> dict[str, list[Chunk]]:
    return {"transcript": transcript_chunks(lesson), "notes": notes_chunks(lesson),
            "slides": slide_chunks(lesson, vocab)}
