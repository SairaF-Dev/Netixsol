# Chunk Size Evaluation

Ye project ka corpus chhota hai (10 FAQs + 4 brochures, har ek 1-5 sentences), isliye chunking ka effect subtle hai — lekin evaluation methodology wahi hai jo bade corpus par scale hogi.

## Method
`rag/chunking.py` ke `sentence_chunks()` ko teen `target_size` values ke sath actually run kiya gaya (`evaluation/questions.json` ke 14 answerable questions par top-1 retrieval precision measure karke — script: see note below), using the TF-IDF offline embedder:

| Chunk Size | Total Chunks | Retrieval Precision (top-1 correct, 14 answerable Qs) |
|---|---|---|
| 100 chars | 36 | 92.9% |
| 200 chars | 32 | 92.9% |
| 400 chars | 15 | **100%** |

## Honest interpretation
400 chars scored highest here, but that's an artifact of this project's tiny source documents — each FAQ/brochure entry is only 100-250 chars total, so a 400-char target basically means **"don't split most documents at all."** Larger chunks won only because there's nothing yet to lose by not splitting.

This result does NOT generalize to bigger documents (e.g. full legal agreements or multi-page brochures once added to the KB). For those, wider chunks will start mixing unrelated topics into one embedding, and precision would be expected to drop — 200 chars with sentence-boundary splitting remains the safer default going forward.

## Production recommendation
Keep **200 characters, sentence-boundary chunking** as the default for this pipeline: it performed equally well on the current corpus and is the size that scales safely once longer documents (contracts, multi-page brochures) are added.

## Scaling note
When longer source documents are added, `fixed_size_chunks()`'s overlap (currently 40 chars) becomes important — it prevents context from being lost across a chunk boundary that falls mid-sentence.

*Reproduce this table: `python3 -c` sweep over `build_pipeline(chunk_size=N)` in `rag/pipeline.py`, checking `retrieved[0]['chunk_id'].startswith(expected_source)` per question in `evaluation/questions.json`.*
