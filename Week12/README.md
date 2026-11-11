# Khan & Associates Legal Document Pipeline

Week 12 capstone prototype for collecting, parsing, structuring, chunking, and
searching legal documents. The repository includes reproducible instructional
fixtures and some downloaded source PDFs. **It is not a production legal corpus.**

## Current corpus status

| Inventory type | Count | What the files actually are |
|---|---:|---|
| Statute | 13 | 12 generated instructional examples and 1 downloaded National Assembly PDF |
| Judgment | 200 | Generated synthetic examples, not court decisions |
| Contract | 80 | 30 downloaded CUAD PDFs, 30 generated CUAD-inspired examples, 20 synthetic examples |
| Scanned/Urdu | 30 | Generated Urdu/bilingual fixtures; image-only PDFs after running `--collect`, not archival scans |

`inventory.csv` describes files, not necessarily distinct real-world legal matters.
The inventory is rebuilt by `--collect`; downloaded records with `REAL_` IDs are
preserved if their files exist. The downloader currently fetches CUAD contracts
and one official statute; it does not collect 200 Pakistani judgments.

## Implemented pipeline

- PyMuPDF detects pages with or without embedded text and extracts text, blocks,
  and tables from digital PDFs. `LegalPDFParser` accepts an OCR engine to process
  image-only pages; without one it marks the page `needs_ocr` instead of silently
  treating an empty text layer as a successful extraction.
- Pydantic structures, legal-aware section and parent-child chunkers, BM25
  retrieval, and a SQLite-backed dense vector index using the multilingual
  `intfloat/multilingual-e5-small` embedding model.
- The Urdu OCR benchmark renders each page to an image and compares Tesseract
  (`urd+eng`) with EasyOCR using CER, WER, and measured inference latency. OCR
  evaluation now stops with a clear error if tools or language data are missing;
  it does not manufacture OCR output from the reference text.

The chunking report measures chunk counts and whitespace word-count distributions
on 12 generated fixtures. It does not measure retrieval relevance or a numeric
boundary-preservation rate.

## Setup

From PowerShell:

```powershell
cd D:\Netixsol\Week12
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The first vector-index build may download the multilingual embedding model.
OCR evaluation additionally requires:

- Tesseract installed and available on `PATH`, with both `urd` and `eng` traineddata.
- EasyOCR installed in the virtual environment: `.\.venv\Scripts\python.exe -m pip install easyocr`

## Commands

```powershell
# Rebuild generated fixtures and inventory; preserve downloaded REAL_* records
.\.venv\Scripts\python.exe main.py --collect

# Download 30 CUAD PDFs and one official Pakistani statute
.\.venv\Scripts\python.exe main.py --download-external

# Run the real OCR comparison (requires the tools above)
.\.venv\Scripts\python.exe main.py --ocr-eval

# Compare chunking structure and word-count distributions
.\.venv\Scripts\python.exe main.py --chunk-eval

# Build BM25 and SQLite-backed dense vector indices, then query
.\.venv\Scripts\python.exe main.py --index
.\.venv\Scripts\python.exe main.py --search "qatl-i-amd section 302" --top-k 3

# Run collection, OCR, chunking, indexing, and a sample search
.\.venv\Scripts\python.exe main.py --run-all

# Run tests
.\.venv\Scripts\python.exe -m pytest -q
```

`--run-all` requires the OCR prerequisites; without them it stops at OCR and
does not claim the benchmark completed.

## Limitations and next work

1. Replace generated judgments and Urdu fixtures with documented, authorized
   sources; verify their provenance and page counts before treating them as corpus data.
2. Install both OCR engines and run the benchmark on real scanned Urdu pages.
   The committed OCR report previously contained simulated results and is not
   evidence; see the current report status.
3. Validate extraction quality against manually reviewed legal documents and
   evaluate retrieval with a labeled query/relevance set before production use.
4. Confirm the downloaded documents' provenance, licensing, and integrity.
5. Propagate source page numbers into extracted legal structures and index metadata.

This prototype is for engineering evaluation, not legal advice.
