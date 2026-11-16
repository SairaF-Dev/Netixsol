"""
Festival calendar as the forecasters see it: only what a retailer knows in advance.

A planner knows WHEN Ramadan, Eid, 11.11 etc. happen (name, type, start and end date). A planner does NOT know how
much each festival will lift sales; that has to be learned from past sales. The `festival_calendar` table also holds
`demand_multiplier` and `boost_categories`, which the data generator used to create the synthetic sales. Reading
them would hand the model the answer, so this class reads only the four columns below and nothing else.
(`tests/test_forecast_leakage.py` checks this.)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

KNOWN_IN_ADVANCE_COLUMNS = ("festival_name", "festival_type", "start_date", "end_date")


@dataclass(frozen=True)
class FestivalOccurrence:
    name: str
    festival_type: str
    start: pd.Timestamp
    end: pd.Timestamp


class FestivalCalendar:
    """Festival dates and names only (no effect sizes)."""

    def __init__(self, festival_cal_df: pd.DataFrame) -> None:
        df = festival_cal_df.loc[:, list(KNOWN_IN_ADVANCE_COLUMNS)].copy()
        df["start_date"] = pd.to_datetime(df["start_date"])
        df["end_date"] = pd.to_datetime(df["end_date"])
        df = df.sort_values(["start_date", "festival_name"]).reset_index(drop=True)
        self.occurrences: list[FestivalOccurrence] = [
            FestivalOccurrence(str(r.festival_name), str(r.festival_type), r.start_date, r.end_date)
            for r in df.itertuples(index=False)
        ]
        self.names: list[str] = sorted({o.name for o in self.occurrences})

    def seen_before(self, day: pd.Timestamp) -> FestivalCalendar:
        """
        Calendar restricted to festivals that already happened at least once by `day` (start date <= day).
        A festival with no history (e.g. a sale running for the first time) is treated as a regular day: there is
        nothing to learn its effect from, and treating it like Eid would invent demand.
        """
        known = {o.name for o in self.occurrences if o.start <= pd.Timestamp(day)}
        out = object.__new__(FestivalCalendar)
        out.occurrences = [o for o in self.occurrences if o.name in known]
        out.names = sorted(known)
        return out

    def active_matrix(self, dates: pd.DatetimeIndex | pd.Series) -> np.ndarray:
        """Boolean (n_dates, n_names): which festivals are running on each date."""
        d = pd.DatetimeIndex(pd.to_datetime(dates)).normalize()
        out = np.zeros((len(d), len(self.names)), dtype=bool)
        col = {n: i for i, n in enumerate(self.names)}
        for o in self.occurrences:
            out[:, col[o.name]] |= (d >= o.start) & (d <= o.end)
        return out

    def is_festival(self, dates: pd.DatetimeIndex | pd.Series) -> np.ndarray:
        return self.active_matrix(dates).any(axis=1)

    def days_since_start(self, dates: pd.DatetimeIndex | pd.Series) -> np.ndarray:
        """Days since the most recently started running festival (-1 on regular days)."""
        d = pd.DatetimeIndex(pd.to_datetime(dates)).normalize()
        out = np.full(len(d), -1.0)
        for o in self.occurrences:
            active = (d >= o.start) & (d <= o.end)
            since = (d - o.start).days.to_numpy(dtype=float)
            out = np.where(active & ((out < 0) | (since < out)), since, out)
        return out

    def prophet_holidays(self) -> pd.DataFrame:
        """Prophet's `holidays=` frame: one row per occurrence, the window covers the whole festival."""
        return pd.DataFrame(
            {
                "holiday": [o.name for o in self.occurrences],
                "ds": [o.start for o in self.occurrences],
                "lower_window": 0,
                "upper_window": [int((o.end - o.start).days) for o in self.occurrences],
            }
        )


def festival_uplift_features(
    y: np.ndarray,
    dates: pd.DatetimeIndex,
    calendar: FestivalCalendar,
    origin_idx: np.ndarray,
    target_dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Festival uplift LEARNED FROM THIS SERIES' OWN HISTORY, using only sales up to each origin.

    For a target date inside festival F:
    - `hist`: how much F lifted sales the previous time it happened (mean sales during that occurrence / mean of the
      28 days before it). Islamic festivals move ~11 days a year; matching by name handles that.
    - `cur`: if this occurrence of F had already started by the origin, the lift observed so far.
    Both are NaN when not available (gradient boosting handles missing values). With several festivals running,
    the largest value is used.
    """
    n_rows = len(origin_idx)
    hist = np.full(n_rows, np.nan)
    cur = np.full(n_rows, np.nan)
    if not calendar.occurrences:
        return hist, cur
    pos = {d: i for i, d in enumerate(pd.DatetimeIndex(dates).normalize())}
    csum = np.concatenate([[0.0], np.cumsum(y)])

    def mean(a: int, b: int) -> float:  # mean of y[a..b] inclusive
        a = max(a, 0)
        return (csum[b + 1] - csum[a]) / (b - a + 1) if b >= a else np.nan

    td = pd.DatetimeIndex(target_dates).normalize()
    for occ in calendar.occurrences:
        in_occ = np.flatnonzero((td >= occ.start) & (td <= occ.end))
        if len(in_occ) == 0:
            continue
        s_idx = pos.get(occ.start)
        # Previous occurrence(s) of the same festival
        prev = [p for p in calendar.occurrences if p.name == occ.name and p.end < occ.start]
        for r in in_occ:
            o = int(origin_idx[r])
            for p in reversed(prev):
                ps, pe = pos.get(p.start), pos.get(p.end)
                if ps is None or pe is None or pe > o or ps < 28:
                    continue
                v = mean(ps, pe) / (mean(ps - 28, ps - 1) + 0.1)
                hist[r] = v if np.isnan(hist[r]) else max(hist[r], v)
                break
            if s_idx is not None and s_idx <= o and s_idx >= 28:
                v = mean(s_idx, o) / (mean(s_idx - 28, s_idx - 1) + 0.1)
                cur[r] = v if np.isnan(cur[r]) else max(cur[r], v)
    return hist, cur
