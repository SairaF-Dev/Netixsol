# Khan & Associates AI Legal Assistant

Week 12 capstone: an AI legal assistant for a Pakistani law firm. It answers questions in English, Urdu and
Roman Urdu from Pakistani statutes and judgments with citations checked word for word against the source,
explores case law as a knowledge graph, reviews, compares and drafts contracts, and keeps each client's
documents visible only to the lawyers on that matter. "Khan & Associates" is the fictional firm of the
capstone brief; the corpus is real public law plus sample and CUAD contracts. **It is a prototype for
evaluation, not legal advice and not a production legal corpus.**

**Live demo:** https://legal-assistant-g45g44rgv95vfgpv-8000.app.github.dev (GitHub Codespace; started for
demos and grading - it stops when idle). Demo sign-ins are given with the submission.

## Documentation

| Document | For |
|---|---|
| [Architecture](docs/architecture.md) | How the parts fit together - diagrams of the system, a question, an upload, access and deployment |
| [User guide](docs/user_guide.md) | Lawyers: every page, how to read answers, reviews and drafts |
| [Admin guide](docs/admin_guide.md) | Accounts, matters, secrets, audit log, monitoring, backups, troubleshooting |
| [API reference](docs/api.md) | Every endpoint, with examples (interactive: `/api/docs`) |
| [Deployment](docs/deployment.md) | Laptop, Docker (API, worker, Qdrant, Neo4j) and the live Codespace |
| [Future enhancements](docs/future_enhancements.md) | What comes next, from measured gaps and the red team |
| [Red-team report](evaluations/red_team_report.md) | 80 attacks on the running app, 7 weaknesses found and fixed |
| [Graph schema](docs/graph_schema.md) | Node and relationship types of the knowledge graph |
| Evaluation reports | `evaluations/*.md` - one per experiment, also on the app's Accuracy Audits page |

The sections below follow the five days of the brief.

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
    clause and top-level clauses. Clause headings may be "ARTICLE IV", "4. Term.", "4.1 Term"
    (decimal only), "2.TERM:" (no space), Roman "I. Object" or untitled numbered paragraphs; a
    table of contents is recognised because its clauses hold no text (every increasing run of
    numbers is built and the run whose clauses hold text wins); clauses over 2,500 words are split
    at their own sub-clauses ("Clause 3.12"), so a review can point to the exact place.

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
| CUAD contracts (53) | title 100%, 3+ clauses 98% (52/53; was 87%, see below), effective date 72%, governing law 70%, both parties 60% |

**Contract clause fix (found on Day 4).** A Day 4 review pointed almost every finding at "Clause 26" of a
franchise agreement: its table of contents had been taken as the headings, leaving clauses 1-25 empty and the
whole contract (23,775 words) in clause 26. A check of all 53 CUAD contracts found 11 broken this way or with
no clauses at all (headings like "1.1 Scope", "2.TERM:", "I. Object", untitled numbered paragraphs, and one PDF
that writes ";" as the look-alike Greek question mark U+037E). After the fix (above), 9 of the 11 split
correctly, 15 other contracts gained clauses they had merged into the previous one, and none got worse
(compared clause by clause). Still wrong: `REAL_CUAD_025` (a scan with 123 words of text: needs OCR) and
`CUAD_REAL_022` (a numbered list of people inside clause 3 is taken as clauses 4-9). The Day 2 search index
still holds the earlier contract split: rebuilding it would change the reported Day 2 numbers, and the Day 2
questions do not use contracts.

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
| 4. + Query rewriting (Gemini: English legal search query) | **94%** | **0.85** | **84%** |
| 5. + HyDE (Gemini hypothetical answer passage) | 94% | 0.85 | 84% |
| 6. + Metadata filters (Act / section / court extracted from the question) | 92% | 0.84 | pending |
| 7. + Parent-child (80-word children searched, parent unit returned) | 91% | 0.82 | pending |

