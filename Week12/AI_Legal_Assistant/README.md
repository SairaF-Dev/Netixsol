# Khan & Associates Legal Document Pipeline

Week 12 capstone prototype for collecting, parsing, structuring, chunking, and
searching legal documents. The inventory lists real legal documents plus the 20
synthetic contracts the brief asks for. **It is not a production legal corpus.**

## Current corpus status

| Inventory type | Count | What the files actually are |
|---|---:|---|
| Statute | 13 | 12 official Pakistan Code law PDFs (`data/raw/pakistani_laws`, incl. Pakistan Penal Code, Contract Act, CPC, Income Tax Ordinance) and the Constitution as amended up to the 27th Amendment (Ministry of Law and Justice, 14th edition, 2025; `REAL_STAT_001`) |
| Judgment | 225 | 175 Supreme Court of Pakistan and 50 Lahore High Court judgment PDFs (`data/scp_judgments_pdfs`); 22 are scanned or partly scanned and need OCR |
| Contract | 73 | 53 real CUAD contracts (30 downloaded `REAL_CUAD` + one from each of the 23 other CUAD categories, copied from CUAD v1 `full_contract_pdf` into `data/contracts/cuad` and listed in `cuad_real_manifest.csv`, so all 25 categories are covered) and 20 synthetic Pakistani contracts |
| Scanned/Urdu | 50 | 40 Pakistan Code Urdu laws (1,602 pages; 1 image-only scan, 39 with an unusable InPage-style text layer; all pages OCR'd with EasyOCR, text in `data/ocr_text/`) and 10 single-page OCR benchmark exports taken from 8 of those laws |

`inventory.csv` describes files, not necessarily distinct real-world legal matters.
The inventory is rebuilt by `--collect`, which lists the PDFs in the folders above
(it does not download them); downloaded records with `REAL_` IDs are preserved if
their files exist. Some judgments are several documents of one case (for example
three files for C.A. 333/2024); extraction gives them the same `matter_id`.

`data/source_catalog.csv` lists 25 Supreme Court judgments, 50 Lahore High Court
judgments, and 51 Urdu-law PDF links from official court and Ministry listings.
Where a judgment or Urdu law in the corpus matches a catalog entry, its title and
source URL come from the catalog. Reuse permissions are unverified, and the Urdu
laws page warns that its contents are under review.

The earlier generated statutes, judgments and CUAD-inspired contracts have been
deleted. Extraction, chunking and indexing all read the documents listed in
`inventory.csv`, including the 40 OCR'd Urdu laws (the 10 benchmark pages are
excerpts of those laws and are not indexed separately).

## Implemented pipeline

- PyMuPDF detects pages with or without embedded text and extracts text, blocks,
  and tables from digital PDFs. `LegalPDFParser` accepts an OCR engine to process
  image-only pages; without one it marks the page `needs_ocr` instead of silently
  treating an empty text layer as a successful extraction.
- Pages whose text layer is mostly Private Use Area codes (legacy InPage-style Urdu
  fonts: the page renders as Urdu but extracts as glyph codes) are classified
  `garbled_text_layer`, their text is discarded, and they are routed to OCR like scans.
  This applies to 39 of the 40 Pakistan Code Urdu law PDFs.
- Structure extraction (`src/extraction`, Task 3) works on the real PDF layouts and
  keeps the page where each unit starts:
  - statutes: Act → Chapter/Part/Order → Section / Article / Order-Rule / schedule
    item. Tables of contents are dropped and section numbers must increase, which
    filters out numbered lists inside sections;
  - judgments: court, bench or author judge, case number, parties, hearing date,
    case-law citations (PLD/SCMR/CLC/YLR…), statutes cited, numbered paragraphs,
    holding (last paragraph stating the outcome) and a `matter_id`;
  - contracts: title, type, parties, effective date, governing law, arbitration
    clause and top-level clauses.

  - Urdu laws: one unit per OCR'd page, labelled with the official Urdu title,
    year and page number (see "Urdu laws (OCR)" below for why not per section).

  Fields that cannot be found stay empty; nothing is filled with defaults. The 22
  scanned judgments are OCR'd with Tesseract (`eng`). Output: one JSON per document
  in `data/structured/`.
- Section-level chunks (one legal unit each; units over 350 words are split into
  labelled parts), parent-child chunks (whole units as parents, ~80-word children)
  and fixed-size chunks. Chunks carry act / section / court / year / page / matter_id metadata.
- BM25 and a SQLite-backed dense vector index (multilingual `intfloat/multilingual-e5-small`)
  over the section-level chunks, combined with reciprocal rank fusion and exact metadata filters.
- The Urdu OCR benchmark renders each page to an image and compares Tesseract
  (`urd+eng`) with EasyOCR using CER, WER, and measured inference latency. OCR
  evaluation now stops with a clear error if tools or language data are missing;
  it does not manufacture OCR output from the reference text.

