"""Day 1 setup tests: isolation works, and the vector DB stack runs end to end."""
from __future__ import annotations

import pytest

from ilm import config


def test_tests_never_use_real_data_dir():
    # If this fails, a test could overwrite the real dataset.
    assert "ilm_tests_" in str(config.DATA_DIR)
    assert config.DATA_DIR != config.PROJECT_ROOT / "data"


@pytest.mark.slow
def test_embeddings_and_chroma_retrieve_the_right_chunk():
    """Smoke test of the Day 1 retrieval stack with real models (no mocks).

    This only proves the stack runs. Model QUALITY is judged by the retrieval
    benchmark (Recall@k on ~40 student questions), not by 3 sentences.
    Note: all-MiniLM-L6-v2 FAILS this case (picks "functions" on the shared
    word "function"); that is why the default is bge-small-en-v1.5.
    """
    import chromadb
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(config.EMBEDDING_MODEL)
    docs = [
        "A for loop repeats a block of code for each item in a list.",
        "A function is defined with def and can return a value.",
        "Recursion is when a function calls itself with a smaller input.",
    ]
    # In-memory client: nothing on disk (a PersistentClient keeps the sqlite
    # file locked on Windows and the temp dir could not be deleted).
    client = chromadb.EphemeralClient()
    col = client.create_collection("smoke")
    col.add(ids=["loops", "functions", "recursion"], documents=docs,
            embeddings=model.encode(docs).tolist())

    query = model.encode(["my function keeps calling itself"]).tolist()
    hit = col.query(query_embeddings=query, n_results=1)["ids"][0][0]
    assert hit == "recursion"
