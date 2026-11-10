"""
Real-time recommendation serving (Day 5, Task 1) built on the Day 2 item-to-item CF model.

Batch step (daily, `scripts/precompute_recommendations.py`):
    Retrain item-CF on ALL interactions (`interactions_clean`) and save `models/item_cf_serving.joblib`.
    The expensive part, the sparse 25k x 25k item-item similarity matrix, is computed here.

Online step (per request, a few ms):
    user vector = stored history + live session clicks  ->  scores = user_vector @ S
    -> BusinessReRanker (stock, already-bought, brand diversity, sale/margin/festival boosts)
    -> per-item explanation saying WHY (revisit, or which history item it is similar to).

Why item-CF: it had the best NDCG@10 of all Day 2 models (reports/day2_model_comparison.csv), and
item-to-item scoring is cheap enough to recompute on every click, which is what lets the
homepage react to the current session in real time.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import threading
import time
from typing import Any

import duckdb
import joblib
import numpy as np
import scipy.sparse as sp

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import BaseRecommender
from shopkaro.recommendations.collaborative import (
    ItemToItemCFRecommender,
    _load_sparse_interaction_data,
)

logger = logging.getLogger(__name__)

ARTIFACT_PATH = settings.models_dir / "item_cf_serving.joblib"
ARTIFACT_FORMAT_VERSION = 2
# Same implicit weights as the Day 1 pipeline (interactions_clean.implicit_weight)
EVENT_WEIGHTS: dict[str, float] = {"view": 1.0, "addtocart": 3.0, "transaction": 6.0}
SESSION_TTL_SECONDS = 30 * 60  # Day 1 session rule: 30 minutes of inactivity ends a session


# ---------------------------------------------------------------------------
# Batch: train / save / load
# ---------------------------------------------------------------------------
@dataclass
class ServingArtifact:
    model: ItemToItemCFRecommender
    trained_at: str
    source_table: str
    n_users: int
    n_items: int
    n_interactions: int
    fit_seconds: float
    data_fingerprint: str = ""
    format_version: int = ARTIFACT_FORMAT_VERSION

    def info(self) -> dict[str, Any]:
        return {
            "model": self.model.name,
            "trained_at": self.trained_at,
            "source_table": self.source_table,
            "n_users": self.n_users,
            "n_items": self.n_items,
            "n_interactions": self.n_interactions,
            "fit_seconds": self.fit_seconds,
            "data_fingerprint": self.data_fingerprint,
        }


def data_fingerprint(con: duckdb.DuckDBPyConnection, table: str = "interactions_clean") -> str:
    """Cheap fingerprint of the catalogue + interactions, so a model trained on old data is never served."""
    cat = con.execute(
        "SELECT COUNT(*), bit_xor(hash(product_id || '|' || category || '|' || CAST(in_stock AS VARCHAR))) "
        "FROM product_catalogue"
    ).fetchone()
    inter = con.execute(
        f"SELECT COUNT(*), bit_xor(hash(user_id || '|' || product_id || '|' || event_type)) FROM {table}"
    ).fetchone()
    return f"cat:{cat[0]}:{cat[1]}|int:{inter[0]}:{inter[1]}"


def train_serving_model(con: duckdb.DuckDBPyConnection, table: str = "interactions_clean") -> ServingArtifact:
    """Fit item-CF with the Day 2 hyperparameters on `table` (all history for production)."""
    t0 = time.perf_counter()
    catalogue_df, user_to_row, _user_ids, item_to_col, item_ids, R_csr, user_purchased = (
        _load_sparse_interaction_data(con, table=table)
    )
    model = ItemToItemCFRecommender().fit_from_sparse(
        catalogue_df, user_to_row, item_to_col, item_ids, R_csr, user_purchased
    )
    return ServingArtifact(
        model=model,
        trained_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_table=table,
        n_users=len(user_to_row),
        n_items=len(item_ids),
        n_interactions=int(R_csr.nnz),
        fit_seconds=round(time.perf_counter() - t0, 2),
        data_fingerprint=data_fingerprint(con, table),
    )


def save_artifact(artifact: ServingArtifact, path: Path = ARTIFACT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    joblib.dump(artifact, tmp, compress=3)
    tmp.replace(path)  # atomic swap so the API never reads a half-written file
    return path


def load_artifact(path: Path = ARTIFACT_PATH) -> ServingArtifact | None:
    """Load our own trained artifact (joblib/pickle: only load files this project produced)."""
    if not path.exists():
        return None
    artifact = joblib.load(path)
    if getattr(artifact, "format_version", None) != ARTIFACT_FORMAT_VERSION:
        logger.warning("Ignoring %s: artifact format version mismatch", path)
        return None
    return artifact


def load_or_train(con: duckdb.DuckDBPyConnection, path: Path = ARTIFACT_PATH) -> tuple[ServingArtifact, str]:
    """Use the batch artifact if present; otherwise train now (and save) so the API still starts."""
    artifact = load_artifact(path)
    if artifact is not None:
        if artifact.data_fingerprint == data_fingerprint(con, artifact.source_table):
            return artifact, "loaded_batch_artifact"
        logger.warning("Serving artifact %s was trained on different data; retraining", path)
    else:
        logger.warning("No serving artifact at %s; training item-CF in-process", path)
    artifact = train_serving_model(con)
    try:
        save_artifact(artifact, path)
    except OSError as exc:  # read-only volume etc.: serve from memory anyway
        logger.warning("Could not save serving artifact: %s", exc)
    return artifact, "trained_at_startup"


# ---------------------------------------------------------------------------
# Online: live session events
# ---------------------------------------------------------------------------
class SessionEventStore:
    """
    Recent clicks per user, kept for one session (30 min). In-memory and per-process: with several
    API workers this should move to Redis (a list per user) so all workers see the same clicks.
    """

    def __init__(self, max_events_per_user: int = 50, ttl_seconds: float = SESSION_TTL_SECONDS) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[tuple[str, str, float, float]]] = {}
        self._versions: dict[str, int] = {}
        self._preferences: dict[str, list[str]] = {}
        self.max_events = max_events_per_user
        self.ttl = ttl_seconds

    def add(self, user_id: str, product_id: str, event_type: str) -> int:
        if event_type not in EVENT_WEIGHTS:
            raise ValueError(f"event_type must be one of {sorted(EVENT_WEIGHTS)}")
        with self._lock:
            q = self._events.setdefault(user_id, deque(maxlen=self.max_events))
            q.append((product_id, event_type, EVENT_WEIGHTS[event_type], time.time()))
            self._versions[user_id] = self._versions.get(user_id, 0) + 1
            return self._versions[user_id]

    def events(self, user_id: str) -> list[tuple[str, str, float, float]]:
        cutoff = time.time() - self.ttl
        with self._lock:
            return [e for e in self._events.get(user_id, ()) if e[3] >= cutoff]

    def set_preferences(self, user_id: str, categories: list[str]) -> int:
        """Onboarding answers ("which categories do you shop for?") for a brand-new user."""
        with self._lock:
            self._preferences[user_id] = list(dict.fromkeys(categories))
            self._versions[user_id] = self._versions.get(user_id, 0) + 1
            return self._versions[user_id]

    def preferences(self, user_id: str) -> list[str]:
        with self._lock:
            return list(self._preferences.get(user_id, []))

    def version(self, user_id: str) -> int:
        with self._lock:
            return self._versions.get(user_id, 0)


# ---------------------------------------------------------------------------
# Online: session-aware recommender
# ---------------------------------------------------------------------------
class RealtimeItemCFRecommender(BaseRecommender):
    """Item-CF whose user vector = stored history + live session clicks. Scoring is the Day 2 code."""

    name = "Item-CF real-time (history + session clicks)"

    def __init__(self, cf: ItemToItemCFRecommender, events: SessionEventStore) -> None:
        super().__init__()
        self.cf = cf
        self.events = events
        self.item_metadata = cf.item_metadata
        self.in_stock_ids = cf.in_stock_ids
        self.total_catalogue_size = cf.total_catalogue_size

    def is_known(self, user_id: str) -> bool:
        """True when the user has stored history or live clicks (i.e. not a cold start)."""
        return user_id in self.cf.user_to_row or bool(self.events.events(user_id))

    def favourite_category(self, u_vec: sp.csr_matrix | None) -> str | None:
        if u_vec is None or u_vec.nnz == 0:
            return None
        return str(self.cf.item_categories[int(u_vec.indices[int(np.argmax(u_vec.data))])])

    def history_size(self, user_id: str) -> int:
        row = self.cf.user_to_row.get(user_id)
        return 0 if row is None else int(self.cf.R_log_csr[row].nnz)

    def session_purchases(self, user_id: str) -> set[str]:
        return {pid for pid, et, _w, _t in self.events.events(user_id) if et == "transaction"}

    def user_vector(self, user_id: str) -> sp.csr_matrix | None:
        """1 x n_items log-dampened vector, same transform as training: log1p(sum of raw weights)."""
        cf = self.cf
        raw: dict[int, float] = {}
        row = cf.user_to_row.get(user_id)
        if row is not None:
            hist = cf.R_log_csr[row]
            for col, w in zip(hist.indices, hist.data):
                raw[int(col)] = float(np.expm1(w))
        for pid, _et, weight, _ts in self.events.events(user_id):
            col = cf.item_to_col.get(pid)
            if col is not None:
                raw[col] = raw.get(col, 0.0) + weight
        if not raw:
            return None
        cols = np.fromiter(raw.keys(), dtype=np.int32)
        data = np.log1p(np.fromiter(raw.values(), dtype=np.float32))
        return sp.csr_matrix((data, (np.zeros_like(cols), cols)), shape=(1, len(cf.col_to_item)))

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        scores = self.cf._score_user_vector(
            user_id=user_id,
            exclude_seen=exclude_seen,
            only_in_stock=only_in_stock,
            u_vec=self.user_vector(user_id),
            extra_purchased=self.session_purchases(user_id),
        )
        # Cold start with onboarding answers: popularity restricted to the chosen categories
        prefs = self.events.preferences(user_id) if not self.is_known(user_id) else []
        if prefs:
            allowed = np.zeros(len(scores), dtype=bool)
            for cat in prefs:
                allowed[self.cf.cat_to_cols.get(cat, np.array([], dtype=int))] = True
            if allowed.any():
                scores = np.where(allowed, scores, -1e9)
        k = min(k, len(scores))
        top = np.argpartition(scores, -k)[-k:]
        top = top[np.argsort(scores[top])[::-1]]
        # Drop filtered items (-1e9): they would distort the re-ranker's min-max score scaling
        return [(self.cf.col_to_item[int(i)], float(scores[i])) for i in top if scores[i] > -1e8]

    def explain_many(self, user_id: str, product_ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Why was each product recommended?
        - "revisit": the user already viewed / carted it (and has not bought it)
        - "similar_to_history": names the history item contributing most to its CF score
        - "popular_in_category": no co-occurrence signal (cold start / popularity prior)
        """
        default = {"reason_type": "popular_in_category", "because_of": None}
        u_vec = self.user_vector(user_id)
        if u_vec is None:
            return {pid: dict(default) for pid in product_ids}
        hist_cols = u_vec.indices
        hist_set = set(hist_cols.tolist())
        cols = [self.cf.item_to_col.get(pid) for pid in product_ids]
        valid = [c for c in cols if c is not None]
        # contrib[h, j] = weight of history item h * similarity(h, candidate j)
        sub = self.cf.sim_matrix_csr[hist_cols][:, valid].toarray() if valid else np.zeros((0, 0))
        contrib = sub * u_vec.data[:, None]
        out: dict[str, dict[str, Any]] = {}
        j = 0
        for pid, col in zip(product_ids, cols):
            if col is None:
                out[pid] = dict(default)
                continue
            column = contrib[:, j]
            j += 1
            if col in hist_set:
                out[pid] = {"reason_type": "revisit", "because_of": pid}
            elif column.size and float(column.max()) > 0:
                out[pid] = {
                    "reason_type": "similar_to_history",
                    "because_of": self.cf.col_to_item[int(hist_cols[int(np.argmax(column))])],
                }
            else:
                out[pid] = dict(default)
        return out


def explanation_text(reason: dict[str, Any], item: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """One-line Roman Urdu + English explanation that states the real reason."""
    brand = str(item.get("brand", ""))
    sub = str(item.get("sub_category") or item.get("category", "product"))
    sale = f" ({int(float(item.get('discount_pct', 0)))}% OFF)" if item.get("on_sale") else ""
    rtype = reason["reason_type"]
    if rtype == "revisit":
        return (
            f"Aap ne yeh pehle dekha tha — abhi bhi stock mein hai{sale}.",
            f"You viewed this before and it's still in stock{sale}.",
        )
    if rtype == "similar_to_history":
        src = catalog.get(reason["because_of"], {})
        short = " ".join(str(src.get("title", "")).split()[:3]) or "is product"
        return (
            f"Kyun ke aap ne {short} dekha, yeh {brand} {sub}{sale} bhi pasand kiya ja raha hai.",
            f"Because you viewed {short}, shoppers also like this {brand} {sub}{sale}.",
        )
    cat = str(item.get("category", ""))
    return (
        f"'{cat}' mein ShopKaro ke maqbool products mein se ek{sale}.",
        f"Popular in {cat} on ShopKaro{sale}.",
    )
