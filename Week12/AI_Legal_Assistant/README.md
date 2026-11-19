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

## Day 2: RAG with verified citations

Goal: answer questions such as *"Agar consideration unlawful ho to kya contract void hai?"* with the
exact section and a quote from the source, and never show a fabricated citation. The LLM is Gemini
(`gemini-3.5-flash-lite`, key in `.env` as `LLM_API_KEY`); every Gemini response is cached in
`data/llm_cache/`, so re-running costs nothing and gives the same output.

### Evaluation set (Task 1)

`evaluations/rag_eval_set.jsonl`: 100 questions, each with its gold source.

| Type | Count | Gold source | Languages |
|---|---:|---|---|
| Statute | 50 | Act + section/article + page | English, Roman Urdu, Urdu |
| Case law | 30 | Judgment (document / matter id) + paragraph + page | English, Roman Urdu, Urdu |
| Not in the corpus | 20 | none: the answer must be "No sufficient source found" | mostly Roman Urdu |

How it was made (`evaluations/build_eval_set.py`): sources sampled from the structured corpus;
Gemini drafted a question, expected answer and a quote from **that source only**; code rejected any
draft whose quote is not in the source; no-answer candidates were rejected if they name an Act in
the corpus, cite a section that exists in it, or a judge model found the answer in the top-5 results.
Every question was then **reviewed by Claude (an AI model, not a person) against its source text**:
16 drafts were dropped (6 no-answer questions that the judgments do answer, 8 case questions too
general to identify one case, 2 that attributed counsel's argument or a dissent to the court, 2 based
on the outdated 2012 Constitution) and replaced, 6 were corrected. Decisions and reasons:
`evaluations/rag_eval_set_review.csv`, `evaluations/rag_eval_set_dropped.jsonl`.

### Naive vs advanced retrieval (Tasks 2-3)

`evaluations/rag_evaluation.py` runs each configuration on the 100 questions. Each step keeps all
steps before it. Recall@5: share of answerable questions whose gold section / paragraph is in the top 5;
MRR@5: mean 1/rank of the first gold chunk. Citation accuracy: share of answerable questions whose
Gemini answer cites the gold section / paragraph. Faithfulness: claims supported by the passages,
judged by Gemini (an LLM judge, not a person). Full table: `evaluations/rag_comparison_report.md`.

| Configuration | Recall@5 | MRR@5 | Citation accuracy |
|---|---:|---:|---:|
| 0. Naive: fixed 200-word chunks, vector search only | 54% | 0.37 | 42% |
| 1. Section-level chunks, vector search | 64% | 0.52 | 56% |
| 2. + Hybrid (BM25 + vector, reciprocal rank fusion) | 70% | 0.56 | 64% |
| 3. + Reranking (multilingual cross-encoder `mmarco-mMiniLMv2-L12`, top 30) | 78% | 0.73 | 70% |
| 4. + Query rewriting (Gemini: English legal search query) | **94%** | **0.85** | pending |
| 5. + HyDE (Gemini hypothetical answer passage) | 94% | 0.85 | pending |
| 6. + Metadata filters (Act / section / court extracted from the question) | 92% | 0.84 | pending |
| 7. + Parent-child (80-word children searched, parent unit returned) | 91% | 0.82 | pending |

The naive baseline answers faithfully (99%) but refuses 41% of answerable questions, because the
right passage is often not retrieved; retrieval, not the LLM, is the main weakness. Reranking helps
case law most (63% → 83% Recall@5): judgment paragraphs are long and similar to each other.
Query rewriting gives the largest single gain (78% → 94%): many questions are in Roman Urdu or
everyday words, while the sources use formal English legal terms. Steps 5-7 add nothing on top of
rewriting; their small drops are 1-3 of the 80 answerable questions, too few to call a real
difference. Free-tier Gemini allows 500 requests a day, so steps 4-7 were first run for retrieval
only; their answer metrics are pending.

### Cited answers and citation verification (Tasks 4-5)

`python main.py --ask "..."` retrieves 5 passages, asks Gemini for a short answer, explanation and
citations (Act + section or case + paragraph, with a quote), then **verifies every citation in code**
(`src/rag/verify.py`, no LLM):

1. the cited passage was actually retrieved;
2. the Act / case named matches that passage's document (a statute quoted inside a judgment is
   accepted if that section exists in the statute);
