"""Final knowledge-tracing comparison on the TEST students (ASSISTments 2009-10, cleaned).

Every setting below was chosen on the VALIDATION students (logs/*_tuning.log); the test
students are used here only, once per model. Models are retrained on train (not train+valid)
so the deep models' early stopping uses exactly the validation set they were tuned with.

Run:  python -m ilm.tracing.compare      -> reports/tracing/results.{json,md}
"""
from __future__ import annotations

import json
import time

from ilm import config
from ilm.learners.assistments import load_clean
from ilm.tracing.bkt import BKT
from ilm.tracing.deep import DeepKT
from ilm.tracing.evaluate import GlobalMean, SkillMean, StudentSoFar, load_splits, metrics
from ilm.tracing.pfa import PFA

# chosen on validation (see the tuning logs); never changed after looking at test
CHOSEN = {
    "student_so_far_m": 40,         # AUC flat at 40-80; tie broken by RMSE
    "pfa": {"C": 1.0, "transform": "log"},
    "bkt_forgets": None,            # filled in from logs/bkt_tuning.log
    # deep (logs/deep_tuning.log): DKT 64 -> 0.7505, 128 -> 0.7537 (stopped early at 12);
    # SAKT 64 -> 0.7312, 128 -> 0.7325. Both size-64 runs hit the 20-epoch cap while still
    # improving, but 128 was better AND converged, so 128 for both.
    "dkt_dim": 128,
    "sakt_dim": 128,
}


def models():
    return [GlobalMean(), SkillMean(), StudentSoFar(CHOSEN["student_so_far_m"]),
            PFA(**CHOSEN["pfa"]), BKT(forgets=CHOSEN["bkt_forgets"]),
            DeepKT("dkt", dim=CHOSEN["dkt_dim"]), DeepKT("sakt", dim=CHOSEN["sakt_dim"])]


def main() -> None:
    if None in CHOSEN.values():
        raise SystemExit("Finish tuning on validation first: some CHOSEN settings are empty.")
    train, valid, test = load_splits(load_clean())
    rows = []
    for m in models():
        t = time.time()
        m.fit(train, valid) if isinstance(m, DeepKT) else m.fit(train)
        rows.append({"model": m.name, **metrics(test["correct"], m.predict(test)),
                     "train_seconds": round(time.time() - t)})
        print(rows[-1], flush=True)

    out = config.REPORTS_DIR / "tracing"
    out.mkdir(parents=True, exist_ok=True)
    meta = {"data": "ASSISTments 2009-10 skill builder, cleaned (one row per real answer)",
            "split": "student-level: train/valid/test students = "
                     f"{train.user_id.nunique()}/{valid.user_id.nunique()}/{test.user_id.nunique()}",
            "test_answers": len(test), "chosen_on_validation": CHOSEN, "seed": config.RANDOM_SEED}
    (out / "results.json").write_text(json.dumps({"meta": meta, "results": rows}, indent=1), encoding="utf-8")
    lines = ["| model | AUC | accuracy | RMSE | train time (s) |", "|---|---|---|---|---|"]
    lines += [f"| {r['model']} | {r['auc']:.3f} | {r['accuracy']:.3f} | {r['rmse']:.3f} | {r['train_seconds']} |"
              for r in sorted(rows, key=lambda r: -r["auc"])]
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
