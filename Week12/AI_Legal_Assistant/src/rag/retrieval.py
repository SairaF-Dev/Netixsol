"""
Retrievers for the Day 2 RAG comparison and the rule that decides whether a
retrieved chunk "is" the gold source.

Every retriever returns a list of result dicts (chunk_id, document_id,
document_type, content, metadata), best first, like the Day 1 search engines.
Task 3 adds more retrievers (hybrid, reranking, query rewriting, ...) here.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from src.indexing.vector_store import DenseVectorStore

INDEX_DIR = Path("data/indices")


class NaiveDenseRetriever:
    """Naive baseline: fixed-size 200-word chunks, vector search only, no metadata use."""

    name = "naive"

    def __init__(self, index_path: Path = INDEX_DIR / "vstore_naive_fixed.sqlite3"):
        self.store = DenseVectorStore.load(index_path)

    def retrieve(self, question: str, top_k: int = 5) -> List[Dict]:
        return self.store.search(question, top_k=top_k)


# --------------------------------------------------------------------------- gold matching
def _norm(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _para_numbers(label: str) -> List[str]:
    """'para 5' -> ['5']; 'paras 3-6' -> ['3','4','5','6']; anything else -> []."""
    match = re.fullmatch(r"paras? (\d+)(?:-(\d+))?", label.strip())
    if not match:
        return []
    first, last = int(match.group(1)), int(match.group(2) or match.group(1))
    return [str(n) for n in range(first, last + 1)]


def same_document(result: Dict, gold: Dict) -> bool:
    if result["document_id"] == gold["document_id"]:
        return True
    matter = gold.get("matter_id")
    return bool(matter) and result.get("metadata", {}).get("matter_id") == matter


def hits_gold(result: Dict, gold: Dict, quote: str = "") -> bool:
    """True if the chunk is from the gold document (or the same legal matter) and holds
    the gold unit: its section / paragraph label covers it, or it contains the gold quote."""
    if not same_document(result, gold):
        return False
    meta = result.get("metadata", {})
    labels = list(meta.get("covers", []))
    if meta.get("section"):
        labels.append(str(meta["section"]))
    if gold.get("section") and gold["section"] in labels:
        return True
    if gold.get("paragraph") and result["document_id"] == gold["document_id"]:
        if any(gold["paragraph"] in _para_numbers(label) for label in labels):
            return True
    return bool(quote) and _norm(quote).strip(" .;,\"'") in _norm(result["content"])


def first_hit_rank(results: List[Dict], item: Dict) -> Optional[int]:
    """1-based rank of the first result that hits any gold source, or None."""
    for rank, result in enumerate(results, start=1):
        if any(hits_gold(result, gold, item.get("quote", "")) for gold in item["gold"]):
            return rank
    return None
