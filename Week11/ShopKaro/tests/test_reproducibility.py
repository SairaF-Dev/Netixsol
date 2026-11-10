"""Regression test: the interaction matrix must be built in a fixed order, or seeded models train differently each run."""

from __future__ import annotations

import duckdb

from shopkaro.config.settings import settings
from shopkaro.recommendations.collaborative import _load_sparse_interaction_data


def test_interaction_matrix_rows_are_in_fixed_order() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        _cat, user_to_row, user_ids, _i2c, _c2i, R, _bought = _load_sparse_interaction_data(con)
    finally:
        con.close()
    # Rows sorted by user id (DuckDB's GROUP BY output order alone changes between runs)
    assert user_ids == sorted(user_ids)
    assert all(user_to_row[u] == i for i, u in enumerate(user_ids[:1000]))
    assert R.shape[0] == len(user_ids)