The naive baseline answers faithfully (99%) but refuses 41% of answerable questions, because the
right passage is often not retrieved; retrieval, not the LLM, is the main weakness. Reranking helps
case law most (63% → 83% Recall@5): judgment paragraphs are long and similar to each other.
Query rewriting gives the largest single gain (78% → 94%): many questions are in Roman Urdu or
everyday words, while the sources use formal English legal terms. Steps 5-7 add nothing on top of
rewriting; their small drops are 1-3 of the 80 answerable questions, too few to call a real
difference. With rewriting, wrongly refused answerable questions fall from 15% (reranking) to 2%,
faithfulness stays 98-100%, and 19 of 20 no-answer questions are still refused (95%). HyDE gives the
same results as rewriting at one more Gemini call per question. Free-tier Gemini allows 500 requests
a day, so steps 6-7 have been run for retrieval only; their answer metrics are pending.

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
| 4. + Query rewriting | 99 | 90% | 6% | 4% | **0** |
| 5. + HyDE | 96 | 92% | 3% | 5% | **0** |

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
left out without "...". Demo of 5 questions: `evaluations/demo_verified_answers.md` (3 answered with
verified citations, 2 correctly refused, one of them after the conclusion check below).

### Conclusion check: does the answer follow from its sources?

The verifier proves a quote exists; it cannot tell whether the conclusion drawn from it is right. The Urdu demo
question asks whether a court can award **more** than the penalty amount fixed in a contract. Gemini answered
"yes", citing a real Specific Relief Act passage (verified) that says only that such a contract can still be
**enforced**; nothing retrieved says a court can award more. The LLM faithfulness judge passed it too, because
each sentence matched a passage.

`src/rag/conclusion_check.py` adds a second Gemini call that reviews the answer like a senior lawyer, from the
retrieved passages only. It first writes down what exactly the question asks, what the relied-on passages
establish on *that* point, and any passage that contradicts or limits the answer, then decides: **supported**
(shown), **partly** (shown with a "read with care" note) or **not supported** (drafted once more with the
reviewer's objection; withheld if it fails again). A first version that gave only a verdict passed the Urdu
answer; asking for the reasoning first made it catch it. On the Urdu question the redraft now answers "No
sufficient source found", which is right for the passages retrieved.

Measured on the 79 answered questions of the query-rewriting run (same passages and answers; one extra Gemini
call each; `python -m evaluations.conclusion_check_eval`, report `evaluations/conclusion_check_report.md`):
75 supported, 2 partly, 2 not supported. All **4 flags point to a real problem**: an answer to a question the
corpus cannot answer (the Partnership Act is not in it) built from another law; a fact reported as the court's
view where the court said it was not important; "reporting is mandatory" resting on a passage about
cooperating with the police; and (minor) a rule for co-sureties left out. The 10 passed answers most likely to
hide an error (their Day 2 citation missed the gold paragraph) were read the same way: no conclusion errors (one
answered from a similar, different judgment, a retrieval ambiguity the check cannot see). This review was done
by Claude (an AI model) against the expected answers, not by a lawyer, and 79 answers is a small sample. The
check runs in `main.py --ask` and the web app; the Day 2 evaluation numbers above were measured without it.

## Day 3: knowledge graph and GraphRAG

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
"Akhter" / "Akhtar" merged, kept as `aliases`), and per CPC Order ("Order 39" = "Order XXXIX"). Loaded graph
(after the relationship-type check below): 1,649 Case, 3,214 Section, 138 Act, 52 Judge, 73 Contract and 1,186
Clause nodes; 2,149 REFERS_TO, 67 INTERPRETS, 1,248 CITES, 108 FOLLOWS, 4 DISTINGUISHES, 2 OVERRULES (sentences are
split with abbreviations in mind, so "Reliance is placed on A v. State (...), B v. State (...)" links every listed
case, not only the first).

**Relationship types checked by Gemini** (`python -m src.graph.llm_relation_check`). The regex step types a link
from cue words ("relied", "distinguish", "overrul", "meaning of"), which cannot tell who is speaking: "counsel
relied upon X" is not the court following X. Gemini read the evidence sentence of all 385 regex-typed links
(FOLLOWS, DISTINGUISHES, OVERRULES, INTERPRETS; 10 per request) and changed 211: 123 FOLLOWS were only CITES
(relied on by counsel or by the court below, or a neutral mention) and 79 INTERPRETS only REFERS_TO. On 34 links
labelled by hand before the check (all OVERRULES and DISTINGUISHES, random FOLLOWS and INTERPRETS;
`evaluations/relation_gold_sample.json`, labelled by Claude, an AI model, not a person) the type is right for
**28/34 with the check vs 16/34 for the regex**. Links the regex typed CITES / REFERS_TO were not re-checked:
this fixes wrong types, it does not find missed ones. Multi-hop answers use any precedent link, so they do not
depend on these types.

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

