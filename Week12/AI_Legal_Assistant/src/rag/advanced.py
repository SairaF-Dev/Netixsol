"""
Day 2, Task 3: advanced retrieval, added one step at a time.

`AdvancedRetriever` switches each technique on or off; the comparison runs them
cumulatively (each configuration keeps everything before it):

  section       section-level chunks (one legal unit each), vector search only
  hybrid        + BM25 keyword search fused with vector search (reciprocal rank fusion)
  rerank        + a multilingual cross-encoder re-scores the top 30 candidates
  rewrite       + Gemini rewrites the question as an English legal search query (searched too)
  hyde          + Gemini writes a hypothetical answer passage; its embedding is searched too
  metadata      + Gemini extracts Act / section / court / year from the question; exact
                  section matches and court/year-filtered results are added to the candidates
  parent_child  + search ~80-word child chunks (precise match), return their parent unit

Every candidate list is fused with reciprocal rank fusion (RRF); the reranker,
when on, decides the final order.
"""

import json
import os
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from src.indexing.bm25_index import LegalBM25Index
from src.utils.logger import setup_logger

logger = setup_logger("advanced_retrieval")

INDEX_DIR = Path("data/indices")
RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
POOL = 30          # candidates per list / reranked
RRF_K = 60


# --------------------------------------------------------------------------- in-memory dense index
class MemoryDenseIndex:
    """Loads a SQLite vector store once and searches with one matrix product."""

    def __init__(self, path: Path):
        with sqlite3.connect(str(path)) as con:
            rows = con.execute("SELECT chunk_id, document_id, document_type, content, metadata_json, embedding "
                               "FROM legal_chunks").fetchall()
        self.rows = [{"chunk_id": r[0], "document_id": r[1], "document_type": r[2], "content": r[3],
                      "metadata": json.loads(r[4])} for r in rows]
        self.matrix = np.vstack([np.frombuffer(r[5], dtype=np.float32) for r in rows])
        self.by_id = {row["chunk_id"]: row for row in self.rows}

    def search(self, text: str, top_k: int = POOL, prefix: str = "query: ",
               metadata_filter: Optional[Dict] = None) -> List[Dict]:
        vector = _embedder().encode([prefix + text], normalize_embeddings=True)[0].astype(np.float32)
        scores = self.matrix @ vector
        order = np.argsort(-scores)
        out = []
        for i in order:
            row = self.rows[i]
            if metadata_filter and any(str(row["metadata"].get(k, "")).lower() != str(v).lower()
                                       for k, v in metadata_filter.items()):
                continue
            out.append(row)
            if len(out) == top_k:
                break
        return out


@lru_cache(maxsize=1)
def _embedder():
    from src.indexing.vector_store import _load_embedding_model
    return _load_embedding_model()


@lru_cache(maxsize=1)
def _reranker():
    from src.indexing.onnx_models import reranker      # ONNX Runtime by default (no PyTorch)
    return reranker()


