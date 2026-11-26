"""Day 1 EDA: accuracy per concept, learning curves, dropout points, hardest concepts.

Logic lives here (tested in tests/test_eda.py); notebooks/day1_eda.ipynb only calls it.
Every insight sentence is BUILT FROM THE NUMBERS, so it cannot go stale when data changes.

Two data sources, never mixed in one number:
  real       ASSISTments 2009-10 (real students, maths skills)  - real findings
  simulated  our Python course (1,000 simulated students)       - reflects OUR assumptions;
             shown to test the pipeline that will run on Ilm Academy's real logs
"""
from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Validated palette (dataviz reference instance; light surface). Orange and aqua are
# below 3:1 contrast on white, so every chart has direct labels AND a printed table.
BLUE, ORANGE, AQUA = "#257de0", "#f47230", "#00b894"
INK, INK_2, GRID = "#191919", "#666666", "#e7e7e7"
MIN_N = 200  # fewer answers than this: the accuracy is too uncertain to rank


# ---------------------------------------------------------------- statistics ----
def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """95% interval for a proportion k/n. Better than p +/- 1.96*sqrt(p(1-p)/n), which
    breaks near 0 or 1 and for small n (it can even go below 0)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (mid - half, mid + half)


def accuracy_by(df: pd.DataFrame, col: str, min_n: int = MIN_N) -> pd.DataFrame:
    """Accuracy per group with a 95% interval; groups with < min_n answers are dropped."""
    g = df.groupby(col)["correct"].agg(k="sum", n="size").reset_index()
    g = g[g["n"] >= min_n].copy()
    g["accuracy"] = g["k"] / g["n"]
    g[["low", "high"]] = [wilson(k, n) for k, n in zip(g["k"], g["n"])]
    return g.drop(columns="k").sort_values("accuracy").reset_index(drop=True)


def add_attempt(df: pd.DataFrame, student: str, skill: str) -> pd.DataFrame:
    """attempt = how many times this student has now practised this skill (1, 2, ...)."""
    df = df.copy()
    df["attempt"] = df.groupby([student, skill]).cumcount() + 1
    df["attempts_total"] = df.groupby([student, skill])["attempt"].transform("max")
    return df


def learning_curve(df: pd.DataFrame, max_attempt: int, same_students: bool) -> pd.DataFrame:
    """Accuracy at attempt 1..max_attempt (df needs add_attempt columns).
    same_students=True keeps only student-skill pairs that reached max_attempt, so every
    point is the SAME people. Otherwise who is still answering changes along the curve."""
    d = df[df["attempt"] <= max_attempt]
    if same_students:
        d = d[d["attempts_total"] >= max_attempt]
    return d.groupby("attempt")["correct"].agg(accuracy="mean", n="size").reset_index()


def survival(people: pd.DataFrame, weeks: int) -> pd.DataFrame:
    """Per week: still enrolled at the start, dropped during it, hazard, share left after it.
    hazard = dropped / at risk: the chance of quitting THIS week, given you made it here."""
    n = len(people)
    dropped_wk = people["dropped_week"].fillna(np.inf)
    finished_wk = people["finished_week"].fillna(np.inf)
    rows = []
    for w in range(1, weeks + 1):
        at_risk = int(((dropped_wk >= w) & (finished_wk >= w)).sum())  # still studying at week start
        dropped = int((dropped_wk == w).sum())
        rows.append({"week": w, "at_risk": at_risk, "dropped": dropped,
                     "hazard": dropped / at_risk if at_risk else 0.0,
                     # finishing is not dropping out: only dropouts reduce this share
                     "not_dropped_share": 1 - int((dropped_wk <= w).sum()) / n})
    return pd.DataFrame(rows)


def dropout_position(log: pd.DataFrame, people: pd.DataFrame, lesson_of: dict) -> pd.DataFrame:
    """For each student who quit: the lesson of the last concept they worked on."""
    last = log.sort_values("seq").groupby("student_id").tail(1).set_index("student_id")["concept"]
    quit_ids = people.loc[people["dropped_week"].notna(), "student_id"]
    lessons = last.reindex(quit_ids).map(lesson_of)
    return lessons.value_counts().rename_axis("lesson").reset_index(name="dropouts")


def separable(a: pd.Series, b: pd.Series) -> bool:
    """True when two 95% intervals do not overlap: a cautious 'really different'."""
    return a["high"] < b["low"] or b["high"] < a["low"]


# ---------------------------------------------------------------- charts ----
def _style(ax, title: str, subtitle: str = ""):
    ax.set_title(title, loc="left", color=INK, fontsize=12, pad=18 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK_2, fontsize=9)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(axis="x" if ax.get_ylabel() == "" else "y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def dot_plot(table: pd.DataFrame, label: str, title: str, subtitle: str, color: str = BLUE):
    """Accuracy with 95% interval whiskers: a dot plot, not bars, because the
    interval matters as much as the point."""
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(table) + 1.2))
    y = np.arange(len(table))
    ax.hlines(y, table["low"], table["high"], color=color, linewidth=2, alpha=0.45)
    ax.plot(table["accuracy"], y, "o", color=color, markersize=7, markeredgecolor="white",
            markeredgewidth=1.5)
    for yi, (acc, n) in enumerate(zip(table["accuracy"], table["n"])):
        ax.text(table["high"].iloc[yi] + 0.015, yi, f"{acc:.0%}  (n={n:,})", va="center",
                color=INK_2, fontsize=8)
    ax.set_yticks(y, table[label], color=INK)
    ax.set_xlim(0, 1.12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.invert_yaxis()
    _style(ax, title, subtitle)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    return fig


def label_offsets(ends: list[float], span: float, min_gap: float = 0.06) -> list[float]:
    """Vertical offsets (points) for end-of-line labels, pushing apart labels whose lines
    end closer than min_gap of the y-range (found 2026-11-26: two curves ending at 68%
    printed their names on top of each other)."""
    order = sorted(range(len(ends)), key=lambda i: ends[i])
    offsets = [0.0] * len(ends)
    for a, b in zip(order, order[1:]):
        if abs(ends[b] - ends[a]) < min_gap * span:
            offsets[a] -= 6
            offsets[b] += 6
    return offsets


def line_chart(series: dict[str, pd.DataFrame], x: str, y: str, title: str, subtitle: str,
               xlabel: str, ylabel: str, percent: bool = True, marker_line: float | None = None,
               ylim: tuple[float, float] | None = None):
    fig, ax = plt.subplots(figsize=(8, 4))
    ends = [d[y].iloc[-1] for d in series.values()]
    all_y = pd.concat([d[y] for d in series.values()])
    span = (ylim[1] - ylim[0]) if ylim else float(all_y.max() - all_y.min()) or 1.0
    for (name, d), color, dy in zip(series.items(), (BLUE, ORANGE, AQUA), label_offsets(ends, span)):
        ax.plot(d[x], d[y], "-o", color=color, linewidth=2, markersize=6,
                markeredgecolor="white", markeredgewidth=1.2, label=name)
        ax.annotate(name, (d[x].iloc[-1], d[y].iloc[-1]), xytext=(8, dy),
                    textcoords="offset points", va="center", color=INK, fontsize=9)
    if ylim:
        ax.set_ylim(*ylim)
    if marker_line is not None:
        ax.axvline(marker_line, color=INK_2, linewidth=1, linestyle=":")
    if percent:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel(xlabel, color=INK_2, fontsize=9)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=9)
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="lower right")
    _style(ax, title, subtitle)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.margins(x=0.12)
    fig.tight_layout()
    return fig


def bar_chart(table: pd.DataFrame, label: str, value: str, title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(table) + 1.2))
    y = np.arange(len(table))
    ax.barh(y, table[value], color=BLUE, height=0.7, edgecolor="white", linewidth=2)
    for yi, v in enumerate(table[value]):
        ax.text(v, yi, f" {v:,}", va="center", color=INK_2, fontsize=8)
    ax.set_yticks(y, table[label], color=INK)
    ax.invert_yaxis()
    _style(ax, title, subtitle)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    return fig
