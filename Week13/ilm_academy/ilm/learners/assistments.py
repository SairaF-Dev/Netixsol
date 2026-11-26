"""Load and clean ASSISTments 2009-2010 "skill builder" data (real students, maths).

Source: the copy hosted by the pyBKT project (github.com/CAHLR/pyBKT-examples, data/as.csv).
Dataset by the ASSISTments team (WPI), free for research use; cite:
  Feng, M., Heffernan, N.T., & Koedinger, K.R. (2009). Addressing the assessment challenge
  with an online system that tutors as it assesses. User Modeling and User-Adapted Interaction.

Known problems in this file (measured on our copy, 525,534 rows):
  - the same answer repeated under the same skill (124,072 extra rows): a documented bug
  - an answer to a multi-skill problem is copied once per skill
  - 66,326 rows have no skill id
  - rows are not in time order
These leak answers to knowledge-tracing models and inflate their scores (Xiong et al., 2016,
"Going Deeper with Deep Knowledge Tracing"). Cleaning rule: ONE ROW PER REAL ANSWER (order_id),
multi-skill problems get one combined skill, rows in time order. Every dropped row is counted.

Run:  python -m ilm.learners.assistments
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ilm import config

RAW_URL = "https://raw.githubusercontent.com/CAHLR/pyBKT-examples/master/data/as.csv"
RAW_PATH = config.RAW_DIR / "assistments" / "as.csv"
OUT_DIR = config.PROCESSED_DIR / "assistments"
MAX_RESPONSE_MS = 3_600_000  # an hour: longer means the tab was left open, not thinking time


def download() -> str:
    from ilm.content.download import download as fetch
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    return fetch(RAW_URL, RAW_PATH)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Raw rows -> one row per answer. Returns (clean table, report of every step)."""
    report = {"raw_rows": len(raw), "raw_users": int(raw["user_id"].nunique())}

    df = raw.dropna(subset=["skill_id"]).copy()
    report["dropped_no_skill"] = len(raw) - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=["order_id", "skill_id"])
    report["dropped_repeated_same_skill"] = before - len(df)

    df["skill_id"] = df["skill_id"].astype(int)
    df["skill_name"] = df["skill_name"].fillna("skill " + df["skill_id"].astype(str))
    skills = (df.sort_values("skill_id").groupby("order_id")
                .agg(skill=("skill_id", lambda s: "_".join(map(str, s))),
                     skill_name=("skill_name", lambda s: " + ".join(s)),
                     n_skills=("skill_id", "size")))
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"]).drop(columns=["skill_id", "skill_name"])
    df = df.join(skills, on="order_id")
    report["merged_multi_skill_copies"] = before - len(df)
    report["multi_skill_answers"] = int((df["n_skills"] > 1).sum())

    bad_time = (df["ms_first_response"] <= 0) | (df["ms_first_response"] > MAX_RESPONSE_MS)
    df["response_time_sec"] = np.where(bad_time, np.nan, df["ms_first_response"] / 1000).round(2)
    report["blanked_bad_response_times"] = int(bad_time.sum())

    df = df.sort_values(["user_id", "order_id"]).reset_index(drop=True)  # order_id = time order
    df["seq"] = df.groupby("user_id").cumcount() + 1
    df["is_scaffolding"] = (df["original"] == 0).astype(int)

    out = df[["user_id", "seq", "order_id", "problem_id", "skill", "skill_name", "n_skills",
              "correct", "attempt_count", "hint_count", "response_time_sec", "is_scaffolding",
              "assignment_id"]]
    report.update({"rows": len(out), "users": int(out["user_id"].nunique()),
                   "problems": int(out["problem_id"].nunique()), "skills": int(out["skill"].nunique()),
                   "accuracy": round(float(out["correct"].mean()), 3),
                   "answers_per_user_median": float(out.groupby("user_id").size().median()),
                   "users_with_under_5_answers": int((out.groupby("user_id").size() < 5).sum())})
    return out, report


def load_clean() -> pd.DataFrame:
    return pd.read_csv(OUT_DIR / "interactions.csv.gz")


def main() -> None:
    if not RAW_PATH.exists():
        print(download())
    raw = pd.read_csv(RAW_PATH, encoding="latin-1", low_memory=False)
    df, report = clean(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "interactions.csv.gz", index=False)
    (OUT_DIR / "cleaning_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