3. the section / article / paragraph exists in that document in the structured corpus;
4. the quote appears verbatim in the passage (punctuation, spacing and footnote marks ignored;
   omissions must be marked with "...").

A failing citation is removed; an answer with none left becomes **"No sufficient source found"**.
On the saved answers (`evaluations/citation_verification_report.md`):

| Configuration | Citations | Verified | Fabricated | Page / unverifiable only | Fabricated shown to the user |
|---|---:|---:|---:|---:|---:|
| 0. Naive | 53 | 68% | 9% | 23% | **0** |
| 1. Section-level | 67 | 93% | 6% | 1% | **0** |
| 2. + Hybrid | 77 | 94% | 3% | 4% | **0** |
| 3. + Reranking | 86 | 90% | 5% | 6% | **0** |

**Urdu laws.** Their text comes from OCR (about 1 letter in 3 wrong) and is indexed by page, because
section numbers do not survive OCR. So for an Urdu law the page is the reference (it must be the
retrieved passage's page; a guessed دفعہ number is removed), and the model's clean Urdu quote cannot
match the OCR text word for word. A quote that matches its page closely (85%+; measured: real quotes
84-100% on their own page, at most 59% on any of 40 other pages) is accepted, **but the quote shown is
the source's own OCR text**, never the model's wording: a fuzzy match would also accept a quote with
"not" (نہیں) added, so the model's version of an Urdu quote is never displayed. The answer prompt now also
tells Gemini to cite Urdu laws by page; configurations 0-3 were answered before that change, 4-7 after it.

Fabrications caught include a precedent named instead of the judgment the passage comes from, a
quote "cleaned up" by removing a footnote that sits inside the statute text, and a quote with words
left out without "...". Demo of 5 verified answers: `evaluations/demo_verified_answers.md`.

## Day 3: knowledge graph (in progress)

Schema: `docs/graph_schema.md` (Act, Section, Case, Court, Judge, Party, Contract, Clause; CITES,
FOLLOWS, DISTINGUISHES, OVERRULES, REFERS_TO, INTERPRETS, SAT_ON, ...). Built from the structured corpus
by `python -m src.graph.regex_extract` (regex and rules, every link keeps its sentence, paragraph and page)
and loaded into Neo4j AuraDB with PageRank by `python -m src.graph.load_neo4j`. Example queries:
`evaluations/graph_queries.cypher`.

**Extraction quality** (`python -m evaluations.graph_extraction_eval`, details in
`evaluations/graph_precision_recall.md`). Answer keys were made by Claude (an AI model, not a person) from the
judgment text without looking at the extractor's output. The 20-judgment development set guided the fixes,
so the held-out set of 5 other judgments, annotated afterwards, is the fairer estimate:

| Links | Before fixes (20 dev.) | After fixes (20 dev.) | After fixes (5 held-out) |
|---|---:|---:|---:|
| Precedent citations | P 100% / R 81% | P 100% / R 99% | P 100% / R 95% |
| Statute provisions | P 96% / R 54% | P 97% / R 92% | P 100% / R 96% |
| Judges | P 100% / R 93% | P 100% / R 100% | P 100% / R 100% |

Entity resolution: one node per law however it is written ("Cr.P.C." = "Code of Criminal Procedure" =
"Criminal Procedure Code"; "Qanoon-" = "Qanun-e-Shahadat"), per judge (spelling variants such as
"Akhter" / "Akhtar" merged, kept as `aliases`), and per CPC Order ("Order 39" = "Order XXXIX"). Loaded graph:
1,649 Case, 3,214 Section, 138 Act, 52 Judge nodes; 2,102 REFERS_TO, 146 INTERPRETS, 1,123 CITES, 232 FOLLOWS
(sentences are split with abbreviations in mind, so "Reliance is placed on A v. State (...), B v. State (...)" marks
every listed case as FOLLOWS, not only the first).

**Multi-hop question set** (`evaluations/multihop_eval_set.jsonl`, built by `python -m evaluations.build_multihop_set`):
30 questions that need several connected facts: 24 local ("Which judges sat on the cases that refer to Section
324 PPC?" = Section -> Case -> Judge; "Which precedents do judgments A and B both cite?") and 6 global ("Which
judge sat on the most cases?"); 2 in Roman Urdu. Each answer is computed from the graph and then checked
against the text (`review_note` says how): the evidence sentence of every link was read, and a full-text search
looked for judgments the graph missed. It found 3 (in MH_02, MH_04, MH_26), which were added to the answers, so
the key is not limited by extraction recall. Run `--review` to print the evidence. Building the set also
exposed and fixed extraction errors: "Sections 4 to 25" read as "Section 4TO", slash lists ("302/324/186"),
judge names from page text, and one judgment cited under two reports ("PLJ 2024 SC 114 = 2024 SCP 4", now
one node; 9 such pairs merged).

**GraphRAG** (`src/graph/graphrag.py`, `python -m src.graph.graphrag "question"`), tried in this order:

1. *Local search* (no LLM): provisions, citations, judges, case numbers and a court named in the question are
   linked to graph nodes, and a Cypher query is built from them; the "which ..." word decides what is returned
   (judges, courts, judgments, provisions of a law, precedents). Judgments come back with the sentence each link
   was extracted from, so they can be cited.
2. *Global search* (no LLM): "most" / "largest number" questions count over the graph and return the top result
   (all of them on a tie).
3. *Text-to-Cypher* (Gemini): for anything else, Gemini writes Cypher from the schema and examples; the query must
   be read-only, runs in a read transaction, and is repaired once if Neo4j reports an error.

**Router** (`src/rag/router.py`, rules only): vector for "what does the law say" questions, graph for questions
about links and counts, hybrid for both ("Which judgments refer to Section 324 PPC, and what did they hold?").
Accuracy: 100/100 Day 2 questions to vector, 30/30 multi-hop questions to graph, and on 30 new mixed questions
(`evaluations/router_eval_extra.jsonl`, 10 vector / 10 graph / 10 hybrid, written before the router was run on
them) 29/30 on the first run (30/30 after a fix for a Roman Urdu phrasing the miss exposed).

**Vector vs Graph vs Hybrid** (`python -m evaluations.graph_vs_vector [--no-llm]`, report
`evaluations/graph_vs_vector_report.md`). Without Gemini so far; graph is scored as an answer, vector and hybrid by
how much of the answer is present in their context at all (an upper bound for an LLM answer):

| Question set | Graph answer (F1) | Answer present in top 10 vector passages | Graph + passages |
|---|---:|---:|---:|
| Development (30; GraphRAG's rules were built on these) | 0.99 | 53% | 100% |
| Held-out (10; `evaluations/multihop_heldout.jsonl`) | 0.90 | 56% | 90% |

Vector search cannot answer most multi-hop questions: the answer is spread over many judgments (6 judgments
behind one judge list) or is a count, and the top 10 passages hold about half of it. On the held-out set
the graph misses one question that needs text-to-Cypher ("How many judgments cite ...?") and one link
read wrongly ("Article 51(3) & 4" read as Article 4). The LLM answer scores for vector and hybrid, and
text-to-Cypher, run with Gemini.

Not yet done: an LLM check of the regex-typed relationship types. OVERRULES / DISTINGUISHES / INTERPRETS are
flagged `needs_check` (2 of the 3 OVERRULES candidates are false positives: "per incuriam" mentioned as a review
ground), and a sample of FOLLOWS shows cue-word errors ("counsel relied upon", "not supported by any evidence").
Multi-hop answers use any precedent link, so they do not depend on these types.

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

# Day 2: answer a question with verified citations (Gemini key in .env as LLM_API_KEY)
.\.venv\Scripts\python.exe main.py --ask "Agar consideration unlawful ho to kya contract void hai?"
.\.venv\Scripts\python.exe main.py --ask "..." --config parent_child --json

# Day 2: evaluation set, comparison of retrieval configurations, citation verification, demo
.\.venv\Scripts\python.exe -m evaluations.build_eval_set            # draft (then review the CSV)
.\.venv\Scripts\python.exe -m evaluations.build_eval_set --apply-review
.\.venv\Scripts\python.exe -m evaluations.rag_evaluation --config hybrid --reviewed-only [--no-llm]
.\.venv\Scripts\python.exe -m evaluations.verify_citations
.\.venv\Scripts\python.exe -m evaluations.demo_answers

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
3. The Day 2 evaluation set was reviewed by an AI model, not by a lawyer; a person should
   check it (and the LLM-judged faithfulness) before relying on the numbers.
4. Confirm the documents' provenance, licensing, and integrity.

This prototype is for engineering evaluation, not legal advice.
