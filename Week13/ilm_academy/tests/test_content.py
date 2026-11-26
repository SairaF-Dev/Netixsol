"""Fast unit tests for content ingestion helpers (no network, no models)."""
from __future__ import annotations

from ilm.content.download import lesson_files, load_sources
from ilm.content.srt import normalise, parse_srt, text_between

SRT = """1
00:00:00,000 --> 00:00:03,444
[GENTLE ORCHESTRAL MUSIC PLAYING]

2
00:00:24,110 --> 00:00:26,840
DAVID MALAN: All right,
this is CS50's Introduction

3
01:45:36,590 --> 01:45:38,000
Let's write def main().
"""


def test_parse_srt_reads_times_and_multiline_text(tmp_path):
    p = tmp_path / "x.srt"
    p.write_text(SRT, encoding="utf-8")
    cues = parse_srt(p)
    assert len(cues) == 3
    assert cues[1].start == 24.11 and cues[1].end == 26.84
    assert cues[1].text == "DAVID MALAN: All right, this is CS50's Introduction"
    assert cues[2].start == 1 * 3600 + 45 * 60 + 36.59  # hours are parsed, not dropped


def test_parse_srt_handles_windows_line_endings_and_bom(tmp_path):
    p = tmp_path / "x.srt"
    p.write_bytes(("﻿" + SRT).replace("\n", "\r\n").encode("utf-8"))
    assert len(parse_srt(p)) == 3


def test_normalise_removes_tags_speaker_labels_and_punctuation():
    assert normalise("[MUSIC PLAYING] DAVID MALAN: All right, CS50's def main().") == \
        "all right cs50s def main"


def test_text_between_uses_cue_start_time(tmp_path):
    p = tmp_path / "x.srt"
    p.write_text(SRT, encoding="utf-8")
    cues = parse_srt(p)
    assert "Introduction" in text_between(cues, 20, 30)
    assert "def main" not in text_between(cues, 20, 30)


def test_every_lesson_has_licence_youtube_id_and_five_files():
    src = load_sources()
    assert src["course"]["license"] == "CC BY-NC-SA 4.0"
    assert [l["n"] for l in src["lessons"]] == list(range(10))
    for lesson in src["lessons"]:
        assert len(lesson["youtube"]) == 11  # YouTube ids are 11 chars
        files = lesson_files(src["course"], lesson["n"])
        assert set(files) == {f"lecture{lesson['n']}.mp3", f"lecture{lesson['n']}.pdf",
                              f"lecture{lesson['n']}.srt", f"src{lesson['n']}.zip",
                              f"notes{lesson['n']}.html"}
