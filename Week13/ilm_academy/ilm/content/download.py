"""Download course materials listed in sources.yaml into data/raw/<course>/<lesson>/.

Per lesson: audio, slides (pdf), official subtitles (srt), code, notes.
For CS50P we download the MP3, not the MP4: Whisper only needs the audio, and the MP3s
are ~1.2 GB in total vs ~11 GB for 360p video. MIT only publishes MP4 (audio is decoded
from it). Video links in the tutor use YouTube + timestamp.

Run:  python -m ilm.content.download            (all lessons)
      python -m ilm.content.download --lessons cs50p-l5 mit6001-l6
      python -m ilm.content.download --roles slides notes   (what the search index needs; no audio/video)
"""
from __future__ import annotations

import argparse
import shutil
import urllib.request
from pathlib import Path

import yaml

from ilm import config

SOURCES = Path(__file__).with_name("sources.yaml")
USER_AGENT = "ilm-academy-course-ingest/0.1 (educational, non-commercial)"


def load_sources() -> dict:
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))


def all_lessons(sources: dict | None = None) -> list[dict]:
    """Every lesson across all courses, in course order, with its course and an
    `order` index attached (`order` is unique; `n` repeats across courses)."""
    sources = sources or load_sources()
    out = []
    for course in sources["courses"]:
        for lesson in course["lessons"]:
            out.append({**lesson, "course": course, "order": len(out)})
    return out


def lesson_dir(lesson: dict) -> Path:
    return config.RAW_DIR / lesson["course"]["id"] / lesson["id"]


def lesson_files(lesson: dict) -> dict[str, dict]:
    """Role (audio/slides/subtitles/code/notes) -> {name, url} for one lesson."""
    course = lesson["course"]
    if course.get("url_pattern") == "cs50p":
        n, base = lesson["n"], f"{course['cdn_base']}/{lesson['n']}"
        return {
            "audio": {"name": f"lecture{n}.mp3", "url": f"{base}/lecture{n}.mp3"},
            "slides": {"name": f"lecture{n}.pdf", "url": f"{base}/lecture{n}.pdf"},
            "subtitles": {"name": f"lecture{n}.srt", "url": f"{base}/lang/en/lecture{n}.srt"},
            "code": {"name": f"src{n}.zip", "url": f"{base}/src{n}.zip"},
            "notes": {"name": f"notes{n}.html",
                      "url": f"{course['homepage'].rstrip('/')}/notes/{n}/"},
        }
    return lesson["files"]


def lesson_path(lesson: dict, role: str) -> Path:
    """Local path of one downloaded file, e.g. lesson_path(lesson, "audio")."""
    return lesson_dir(lesson) / lesson_files(lesson)[role]["name"]


def remote_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        size = resp.headers.get("Content-Length")
        return int(size) if size else None


def download(url: str, dest: Path) -> str:
    """Download url to dest. Returns 'skipped' or 'downloaded'.

    Skips when dest exists with the same size as the server reports (resume-friendly).
    Writes to dest.part first, then renames: an interrupted download never looks complete.
    """
    expected = remote_size(url)
    if dest.exists() and (expected is None or dest.stat().st_size == expected):
        return "skipped"
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp, open(part, "wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)
    if expected is not None and part.stat().st_size != expected:
        raise IOError(f"size mismatch for {url}: got {part.stat().st_size}, expected {expected}")
    part.replace(dest)
    return "downloaded"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lessons", nargs="*", help="lesson ids, e.g. cs50p-l5 mit6001-l6 (default: all)")
    parser.add_argument("--roles", nargs="*", help="only these files, e.g. slides notes (default: all)")
    args = parser.parse_args(argv)

    for lesson in all_lessons():
        if args.lessons and lesson["id"] not in args.lessons:
            continue
        folder = lesson_dir(lesson)
        folder.mkdir(parents=True, exist_ok=True)
        for role, f in lesson_files(lesson).items():
            if args.roles and role not in args.roles:
                continue
            status = download(f["url"], folder / f["name"])
            size_mb = (folder / f["name"]).stat().st_size / 1e6
            print(f"{lesson['id']:11s} {role:9s} {f['name']:32s} {status:10s} {size_mb:8.1f} MB", flush=True)


if __name__ == "__main__":
    main()
