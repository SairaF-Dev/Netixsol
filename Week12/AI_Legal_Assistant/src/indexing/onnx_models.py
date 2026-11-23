"""
The two local models - the embedding model (multilingual-e5-small) and the reranker (mmarco cross-encoder) -
run with ONNX Runtime instead of PyTorch.

Why: PyTorch is a training framework; loading it costs about 1 GB of memory and 2 GB of disk before any model
is loaded. ONNX Runtime only runs already-trained models. The ONNX files are the official exports published
in the same Hugging Face repositories, so the numbers match the PyTorch ones (checked by
evaluations/onnx_equivalence.py) and the existing search index stays valid.

Both classes copy the call style of sentence-transformers (`encode`, `predict`), so callers do not change.

Settings:
  MODEL_BACKEND = onnx (default) | torch   - torch keeps the old sentence-transformers path (needs torch)
  ONNX_EMBED_FILE / ONNX_RERANK_FILE        - which file in the repo's onnx/ folder (default model.onnx)
"""

import os
from functools import lru_cache
from typing import Iterable, List, Sequence, Tuple

import numpy as np

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MAX_LENGTH = 512


def backend() -> str:
    return os.getenv("MODEL_BACKEND", "onnx").strip().lower()


def _files(repo: str, onnx_file: str) -> Tuple[str, str]:
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo, f"onnx/{onnx_file}"), hf_hub_download(repo, "tokenizer.json")


def _session(path: str):
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    # Every question has a different length, so the input shape changes on each call. With the memory arena on,
    # ONNX Runtime keeps a reserved block for each shape it has seen and memory only grows (5.4 GB after 100
    # searches, measured); off, memory is returned after each call. ONNX_MEMORY_ARENA=1 turns it back on.
    if os.getenv("ONNX_MEMORY_ARENA", "0") != "1":
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
    threads = int(os.getenv("ONNX_THREADS", "0"))      # 0 = ONNX Runtime picks (one per core)
    if threads:
        options.intra_op_num_threads = threads
    return ort.InferenceSession(path, options, providers=["CPUExecutionProvider"])


@lru_cache(maxsize=None)
def _tokenizer(path: str):
    """One instance per file. Each takes ~280 MB in memory (a 250,000-word vocabulary for ~100 languages)."""
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(path)
    tok.enable_truncation(MAX_LENGTH)                  # longest_first for pairs, like transformers' truncation=True
    tok.no_padding()                                   # padding is done per batch below
    return tok


def _batches(n: int, size: int, lengths: Sequence[int]) -> Iterable[List[int]]:
    """Indices in batches of similar length (less padding = faster), longest first like sentence-transformers."""
    order = sorted(range(n), key=lambda i: -lengths[i])
    for start in range(0, n, size):
        yield order[start:start + size]


def _pad(encodings, pad_id: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    width = max(len(e.ids) for e in encodings)
    ids = np.full((len(encodings), width), pad_id, dtype=np.int64)
    mask = np.zeros((len(encodings), width), dtype=np.int64)
    types = np.zeros((len(encodings), width), dtype=np.int64)
    for row, e in enumerate(encodings):
        ids[row, :len(e.ids)] = e.ids
        mask[row, :len(e.ids)] = 1
        types[row, :len(e.ids)] = e.type_ids
    return ids, mask, types


class OnnxEmbedder:
    """multilingual-e5-small: mean of the token vectors (padding excluded), then unit length."""

    def __init__(self, repo: str = EMBEDDING_MODEL, onnx_file: str | None = None):
        model_path, tok_path = _files(repo, onnx_file or os.getenv("ONNX_EMBED_FILE", "model.onnx"))
        self.session = _session(model_path)
        self.tokenizer = _tokenizer(tok_path)
        self.pad_id = self.tokenizer.token_to_id("<pad>") or 1
        self.inputs = {i.name for i in self.session.get_inputs()}

    def get_sentence_embedding_dimension(self) -> int:
        return 384

    def encode(self, texts, batch_size: int = 32, normalize_embeddings: bool = True, convert_to_numpy: bool = True,
               show_progress_bar: bool = False, **_ignored) -> np.ndarray:
        single = isinstance(texts, str)
        texts = [texts] if single else list(texts)
        out = np.zeros((len(texts), 384), dtype=np.float32)
        if not texts:
            return out
        encodings = self.tokenizer.encode_batch(texts)
        for idx in _batches(len(texts), batch_size, [len(e.ids) for e in encodings]):
            ids, mask, types = _pad([encodings[i] for i in idx], self.pad_id)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = types
            hidden = self.session.run(["last_hidden_state"], feed)[0]
            weights = mask[..., None].astype(np.float32)
            vectors = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
            if normalize_embeddings:
                vectors /= np.clip(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12, None)
            out[idx] = vectors
        return out[0] if single else out


class OnnxReranker:
    """mmarco cross-encoder: reads (question, passage) together, one relevance score per pair (sigmoid, 0..1)."""

    def __init__(self, repo: str = RERANKER_MODEL, onnx_file: str | None = None):
        model_path, tok_path = _files(repo, onnx_file or os.getenv("ONNX_RERANK_FILE", "model.onnx"))
        self.session = _session(model_path)
        # Both models use the same XLM-RoBERTa vocabulary. Their tokenizer.json files differ only in how spaces are
        # handled (one collapses runs of spaces, the other splits on them) and give the same token ids on all
        # 11,232 indexed passages and the 100 evaluation questions, so the reranker reuses the embedding model's
        # tokenizer instead of holding a second ~280 MB copy. ONNX_SHARED_TOKENIZER=0 loads its own.
        if os.getenv("ONNX_SHARED_TOKENIZER", "1") == "1":
            tok_path = _files(EMBEDDING_MODEL, os.getenv("ONNX_EMBED_FILE", "model.onnx"))[1]
        self.tokenizer = _tokenizer(tok_path)
        self.pad_id = self.tokenizer.token_to_id("<pad>") or 1
        self.inputs = {i.name for i in self.session.get_inputs()}

    def predict(self, pairs, batch_size: int = 32, show_progress_bar: bool = False, **_ignored) -> np.ndarray:
        pairs = [(str(q), str(p)) for q, p in pairs]
        scores = np.zeros(len(pairs), dtype=np.float32)
        if not pairs:
            return scores
        encodings = self.tokenizer.encode_batch(pairs)
        for idx in _batches(len(pairs), batch_size, [len(e.ids) for e in encodings]):
            ids, mask, types = _pad([encodings[i] for i in idx], self.pad_id)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = types
            logits = self.session.run(["logits"], feed)[0][:, 0]
            scores[idx] = 1.0 / (1.0 + np.exp(-logits))
        return scores


@lru_cache(maxsize=1)
def embedder():
    """The embedding model for this process (ONNX by default; MODEL_BACKEND=torch for sentence-transformers)."""
    if backend() == "torch":
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    return OnnxEmbedder()


@lru_cache(maxsize=1)
def reranker():
    if backend() == "torch":
        from sentence_transformers import CrossEncoder
        return CrossEncoder(RERANKER_MODEL, max_length=MAX_LENGTH)
    return OnnxReranker()
