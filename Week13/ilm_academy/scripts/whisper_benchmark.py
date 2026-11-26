"""Measure Whisper speed and accuracy on our CPU against CS50's official subtitles.

Decides, with numbers, which model size we use and whether Colab is worth it.
Output: reports/whisper_benchmark.json

Run:  python scripts/whisper_benchmark.py --lesson 5 --minutes 5 --models tiny base small
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jiwer

from ilm import config
from ilm.content.srt import normalise, parse_srt, text_between
from ilm.content.transcribe import load_model, transcribe_audio


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lesson", type=int, default=5)
    p.add_argument("--minutes", type=float, default=5)
    p.add_argument("--models", nargs="+", default=["tiny", "base", "small"])
    a = p.parse_args()

    folder = config.RAW_DIR / "cs50p" / f"cs50p-l{a.lesson}"
    cues = parse_srt(folder / f"lecture{a.lesson}.srt")
    results = []
    for size in a.models:
        model = load_model(size)
        segs, stats = transcribe_audio(model, folder / f"lecture{a.lesson}.mp3", a.minutes)
        # Compare over the time window Whisper actually covered (up to its last segment end),
        # so a cue cut off at the edge doesn't count as a "missed" word.
        window_end = segs[-1].end if segs else 0
        ref = normalise(text_between(cues, 0, window_end))
        hyp = normalise(" ".join(s.text for s in segs))
        wer = jiwer.wer(ref, hyp)
        row = {"model": size, **stats, "wer": round(wer, 4), "ref_words": len(ref.split()),
               "hyp_words": len(hyp.split())}
        results.append(row)
        print(json.dumps(row), flush=True)

    out = config.REPORTS_DIR / "whisper_benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"lesson": a.lesson, "minutes": a.minutes,
                               "reference": "official CS50P English .srt",
                               "results": results}, indent=1), encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