def rrf(lists: List[List[Dict]], k: int = RRF_K) -> List[Dict]:
    scores: Dict[str, float] = {}
    lookup: Dict[str, Dict] = {}
    for results in lists:
        for rank, item in enumerate(results, start=1):
            lookup[item["chunk_id"]] = item
            scores[item["chunk_id"]] = scores.get(item["chunk_id"], 0.0) + 1.0 / (k + rank)
    return [lookup[cid] for cid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


# --------------------------------------------------------------------------- LLM helpers
class Rewrite(BaseModel):
    query: str = Field(description="English search query")


class Hypothetical(BaseModel):
    passage: str


class LegalFilters(BaseModel):
    act: Optional[str] = Field(None, description="Name of the Act/Ordinance/Constitution if the question names one")
    section: Optional[str] = Field(None, description='e.g. "Section 23", "Article 199", only if the question names it')
    court: Optional[str] = Field(None, description='"Supreme Court of Pakistan" or "Lahore High Court" if named')
    year: Optional[int] = Field(None, description="Year of a judgment if the question names one")


REWRITE_PROMPT = """Rewrite this legal question as a short English search query for a library of Pakistani
statutes (Contract Act, Penal Code, Constitution, CPC, Income Tax Ordinance ...) and Supreme Court /
Lahore High Court judgments. Translate Urdu or Roman Urdu. Keep any Act name and section or article
number exactly. Use the legal terms a statute or judgment would use. Do not answer the question.

Question: {question}"""

HYDE_PROMPT = """Write a short passage (60-120 words) in the style of a Pakistani statute provision or a
court judgment paragraph that would answer this question, in English. It is only used to search for
the real text, so write it as the source would read; do not invent section numbers.

Question: {question}"""

FILTER_PROMPT = """Extract search filters from this legal question. Fill a field only if the question
explicitly names it; otherwise leave it null. Use the full English name of an Act if one is named
(e.g. PPC -> Pakistan Penal Code, CPC -> Code of Civil Procedure). Translate Urdu if needed.

Question: {question}"""

_ACT_ALIASES = {"ppc": "penal code", "cpc": "civil procedure", "ito": "income tax ordinance",
                "ata": "anti-terrorism", "aml": "anti-money laundering", "mflo": "muslim family laws"}


def _norm_section(label: str) -> str:
    match = re.search(r"(section|article|s\.|art\.)?\s*(\d+)\s*-?\s*([A-Za-z]{0,2})\b", label, re.I)
    if not match:
        return ""
    kind = "Article" if (match.group(1) or "").lower().startswith("art") else "Section"
    return f"{kind} {match.group(2)}{match.group(3).upper()}"


# --------------------------------------------------------------------------- retriever
class AdvancedRetriever:
    def __init__(self, name: str, hybrid=False, rerank=False, rewrite=False, hyde=False,
                 metadata=False, parent_child=False):
        self.name = name
        self.hybrid, self.rerank, self.rewrite = hybrid, rerank, rewrite
        self.hyde, self.metadata, self.parent_child = hyde, metadata, parent_child
        if parent_child:
            from src.rag.parent_child_index import CHILD_BM25, CHILD_VECTORS, load_parents
            self.dense = MemoryDenseIndex(CHILD_VECTORS)
            self.bm25 = LegalBM25Index.load(CHILD_BM25) if hybrid else None
            self.parents = load_parents()
        else:
            if os.getenv("VECTOR_BACKEND", "sqlite").lower() == "qdrant":   # Docker: the Qdrant vector database
                from src.indexing.qdrant_store import QdrantDenseIndex
                self.dense = QdrantDenseIndex()
            else:                                                           # laptop: SQLite file, searched in memory
                self.dense = MemoryDenseIndex(INDEX_DIR / "vstore_legal.sqlite3")
            self.bm25 = LegalBM25Index.load(INDEX_DIR / "bm25_legal.pkl") if hybrid else None
        self.llm = None
        if rewrite or hyde or metadata:
            from src.llm.gemini_client import GeminiClient
            self.llm = GeminiClient()
        self.last_trace: Dict = {}

    # one query -> one fused candidate list (vector, plus BM25 when hybrid is on)
    def _search(self, text: str, metadata_filter: Optional[Dict] = None,
                allow: Optional[Callable[[Dict], bool]] = None) -> List[Dict]:
        # with an access filter, fetch 3x the pool and filter first, so a user whose top hits belong to
        # other matters still gets a full pool; without one, results are exactly as before
        k = POOL if allow is None else POOL * 3
        keep = (lambda hits: hits) if allow is None else (lambda hits: [h for h in hits if allow(h)])
        lists = [keep(self.dense.search(text, k, metadata_filter=metadata_filter))]
        if self.bm25 is not None:
            lists.append(keep([self.dense.by_id.get(hit["chunk_id"], hit)
                               for hit in self.bm25.search(text, top_k=k, metadata_filter=metadata_filter)]))
        return rrf(lists)[:POOL]

    def _metadata_candidates(self, question: str) -> List[List[Dict]]:
        filters = self.llm.generate_json(FILTER_PROMPT.format(question=question), LegalFilters, temperature=0.0)
        self.last_trace["filters"] = filters.model_dump()
        lists = []
        section = _norm_section(filters.section or "")
        act = (filters.act or "").lower()
        act = _ACT_ALIASES.get(act, act)
        if section:
            exact = [row for row in self.dense.rows
                     if row["metadata"].get("section") == section
                     and (not act or any(word in str(row["metadata"].get("act", "")).lower()
                                         for word in act.replace(",", " ").split() if len(word) > 3))]
            if exact and (act or len({r["document_id"] for r in exact}) <= 3):
                lists.append(exact[:POOL])
        if filters.court:
            court = "Supreme Court of Pakistan" if "supreme" in filters.court.lower() else (
                "Lahore High Court" if "lahore" in filters.court.lower() else None)
            if court:
                lists.append(self._search(question, metadata_filter={"court": court}))
        return lists

    def _to_parents(self, results: List[Dict]) -> List[Dict]:
        """Replace each child by its parent unit (deduplicated); long parents are cut to a
        ~450-word window around the matching child so the answer model sees the relevant part."""
        out, seen = [], set()
        for child in results:
            parent_id = child["metadata"].get("parent_id", child["chunk_id"])
            if parent_id in seen:
                continue
            seen.add(parent_id)
            parent = dict(self.parents.get(parent_id, child))
            words = parent["content"].split()
            if len(words) > 450:
                header, _, _ = parent["content"].partition("\n")
                piece = child["content"].split("\n", 1)[-1]
                start = parent["content"].find(piece[:80])
                position = len(parent["content"][:start].split()) if start >= 0 else 0
                begin = max(0, position - 150)
                parent["content"] = header + "\n" + " ".join(words[begin:begin + 450])
            parent["chunk_id"] = parent_id
            out.append(parent)
        return out

    def retrieve(self, question: str, top_k: int = 5, allow: Optional[Callable[[Dict], bool]] = None) -> List[Dict]:
        """allow: access-control filter (src/security/access.py). Applied to the candidate pool before
        reranking and the top-k cut, so passages of other client matters never reach the LLM."""
        self.last_trace = {}
        lists = [self._search(question, allow=allow)]
        queries = [question]
        if self.rewrite:
            rewritten = self.llm.generate_json(REWRITE_PROMPT.format(question=question), Rewrite, temperature=0.0).query
            self.last_trace["rewrite"] = rewritten
            queries.append(rewritten)
            lists.append(self._search(rewritten, allow=allow))
        if self.hyde:
            passage = self.llm.generate_json(HYDE_PROMPT.format(question=question), Hypothetical, temperature=0.0).passage
            self.last_trace["hyde"] = passage
            hyde_hits = self.dense.search(passage, POOL if allow is None else POOL * 3, prefix="passage: ")
            lists.append([h for h in hyde_hits if allow is None or allow(h)][:POOL])
        if self.metadata:
            lists.extend(self._metadata_candidates(question))
        candidates = [c for c in rrf(lists) if allow is None or allow(c)][:POOL]

        if self.rerank and candidates:
            model = _reranker()
            pairs = [(q, c["content"][:2000]) for q in queries for c in candidates]
            scores = np.asarray(model.predict(pairs, batch_size=32, show_progress_bar=False)).reshape(len(queries), -1)
            best = scores.max(axis=0)
            candidates = [candidates[i] for i in np.argsort(-best)]

        if self.parent_child:
            return self._to_parents(candidates)[:top_k]
        return candidates[:top_k]


CONFIGS = {
    "section": dict(),
    "hybrid": dict(hybrid=True),
    "rerank": dict(hybrid=True, rerank=True),
    "rewrite": dict(hybrid=True, rerank=True, rewrite=True),
    "hyde": dict(hybrid=True, rerank=True, rewrite=True, hyde=True),
    "metadata": dict(hybrid=True, rerank=True, rewrite=True, hyde=True, metadata=True),
    "parent_child": dict(hybrid=True, rerank=True, rewrite=True, hyde=True, metadata=True, parent_child=True),
}
DESCRIPTIONS = {
    "section": "1. Section-level chunks, vector search only",
    "hybrid": "2. + Hybrid search (BM25 + vector, RRF)",
    "rerank": "3. + Reranking (multilingual cross-encoder, top 30)",
    "rewrite": "4. + Query rewriting (Gemini, English legal query)",
    "hyde": "5. + HyDE (Gemini hypothetical answer passage)",
    "metadata": "6. + Metadata filters (Act/section/court from the question)",
    "parent_child": "7. + Parent-child retrieval (80-word children, parent unit returned)",
}
