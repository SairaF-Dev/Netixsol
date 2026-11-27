"""Difficulty calibration: LLM-predicted vs IRT-measured (Day 3 Task 5).

    python -m ilm.questions.difficulty           predict (LLM), compare, write the retire/relabel list
    python -m ilm.questions.difficulty --report  reuse saved predictions

The LLM sees each bank question WITHOUT the author's 1-5 guess and predicts the share of
beginners who would answer it correctly (a number ranks finer than a 1-5 label). We then ask:
  - does it rank questions by difficulty as well as the IRT model fitted on answers does?
    (Spearman with IRT b; the author's guess gets 0.573, the baseline to beat)
  - IN THIS SIMULATION ONLY: how close do author, LLM and IRT each get to the simulator's
    hidden true difficulty?

CAVEAT, read before trusting any number here: the simulator builds each question's true
difficulty from the author's guess plus noise (ilm/learners/simulator.py). So "measured"
difficulty is partly the author's guess by construction, and agreement with it favours the
author. Only real students' answers can settle LLM vs author. The pipeline is what carries over.

Decisions per question (IRT, at least 50 answers):
  retire    discrimination a < 0.3 or negative: strong students do no better than weak ones,
            so the question says nothing about knowledge (Day 2 found 12/12 planted bad ones)
  relabel   the author label is 2+ levels from the measured level (b cut into 5 equal-count bands)
  keep      otherwise; never-asked questions stay "unmeasured"
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import yaml
import pandas as pd
from scipy.stats import spearmanr

from ilm import config
from ilm.questions.validate import load_bank

MODEL = os.getenv("DIFFICULTY_MODEL", "gemini-3.5-flash-lite")
OUT = config.PROJECT_ROOT / "reports" / "difficulty"
PREDICTIONS = OUT / "llm_predictions.json"
IRT = config.PROJECT_ROOT / "reports" / "irt" / "question_params_2pl.csv"
BATCH = 25
WEAK_A = 0.3
MIN_N = 50

PROMPT = """You are an experienced teacher of a beginner Python course (CS50P style). For each
question below, estimate what percentage of beginner students answer it correctly when they
meet it right after the lesson on its concept. Judge the question itself (how many steps, how
tricky the distractors, how easy the mistake). Reply JSON
{{"predictions": [{{"id": "...", "p_correct": 0-100, "why": "few words"}}, ...]}}

