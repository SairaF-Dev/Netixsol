"""
Chunking Strategy Evaluation Benchmark for Khan & Associates Legal Assistant.
Compares:
1. Fixed-Size Chunking (Window = 200 words, Overlap = 40)
2. Section-Level Legal Chunking (Domain boundaries: Sections, Ratios, Clauses)
3. Parent-Child Chunking (2-Tier Context Hierarchy)
Across Pakistani Statutes, Judgments, and Commercial Contracts.
"""

from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from tabulate import tabulate

from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory, write_text, load_json
from src.extraction.structure_extractor import UnifiedStructureExtractor
from src.chunking.fixed_chunker import FixedSizeChunker
from src.chunking.section_chunker import SectionLevelChunker
from src.chunking.parent_child_chunker import ParentChildChunker

logger = setup_logger("chunking_evaluation")
EVAL_DIR = Path("evaluations")

def run_chunking_benchmark() -> pd.DataFrame:
    ensure_directory(EVAL_DIR)
    logger.info("=== Starting Task 4: Legal Chunking Strategy Comparison ===")
    
    extractor = UnifiedStructureExtractor()
    fixed_chunker = FixedSizeChunker(chunk_size=200, chunk_overlap=40)
    section_chunker = SectionLevelChunker()
    parent_child_chunker = ParentChildChunker()
    
    # Select sample documents from each category
    statute_files = list(Path("data/statutes").glob("*.json"))[:3]
    judgment_files = list(Path("data/judgments").glob("*.json"))[:5]
    contract_files = (list(Path("data/contracts/cuad").glob("*.json")) + list(Path("data/contracts/synthetic").glob("*.json")))[:4]
    
    sample_docs = []
    for sf in statute_files:
        sample_docs.append((extractor.extract(sf, "Statute"), "Statute"))
    for jf in judgment_files:
        sample_docs.append((extractor.extract(jf, "Judgment"), "Judgment"))
    for cf in contract_files:
        sample_docs.append((extractor.extract(cf, "Contract"), "Contract"))
        
    fixed_chunks = []
    section_chunks = []
    parent_chunks = []
    child_chunks = []
    
    for doc, dtype in sample_docs:
        # 1. Fixed Chunking
        raw_text = getattr(doc, "full_text", None) or getattr(doc, "raw_text", None)
        if not raw_text and hasattr(doc, "chapters"):
            raw_text = f"{doc.act_name}\n{doc.preamble}\n" + "\n".join([f"{s.section_number} {s.content}" for ch in doc.chapters for s in ch.sections])
        elif not raw_text and hasattr(doc, "clauses"):
            raw_text = f"{doc.contract_title}\n" + "\n".join([f"{c.clause_title} {c.text}" for c in doc.clauses])
            
        f_res = fixed_chunker.chunk_text(raw_text, doc.document_id, dtype)
        fixed_chunks.extend(f_res)
        
        # 2. Section Chunking
        if dtype == "Statute":
            s_res = section_chunker.chunk_statute(doc)
            p_res, c_res = parent_child_chunker.chunk_statute(doc)
        elif dtype == "Judgment":
            s_res = section_chunker.chunk_judgment(doc)
            p_res, c_res = parent_child_chunker.chunk_judgment(doc)
        else:
            s_res = section_chunker.chunk_contract(doc)
            p_res, c_res = parent_child_chunker.chunk_contract(doc)
            
        section_chunks.extend(s_res)
        parent_chunks.extend(p_res)
        child_chunks.extend(c_res)
        
    # Metrics computation
    f_tokens = [c.token_count for c in fixed_chunks]
    s_tokens = [c.token_count for c in section_chunks]
    pc_tokens = [c.token_count for c in child_chunks]
    p_tokens = [c.token_count for c in parent_chunks]
    
    metrics = [
        {
            "Strategy": "Fixed-Size (Sliding Window)",
            "Total Chunks": len(fixed_chunks),
            "Avg Tokens": round(float(np.mean(f_tokens)), 1),
            "Token StdDev": round(float(np.std(f_tokens)), 1),
            "Boundary Preservation": "Not measured; windows may split legal units",
            "Metadata Completeness": "Offsets only",
            "Retrieval Context": "Window-sized text"
        },
        {
            "Strategy": "Section-Level (Legal Aware)",
            "Total Chunks": len(section_chunks),
            "Avg Tokens": round(float(np.mean(s_tokens)), 1),
            "Token StdDev": round(float(np.std(s_tokens)), 1),
            "Boundary Preservation": "Structure-aware; not independently scored",
            "Metadata Completeness": "Document-specific legal metadata",
            "Retrieval Context": "One chunk per legal structure unit"
        },
        {
            "Strategy": "Parent-Child (Hierarchical)",
            "Total Chunks": f"{len(child_chunks)} (Child) / {len(parent_chunks)} (Parent)",
            "Avg Tokens": f"{round(float(np.mean(pc_tokens)), 1)} (Child) / {round(float(np.mean(p_tokens)), 1)} (Parent)",
            "Token StdDev": round(float(np.std(pc_tokens)), 1),
            "Boundary Preservation": "Parent hierarchy retained; not independently scored",
            "Metadata Completeness": "Child chunks carry parent_id",
            "Retrieval Context": "Child match with parent context available"
        }
    ]
    
    df = pd.DataFrame(metrics)
    csv_path = EVAL_DIR / "chunking_comparison_report.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    
    table_md = tabulate(df, headers="keys", tablefmt="github", showindex=False)
    
    report = f"""# Khan & Associates - Legal Chunking Strategy Comparison Report

## 1. Executive Summary
Legal documents (statutes, case law judgments, commercial contracts) possess strict hierarchical structures that make generic fixed-size chunking hazardous. Cutting across a statutory proviso, an exception clause, or a ratio decidendi destroys legal semantics.

This benchmark evaluates **3 chunking strategies** on 12 generated instructional
documents (3 statutes, 5 judgments, and 4 contracts). They are not authoritative
legal sources. `Avg Tokens` and `Token StdDev` are whitespace word counts, not
model-token counts. Boundary preservation and retrieval relevance are not scored.

1. **Fixed-Size Chunking** (200-word window, 40-word overlap)
2. **Section-Level Chunking** (Section / Article / Ratio / Clause boundaries)
3. **Parent-Child Chunking** (Sub-clause child chunks indexed, full Section parents returned)

## 2. Benchmark Comparison Matrix

{table_md}

## 3. Design Notes (not measured retrieval results)

### A. Fixed-Size Chunking
* **Tradeoff**: A fixed window can separate a provision from adjacent context.

### B. Section-Level Legal Chunking
* **Strengths**: Every chunk corresponds to an autonomous legal unit (e.g. Section 497 CrPC, Article 199 Constitution, or Clause 5 Governing Law).
* **Metadata Richness**: Automatically attaches `act`, `section`, `court`, `year`, `matter_id`.
* **Fit**: Ideal for direct BM25 keyword matching and standard legal research queries.

### C. Parent-Child Chunking (Recommended for RAG)
* **Potential benefit**: Provides a retrieval tradeoff:
  - **Children** (~20-50 tokens) provide pinpoint semantic matching against specific user questions.
  - **Parents** (~150-400 tokens) provide the LLM with the full statutory section or contract clause upon retrieval.
* **Recommendation**: Evaluate **Parent-Child Chunking** for vector retrieval and **Section-Level Chunking** for BM25 against a judged relevance set before production use.
"""
    
    md_path = EVAL_DIR / "chunking_comparison_report.md"
    write_text(report, md_path)
    
    logger.info(f"Chunking benchmark complete. Reports written to:\n- {csv_path}\n- {md_path}")
    print("\n" + report)
    
    return df

if __name__ == "__main__":
    run_chunking_benchmark()
