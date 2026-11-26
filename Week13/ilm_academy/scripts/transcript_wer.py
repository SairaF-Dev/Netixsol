"""Word error rate of every Whisper transcript against the lecture's official subtitles.

WER = (substituted + deleted + inserted words) / words in the reference.
The official subtitles are edited: they drop filler words ("um", "uh"). Whisper often keeps
them, which counts as an error although nothing is wrong. So WER is reported twice:
as is, and with filler words removed from both sides.

Run:  python scripts/transcript_wer.py   -> reports/transcription_wer.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jiwer  # noqa: E402

from ilm import config  # noqa: E402
from ilm.content.download import all_lessons, lesson_path  # noqa: E402
from ilm.content.srt import normalise, parse_srt  # noqa: E402
from ilm.content.transcribe import transcript_path  # noqa: E402

FILLERS = {"um", "uh", "uhm", "erm", "hmm", "mm", "ah", "oh"}


def drop_fillers(text: str) -> str:
    return " ".join(w for w in text.split() if w not in FILLERS)


def score(ref: str, hyp: str) -> dict:
    o = jiwer.process_words(ref, hyp)
    n = len(ref.split())
    return {"wer": round(o.wer, 4), "substitutions": o.substitutions, "deletions": o.deletions,
            "insertions": o.insertions, "ref_words": n}


def main() -> None:
    rows = []
    for lesson in all_lessons():
        tp, sp = transcript_path(lesson["id"]), lesson_path(lesson, "subtitles")
        if not (tp.exists() and sp.exists()):
            print("skip", lesson["id"])
            continue
        hyp = normalise(" ".join(s["text"] for s in json.loads(tp.read_text(encoding="utf-8"))["segments"]))
        ref = normalise(" ".join(c.text for c in parse_srt(sp)))
        as_is, clean = score(ref, hyp), score(drop_fillers(ref), drop_fillers(hyp))
        fillers_in_hyp = sum(w in FILLERS for w in hyp.split())
        rows.append({"lesson": lesson["id"], **as_is, "wer_without_fillers": clean["wer"],
                     "filler_words_whisper_kept": fillers_in_hyp})
        print(f"{lesson['id']:12s} WER {as_is['wer']:.3f}  without fillers {clean['wer']:.3f}  "
              f"({as_is['ref_words']:,} words, {fillers_in_hyp} fillers)", flush=True)

    total = sum(r["ref_words"] for r in rows)
    errors = sum(r["substitutions"] + r["deletions"] + r["insertions"] for r in rows)
    summary = {"lessons": len(rows), "ref_words": total, "overall_wer": round(errors / total, 4),
               "overall_wer_without_fillers": round(
                   sum(r["wer_without_fillers"] * r["ref_words"] for r in rows) / total, 4),
               "per_lesson": rows}
    out = config.REPORTS_DIR / "transcription_wer.json"
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\noverall WER {summary['overall_wer']:.3f}, without fillers "
          f"{summary['overall_wer_without_fillers']:.3f} over {total:,} words -> {out}")


if __name__ == "__main__":
    main()
