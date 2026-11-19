# Legal Chunking Strategy Comparison

## Corpus and method

Real corpus from `inventory.csv`: 66 contracts, 225 judgments, 13 statutes (the 20 synthetic contracts are
included; Urdu laws are not, as they are not OCR'd yet). All strategies chunk the same text:
the legal units extracted in Task 3 (statute sections/articles/rules, judgment
paragraphs, contract clauses). Word counts are whitespace words, not model tokens.

* **Cross a legal boundary**: share of chunks containing words from more than one
  legal unit (e.g. the end of Section 301 and the start of Section 302). Section-level
  and parent-child chunks never cross by construction.
* **> 400 words**: chunks likely to be truncated by multilingual-e5-small (512 tokens).
* **Have legal label / page**: chunks whose metadata names the section, paragraph or
  clause, and the PDF page where it starts (needed for citing sources).

Retrieval quality is **not** measured; that needs a labelled query/relevance set.

## Results

| Strategy                                       |   Chunks |   Mean words |   Median words |   Max words | > 400 words   | Cross a legal boundary   | Have legal label   | Have page   |
|------------------------------------------------|----------|--------------|----------------|-------------|---------------|--------------------------|--------------------|-------------|
| Fixed-size (200 words, 40 overlap)             |    10342 |        197.6 |            200 |         200 | 0.0%          | 51.4%                    | 0.0%               | 0.0%        |
| Section-level (legal units, split > 350 words) |     9315 |        206.3 |            208 |         420 | 0.2%          | 0.0%                     | 100.0%             | 98.6%       |
| Parent-child: children (~80 words)             |    19261 |        112   |            114 |         314 | 0.0%          | 0.0%                     | 100.0%             | 99.3%       |
| Parent-child: parents (whole units)            |     7007 |        267   |            155 |       24721 | 13.7%         | 0.0%                     | 100.0%             | 98.1%       |

## Chunks per document type

| Type     |   Documents |   Fixed chunks |   Section chunks |   Child chunks |
|----------|-------------|----------------|------------------|----------------|
| Contract |          66 |           2157 |             1524 |           3503 |
| Judgment |         225 |           4658 |             4187 |           9508 |
| Statute  |          13 |           3527 |             3604 |           6250 |

## Reading the results

* Fixed-size windows ignore structure: the "Cross a legal boundary" column shows
  how often a retrieved chunk mixes two provisions, and these chunks carry no
  section label or page.
* Section-level chunks map one-to-one to citable units (`Section 302`, `para 12`,
  `Clause 9`) with page numbers; long units are split into labelled parts so no
  chunk exceeds the embedding limit. This strategy is used for the BM25 and vector index.
* Parent-child gives small children for precise matching while the parent keeps the
  whole unit for context; parents can be very long (whole Income Tax definitions
  sections), so they suit an LLM context window rather than the embedding model.
