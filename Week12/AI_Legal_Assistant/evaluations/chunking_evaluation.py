"""
Task 4: compare fixed-size, section-level and parent-child chunking on the real corpus.

All three strategies see the same text: the legal units extracted in Task 3
(statute sections, judgment paragraphs + holding, contract clauses) read from
data/structured/. Measured per strategy:

* chunk count and word-length distribution (whitespace words, not model tokens);
* share of chunks over 400 words (multilingual-e5-small reads at most 512 tokens);
* boundary crossings: share of chunks containing text from more than one legal unit;
* share of chunks that carry a legal label (section / paragraph / clause) and a page.

Retrieval relevance is not measured (there is no labelled query set).
"""

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from tabulate import tabulate

from src.chunking.fixed_chunker import FixedSizeChunker
from src.chunking.parent_child_chunker import ParentChildChunker
from src.chunking.section_chunker import SectionLevelChunker
from src.extraction.corpus_extraction import STRUCTURED_DIR, extract_corpus
from src.utils.file_utils import ensure_directory, load_json, write_text
from src.utils.logger import setup_logger
from src.utils.schemas import ContractDocument, JudgmentDocument, LegalChunk, StatuteDocument

logger = setup_logger("chunking_evaluation")
EVAL_DIR = Path("evaluations")
LONG_CHUNK_WORDS = 400


def load_structured_documents(structured_dir: Path = STRUCTURED_DIR) -> List:
    """Load Task 3 output; run the extraction first if it is missing."""
    if not any(structured_dir.glob("*/*.json")):
        logger.info("No structured JSON found; running Task 3 extraction first.")
        extract_corpus()
    models = {"statute": StatuteDocument, "judgment": JudgmentDocument, "contract": ContractDocument}
    documents = [models[path.parent.name].model_validate(load_json(path))
                 for path in sorted(structured_dir.glob("*/*.json")) if path.parent.name in models]
    # OCR'd Urdu laws are split by page, not by legal unit, so they cannot be scored
    # for boundary crossings and are left out of this comparison.
    return [d for d in documents if getattr(d, "language", "English") != "Urdu"]


def legal_units(doc) -> List[Tuple[str, str, int]]:
    """(label, text, page) for each legal unit; the shared input of all strategies."""
    if isinstance(doc, StatuteDocument):
        return [(sec.section_number, " ".join([sec.title, sec.content] + sec.subsections), sec.page_start)
                for ch in doc.chapters for sec in ch.sections]
    if isinstance(doc, JudgmentDocument):
        units = [(f"para {p.number or 'opening'}", p.text, p.page) for p in doc.paragraphs]
        return units or [("holding", doc.holding, doc.holding_page)]
    return [(c.clause_id, f"{c.clause_title} {c.text}", c.page_number) for c in doc.clauses]


def fixed_chunks_with_boundaries(doc, chunker: FixedSizeChunker) -> Tuple[List[LegalChunk], int]:
    """Fixed windows over the concatenated units; returns chunks and how many cross a unit boundary."""
    units = legal_units(doc)
    starts, words = [], []
    for _, text, _ in units:
        starts.append(len(words))
        words.extend(text.split())
    chunks = chunker.chunk_text(" ".join(words), doc.document_id, type(doc).__name__.replace("Document", ""))
    crossings = 0
    for chunk in chunks:
        first, last = chunk.metadata["start_word"], chunk.metadata["end_word"] - 1
        unit_first = int(np.searchsorted(starts, first, side="right")) - 1
        unit_last = int(np.searchsorted(starts, last, side="right")) - 1
        crossings += unit_last > unit_first
    return chunks, crossings


def _row(name: str, chunks: List[LegalChunk], crossings: int) -> Dict[str, object]:
    sizes = np.array([c.token_count for c in chunks]) if chunks else np.array([0])
    labelled = sum(1 for c in chunks if c.metadata.get("section"))
    paged = sum(1 for c in chunks if c.metadata.get("page"))
    pct = lambda n: f"{100 * n / max(1, len(chunks)):.1f}%"
    return {
        "Strategy": name,
        "Chunks": len(chunks),
        "Mean words": round(float(sizes.mean()), 1),
        "Median words": int(np.median(sizes)),
        "Max words": int(sizes.max()),
        f"> {LONG_CHUNK_WORDS} words": pct(int((sizes > LONG_CHUNK_WORDS).sum())),
        "Cross a legal boundary": pct(crossings),
        "Have legal label": pct(labelled),
        "Have page": pct(paged),
    }