{items}"""


def describe(q) -> str:
    s = f"[{q.id}] ({q.type}; concept {q.concepts[0]}) {q.stem}"
    if q.code:
        s += f"\n```python\n{q.code}```"
    if q.type == "mcq":
        s += "\n" + "\n".join(f"  {chr(65 + i)}. {o}" for i, o in enumerate(q.options))
    return s


def predict(bank, ask, done: dict, save=None) -> dict:
    todo = [q for q in bank if q.id not in done]
    out = dict(done)
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        raw = ask(PROMPT.format(items="\n\n".join(describe(q) for q in batch)), temperature=0,
                  model=MODEL, max_tokens=8192, json_mode=True)
        try:
            rows = json.loads(raw).get("predictions", [])
        except (json.JSONDecodeError, AttributeError):
            rows = []
        for r in rows:
            if r.get("id") in {q.id for q in batch}:
                try:
                    out[r["id"]] = {"p_correct": float(r["p_correct"]), "why": str(r.get("why", ""))}
                except (TypeError, ValueError, KeyError):
                    pass
        (save or PREDICTIONS).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"predicted {len(out)}/{len(bank)}", flush=True)
    return out


def bands(x: pd.Series, n: int = 5) -> pd.Series:
    """Cut into n equal-count bands, 1 = easiest ... n = hardest (x = difficulty, high = hard)."""
    return pd.qcut(x.rank(method="first"), n, labels=list(range(1, n + 1))).astype(int)


def table(bank, preds: dict, irt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q in bank:
        p = preds.get(q.id, {})
        rows.append({"id": q.id, "type": q.type, "concept": q.concepts[0], "author": q.difficulty,
                     "llm_p_correct": p.get("p_correct"), "llm_why": p.get("why", "")})
    t = pd.DataFrame(rows).set_index("id")
    t = t.join(irt[["b", "a", "n", "p_correct", "truth_b", "truth_bad"]].rename(columns={"p_correct": "observed_p"}))
    t["llm_hardness"] = 100 - t["llm_p_correct"]                    # high = hard, like b
    return t


def decide(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    measured = t["b"].notna() & (t["n"] >= MIN_N)
    t["measured_level"] = np.nan
    t.loc[measured, "measured_level"] = bands(t.loc[measured, "b"])
    t["decision"], t["reason"] = "unmeasured", "never asked often enough to measure"
    m = measured
    t.loc[m, ["decision", "reason"]] = ["keep", ""]
    off = m & ((t["author"] - t["measured_level"]).abs() >= 2)
    t.loc[off, "decision"] = "relabel"
    t.loc[off, "reason"] = ("author says " + t.loc[off, "author"].astype(int).astype(str)
                            + ", students' answers say " + t.loc[off, "measured_level"].astype(int).astype(str))
    weak = m & (t["a"] < WEAK_A)
    t.loc[weak, "decision"] = "retire"
    t.loc[weak, "reason"] = np.where(t.loc[weak, "a"] < 0, "negative discrimination: strong students do WORSE",
                                     "weak discrimination: strong and weak students do about the same")
    return t


def rho(x, y) -> float | None:
    ok = x.notna() & y.notna()
    return round(float(spearmanr(x[ok], y[ok]).statistic), 3) if ok.sum() > 2 else None


def compare(t: pd.DataFrame) -> dict:
    m = t[t["b"].notna() & (t["n"] >= MIN_N) & ~t["truth_bad"].fillna(False).astype(bool)]
    out = {
        "questions_compared": int(len(m)),
        "llm_predicted": int(t["llm_p_correct"].notna().sum()),
        "spearman_with_irt_b": {"author": rho(m["author"], m["b"]), "llm": rho(m["llm_hardness"], m["b"]),
                                "llm_plus_author_rank_mean": rho(m["llm_hardness"].rank() + m["author"].rank(), m["b"])},
        "simulation_only_spearman_with_true_b": {"author": rho(m["author"], m["truth_b"]),
                                                 "llm": rho(m["llm_hardness"], m["truth_b"]),
                                                 "irt": rho(m["b"], m["truth_b"])},
        "llm_vs_author": rho(m["llm_hardness"], m["author"]),
        "llm_p_correct_vs_observed_p": rho(m["llm_p_correct"], m["observed_p"]),
        "mean_llm_p_correct": round(float(m["llm_p_correct"].mean()), 1) if m["llm_p_correct"].notna().any() else None,
        "mean_observed_p": round(float(m["observed_p"].mean() * 100), 1),
        "by_type_spearman_llm": {ty: rho(g["llm_hardness"], g["b"]) for ty, g in m.groupby("type")},
        "by_type_spearman_author": {ty: rho(g["author"], g["b"]) for ty, g in m.groupby("type")},
    }
    d = t["decision"].value_counts().to_dict()
    planted = t["truth_bad"].fillna(False).astype(bool)
    out["decisions"] = {k: int(v) for k, v in d.items()}
    out["retired_that_were_planted_bad"] = int((planted & (t["decision"] == "retire")).sum())
    out["planted_bad_measured"] = int((planted & (t["decision"] != "unmeasured")).sum())
    return out


def to_markdown(s: dict, t: pd.DataFrame) -> str:
    sw, st = s["spearman_with_irt_b"], s["simulation_only_spearman_with_true_b"]
    L = ["# Difficulty calibration: LLM vs IRT", "",
         f"`{MODEL}` predicted the share of beginners answering correctly for {s['llm_predicted']} bank questions "
         f"(without seeing the author's label). Compared on {s['questions_compared']} questions with 50+ "
         "simulated answers (planted bad questions left out).", "",
         "| difficulty source | Spearman with IRT b (measured) | simulation only: with the hidden true b |",
         "|---|---|---|",
         f"| author's 1-5 guess | {sw['author']} | {st['author']} |",
         f"| LLM prediction | {sw['llm']} | {st['llm']} |",
         f"| LLM + author (mean rank) | {sw['llm_plus_author_rank_mean']} | |",
         f"| IRT itself | 1 | {st['irt']} |", "",
         f"LLM vs author: {s['llm_vs_author']}. Mean predicted correct {s['mean_llm_p_correct']}% vs "
         f"observed {s['mean_observed_p']}%.", "",
         "By type (Spearman with IRT b): " + ", ".join(
             f"{k} LLM {v} / author {s['by_type_spearman_author'].get(k)}" for k, v in s["by_type_spearman_llm"].items()), "",
         "**Caveat.** The simulator makes true difficulty = the author's guess + noise, so these numbers "
         "favour the author by construction. They show the pipeline works; only real students can say "
         "whether the LLM or the author judges difficulty better.", "",
         "## Decisions", "", "| decision | questions |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in s["decisions"].items()]
    L += ["", f"Retired questions that were planted bad: {s['retired_that_were_planted_bad']} of "
          f"{s['planted_bad_measured']} planted bad that were measured.", "",
          "## Retire", "", "| question | a | b | reason |", "|---|---|---|---|"]
    for qid, r in t[t["decision"] == "retire"].sort_values("a").iterrows():
        L.append(f"| {qid} | {r['a']:.2f} | {r['b']:.2f} | {r['reason']} |")
    L += ["", "## Relabel (author's level is 2+ away from the measured level)", "",
          "| question | author | measured | LLM % correct | LLM's reason |", "|---|---|---|---|---|"]
    for qid, r in t[t["decision"] == "relabel"].iterrows():
        llm = "" if pd.isna(r["llm_p_correct"]) else f"{r['llm_p_correct']:.0f}"
        L.append(f"| {qid} | {int(r['author'])} | {int(r['measured_level'])} | {llm} | {r['llm_why']} |")
    return "\n".join(L) + "\n"


def generated_difficulty(runs: list[str], ask=None) -> dict:
    """The same predictor on generated question sets: an independent look at how hard they
    really are (the generator's own 1-5 label is a claim, not a measurement)."""
    from pydantic import TypeAdapter

    from ilm.questions.generate import GENERATED_DIR
    from ilm.questions.schema import Question
    adapter, out = TypeAdapter(Question), {}
    bank, _ = load_bank()
    bank_preds = json.loads(PREDICTIONS.read_text(encoding="utf-8")) if PREDICTIONS.exists() else {}
    sets = {"bank": [(q, bank_preds.get(q.id)) for q in bank]}
    for run in runs:
        raw = yaml.safe_load((GENERATED_DIR / f"{run}.yaml").read_text(encoding="utf-8"))["questions"]
        qs = [adapter.validate_python(d) for d in raw]
        save = OUT / f"llm_predictions_generated_{run}.json"
        preds = json.loads(save.read_text(encoding="utf-8")) if save.exists() else {}
        if ask is not None:
            preds = predict(qs, ask, preds, save=save)
        sets[run] = [(q, preds.get(q.id)) for q in qs]
    for name, rows in sets.items():
        got = [(q, p["p_correct"]) for q, p in rows if p]
        by_label = {d: round(float(np.mean([pc for q, pc in got if q.difficulty == d])), 1)
                    for d in range(1, 6) if any(q.difficulty == d for q, _ in got)}
        out[name] = {"questions": len(rows), "predicted": len(got),
                     "mean_predicted_p_correct": round(float(np.mean([pc for _, pc in got])), 1) if got else None,
                     "share_predicted_hard (p_correct < 50)": round(float(np.mean([pc < 50 for _, pc in got])), 2) if got else None,
                     "mean_predicted_p_correct_by_own_label": by_label,
                     "label_vs_prediction_spearman": rho(pd.Series([q.difficulty for q, _ in got], dtype=float),
                                                         pd.Series([100 - pc for _, pc in got], dtype=float)) if got else None}
    (OUT / "generated_sets.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="no LLM calls; reuse saved predictions")
    ap.add_argument("--generated", nargs="*", help="also rate these generated sets (e.g. v1 v2)")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.generated:
        from ilm import llm
        print(json.dumps(generated_difficulty(args.generated, None if args.report else llm.ask), indent=1))
        return
    bank, _ = load_bank()
    preds = json.loads(PREDICTIONS.read_text(encoding="utf-8")) if PREDICTIONS.exists() else {}
    if not args.report:
        from ilm import llm
        preds = predict(bank, llm.ask, preds)
    t = decide(table(bank, preds, pd.read_csv(IRT, index_col=0)))
    s = compare(t)
    t.to_csv(OUT / "questions.csv")
    (OUT / "report.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    (OUT / "report.md").write_text(to_markdown(s, t), encoding="utf-8")
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
