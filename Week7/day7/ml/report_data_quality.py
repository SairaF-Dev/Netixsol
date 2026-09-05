"""Print separate real and synthetic data-quality summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.build_dataset import fetch_interaction_rows
from ml.readiness import summarize_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", type=Path)
    args = parser.parse_args()
    print("REAL DATA:", json.dumps(summarize_rows(fetch_interaction_rows()), sort_keys=True))
    if args.synthetic:
        rows = json.loads(args.synthetic.read_text(encoding="utf-8"))
        print("SYNTHETIC DEV DATA:", json.dumps(summarize_rows(rows, synthetic=True), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())