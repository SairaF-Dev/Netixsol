"""Text cleaning and chunking: each test pins a real bug found on 2026-11-26."""
from __future__ import annotations

import json

from ilm.content import chunking
from ilm.content.download import all_lessons
from ilm.content.text_clean import clean_pdf_text, fix_ti_glyph

MIT6 = next(l for l in all_lessons() if l["id"] == "mit6001-l6")
CS50P5 = next(l for l in all_lessons() if l["id"] == "cs50p-l5")


def test_ligature_fi_becomes_two_letters():
    assert clean_pdf_text("deﬁne inﬁnite") == "define infinite"


VOCAB = {"function", "iterative", "semantically", "dictionary", "computation", "solve"}


def test_broken_ti_glyph_is_repaired_when_the_word_is_known():
    assert fix_ti_glyph("funcSon func0on itera0ve SemanScally dicSonary", VOCAB) == \
        "function function iterative Semantically dictionary"


def test_ti_repair_accepts_plurals_of_known_words():
    assert fix_ti_glyph("computaSons", VOCAB) == "computations"


def test_ti_repair_leaves_camelcase_code_names_alone():
    # Found by review on 2026-11-26: the first rule turned isSorted into "istiorted".
    names = "isSorted numSteps maxSize getSum hasSon item0a"
    assert fix_ti_glyph(names, VOCAB) == names


def test_ti_repair_leaves_unknown_words_alone():
    assert fix_ti_glyph("gestaSon", VOCAB) == "gestaSon"  # unknown: better unfixed than wrong


def test_ti_repair_does_not_touch_real_words_starting_with_s():
    assert fix_ti_glyph("Solve Some Same Stack Science Sylvan", VOCAB) == \
        "Solve Some Same Stack Science Sylvan"
    assert fix_ti_glyph("many Smes", VOCAB) == "many times"


def test_clean_pdf_text_without_vocab_does_not_guess():
    assert clean_pdf_text("funcSon isSorted") == "funcSon isSorted"


def _fake_transcript(monkeypatch, tmp_path, segments):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"segments": segments}), encoding="utf-8")
    monkeypatch.setattr(chunking, "transcript_path", lambda _id: path)


def test_transcript_chunks_respect_time_limit_overlap_and_link(monkeypatch, tmp_path):
    # 20 segments of 10 s each = 200 s of speech
    segs = [{"start": i * 10.0, "end": i * 10.0 + 10, "text": f"word{i} " * 5} for i in range(20)]
    _fake_transcript(monkeypatch, tmp_path, segs)
    chunks = chunking.transcript_chunks(MIT6)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.end_sec - c.start_sec <= chunking.MAX_SECONDS + 10  # one segment of slack
        assert c.url == f"https://youtu.be/WPSeyjX1-4s?t={int(c.start_sec)}"
    # overlap: each chunk starts with the segment that ended the previous one
    for a, b in zip(chunks, chunks[1:]):
        assert b.start_sec == a.end_sec - 10
    assert chunks[-1].end_sec == 200  # nothing lost at the end


def test_missing_transcript_gives_no_chunks_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(chunking, "transcript_path", lambda _id: tmp_path / "nope.json")
    assert chunking.transcript_chunks(MIT6) == []


def test_split_words_keeps_all_text():
    text = " ".join(f"Sentence number {i} is here." for i in range(100))
    parts = chunking._split_words(text, 50)
    assert len(parts) > 1 and " ".join(parts) == text


def test_metadata_has_no_none_values():
    c = chunking.Chunk(id="x", lesson_id="l", course_id="c", source="notes", title="t",
                       text="hello", url="u", license="CC", section="s")
    meta = c.metadata()
    assert None not in meta.values() and "text" not in meta and meta["section"] == "s"


# These use the downloaded course files (data/raw); skipped on a fresh clone.
def _have(lesson, role):
    from ilm.content.download import lesson_path
    from ilm import config
    real = lesson_path(lesson, role)
    # tests run with a temp DATA_DIR, so look in the project's real data folder (read-only)
    return config.PROJECT_ROOT / "data" / real.relative_to(config.DATA_DIR)


def test_notes_code_is_extracted_without_token_spaces(monkeypatch):
    import pytest
    real = _have(CS50P5, "notes")
    if not real.exists():
        pytest.skip("course files not downloaded")
    monkeypatch.setattr(chunking, "lesson_path", lambda lesson, role: real)
    text = " ".join(c.text for c in chunking.notes_chunks(CS50P5))
    assert "square(2) == 4" in text and 'if __name__ == "__main__":' in text
    assert "square ( 2 )" not in text and "_ _name_ _" not in text


def test_mit_slides_are_clean_and_linked_to_pages(monkeypatch):
    import pytest
    real = _have(MIT6, "slides")
    if not real.exists():
        pytest.skip("course files not downloaded")
    monkeypatch.setattr(chunking, "lesson_path", lambda lesson, role: real)
    chunks = chunking.slide_chunks(MIT6, vocab={"function", "dictionary", "iteration"})
    text = " ".join(c.text for c in chunks)
    assert "function" in text and "funcSon" not in text and "func0on" not in text
    assert all("#page=" in c.url for c in chunks if c.page)
