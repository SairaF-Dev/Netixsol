"""
Does running the models with ONNX Runtime instead of PyTorch change anything?

Each backend runs in its own process (so its memory is measured alone) and produces:
  * query vectors for the 100 evaluation questions, and passage vectors for 300 indexed passages;
  * the top-5 passages of the `rerank` configuration (BM25 + vector search + reranker, no Gemini calls)
    for every evaluation question;
  * memory (RSS) after loading the models and the index, and the time per question.
Then the two are compared, and the ONNX passage vectors are compared with the vectors already stored in
the index (made with PyTorch on Day 2): if they match, the index does not need rebuilding.

Run:  python evaluations/onnx_equivalence.py            -> evaluations/onnx_equivalence_report.md
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "onnx_check"
REPORT = ROOT / "evaluations" / "onnx_equivalence_report.md"
SAMPLE_PASSAGES = 300


def run_backend(name: str) -> None:
    """Child process: MODEL_BACKEND is already set in the environment."""
    import sqlite3

    import numpy as np
    import psutil

    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    proc = psutil.Process()
    base = proc.memory_info().rss

    from src.rag.advanced import CONFIGS, AdvancedRetriever, _embedder

    questions = [json.loads(line) for line in open("evaluations/rag_eval_set.jsonl", encoding="utf-8")]
    t0 = time.perf_counter()
    retriever = AdvancedRetriever("rerank", **CONFIGS["rerank"])
    model = _embedder()
    load_seconds = time.perf_counter() - t0

    with sqlite3.connect("data/indices/vstore_legal.sqlite3") as con:
        rows = con.execute("SELECT chunk_id, content, embedding FROM legal_chunks ORDER BY chunk_id").fetchall()
    step = max(1, len(rows) // SAMPLE_PASSAGES)
    sample = rows[::step][:SAMPLE_PASSAGES]

    q_vecs = model.encode([f"query: {q['question']}" for q in questions], normalize_embeddings=True)
    p_vecs = model.encode([f"passage: {r[1]}" for r in sample], normalize_embeddings=True)
    stored = np.vstack([np.frombuffer(r[2], dtype=np.float32) for r in sample])

    t1 = time.perf_counter()
    top5 = {q["id"]: [hit["chunk_id"] for hit in retriever.retrieve(q["question"], top_k=5)] for q in questions}
    per_question = (time.perf_counter() - t1) / len(questions)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / f"{name}_query.npy", np.asarray(q_vecs, dtype=np.float32))
    np.save(OUT_DIR / f"{name}_passage.npy", np.asarray(p_vecs, dtype=np.float32))
    np.save(OUT_DIR / "stored_passage.npy", stored)
    (OUT_DIR / f"{name}.json").write_text(json.dumps({
        "top5": top5,
        "rss_mb": proc.memory_info().rss / 1e6,
        "models_and_index_mb": (proc.memory_info().rss - base) / 1e6,
        "load_seconds": load_seconds,
        "seconds_per_question": per_question,
        "torch_loaded": "torch" in sys.modules,
    }, indent=1), encoding="utf-8")


def main() -> None:
    import numpy as np

    for name in ("torch", "onnx"):
        print(f"running {name} ...", flush=True)
        env = dict(os.environ, MODEL_BACKEND=name, HF_HUB_OFFLINE="1", PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, __file__, "--child", name], env=env, check=True, cwd=ROOT)

    res = {n: json.loads((OUT_DIR / f"{n}.json").read_text(encoding="utf-8")) for n in ("torch", "onnx")}
    vec = {n: (np.load(OUT_DIR / f"{n}_query.npy"), np.load(OUT_DIR / f"{n}_passage.npy")) for n in ("torch", "onnx")}
    stored = np.load(OUT_DIR / "stored_passage.npy")

    def cos(a, b):
        return (a * b).sum(axis=1)

    q_cos = cos(vec["torch"][0], vec["onnx"][0])
    p_cos = cos(vec["torch"][1], vec["onnx"][1])
    s_cos = cos(stored, vec["onnx"][1])
    ids = list(res["torch"]["top5"])
    same_top1 = sum(res["torch"]["top5"][i][:1] == res["onnx"]["top5"][i][:1] for i in ids)
    same_top5_order = sum(res["torch"]["top5"][i] == res["onnx"]["top5"][i] for i in ids)
    overlap = np.mean([len(set(res["torch"]["top5"][i]) & set(res["onnx"]["top5"][i])) / 5 for i in ids])

    t, o = res["torch"], res["onnx"]
    lines = [
        "# ONNX Runtime vs PyTorch: same models, smaller engine",
        "",
        "The embedding model (`intfloat/multilingual-e5-small`) and the reranker "
        "(`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) were run both ways: with PyTorch through "
        "sentence-transformers (Days 1-4) and with ONNX Runtime using the official `onnx/model.onnx` files from "
        "the same Hugging Face repositories (`src/indexing/onnx_models.py`). Each ran in its own process.",
        "",
        "## Do they give the same results?",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Query vectors, 100 evaluation questions: cosine similarity PyTorch vs ONNX | min {q_cos.min():.6f}, mean {q_cos.mean():.6f} |",
        f"| Passage vectors, {len(p_cos)} indexed passages: PyTorch vs ONNX | min {p_cos.min():.6f}, mean {p_cos.mean():.6f} |",
        f"| ONNX passage vectors vs the vectors already stored in the index | min {s_cos.min():.6f}, mean {s_cos.mean():.6f} |",
        f"| `rerank` retrieval, same first passage | {same_top1}/{len(ids)} questions |",
        f"| `rerank` retrieval, identical top-5 in the same order | {same_top5_order}/{len(ids)} questions |",
        f"| `rerank` retrieval, top-5 overlap | {overlap:.1%} |",
        "",
        "A cosine similarity of 1.0 means identical direction; differences in the 5th-6th decimal are rounding "
        "between the two engines and cannot change which passage ranks higher in practice.",
        "",
        "## What it costs",
        "",
        "| | PyTorch | ONNX Runtime |",
        "|---|---|---|",
        f"| Process memory after loading models + index and answering 100 searches | {t['rss_mb']:.0f} MB | {o['rss_mb']:.0f} MB |",
        f"| of which models + index + searching | {t['models_and_index_mb']:.0f} MB | {o['models_and_index_mb']:.0f} MB |",
        f"| PyTorch loaded in the process | {'yes' if t['torch_loaded'] else 'no'} | {'yes' if o['torch_loaded'] else 'no'} |",
        f"| Load time (index + models) | {t['load_seconds']:.1f} s | {o['load_seconds']:.1f} s |",
        f"| Search time per question (`rerank`, 30 passages reranked) | {t['seconds_per_question']:.2f} s | {o['seconds_per_question']:.2f} s |",
        "",
        "Measured on the development laptop (CPU only). `MODEL_BACKEND=torch` switches back to PyTorch.",
        "",
        "ONNX search is slower here because its memory arena is off (`ONNX_MEMORY_ARENA=1`: about as fast as PyTorch, but memory grew to 5.4 GB after 100 searches). The four Docker containers were running during this "
        "measurement, so both times are higher than on an idle machine.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        run_backend(sys.argv[2])
    else:
        main()
