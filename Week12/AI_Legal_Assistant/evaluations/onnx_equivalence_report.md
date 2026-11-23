# ONNX Runtime vs PyTorch: same models, smaller engine

The embedding model (`intfloat/multilingual-e5-small`) and the reranker (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) were run both ways: with PyTorch through sentence-transformers (Days 1-4) and with ONNX Runtime using the official `onnx/model.onnx` files from the same Hugging Face repositories (`src/indexing/onnx_models.py`). Each ran in its own process.

## Do they give the same results?

| Check | Result |
|---|---|
| Query vectors, 100 evaluation questions: cosine similarity PyTorch vs ONNX | min 1.000000, mean 1.000000 |
| Passage vectors, 300 indexed passages: PyTorch vs ONNX | min 1.000000, mean 1.000000 |
| ONNX passage vectors vs the vectors already stored in the index | min 1.000000, mean 1.000000 |
| `rerank` retrieval, same first passage | 100/100 questions |
| `rerank` retrieval, identical top-5 in the same order | 100/100 questions |
| `rerank` retrieval, top-5 overlap | 100.0% |

A cosine similarity of 1.0 means identical direction; differences in the 5th-6th decimal are rounding between the two engines and cannot change which passage ranks higher in practice.

## What it costs

| | PyTorch | ONNX Runtime |
|---|---|---|
| Process memory after loading models + index and answering 100 searches | 2541 MB | 1741 MB |
| of which models + index + searching | 2510 MB | 1710 MB |
| PyTorch loaded in the process | yes | no |
| Load time (index + models) | 38.3 s | 8.1 s |
| Search time per question (`rerank`, 30 passages reranked) | 11.50 s | 14.55 s |

Measured on the development laptop (CPU only). `MODEL_BACKEND=torch` switches back to PyTorch.

ONNX search is slower here because its memory arena is off (`ONNX_MEMORY_ARENA=1`: about as fast as PyTorch, but memory grew to 5.4 GB after 100 searches). The four Docker containers were running during this measurement, so both times are higher than on an idle machine.
