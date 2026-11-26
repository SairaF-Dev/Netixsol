"""Dropout early warning: at the end of each week, which active students will not come back?

Setup (simulated students: the real ASSISTments log cannot show dropout, see Day 1 notes):
  checkpoint   end of week w (1-7), every student still active (not dropped, not finished)
  features     ONLY answers up to the end of week w (public data: no truth_* columns)
  label        1 if the student quits right after week w (simulator: dropped_week == w)
  students     train / valid = the seed-42 history split by student; test = a FRESH cohort
               (seed 2027) on the same fixed course, scored once
  models       baseline: logistic regression on 3 obvious signals; LightGBM, settings chosen
               on validation (early stopping on validation log loss)
  metric       PR-AUC (average precision): dropouts are the minority at each checkpoint, and
               the question is "of the students we flag, how many really leave?"
  explanation  SHAP (TreeExplainer): how much each feature pushed THIS student's risk up/down
  actions      risk levels by capacity, cut-offs set on validation: high = top 10% (a mentor
               can call that many), medium = next 20% (an automatic nudge), low = the rest;
               plus a reason-specific action from the student's biggest SHAP push

Ceiling: the simulator's own rule scored on the test cohort shows the best PR-AUC any model
could reach (ceiling(); with and without the hidden motivation).

Caveat: the simulator's dropout rule (recent wrong answers, low motivation, an empty week)
was written by us, so SHAP rediscovering it checks the pipeline, not the real world.

Run:  python -m ilm.analytics.dropout   -> reports/dropout/{report.json, report.md, shap_importance.png}
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ilm import config

CHECKPOINTS = range(1, 8)
HIGH_SHARE, MEDIUM_SHARE = 0.10, 0.20
TEST_SEED = 2027

FEATURES = ["week", "answers_total", "answers_this_week", "sessions_this_week", "sessions_last_week",
            "empty_week", "active_weeks_share", "days_since_last", "acc_total", "acc_this_week",
            "acc_last10", "acc_change", "wrong_streak", "speed", "code_share_this_week"]
BASELINE = ["acc_last10", "empty_week", "sessions_this_week"]

# the action that answers each kind of reason (by the feature that pushed risk up most)
REASON_ACTION = {
    "activity": ("sessions_this_week", "sessions_last_week", "empty_week", "days_since_last",
                 "answers_this_week", "active_weeks_share", "answers_total"),
    "struggling": ("acc_total", "acc_this_week", "acc_last10", "acc_change", "wrong_streak"),
    "pace": ("speed", "code_share_this_week"),
}
ACTION_TEXT = {
    "activity": "reminder at the student's usual study time + a 10-minute 'quick win' session",
    "struggling": "switch to easier ZPD questions and offer the Socratic tutor on the last mistake",
    "pace": "shorter sessions; split code exercises into smaller steps",
    "other": "check in: ask what is getting in the way",
}
LEVEL_ACTION = {
    "high": "mentor calls within 24 hours (plus the reason action)",
    "medium": "personalised UrduLish nudge in the app / WhatsApp (plus the reason action)",
    "low": "no extra action: the normal weekly progress summary",
}


# ------------------------------------------------------------------ features ----
def _wrong_streak(correct: np.ndarray) -> int:
    n = 0
    for ok in correct[::-1]:
        if ok:
            break
        n += 1
    return n


def snapshot(log: pd.DataFrame, people: pd.DataFrame, q_seconds: pd.Series) -> pd.DataFrame:
    """One row per (student, checkpoint week) for students active at that checkpoint."""
    log = log.sort_values(["student_id", "seq"])
    by_student = dict(tuple(log.groupby("student_id", sort=False)))
    rows = []
    for p in people.itertuples():
        h_all = by_student.get(p.student_id, log.iloc[:0])
        for w in CHECKPOINTS:
            if (pd.notna(p.dropped_week) and p.dropped_week < w) or (pd.notna(p.finished_week) and p.finished_week <= w):
                break                                       # gone (or done) before this checkpoint
            h = h_all[h_all["week"] <= w]
            this, last = h[h["week"] == w], h[h["week"] == w - 1]
            c = h["correct"].to_numpy()
            earlier = h[h["week"] < w]["correct"]
            ratio = (h["response_time_sec"].to_numpy() / q_seconds.reindex(h["question_id"]).to_numpy())
            rows.append({
                "student_id": p.student_id, "week": w,
                "answers_total": len(h), "answers_this_week": len(this),
                "sessions_this_week": this["day"].nunique(), "sessions_last_week": last["day"].nunique(),
                "empty_week": int(len(this) == 0),
                "active_weeks_share": h["week"].nunique() / w,
                "days_since_last": (7 * w - 1 - h["day"].max()) if len(h) else 7 * w,
                "acc_total": c.mean() if len(c) else np.nan,
                "acc_this_week": this["correct"].mean() if len(this) else np.nan,
                "acc_last10": c[-10:].mean() if len(c) else np.nan,
                "acc_change": (this["correct"].mean() - earlier.mean()) if len(this) and len(earlier) else np.nan,
                "wrong_streak": _wrong_streak(c),
                "speed": float(np.nanmedian(ratio)) if len(h) else np.nan,
                "code_share_this_week": (this["qtype"] == "code").mean() if len(this) else np.nan,
                "label": int(pd.notna(p.dropped_week) and p.dropped_week == w),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ models ----
def fit_baseline(train: pd.DataFrame):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    m.fit(train[BASELINE].fillna(0.5), train["label"])
    return lambda d: m.predict_proba(d[BASELINE].fillna(0.5))[:, 1]


GRID = [{"num_leaves": nl, "min_child_samples": mc} for nl in (7, 15, 31) for mc in (20, 50, 100)]


def fit_lgbm(train: pd.DataFrame, valid: pd.DataFrame, settings: dict, seed: int = config.RANDOM_SEED):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.03, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.8, random_state=seed, verbose=-1, **settings)
    m.fit(train[FEATURES], train["label"], eval_set=[(valid[FEATURES], valid["label"])],
          eval_metric="binary_logloss", callbacks=[lgb.early_stopping(100, verbose=False)])
    return m


def pr_auc(y, p) -> float:
    from sklearn.metrics import average_precision_score
    return float(average_precision_score(y, p))


def metrics(y, p) -> dict:
    from sklearn.metrics import brier_score_loss, roc_auc_score
    return {"pr_auc": round(pr_auc(y, p), 4), "roc_auc": round(float(roc_auc_score(y, p)), 4),
            "brier": round(float(brier_score_loss(y, p)), 4), "base_rate": round(float(np.mean(y)), 4)}


# ------------------------------------------------------------------ risk levels + actions ----
def cutoffs(valid_scores: np.ndarray) -> tuple[float, float]:
    """Scores above which a student is high / medium risk (set on validation, by capacity)."""
    return (float(np.quantile(valid_scores, 1 - HIGH_SHARE)),
            float(np.quantile(valid_scores, 1 - HIGH_SHARE - MEDIUM_SHARE)))


def ceiling(test: pd.DataFrame, motivation: pd.Series, drop_base: float) -> dict:
    """PR-AUC of the simulator's OWN dropout rule: the best any model could do. With the
    hidden motivation (no platform has it) and with the observable part only."""
    from ilm.learners.simulator import drop_hazard
    recent = 1 - test["acc_last10"].fillna(0.5)
    full = drop_hazard(drop_base, recent, test["student_id"].map(motivation), test["empty_week"])
    seen = drop_hazard(drop_base, recent, 0.0, test["empty_week"])
    return {"rule_with_hidden_motivation": round(pr_auc(test["label"], full), 4),
            "rule_observable_part_only": round(pr_auc(test["label"], seen), 4)}


def level(score: float, cuts: tuple[float, float]) -> str:
    return "high" if score >= cuts[0] else "medium" if score >= cuts[1] else "low"


def reason(shap_row: pd.Series) -> tuple[str, str]:
    """(kind of reason, the feature that pushed this student's risk up the most)."""
    top = shap_row.idxmax()
    if shap_row[top] <= 0:
        return "other", top
    kind = next((k for k, feats in REASON_ACTION.items() if top in feats), "other")
    return kind, top


def level_table(y: np.ndarray, levels: np.ndarray) -> pd.DataFrame:
    d = pd.DataFrame({"y": y, "level": levels})
    t = d.groupby("level")["y"].agg(students="size", dropouts="sum", dropout_rate="mean")
    t["share_of_all_dropouts"] = t["dropouts"] / d["y"].sum()
    return t.reindex(["high", "medium", "low"]).round(3)


# ------------------------------------------------------------------ run ----
def _shap(model, X: pd.DataFrame) -> pd.DataFrame:
    import shap
    values = shap.TreeExplainer(model).shap_values(X)
    if isinstance(values, list):                       # older shap: one array per class
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[..., 1]
    return pd.DataFrame(values, columns=X.columns, index=X.index)


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    from ilm.adaptive import compare as cmp
    from ilm.analytics.eda import bar_chart
    from ilm.learners import simulator as sim
    from ilm.learners.split import student_split

    sim_dir = config.PROCESSED_DIR / "simulated"
    log = sim.public(pd.read_csv(sim_dir / "interactions.csv.gz"))
    people = pd.read_csv(sim_dir / "students.csv")[["student_id", "dropped_week", "finished_week"]]
    q_sec = log.groupby("question_id")["response_time_sec"].median()      # from history only

    # fresh test cohort on the same fixed course
    course = sim.Course.load(config.RANDOM_SEED)
    base = json.loads((sim_dir / "summary.json").read_text())["calibrated_drop_base"]
    t_log, t_people = sim.run_course(cmp.students(course, seed=TEST_SEED), course, sim.FixedPath(course),
                                     TEST_SEED, base)
    t_log = sim.public(t_log)
    t_motivation = t_people.set_index("student_id")["truth_motivation"]   # ceiling check ONLY

    snaps = snapshot(log, people, q_sec)
    train, valid = student_split(snaps, student_col="student_id", test_frac=0.2)
    test = snapshot(t_log, t_people[["student_id", "dropped_week", "finished_week"]], q_sec)
    print(f"rows train/valid/test {len(train)}/{len(valid)}/{len(test)}  "
          f"base rate {train.label.mean():.3f}", flush=True)

    # choose LightGBM settings on validation
    tuning = []
    for g in GRID:
        m = fit_lgbm(train, valid, g)
        tuning.append({**g, "valid_pr_auc": round(pr_auc(valid["label"], m.predict_proba(valid[FEATURES])[:, 1]), 4),
                       "trees": int(m.best_iteration_ or m.n_estimators)})
        print(tuning[-1], flush=True)
    best = max(tuning, key=lambda r: r["valid_pr_auc"])
    chosen = {k: best[k] for k in ("num_leaves", "min_child_samples")}

    baseline = fit_baseline(train)
    model = fit_lgbm(train, valid, chosen)
    p_valid = model.predict_proba(valid[FEATURES])[:, 1]
    p_test = model.predict_proba(test[FEATURES])[:, 1]                    # test used once, here
    cuts = cutoffs(p_valid)

    results = {"baseline (logistic, 3 signals)": metrics(test["label"], baseline(test)),
               "LightGBM": metrics(test["label"], p_test)}
    best_possible = ceiling(test, t_motivation, base)
    by_week = (test.assign(p=p_test).groupby("week")
               .apply(lambda d: pd.Series({"rows": len(d), "base_rate": d.label.mean(),
                                           "pr_auc": pr_auc(d.label, d.p) if d.label.nunique() > 1 else np.nan}),
                      include_groups=False).round(3))

    levels = np.array([level(s, cuts) for s in p_test])
    lv = level_table(test["label"].to_numpy(), levels)

    sv = _shap(model, test[FEATURES])
    importance = sv.abs().mean().sort_values(ascending=False).round(4)
    reasons = [reason(sv.loc[i]) for i in test.index]
    test = test.assign(risk=p_test.round(3), level=levels, reason=[r[0] for r in reasons],
                       top_feature=[r[1] for r in reasons])
    flagged = test[test.level != "low"]
    reason_mix = flagged["reason"].value_counts(normalize=True).round(3).to_dict()

    examples = []
    for lvl in ("high", "medium", "low"):
        row = test[test.level == lvl].sort_values("risk", ascending=False).iloc[len(test[test.level == lvl]) // 2]
        push = sv.loc[row.name].sort_values(ascending=False)
        examples.append({"student_id": row.student_id, "week": int(row.week), "risk": float(row.risk),
                         "level": lvl, "actually_dropped": bool(row.label),
                         "top_pushes_up": {k: round(float(v), 3) for k, v in push.head(3).items()},
                         "top_pushes_down": {k: round(float(v), 3) for k, v in push.tail(2).items()},
                         "action": LEVEL_ACTION[lvl] + ("" if lvl == "low" else f"; reason: {ACTION_TEXT[row.reason]}")})

    out = config.REPORTS_DIR / "dropout"
    out.mkdir(parents=True, exist_ok=True)
    fig = bar_chart(importance.rename_axis("feature").reset_index(name="mean_abs_shap"), "feature", "mean_abs_shap",
                    "What drives the dropout warning", "mean |SHAP| on the test cohort (log-odds); longer = more influence")
    fig.savefig(out / "shap_importance.png", dpi=150)
    report = {
        "setup": {"checkpoints": list(CHECKPOINTS), "train_valid": "seed-42 history, split by student",
                  "test": f"fresh cohort seed {TEST_SEED}, fixed course, scored once",
                  "rows": {"train": len(train), "valid": len(valid), "test": len(test)}},
        "tuning_on_validation": tuning, "chosen": chosen, "trees": int(model.best_iteration_ or model.n_estimators),
        "test_results": results, "best_possible_pr_auc": best_possible, "test_pr_auc_by_week": by_week.reset_index().to_dict("records"),
        "risk_cutoffs_from_validation": {"high": round(cuts[0], 4), "medium": round(cuts[1], 4)},
        "risk_levels_on_test": lv.reset_index().to_dict("records"),
        "actions": {"by_level": LEVEL_ACTION, "by_reason": ACTION_TEXT},
        "flagged_reason_mix": reason_mix,
        "shap_mean_abs": importance.to_dict(),
        "examples": examples,
        "caveat": "Simulated students; the dropout rule is ours, so SHAP recovering it validates the pipeline.",
    }
    (out / "report.json").write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    md = ["# Dropout early warning (test cohort, scored once)", "",
          "| model | PR-AUC | ROC-AUC | Brier | base rate |", "|---|---|---|---|---|"]
    md += [f"| {k} | {v['pr_auc']:.3f} | {v['roc_auc']:.3f} | {v['brier']:.3f} | {v['base_rate']:.3f} |" for k, v in results.items()]
    md += [f"| *ceiling: the simulator's own rule, observable part* | {best_possible['rule_observable_part_only']:.3f} | | | |",
           f"| *ceiling: the rule incl. hidden motivation (impossible)* | {best_possible['rule_with_hidden_motivation']:.3f} | | | |",
           "", "Both models reach the best PR-AUC possible from what a platform can see: the rest of "
           "this simulated dropout is chance (by design) or hidden motivation. LightGBM cannot beat the "
           "logistic baseline here because the simulator's rule IS a logistic formula of the baseline's signals."]
    md += ["", "## Risk levels (cut-offs set on validation)", "",
           "| level | students | dropouts | dropout rate | share of all dropouts | action |", "|---|---|---|---|---|---|"]
    md += [f"| {l} | {int(r.students)} | {int(r.dropouts)} | {r.dropout_rate:.1%} | {r.share_of_all_dropouts:.1%} | {LEVEL_ACTION[l]} |"
           for l, r in lv.iterrows()]
    md += ["", "## Reason actions (from each flagged student's biggest SHAP push)", ""]
    md += [f"- **{k}** ({reason_mix.get(k, 0):.0%} of flagged): {v}" for k, v in ACTION_TEXT.items()]
    md += ["", "![SHAP importance](shap_importance.png)", "", f"*{report['caveat']}*", ""]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(json.dumps(examples, indent=1))


if __name__ == "__main__":
    main()