## Urdu OCR benchmark

Ten pages from official Pakistan Code Urdu laws (eight laws; Nastaleeq type, a
watermark, one table page, two pages of the image-only Constitution scan) were
exported as image-only PDFs to `data/scanned_urdu/benchmark_cer/`
(`evaluations/export_urdu_benchmark_pages.py`; sources in `manifest.csv`). The
ground truth was drafted by Claude from the page images (not one of the compared
engines) and corrected line by line by hand; page numbers and the watermark are
excluded. The earlier benchmark of generated pages has been removed.

| OCR engine | Average CER | Average WER | Average latency |
|---|---:|---:|---:|
| Tesseract (`urd+eng`) | 70.3% | 96.7% | 0.7 s |
| EasyOCR (`ur+en`) | **32.9%** | 86.9% | 17.8 s |

EasyOCR had the lower CER on all 10 pages; Tesseract was about 25x faster but
largely failed on Nastaleeq and on the table page (98% CER). WER is high for both
because OCR often merges or splits Urdu words, so CER is the more informative metric.
Ten pages is a small sample. Full per-page results: `evaluations/ocr_comparison_report.md`.

## Constitution edition

`REAL_STAT_001` was originally the National Assembly PDF "as modified up to the 28th February,
2012", which lacks the 21st–27th Amendments (e.g. the 25th Amendment of 2018 omitted Article 247,
the 26th and 27th Amendments of 2024–2025 added the Federal Constitutional Court). It has been
replaced by the Ministry of Law and Justice edition "as amended up to the Twenty-Seventh Amendment"
(2025). That edition prints article titles as margin notes, so the extractor takes each title from
the contents list and rewrites the body heading ("6.  2[(1) Any person ..." → "6. High treason.— ...");
footnote marks glued to article numbers ("1" + "1." read as "11.") are repaired.

## Urdu laws (OCR)

All 1,602 pages of the 40 Urdu laws were OCR'd with EasyOCR (`ur`+`en`, the
benchmark winner) on a Colab T4 GPU using `colab/urdu_ocr_colab.ipynb`, with the
same settings as `src/ingestion/ocr_engine.py`. Page texts are stored in
`data/ocr_text/<document_id>/page_NNNN.txt` (`--colab-input` builds the notebook's
input zip, `--import-ocr` merges its output).

`src/extraction/urdu_text.py` cleans the OCR text: Arabic letter forms → Urdu
(ي→ی, ك→ک, ه/ة→ہ), Arabic-Indic digits → Urdu digits, and the
"THE PAKISTAN CODE" watermark (read as PAKIS, PASTAN, COD …) is removed. The
keyword index also maps all digits to ASCII, so `دفعہ 302` matches `دفعه ٣٠٢`.

The laws are split **by page, not by section**. Their sections are numbered
`۱۔ عنوان`, but EasyOCR never outputs the Urdu full stop `۔` and merges each page
into one paragraph; the numbered headings that survive come mostly from
table-of-contents pages. A page unit with Act + page number can still be cited
against the official PDF. Text quality matches the benchmark (~33% CER): words are
often merged or misspelt, so Urdu keyword search misses some matches and the
multilingual dense index carries most of the Urdu retrieval.

## Structure extraction coverage (Task 3)

Share of documents where each field was found (`evaluations/extraction_report.md`).
This measures presence, not correctness; no hand-labelled check has been done.

| Type | Result |
|---|---|
| Statutes (13) | 2,871 sections/articles/rules, all with a start page. E.g. PPC Sections 1–511, Contract Act Sections 1–238 (76–123 repealed), CPC Sections 1–159 plus 659 Order rules, Income Tax Ordinance Sections 1–242, Constitution Articles 1–280 incl. 175A–175L (Federal Constitutional Court); 324 articles found, 170, 272 and 273 missed |
| Judgments (225) | case number 95%, bench 94%, parties 88–89%, year 98%, hearing date 75%, citations 77%, statutes cited 83%, numbered paragraphs 94%, outcome 97% |
| CUAD contracts (53) | title 100%, 3+ clauses 87%, effective date 72%, governing law 70%, both parties 60% |

## Chunking comparison (Task 4)

All strategies chunk the same extracted text from the English corpus (the Urdu
laws are split by page, so boundary crossings cannot be measured for them)
(`evaluations/chunking_comparison_report.md`). Retrieval relevance is not measured.

| Strategy | Chunks | Median words | Cross a legal boundary | Have section label | Have page |
|---|---:|---:|---:|---:|---:|
| Fixed-size (200 words, 40 overlap) | 10,342 | 200 | 51.4% | 0% | 0% |
| Section-level (split > 350 words) | 9,315 | 208 | 0% | 100% | 98.6% |
| Parent-child children (~80 words) | 19,261 | 114 | 0% | 100% | 99.3% |