**Vector vs Graph vs Hybrid** (`python -m evaluations.graph_vs_vector`, report `evaluations/graph_vs_vector_report.md`).
Answers are sets (judges, judgments, provisions, precedents), scored by F1 per question and averaged:

| Method | Development (30; GraphRAG's rules built on these) | Held-out (10) |
|---|---:|---:|
| Vector: Gemini lists the answer from the top 10 passages | 0.40 | 0.43 |
| Graph: the Cypher result (text-to-Cypher for 1 held-out question) | 0.99 | 1.00 |
| Hybrid: Gemini with the graph result and the passages | 0.72 | 0.73 |
| Routed (the router chose graph for all 40) | 0.99 | 1.00 |

Vector search cannot answer most multi-hop questions: the answer is spread over many judgments or is a count,
and the top 10 passages hold only about half of it (53% / 56% of the answer items appear in them at all).
Text-to-Cypher answered the one held-out question the query builder could not plan ("How many judgments cite
PLD 2023 SC 588?" -> 3). Hybrid is worse than graph alone: given the graph list and passages together, Gemini
drops or splits list items (its prompt was changed once after the first run, which scored 0.56 / 0.43, see the
report). So list questions should take the graph result as the answer and use the LLM only for content
questions ("... and what did they hold?"), which is what the router does.

## Day 4: contract review, comparison and drafting

Scenario: a 60-page agreement arrives at 6 pm and needs comments by morning. Every output is marked
**"DRAFT — for lawyer review"**, and every quote and legal source in it is checked by code.

### Clause classification: LLM vs fine-tuned models (Task 1)

Data (`python -m src.contracts.cuad_data`): CUAD's lawyer-marked passages for the 28 clause types with at least
100 examples (metadata types such as "Parties" left out), plus sentences no lawyer marked (label: none). A passage
can have several types. Split **by contract** (80 / 10 / 10, seed 42), so test contracts are never seen in
training: 10,088 training, 1,218 validation and 1,054 test passages; the comparison uses a 482-passage test
sample (up to 15 per type plus 150 unmarked sentences) so the LLM run fits the free quota.

* LLM: Gemini (`gemini-3.5-flash-lite`), zero-shot, given CUAD's one-line description of each type, 15 passages
  per request.
* Fine-tuned: a multi-label head (one yes/no output per type) on Legal-BERT-small on the laptop CPU
  (`src/contracts/finetune.py`), and Legal-BERT-small, Legal-BERT-base and DeBERTa-v3-base on a Colab T4 GPU
  (`colab/clause_finetune_colab.ipynb`, generated by `colab/make_clause_notebook.py`). Each keeps the epoch with the
  best validation F1 and one decision threshold tuned on validation; the test set is never used for a choice.

| | Gemini, zero-shot | Legal-BERT-small, 3 epochs (CPU) | DeBERTa-v3-base (GPU) | Legal-BERT-base (GPU) | Legal-BERT-small, 8 epochs (GPU) |
|---|---:|---:|---:|---:|---:|
| Micro F1 | 0.79 | 0.69 | 0.75 | **0.80** | 0.79 |
| Macro F1 (28 types) | 0.77 | 0.59 | 0.68 | 0.77 | 0.77 |
| False alarms on unmarked sentences | 12% | 14% | 11% | 11% | 15% |
| Training | none | 100 min | 16 min | 9 min | 4 min |
| Time per passage | 620 ms (API) | 50 ms | 5.7 ms | 3.0 ms | **1.0 ms** |

A small model trained for 4 minutes matches Gemini (0.79) and labels a passage 600 times faster at no cost per
call. Pre-training on legal text matters more than size: DeBERTa-v3-base, a larger general model, scores below
both Legal-BERT models. Training longer mattered most for the small model (0.69 after 3 epochs on CPU, 0.79
after 8 on GPU), and every model was still improving at its last epoch. Gemini is clearly better on rare,
subtle types the models saw few examples of ("Competitive Restriction Exception": 0.74 vs 0.43 at best) and
worse on some well-defined ones ("Volume Restriction" 0.36 vs 0.88, "Uncapped Liability" 0.64 vs 0.86).
Types with fewer than 15 test passages have unreliable scores. F1 per type:
`evaluations/clause_classification_report.md`.

### Playbook risk review (Task 2)

`data/playbook/firm_playbook.json` holds 14 positions (governing law, dispute resolution, liability cap,
indemnity, termination, renewal, confidentiality, assignment, payment and tax, IP, restraint of trade,
liquidated damages, audit, force majeure), each with green / amber / red positions, a weight, standard wording
and its Pakistani statutory source (Contract Act ss. 27, 28, 73, 74, 124; Income Tax Ordinance s. 153).
`python -m src.contracts.review <contract> --party "..."`:

1. for each position, the 3 contract passages closest in meaning (multilingual-e5-small, 300-word windows, so a
   60-page contract fits one prompt) plus any clause whose title names it;
2. Gemini rates each position ✅ / ⚠️ / ❌ / missing from the client's side, names the clause, quotes it,
   explains why and suggests wording;
3. code checks every quote word for word against the clause it names (an unverified quote is removed and the
   finding says so); statutory sources are quoted from the corpus, never written by the model; a position the
   model skipped is reported, not dropped;
4. risk score 0-100: red adds the position's weight, amber half, a missing required clause counts as red;
5. Word export with a findings table, missing clauses with proposed wording, and the contract text with a
   **Word comment** on each clause that has a finding.

Samples in `evaluations/contract_reviews/`: a supply agreement in the contractor's markup (risk 64: Dubai courts,
a one-month liability cap, one-sided termination and a non-compete rated ❌; 5 positions missing) and a real CUAD
franchise agreement reviewed for the franchisee (risk 85; findings point to clauses 8-25 after the clause fix
above; one quote removed by the check).

### Comparing two versions (Task 3)

`python -m src.contracts.compare v1.json v2.json` matches clauses by content, not number (title and text
similarity, best pairs first), so a renumbered draft still lines up; finds changed words with a word-level diff;
and asks Gemini to explain each change for the client: what changed, its legal effect, which side it favours, a
risk level and the playbook position involved. The diff is computed by code, so the model can neither invent nor
miss a change. Output: Markdown, JSON and a Word redline (deleted text struck through in red, inserted text
underlined in blue). Test pair `data/contracts/versions/supply_agreement_v1.json` / `_v2.json`: **all 9 planted
changes found**; 8 explained as favouring the contractor (e.g. "replaces a non-solicitation clause with a broad
non-compete", with Section 27 of the Contract Act) and the purely stylistic one rated "no risk".

### Drafting agent (Task 4)

`python -m src.contracts.drafting brief | notice | clauses ...`, output in `evaluations/drafts/` (Markdown and Word):

* **Case brief** of a judgment: facts, issues, holding, reasoning and outcome, each point tied to a paragraph
  number and a quote that must appear word for word in that paragraph (2 quotes failed and were removed in the
  sample); the precedents and provisions it relies on come from the knowledge graph.
* **Legal notice** from facts given by the lawyer (sample: unpaid invoices of PKR 4.8 million): the legal basis is
  retrieved from the corpus and every citation passes the Day 2 verifier (here Section 73 of the Contract Act).
* **Contract clauses** adapted to the deal from the firm's standard wording, with the statutory sources quoted
  from the corpus.

A citation that fails its check is removed and the text says "[source removed: not verified]".

### Long context vs RAG (Task 5)

`python -m evaluations.long_context_vs_rag`: 10 CUAD test contracts (3,400-14,200 words), 10 clause types each
(100 questions, 44 clauses present according to CUAD's lawyers). Gemini either reads the whole contract or only
the 3 passages (200 words) retrieved for each clause type, and must say whether the clause is present and quote it.

| | Long context (whole contract) | RAG (3 passages per type) |
|---|---:|---:|
| Correct (present / absent) | **90%** | 88% |
| Missed clauses | **3 / 44** | 7 / 44 |
| False alarms | 7 | 5 |
| Quote real and on the right clause | 40 / 44 | 36 / 44 |
| Input per contract | 14,300 tokens | **10,100 tokens** |
| Time per contract | 18 s | **6 s** |

Long context misses fewer clauses; RAG is 3 times faster and uses 30% fewer tokens. For a review, a missed clause
is the costlier error, so for contracts that fit the model's context, reading the whole contract is the safer
default. Report: `evaluations/long_context_vs_rag_report.md`.

## Day 5: security, deployment and evaluation

### Security

* **Sign-in and roles.** Accounts with PBKDF2 password hashes; signed tokens valid for 8 hours; five wrong
  passwords lock the account for five minutes. Roles: admin, partner (all matters), associate (own matters).
* **Client-matter access control** (`src/security/access.py`). Public law is open to everyone; a contract is
  visible only to the users on its matter - in search results, reviews, comparisons, downloads, job results,
  contract lists and graph queries. Another matter's document answers "404 not found", not "403", so its
  existence is not revealed.
* **Prompt injection in uploads** (`src/security/injection.py`). Two defences. A scanner blocks a document with
  text addressed to an AI - in English, Roman Urdu or Urdu, hidden in white, tiny or hidden Word text or white /
  off-page PDF text, or disguised with invisible characters, look-alike letters, spaced letters or base64.
  Behind it, every review prompt fences the contract inside `<contract_text>` tags as data, never instructions.
  0 false alarms on 9,071 real clauses, statute sections and judgment paragraphs.
* **PII masking** of CNIC, phone, e-mail, IBAN, card and NTN numbers in logs and the audit log.
* **Audit log** (`src/security/audit.py`): every sign-in, question, review, upload, download and denial, each
  entry hash-chained to the one before, so any edit is detected (page 08 for the admin).
* **Red team** ([report](evaluations/red_team_report.md)): 80 attacks in 9 groups. The first run found 7
  weaknesses - a legal notice repeating a fake "Section 489-Z" planted in its facts, the system prompt leaking
  through a refusal check, 9 of 12 disguised injections passing the scanner, two normal contract sentences
  blocked, a CNIC unmasked in the audit user field, corrupt files crashing an upload, a Contract Act graph search
  refused. All 7 were fixed with regression tests; the final run: **78 of 80 held**, one accepted gap (a French
  injection passes the scanner; the fence still stops it) and one documented limitation (questions reach
  Gemini unmasked).

### Background jobs, uploads and health

Reviews, comparisons, drafts and upload indexing run as jobs (`src/jobs/`): a SQLite queue and a worker - a
thread inside the web app, or its own container. An uploaded contract is screened, filed on its matter and
indexed, and becomes searchable for that matter's users without a restart. `GET /api/health` reports the search
index, graph, Gemini key, worker heartbeat, audit log and disk.

### Deployment

* **Docker Compose** (`docker-compose.yml`): API, worker, **Qdrant** vector database, **Neo4j**, and a bootstrap
  task that loads them. Qdrant returns the same rankings as the in-memory index (same top passage on 25/25
  questions, 100% of the top-30 shared).
* **No PyTorch on servers**: the embedding model and reranker run on ONNX Runtime with the official ONNX files
  ([report](evaluations/onnx_equivalence_report.md)): identical vectors and identical top-5 results on all 100
  evaluation questions; image 4.41 GB -> 2.68 GB, memory 2.5 GB -> 1.7 GB.
* **CI** (`.github/workflows/legal-assistant-ci.yml`): the tests, a Docker build and a smoke test on every push.
* **Live link** on a GitHub Codespace (free, no card): one process with the worker inside, graph on Neo4j
  AuraDB, secrets as Codespaces secrets ([deployment guide](docs/deployment.md)).

### Evaluation

* **Blind rating of 30 answers** (`evaluations/blind_rating.py`, page 09 in the app): 15 evaluation questions
  answered by the naive and the final pipeline, shuffled, rated by a person for correctness, citation support
  and usefulness without knowing which version wrote which; the versions are revealed only after all 30 are
  rated. Results: `evaluations/blind_rating_report.md`.
* The Day 1-4 reports remain in `evaluations/` and on the Accuracy Audits page.

## Web app

`python -m web.server`, then open http://127.0.0.1:8000 and sign in. Nine pages: **01 Legal Research** (the
router sends a question to verified-citation search, the case-law graph or both), **02 Precedents & Citations**
(GraphRAG), **03 Agreement Review** (playbook review of a sample or uploaded contract, Word file with margin
comments), **04 Bilateral Redline** (two versions, redline with legal impact), **05 Document Assembly** (case
brief, legal notice, clauses), **06 Matter Repository** (upload and index a contract on a matter), **07 Accuracy
Audits** (the reports), **08 Chain of Custody** (audit log, admin only) and **09 Blind Answer Rating**. Backend:
FastAPI (`web/server.py`); front end: plain HTML, CSS and JavaScript (`web/static/`), all text inserted as text,
never as HTML. Gemini answers are cached, so a question asked before costs nothing. How to use it:
[user guide](docs/user_guide.md); endpoints: [API reference](docs/api.md).

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
.\.venv\Scripts\python.exe -m evaluations.conclusion_check_eval     # conclusion check on saved answers

# Day 3: build the graph, check relationship types, load Neo4j (AuraDB settings in .env), evaluate
.\.venv\Scripts\python.exe -m src.graph.regex_extract
.\.venv\Scripts\python.exe -m src.graph.llm_relation_check         # then regex_extract again
.\.venv\Scripts\python.exe -m src.graph.load_neo4j
.\.venv\Scripts\python.exe -m src.graph.graphrag "Which judges sat on the cases that refer to Section 324 PPC?"
.\.venv\Scripts\python.exe -m evaluations.graph_extraction_eval
.\.venv\Scripts\python.exe -m evaluations.graph_vs_vector

# Day 4: CUAD data, fine-tuning (or the Colab notebook), comparison, review, versions, drafting
.\.venv\Scripts\python.exe -m src.contracts.cuad_data --download
.\.venv\Scripts\python.exe -m src.contracts.finetune
.\.venv\Scripts\python.exe -m evaluations.clause_classification     # --no-llm: fine-tuned models only
.\.venv\Scripts\python.exe -m src.contracts.review data/contracts/versions/supply_agreement_v2.json --party "Pak Telecom Enterprises (the Client)"
.\.venv\Scripts\python.exe -m src.contracts.compare data/contracts/versions/supply_agreement_v1.json data/contracts/versions/supply_agreement_v2.json
.\.venv\Scripts\python.exe -m src.contracts.drafting brief SC_crl.p._207_k_2025
.\.venv\Scripts\python.exe -m src.contracts.drafting notice data/contracts/drafting/notice_facts.json
.\.venv\Scripts\python.exe -m src.contracts.drafting clauses data/contracts/drafting/clause_request.json
.\.venv\Scripts\python.exe -m evaluations.long_context_vs_rag

# Day 5: accounts (first time only: demo users with random passwords in data/security/initial_passwords.txt)
.\.venv\Scripts\python.exe -m src.security.access seed
.\.venv\Scripts\python.exe -m src.security.access set-password ayesha "new-password"

# Web app (http://127.0.0.1:8000); Docker: docker compose up -d (see docs/deployment.md)
.\.venv\Scripts\python.exe -m web.server

# Day 5: red team against a running test server, blind rating set and report, ONNX vs PyTorch check
.\.venv\Scripts\python.exe evaluations/red_team.py --base http://127.0.0.1:8090 --server-log data/redteam_server.log
.\.venv\Scripts\python.exe evaluations/blind_rating.py build      # then rate on page 09, then:
.\.venv\Scripts\python.exe evaluations/blind_rating.py report
.\.venv\Scripts\python.exe evaluations/onnx_equivalence.py

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
3. The Day 2 evaluation set, the graph answer keys, the relationship-type sample and the conclusion-check
   review were made by an AI model, not by a lawyer; a person should check them (and the LLM-judged
   faithfulness) before relying on the numbers.
4. Verified citations do not make an answer right: the conclusion check catches answers that draw the wrong
   conclusion from real quotes, but it is itself an LLM and was measured on 79 answers only. Every output is a
   draft for a lawyer.
5. Day 2 steps 6-7 (metadata filters, parent-child) still need their answer metrics (Gemini quota).
6. Two CUAD contracts are still split wrongly (one needs OCR); the Day 2 search index holds the earlier
   contract split.
7. Confirm the documents' provenance, licensing, and integrity.

8. Security limits found by the red team: personal data typed into a question reaches Gemini unmasked; no
   per-user question limit; the upload scanner does not read French. The full list, with the plan for each:
   [future enhancements](docs/future_enhancements.md).

This prototype is for engineering evaluation, not legal advice.
