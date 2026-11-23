"""The ONNX models must reproduce what the index was built with (PyTorch, Day 2)."""

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from src.indexing.onnx_models import OnnxEmbedder, OnnxReranker

INDEX = Path("data/indices/vstore_legal.sqlite3")


@pytest.fixture(scope="module")
def embedder():
    return OnnxEmbedder()


def test_embeddings_are_unit_length_and_meaningful(embedder):
    vecs = embedder.encode(["query: Is an agreement with an unlawful object void?",
                            "passage: Every agreement of which the object or consideration is unlawful is void.",
                            "passage: The Commissioner may issue a notice for the recovery of tax."],
                           normalize_embeddings=True)
    assert vecs.shape == (3, 384)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)
    assert vecs[0] @ vecs[1] > vecs[0] @ vecs[2]


@pytest.mark.skipif(not INDEX.exists(), reason="search index not built")
def test_onnx_vectors_match_the_stored_index(embedder):
    with sqlite3.connect(str(INDEX)) as con:
        rows = con.execute("SELECT content, embedding FROM legal_chunks ORDER BY chunk_id LIMIT 20").fetchall()
    stored = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    new = embedder.encode([f"passage: {r[0]}" for r in rows], normalize_embeddings=True)
    assert ((stored * new).sum(axis=1) > 0.9999).all()


def test_reranker_prefers_the_relevant_passage():
    model = OnnxReranker()
    q = "Is an agreement with an unlawful object void?"
    scores = model.predict([(q, "Every agreement of which the object or consideration is unlawful is void."),
                            (q, "The Commissioner may issue a notice for the recovery of tax.")])
    assert scores.shape == (2,) and 0.0 <= scores.min() and scores.max() <= 1.0
    assert scores[0] > scores[1]


def test_reranker_shares_the_embedding_tokenizer(embedder):
    assert OnnxReranker().tokenizer is embedder.tokenizer
