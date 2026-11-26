"""Score retrieval systems on the benchmark (retrieval_benchmark.yaml).

Metric unit = lesson: a question is answered if a chunk from a correct lesson is retrieved.
  hit@1  correct lesson ranked first (what the tutor would quote)
  hit@5  correct lesson in the top 5 (what the tutor reads)
  mrr    mean of 1/rank of the first correct lesson (0 if not in the top 10)

Run:  python -m ilm.content.retrieval_eval                    (dev split)
      python -m ilm.content.retrieval_eval --split holdout --final   (ONCE, at the end)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from ilm import config

BENCHMARK = Path(__file__).with_name("retrieval_benchmark.yaml")
TOP_K = 10


def load_questions(split: str) -> list[dict]:
    qs = yaml.safe_load(BENCHMARK.read_text(encoding="utf-8"))["questions"]
    return [q for q in qs if split == "all" or q["split"] == split]


# ------------------------------------------------------------------ systems ----
def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


class BM25System:
    """Classic keyword search: scores chunks by shared words, weighting rare words more.
    The simple baseline every 'smart' method must beat."""
    name = "bm25"

    def __init__(self):
        from rank_bm25 import BM25Okapi
        from ilm.content.index import collect_chunks
        self.chunks, _ = collect_chunks()
        self.bm25 = BM25Okapi([_tokens(c.text) for c in self.chunks])

    def lessons(self, question: str) -> list[str]:
        scores = self.bm25.get_scores(_tokens(question))
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:TOP_K]
        return [self.chunks[i].lesson_id for i in top]


class VectorSystem:
    """Embedding search over the Chroma index."""
    def __init__(self, model_name: str | None = None, collection: str | None = None):
        from ilm.content import index
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.collection = collection or index.COLLECTION
        self.name = f"vector:{self.model_name.split('/')[-1]}"
        self._search = index.search

    def lessons(self, question: str) -> list[str]:
        hits = self._search(question, k=TOP_K, model_name=self.model_name,
                            collection=self.collection)
        return [h["lesson_id"] for h in hits]


# ------------------------------------------------------------------ scoring ----
def first_hit_rank(retrieved: list[str], relevant: list[str]) -> int | None:
    for rank, lesson in enumerate(retrieved, start=1):
        if lesson in relevant:
            return rank
    return None


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks)
    return {"n": n,
            "hit@1": round(sum(r == 1 for r in ranks if r) / n, 3),
            "hit@5": round(sum(r <= 5 for r in ranks if r) / n, 3),
            "mrr": round(sum(1 / r for r in ranks if r) / n, 3)}


def evaluate(system, questions: list[dict]) -> dict:
    rows = []
    for q in questions:
        retrieved = system.lessons(q["q"])
        rows.append({**q, "rank": first_hit_rank(retrieved, q["lessons"]), "top3": retrieved[:3]})
    by_type = {t: metrics([r["rank"] for r in rows if r["type"] == t]) for t in ("term", "symptom")}
    return {"system": system.name, "overall": metrics([r["rank"] for r in rows]),
            "by_type": by_type, "rows": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", default="dev", choices=["dev", "holdout"])
    p.add_argument("--final", action="store_true", help="required to score the holdout set")
    p.add_argument("--systems", nargs="+", default=["bm25", "vector"])
    a = p.parse_args()
    if a.split == "holdout" and not a.final:
        raise SystemExit("Holdout is the final exam: score it once, after all tuning, with --final.")

    questions = load_questions(a.split)
    systems = {"bm25": BM25System, "vector": VectorSystem}
    results = [evaluate(systems[s](), questions) for s in a.systems]

    for res in results:
        o, t, s = res["overall"], res["by_type"]["term"], res["by_type"]["symptom"]
        print(f"\n{res['system']:28s} n={o['n']}  hit@1 {o['hit@1']:.2f}  hit@5 {o['hit@5']:.2f}  "
              f"mrr {o['mrr']:.2f}   | term mrr {t['mrr']:.2f}  symptom mrr {s['mrr']:.2f}")
        for r in res["rows"]:
            mark = "ok " if r["rank"] == 1 else ("~  " if r["rank"] else "MISS")
            print(f"   {mark} rank={str(r['rank'] or '-'):>2} [{r['type'][:4]}] {r['q'][:62]:62s} -> {r['top3'][0]}")

    out = config.REPORTS_DIR / "retrieval" / f"{a.split}_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
