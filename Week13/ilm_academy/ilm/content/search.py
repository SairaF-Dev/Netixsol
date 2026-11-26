"""Course search used by the tutor and scored by the retrieval benchmark.

  1. rewrite   an LLM turns the student's words into course terms ("my function keeps
               calling itself" -> "python recursion explained"); the original is kept too
  2. hybrid    BM25 (exact words) and embeddings (meaning) each rank the chunks; Reciprocal
               Rank Fusion merges the two rankings by position only

Chosen on the dev questions, confirmed once on holdout: MRR 0.96, right lesson in the top 5
for 16/16 (reports/retrieval/holdout_results.json).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from ilm import config

RRF_K = 60          # the constant from Cormack et al. (2009); not tuned
POOL = 50           # chunks taken from each ranking before fusing

REWRITE_PROMPT = """A beginner in an introductory Python course asked the question below.
Rewrite it as a short search query using the standard Python terms a lecture would use
for the concept behind it (for example name the language feature, error or technique).
Reply with the query only, at most 15 words.

Question: {q}"""


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[str]:
    """Reciprocal Rank Fusion: an item's score is the sum of 1 / (k + rank) over rankings."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for r, item in enumerate(ranking, start=1):
            fused[item] = fused.get(item, 0.0) + 1 / (k + r)
    return sorted(fused, key=lambda c: -fused[c])


class HybridSearch:
    def __init__(self):
        from rank_bm25 import BM25Okapi
        from ilm.content import index
        self.chunks, _ = index.collect_chunks()
        self.by_id = {c.id: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokens(c.text) for c in self.chunks])
        self._vector = index.search

    def ranked_ids(self, query: str) -> list[str]:
        scores = self.bm25.get_scores(tokens(query))
        kw = [self.chunks[i].id for i in sorted(range(len(scores)), key=lambda i: -scores[i])[:POOL]]
        vec = [h["id"] for h in self._vector(query, k=POOL)]
        return rrf([kw, vec])

    def top_chunks(self, query: str, k: int = 5) -> list:
        return [self.by_id[c] for c in self.ranked_ids(query)[:k]]


class RewriteSearch(HybridSearch):
    """Hybrid search on (question + LLM rewrite). `cache` (a JSON file) makes benchmark
    reruns free and reproducible; the tutor uses an in-memory cache instead."""

    def __init__(self, ask: Callable[..., str] | None = None, cache: Path | None = None):
        super().__init__()
        if ask is None:
            from ilm import llm
            ask = llm.ask
        self._ask = ask
        self.cache_file = cache
        self.cache = json.loads(cache.read_text(encoding="utf-8")) if cache and cache.exists() else {}

    def rewrite(self, question: str) -> str:
        if question not in self.cache:
            self.cache[question] = self._ask(REWRITE_PROMPT.format(q=question), temperature=0).strip()
            if self.cache_file:
                self.cache_file.write_text(json.dumps(self.cache, indent=1, ensure_ascii=False), encoding="utf-8")
        return self.cache[question]

    def ranked_ids(self, query: str) -> list[str]:
        return super().ranked_ids(f"{query} {self.rewrite(query)}")