Half of the fixed-size chunks mix text from two provisions and none can be cited by
section or page, so the index uses section-level chunks. Parent units can be very
long (one Income Tax definitions section is ~25,000 words), so parents suit an LLM
context rather than the embedding model.

## Index (Task 5)

`--index` extracts the 311 English statutes, judgments and contracts plus the 40
OCR'd Urdu laws (351 documents), builds 11,232 section-level chunks (Urdu: one per
page), and stores them in a BM25 index and a SQLite vector store (embedding took
about 3 h 45 min on the laptop CPU; Urdu text produces many more model tokens per
word). `--update-index DOC_ID ...` re-extracts and re-indexes only the given
documents (e.g. a newly added law) in minutes. Each chunk carries act / section / court / case number / year / page /
matter_id metadata where applicable, and `language: Urdu` for Urdu pages. Spot checks
(not a relevance evaluation):

| Query | Top result |
|---|---|
| `Agar consideration unlawful ho to kya contract void hai?` | Contract Act, 1872, Section 24, page 21, then Section 23, page 19 |
| `punishment of qatl-e-amd` | Pakistan Penal Code, Section 302, page 103 |
| `bail in cross cases` | Supreme Court Crl.P. 183-P/2022 (bail in cross-cases) |
| `harassment at the workplace` with `--court "Lahore High Court"` | 2026 LHC 8275, W.P. 64369/2021, para 7, page 4 |
| `کام کی جگہ پر خواتین کو ہراساں کرنا` | Urdu Protection against Harassment of Women at the Workplace Act, 2010, pages 16, 14, 5 |
| `قتل عمد کی سزا` | Urdu Penal Code pages 185, 184, 182 (Sections 316–321, related homicide provisions); the page with Section 302 (page 176) is 4th, because OCR merged its heading into one word (`قتلعدکیسزا`) |

## Data sources not in git

Two large PDF folders are listed in `inventory.csv` but excluded by `.gitignore`
(one Urdu Constitution scan alone is 98 MB). Place them locally before running
`--collect`, OCR, or the inventory tests:

| Folder | Contents | Source |
|---|---|---|
| `data/scp_judgments_pdfs/` | 225 judgment PDFs (175 Supreme Court, 50 Lahore High Court) | Court websites; links for catalogued ones in `data/source_catalog.csv` |
| `data/pakistani_urdu_code/` | 40 Urdu law PDFs | Pakistan Code Urdu listing; links in `data/source_catalog.csv` |

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
# Rebuild inventory.csv from the PDF folders (and the 20 synthetic contracts)
.\.venv\Scripts\python.exe main.py --collect

# Extract structure for every statute, judgment and contract into data/structured/
.\.venv\Scripts\python.exe main.py --extract

# Download 30 CUAD PDFs and one official Pakistani statute
.\.venv\Scripts\python.exe main.py --download-external

# Compare Tesseract and EasyOCR on the 10 real Urdu pages (requires the tools above)
.\.venv\Scripts\python.exe main.py --ocr-eval

# Compare fixed-size, section-level and parent-child chunking on the extracted corpus
.\.venv\Scripts\python.exe main.py --chunk-eval

# Extract, chunk and build BM25 + dense vector indices, then query (optionally by court)
.\.venv\Scripts\python.exe main.py --index

# Re-index only some documents after adding or fixing them (no full rebuild)
.\.venv\Scripts\python.exe main.py --update-index PKLAW_012
.\.venv\Scripts\python.exe main.py --search "punishment of qatl-e-amd" --top-k 3
.\.venv\Scripts\python.exe main.py --search "harassment at the workplace" --court "Lahore High Court"

# Run collection, OCR, chunking, indexing, and a sample search
.\.venv\Scripts\python.exe main.py --run-all

# Urdu OCR on Colab: build the input zip, then merge the notebook's output zip
.\.venv\Scripts\python.exe main.py --colab-input
.\.venv\Scripts\python.exe main.py --import-ocr "C:\path\to\urdu_ocr_output.zip"

# Run tests
.\.venv\Scripts\python.exe -m pytest -q
```

`--run-all` requires the OCR prerequisites; without them it stops at OCR and
does not claim the benchmark completed.

## Limitations and next work

1. Improve Urdu OCR quality (~33% CER) or detect Urdu sections (e.g. by aligning
   with the English versions of the same laws) so Urdu chunks can carry section
   numbers; Urdu keyword search would also gain from character n-grams.
2. Check extraction correctness against a hand-labelled sample; the coverage
   figures above only show that a field was found. Contract party extraction (60%)
   is the weakest field.
3. Evaluate retrieval with a labelled query/relevance set before production use.
4. Confirm the documents' provenance, licensing, and integrity.

This prototype is for engineering evaluation, not legal advice.
