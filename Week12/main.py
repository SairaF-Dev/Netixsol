"""
Khan & Associates - AI Legal Assistant Pipeline Orchestrator (Day 1 Capstone).
Automates:
1. Corpus Collection & Inventory Generation
2. PDF Parsing, Scanned/Digital Detection & OCR Benchmark (CER/WER)
3. Legal Structure Extraction (Statutes, Judgments, Contracts)
4. Legal-Aware Chunking Strategy Comparison
5. BM25 and Dense Vector Indexing with Hybrid Search
"""

import sys
import argparse
from pathlib import Path

from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory
from src.ingestion.corpus_collector import run_corpus_collection
from src.extraction.corpus_extraction import extract_corpus
from src.utils.schemas import JudgmentDocument, StatuteDocument
from src.chunking.section_chunker import SectionLevelChunker
from src.chunking.fixed_chunker import FixedSizeChunker
from src.indexing.bm25_index import LegalBM25Index
from src.indexing.vector_store import DenseVectorStore
from src.indexing.hybrid_search import HybridLegalSearchEngine
from evaluations.ocr_evaluation import run_ocr_benchmark
from evaluations.chunking_evaluation import run_chunking_benchmark
from src.ingestion.download_external_corpus import run_external_download

logger = setup_logger("legal_orchestrator")

INDEX_DIR = Path("data/indices")

def chunk_documents(documents) -> list:
    """Section-level chunks for extracted documents; fixed-size fallback when no structure was found."""
    chunker = SectionLevelChunker()
    fallback_chunker = FixedSizeChunker()
    all_chunks = []
    for doc in documents:
        if isinstance(doc, StatuteDocument):
            chunks = chunker.chunk_statute(doc)
            has_structure = any(c.sections for c in doc.chapters)
            fallback_text, doc_type = doc.raw_text, "Statute"
            meta = {"act": doc.act_name, "year": doc.year}
        elif isinstance(doc, JudgmentDocument):
            chunks = chunker.chunk_judgment(doc)
            has_structure = bool(doc.paragraphs)
            fallback_text, doc_type = doc.full_text, "Judgment"
            meta = {"court": doc.court, "case_number": doc.case_number, "year": doc.year, "matter_id": doc.matter_id or ""}
        else:
            chunks = chunker.chunk_contract(doc)
            has_structure = bool(doc.clauses)
            fallback_text, doc_type = doc.raw_text, "Contract"
            meta = {"contract_title": doc.contract_title, "contract_type": doc.contract_type}
        if not has_structure and fallback_text:
            # Keep the metadata/summary chunk and add fixed windows over the full text.
            chunks = chunks[:1] + fallback_chunker.chunk_text(
                fallback_text, doc.document_id, doc_type, metadata={**meta, "structure_extraction": "full_text_fallback"})
        all_chunks.extend(chunks)
    return all_chunks


def build_complete_indices() -> HybridLegalSearchEngine:
    """Extract every inventory document (Task 3), chunk it (Task 4) and build BM25 + vector indices (Task 5)."""
    ensure_directory(INDEX_DIR)
    logger.info("=== Building Legal Knowledge Indices from inventory.csv ===")

    documents = extract_corpus()
    all_chunks = chunk_documents(documents)
    logger.info(
        "Total legal chunks ready for indexing: %d from %d documents (incl. OCR'd Urdu laws)",
        len(all_chunks), len(documents),
    )
    
    # Build BM25 Index
    bm25 = LegalBM25Index()
    bm25.add_chunks(all_chunks)
    bm25.save(INDEX_DIR / "bm25_legal.pkl")
    
    # Build Dense Vector Store
    vstore = DenseVectorStore(collection_name="khan_legal_corpus")
    vstore.add_chunks(all_chunks)
    vstore.save(INDEX_DIR / "vstore_legal.sqlite3")
    
    hybrid_engine = HybridLegalSearchEngine(bm25, vstore)
    logger.info("Hybrid indices built and persisted successfully.")
    return hybrid_engine

