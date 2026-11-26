"""Choose model settings on the VALIDATION students (never test).

Run:  python -m ilm.tracing.tune bkt     -> logs/bkt_tuning.log
      python -m ilm.tracing.tune deep    -> logs/deep_tuning.log

Run ONE tuning job at a time: running BKT and the deep models together made a 3-minute
DKT job take over an hour (CPU oversubscription, 2026-11-26).

Must be run as a module FILE, not piped in on stdin: pyBKT trains skills in parallel worker
processes, and on Windows every worker re-imports the main script. A script read from stdin
cannot be re-imported, so every worker crashed (found 2026-11-26). The
`if __name__ == "__main__":` guard below stops the workers from re-running the tuning.
"""
from __future__ import annotations

import argparse
import time

from ilm.learners.assistments import load_clean
from ilm.tracing.evaluate import load_splits, metrics


def tune_bkt(train, valid):
    from ilm.tracing.bkt import BKT
    for forgets in (False, True):
        t = time.time()
        m = BKT(forgets=forgets).fit(train)
        print(m.name, metrics(valid["correct"], m.predict(valid)), f"{time.time() - t:.0f}s", flush=True)


def tune_deep(train, valid):
    from ilm.tracing.deep import DeepKT
    for arch in ("dkt", "sakt"):
        for dim in (64, 128):
            t = time.time()
            m = DeepKT(arch, dim=dim, verbose=True).fit(train, valid)
            best = max(m.history, key=lambda h: h["valid_auc"])
            print(m.name, "best", best, "epochs run", len(m.history),
                  metrics(valid["correct"], m.predict(valid)), f"{time.time() - t:.0f}s", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("which", choices=["bkt", "deep"])
    a = p.parse_args()
    train, valid, _ = load_splits(load_clean())   # the test split is not even kept
    {"bkt": tune_bkt, "deep": tune_deep}[a.which](train, valid)


if __name__ == "__main__":
    main()
