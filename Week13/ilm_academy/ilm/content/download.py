"""Download course materials listed in sources.yaml into data/raw/<course>/<lesson>/.

Per lesson: audio (mp3), slides (pdf), official subtitles (srt), code (zip), notes (html).
We download the MP3, not the MP4: Whisper only needs the audio, and the MP3s are
~1.2 GB in total vs ~11 GB for 360p video. Video links use YouTube + timestamp.

Run:  python -m ilm.content.download            (all lessons)
      python -m ilm.content.download --lessons 0 5
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


def lesson_files(course: dict, n: int) -> dict[str, str]:
    """Map local filename -> remote URL for one lesson."""
    base = f"{course['cdn_base']}/{n}"
    return {
        f"lecture{n}.mp3": f"{base}/lecture{n}.mp3",
        f"lecture{n}.pdf": f"{base}/lecture{n}.pdf",
        f"lecture{n}.srt": f"{base}/lang/en/lecture{n}.srt",
        f"src{n}.zip": f"{base}/src{n}.zip",
        f"notes{n}.html": f"{course['homepage'].rstrip('/')}/notes/{n}/",
    }


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
    parser.add_argument("--lessons", type=int, nargs="*", help="lesson numbers (default: all)")
    args = parser.parse_args(argv)

    src = load_sources()
    course = src["course"]
    wanted = set(args.lessons) if args.lessons else None
    for lesson in src["lessons"]:
        if wanted is not None and lesson["n"] not in wanted:
            continue
        folder = config.RAW_DIR / course["id"] / lesson["id"]
        folder.mkdir(parents=True, exist_ok=True)
        for name, url in lesson_files(course, lesson["n"]).items():
            status = download(url, folder / name)
            size_mb = (folder / name).stat().st_size / 1e6
            print(f"{lesson['id']:10s} {name:16s} {status:10s} {size_mb:8.1f} MB", flush=True)


if __name__ == "__main__":
    main()
