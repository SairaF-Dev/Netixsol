"""Transcribe lesson audio with faster-whisper, keeping segment timestamps.

Timestamps are the whole point: on Day 3 the tutor links a student to
"Lecture 5 at 12:34", which only works if every chunk remembers where it came from.

Run:  python -m ilm.content.transcribe --lessons 5            (full lessons)
      python -m ilm.content.transcribe --lessons 5 --minutes 5 (first 5 min, for timing)
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ilm import config
from ilm.content.download import load_sources

SAMPLE_RATE = 16_000  # Whisper works on 16 kHz mono audio


@dataclass
class Segment:
    start: float
    end: float
    text: str
    avg_logprob: float     # model confidence; very low = likely garbled
    no_speech_prob: float  # high = probably music/silence


def load_model(size: str | None = None):
    from faster_whisper import WhisperModel  # imported lazily: slow import, big model
    size = size or config.WHISPER_MODEL
    model = WhisperModel(size, device=config.WHISPER_DEVICE,
                         compute_type=config.WHISPER_COMPUTE_TYPE)
    # WhisperModel does not remember which size it was built from, so we record it
    # ourselves; reports must name the model that really ran.
    model.ilm_model_name = size
    return model


def transcribe_audio(model, audio_path: Path, minutes: float | None = None) -> tuple[list[Segment], dict]:
    """Return segments and run stats. `minutes` limits to the first N minutes."""
    from faster_whisper import decode_audio

    audio = decode_audio(str(audio_path), sampling_rate=SAMPLE_RATE)
    if minutes is not None:
        audio = audio[: int(minutes * 60 * SAMPLE_RATE)]
    audio_sec = len(audio) / SAMPLE_RATE

    t0 = time.time()
    segments, info = model.transcribe(
        audio,
        language="en",
        vad_filter=True,               # skip music/silence instead of hallucinating text
        beam_size=5,
        condition_on_previous_text=False,  # avoids long repetition loops on long audio
    )
    out = [Segment(round(s.start, 2), round(s.end, 2), s.text.strip(),
                   round(s.avg_logprob, 3), round(s.no_speech_prob, 3)) for s in segments]
    elapsed = time.time() - t0  # segments is a generator: the work happens in the loop above
    stats = {"audio_sec": round(audio_sec, 1), "elapsed_sec": round(elapsed, 1),
             "speed_x_realtime": round(audio_sec / elapsed, 2) if elapsed else None,
             "model": model.ilm_model_name, "compute_type": config.WHISPER_COMPUTE_TYPE}
    return out, stats


def transcript_path(lesson_id: str) -> Path:
    return config.PROCESSED_DIR / "transcripts" / f"{lesson_id}.json"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lessons", type=int, nargs="*")
    parser.add_argument("--minutes", type=float, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--force", action="store_true", help="re-transcribe even if output exists")
    args = parser.parse_args(argv)

    src = load_sources()
    course = src["course"]
    model = load_model(args.model)
    for lesson in src["lessons"]:
        if args.lessons and lesson["n"] not in args.lessons:
            continue
        out_path = transcript_path(lesson["id"])
        if out_path.exists() and not args.force and args.minutes is None:
            print(f"{lesson['id']}: exists, skipping (use --force)")
            continue
        audio = config.RAW_DIR / course["id"] / lesson["id"] / f"lecture{lesson['n']}.mp3"
        segments, stats = transcribe_audio(model, audio, args.minutes)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if args.minutes is not None:  # partial runs never overwrite a full transcript
            out_path = out_path.with_name(f"{lesson['id']}.first{args.minutes:g}min.json")
        out_path.write_text(json.dumps({
            "lesson_id": lesson["id"], "title": lesson["title"], "youtube": lesson.get("youtube"),
            "license": course["license"], "stats": stats,
            "segments": [asdict(s) for s in segments],
        }, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{lesson['id']}: {len(segments)} segments, {stats} -> {out_path.name}", flush=True)


if __name__ == "__main__":
    main()
