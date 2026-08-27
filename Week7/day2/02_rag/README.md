# RAG Pipeline

## Pipeline

Documents → Loader → Chunker → Embeddings → ChromaDB → Retriever → LLM

The implementation is intentionally modular so the embedding provider,
vector store and LLM can be changed without rewriting the entire
pipeline.

## Dependencies

Install:

```bash
pip install -r requirements.txt
```

Optional API keys depend on the embedding/LLM providers selected.

The project includes a lightweight deterministic fallback embedding
implementation for local pipeline testing when external embeddings are
not configured. It is not intended as the final production embedding
model.

## Chunk evaluation

Run:

```bash
python chunk_evaluation.py
```

This compares chunk sizes and reports basic retrieval-hit behaviour
against the Day 2 evaluation questions.