def run_chunking_benchmark() -> pd.DataFrame:
    ensure_directory(EVAL_DIR)
    logger.info("=== Starting Task 4: Legal Chunking Strategy Comparison (real corpus) ===")
    documents = [d for d in load_structured_documents() if legal_units(d)]

    fixed_chunker = FixedSizeChunker(chunk_size=200, chunk_overlap=40)
    section_chunker = SectionLevelChunker()
    parent_child_chunker = ParentChildChunker()

    fixed, section, parents, children = [], [], [], []
    fixed_crossings = 0
    per_type: Dict[str, Dict[str, int]] = {}
    for doc in documents:
        kind = type(doc).__name__.replace("Document", "")
        f_chunks, crossings = fixed_chunks_with_boundaries(doc, fixed_chunker)
        fixed.extend(f_chunks)
        fixed_crossings += crossings
        if kind == "Statute":
            s_chunks = section_chunker.chunk_statute(doc)
            p, c = parent_child_chunker.chunk_statute(doc)
        elif kind == "Judgment":
            s_chunks = section_chunker.chunk_judgment(doc)
            p, c = parent_child_chunker.chunk_judgment(doc)
        else:
            s_chunks = section_chunker.chunk_contract(doc)
            p, c = parent_child_chunker.chunk_contract(doc)
        section.extend(s_chunks)
        parents.extend(p)
        children.extend(c)
        stats = per_type.setdefault(kind, {"documents": 0, "fixed": 0, "section": 0, "children": 0})
        stats["documents"] += 1
        stats["fixed"] += len(f_chunks)
        stats["section"] += len(s_chunks)
        stats["children"] += len(c)

    rows = [
        _row("Fixed-size (200 words, 40 overlap)", fixed, fixed_crossings),
        _row("Section-level (legal units, split > 350 words)", section, 0),
        _row("Parent-child: children (~80 words)", children, 0),
        _row("Parent-child: parents (whole units)", parents, 0),
    ]
    df = pd.DataFrame(rows)
    csv_path = EVAL_DIR / "chunking_comparison_report.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    type_table = tabulate(
        [[k, v["documents"], v["fixed"], v["section"], v["children"]] for k, v in per_type.items()],
        headers=["Type", "Documents", "Fixed chunks", "Section chunks", "Child chunks"], tablefmt="github")
    corpus = ", ".join(f"{v['documents']} {k.lower()}s" for k, v in per_type.items())
    report = f"""# Legal Chunking Strategy Comparison

## Corpus and method

Real corpus from `inventory.csv`: {corpus} (the 20 synthetic contracts are
included; Urdu laws are not, as they are not OCR'd yet). All strategies chunk the same text:
the legal units extracted in Task 3 (statute sections/articles/rules, judgment
paragraphs, contract clauses). Word counts are whitespace words, not model tokens.

* **Cross a legal boundary**: share of chunks containing words from more than one
  legal unit (e.g. the end of Section 301 and the start of Section 302). Section-level
  and parent-child chunks never cross by construction.
* **> {LONG_CHUNK_WORDS} words**: chunks likely to be truncated by multilingual-e5-small (512 tokens).
* **Have legal label / page**: chunks whose metadata names the section, paragraph or
  clause, and the PDF page where it starts (needed for citing sources).

Retrieval quality is **not** measured; that needs a labelled query/relevance set.

## Results

{tabulate(df, headers="keys", tablefmt="github", showindex=False)}

## Chunks per document type

{type_table}

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
"""
    md_path = EVAL_DIR / "chunking_comparison_report.md"
    write_text(report, md_path)
    logger.info("Chunking benchmark complete: %s, %s", csv_path, md_path)
    print("\n" + report)
    return df


if __name__ == "__main__":
    run_chunking_benchmark()