def query_pipeline(query_str: str, top_k: int = 5, court_filter: str = None) -> None:
    """Executes a hybrid legal query against the indexed corpus."""
    bm25_path = INDEX_DIR / "bm25_legal.pkl"
    vstore_path = INDEX_DIR / "vstore_legal.sqlite3"
    
    if not bm25_path.exists() or not vstore_path.exists():
        logger.info("Indices not found on disk. Building indices now...")
        hybrid_engine = build_complete_indices()
    else:
        bm25 = LegalBM25Index.load(bm25_path)
        vstore = DenseVectorStore.load(vstore_path)
        hybrid_engine = HybridLegalSearchEngine(bm25, vstore)
        
    meta_filter = {"court": court_filter} if court_filter else None
    
    logger.info(f"Searching for: '{query_str}' (Top {top_k}, Filter: {meta_filter})")
    results = hybrid_engine.search(query_str, top_k=top_k, metadata_filter=meta_filter)
    
    print("\n" + "=" * 80)
    print(f"HYBRID RETRIEVAL RESULTS FOR: '{query_str}'")
    print("=" * 80)
    
    if not results:
        print("No matching legal chunks found.")
        return
        
    for rank, res in enumerate(results, start=1):
        print(f"\n[Rank {rank}] [RRF Score: {res['rrf_score']:.6f}] Chunk ID: {res['chunk_id']}")
        print(f"Type: {res['document_type']} | Document ID: {res['document_id']}")
        print(f"Metadata: {res['metadata']}")
        print("-" * 80)
        snippet = res["content"][:280] + ("..." if len(res["content"]) > 280 else "")
        print(snippet)
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Khan & Associates AI Legal Assistant Ingestion Pipeline")
    parser.add_argument("--run-all", action="store_true", help="Execute end-to-end Day 1 pipeline")
    parser.add_argument("--download-external", action="store_true", help="Download real CUAD contracts and official statutes from web")
    parser.add_argument("--collect", action="store_true", help="Task 1: Collect corpus & generate inventory.csv")
    parser.add_argument("--ocr-eval", action="store_true", help="Task 2: Run OCR benchmark on 10 real Pakistan Code Urdu pages (CER/WER)")
    parser.add_argument("--extract", action="store_true", help="Task 3: Extract structure for inventory documents into data/structured/ JSON")
    parser.add_argument("--ocr-urdu", action="store_true", help="OCR the Pakistan Code Urdu laws with EasyOCR (resumable; ~8 h)")
    parser.add_argument("--colab-input", action="store_true", help="Build colab/urdu_ocr_input.zip (Urdu PDFs + manifest) for the Colab OCR notebook")
    parser.add_argument("--import-ocr", type=str, default=None, help="Merge page texts from the Colab output zip into data/ocr_text")
    parser.add_argument("--max-pages", type=int, default=None, help="With --ocr-urdu: stop after this many pages")
    parser.add_argument("--chunk-eval", action="store_true", help="Task 4: Run chunking strategy comparison benchmark")
    parser.add_argument("--index", action="store_true", help="Task 5: Build and persist BM25 and Vector indices")
    parser.add_argument("--search", type=str, default=None, help="Query the hybrid search engine")
    parser.add_argument("--court", type=str, default=None, help="Optional court filter for queries")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved results")
    
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.run_all:
        logger.info("=== Executing Complete Khan & Associates Day 1 Pipeline ===")
        run_corpus_collection()
        run_ocr_benchmark()
        run_chunking_benchmark()
        build_complete_indices()
        query_pipeline("punishment qatl-i-amd section 302", top_k=2)
        return
        
    if args.download_external:
        run_external_download()
    if args.collect:
        run_corpus_collection()
    if args.ocr_eval:
        run_ocr_benchmark()
    if args.colab_input:
        from src.ingestion.urdu_ocr import build_colab_input
        build_colab_input()
    if args.import_ocr:
        from src.ingestion.urdu_ocr import import_ocr_results
        import_ocr_results(args.import_ocr)
    if args.ocr_urdu:
        from src.ingestion.urdu_ocr import run_urdu_ocr
        run_urdu_ocr(max_pages=args.max_pages)
    if args.extract:
        extract_corpus()
    if args.chunk_eval:
        run_chunking_benchmark()
    if args.index:
        build_complete_indices()
    if args.search:
        query_pipeline(args.search, top_k=args.top_k, court_filter=args.court)

if __name__ == "__main__":
    main()
