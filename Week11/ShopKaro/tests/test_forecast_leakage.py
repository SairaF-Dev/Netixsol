"""
Leakage guard for the Day 3 forecasters.

The sales history is synthetic. An earlier "LightGBM" rebuilt the generator's own formula (weekly multipliers, season
curves, trend and the TRUE festival multipliers), so its accuracy was not real. These tests make sure the real
forecasters can only learn from past sales and festival DATES:

1. Static: the honest forecasters and the inventory code never mention the generator's answer columns or the oracle.
2. The festival calendar gives identical features whether or not the answer columns are present.
3. "Altered world": sales generated with DIFFERENT rules (weekday pattern moved, Ramadan lowers sales, other
   festival sizes). A model that learns from data still beats seasonal naive; the oracle, which assumes the original
   rules, falls apart. If someone wires the generator's constants back in, test 3 fails.
No database needed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from shopkaro.data.synthesizer import PAKISTANI_FESTIVALS
from shopkaro.forecasting.festivals import FestivalCalendar
from shopkaro.forecasting.models import GlobalLGBMForecaster, SeasonalNaive7DForecaster
from shopkaro.forecasting.oracle import OracleGeneratorFormulaForecaster, build_oracle_festival_lookup

FORECASTING = Path(__file__).resolve().parents[1] / "src" / "shopkaro" / "forecasting"
ANSWER_COLUMNS = {"demand_multiplier", "boost_categories"}
ORACLE_NAMES = {
    "oracle",
    "build_oracle_festival_lookup",
    "OracleGeneratorFormulaForecaster",
    "_category_climate_index",
    "_compute_structural_divisor",
}


def _calendar_df() -> pd.DataFrame:
    return pd.DataFrame(
        [{**f, "boost_categories": ", ".join(f["boost_categories"])} for f in PAKISTANI_FESTIVALS]
    )


def _non_docstring_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(string constants that are not docstrings, identifiers) used in a syntax tree."""
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node) is not None:
            docstrings.add(id(node.body[0].value))
    strings, names = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            strings.add(node.value)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").rsplit(".", 1)[-1])
            names.update(a.name for a in node.names)
    return strings, names


def test_honest_code_never_reads_the_generator_answers() -> None:
    for fname in ("festivals.py", "inventory.py", "inventory_backtest.py"):
        strings, names = _non_docstring_names(ast.parse((FORECASTING / fname).read_text(encoding="utf-8")))
        assert not (strings & ANSWER_COLUMNS), f"{fname} reads {strings & ANSWER_COLUMNS}"
        assert not (names & ORACLE_NAMES), f"{fname} uses {names & ORACLE_NAMES}"

    tree = ast.parse((FORECASTING / "models.py").read_text(encoding="utf-8"))
    honest = {"GlobalLGBMForecaster", "ProphetFourierHolidayForecaster", "_daily_series"}
    checked = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in honest:
            checked.add(node.name)
            strings, names = _non_docstring_names(node)
            assert not (strings & ANSWER_COLUMNS), f"{node.name} reads {strings & ANSWER_COLUMNS}"
            assert not (names & ORACLE_NAMES), f"{node.name} uses {names & ORACLE_NAMES}"
    assert checked == honest


def test_calendar_ignores_answer_columns() -> None:
    full = _calendar_df()
    rng = np.random.default_rng(0)
    scrambled = full.assign(demand_multiplier=rng.uniform(0.1, 9.0, len(full)), boost_categories="nothing")
    dates_only = full[["festival_name", "festival_type", "start_date", "end_date"]]
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    ref = FestivalCalendar(full)
    for other in (FestivalCalendar(scrambled), FestivalCalendar(dates_only)):
        assert other.names == ref.names
        assert (other.active_matrix(days) == ref.active_matrix(days)).all()
        assert (other.days_since_start(days) == ref.days_since_start(days)).all()


def _altered_world_panel(seed: int = 7) -> dict[str, pd.DataFrame]:
    """Two years of daily sales made with rules that differ from the project's generator."""
    rng = np.random.default_rng(seed)
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    dow = days.day_of_week.to_numpy()
    doy = days.day_of_year.to_numpy()
    weekly = np.select([dow == 0, dow == 1], [1.6, 0.7], 1.0)  # Monday peak instead of Fri-Sun
    # Other festival effects; Ramadan LOWERS sales here (the oracle assumes x2.6)
    effects = {"Ramadan": 0.5, "Chaand Raat & Eid ul Fitr": 1.8, "Eid ul Adha": 0.7, "11.11 Mega Sale": 2.5}
    cal = _calendar_df()
    fest = np.ones(len(days))
    for r in cal.itertuples():
        if r.festival_name in effects:
            m = (days >= pd.Timestamp(r.start_date)) & (days <= pd.Timestamp(r.end_date))
            fest[m] = effects[r.festival_name]
    panel = {}
    for i, cat in enumerate(["Women's Lawn & Unstitched", "Winter Wear & Jackets", "Smartphones & Accessories"] * 2):
        season = 1.0 + 0.4 * np.cos(2 * np.pi * (doy - 200 - 40 * i) / 365.25)  # not the generator's curves
        lam = rng.uniform(20, 40) * weekly * season * fest
        panel[f"S{i}"] = pd.DataFrame({"sale_date": days, "units_sold": rng.poisson(lam), "category": cat})
    return panel


def test_altered_world_learning_beats_the_oracle() -> None:
    panel = _altered_world_panel()
    cutoff = pd.Timestamp("2025-03-15")  # Ramadan running, Eid ul Fitr next
    fut = pd.date_range(cutoff + pd.Timedelta(days=1), periods=14, freq="D")
    train = {k: (df[df["sale_date"] <= cutoff], str(df["category"].iloc[0])) for k, df in panel.items()}
    actual = {k: df.set_index("sale_date").loc[fut, "units_sold"].to_numpy(float) for k, df in panel.items()}

    def wape(pred: dict[str, np.ndarray]) -> float:
        return sum(np.abs(actual[k] - pred[k]).sum() for k in actual) / sum(actual[k].sum() for k in actual) * 100

    cal_df = _calendar_df()
    honest = wape(GlobalLGBMForecaster().fit_and_predict_panel(train, fut, FestivalCalendar(cal_df)))
    snaive = wape({k: SeasonalNaive7DForecaster().fit_predict_series(v[0], fut) for k, v in train.items()})
    oracle_lookup = build_oracle_festival_lookup(cal_df, sorted({c for _, c in train.values()}))
    oracle = wape(OracleGeneratorFormulaForecaster().fit_and_predict_panel(train, fut, oracle_lookup))

    assert honest < snaive, (honest, snaive)
    assert honest < oracle, (honest, oracle)
