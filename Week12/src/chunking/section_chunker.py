"""
Section-Aware Hierarchical Chunking for Legal Documents.
Splits strictly at legal domain boundaries (Act -> Section, Case -> Ratio/Issues, Contract -> Clauses).
"""

from typing import List, Dict, Any, Union
from src.utils.schemas import LegalChunk, StatuteDocument, JudgmentDocument, ContractDocument

class SectionLevelChunker:
    """Domain-aware chunker that respects statutory sections, judicial ratios, and contractual clauses."""

    def chunk_statute(self, statute: StatuteDocument) -> List[LegalChunk]:
        chunks = []
        doc_id = statute.document_id
        chunk_idx = 0
        
        # Preamble chunk
        if statute.preamble:
            preamble_words = statute.preamble.split()
            chunks.append(LegalChunk(
                chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
                document_id=doc_id,
                document_type="Statute",
                strategy="section_level",
                content=f"ACT: {statute.act_name}\nPREAMBLE:\n{statute.preamble}",
                token_count=len(preamble_words),
                metadata={
                    "act": statute.act_name,
                    "year": statute.year,
                    "section": "Preamble",
                    "chapter": "Preamble",
                    "chunk_index": chunk_idx
                }
            ))
            chunk_idx += 1

        # Section-level chunks
        for chapter in statute.chapters:
            for sec in chapter.sections:
                content_parts = [
                    f"ACT: {statute.act_name}",
                    f"CHAPTER: {chapter.chapter_number} - {chapter.chapter_title}",
                    f"SECTION: {sec.section_number} - {sec.title}",
                    sec.content
                ]
                for sub in sec.subsections:
                    content_parts.append(f"  * {sub}")
                
                full_content = "\n".join(content_parts)
                words = full_content.split()
                
                chunks.append(LegalChunk(
                    chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
                    document_id=doc_id,
                    document_type="Statute",
                    strategy="section_level",
                    content=full_content,
                    token_count=len(words),
                    metadata={
                        "act": statute.act_name,
                        "year": statute.year,
                        "chapter": chapter.chapter_number,
                        "section": sec.section_number,
                        "section_title": sec.title,
                        "chunk_index": chunk_idx
                    }
                ))
                chunk_idx += 1
                
        return chunks

    def chunk_judgment(self, judgment: JudgmentDocument) -> List[LegalChunk]:
        chunks = []
        doc_id = judgment.document_id
        chunk_idx = 0
        
        # 1. Header & Parties Chunk
        header_text = (
            f"COURT: {judgment.court}\n"
            f"CASE NUMBER: {judgment.case_number}\n"
            f"CITATION: {', '.join(judgment.citations)}\n"
            f"BENCH: {', '.join(judgment.bench)}\n"
            f"PARTIES: {judgment.parties.appellant_or_petitioner} v. {judgment.parties.respondent}\n"
            f"TOPIC: {', '.join(judgment.legal_topics)}\n"
            f"STATUTES CITED: {', '.join(judgment.statutes_cited)}"
        )
        chunks.append(LegalChunk(
            chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
            document_id=doc_id,
            document_type="Judgment",
            strategy="section_level",
            content=header_text,
            token_count=len(header_text.split()),
            metadata={
                "court": judgment.court,
                "case_number": judgment.case_number,
                "year": judgment.year,
                "citation": judgment.citations[0] if judgment.citations else "",
                "matter_id": judgment.matter_id or "",
                "section": "Header & Parties",
                "chunk_index": chunk_idx
            }
        ))
        chunk_idx += 1

        # 2. Issues & Reasoning Chunk
        reasoning_text = (
            f"CASE: {judgment.case_number} ({judgment.citations[0] if judgment.citations else ''})\n"
            f"ISSUES FOR DETERMINATION:\n" + "\n".join([f"- {issue}" for issue in judgment.issues]) + "\n\n"
            f"RECORD & SUBMISSIONS:\n{judgment.full_text}"
        )
        chunks.append(LegalChunk(
            chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
            document_id=doc_id,
            document_type="Judgment",
            strategy="section_level",
            content=reasoning_text,
            token_count=len(reasoning_text.split()),
            metadata={
                "court": judgment.court,
                "case_number": judgment.case_number,
                "year": judgment.year,
                "matter_id": judgment.matter_id or "",
                "section": "Reasoning & Submissions",
                "chunk_index": chunk_idx
            }
        ))
        chunk_idx += 1

        # 3. Holding & Ratio Decidendi Chunk
        holding_text = (
            f"CASE: {judgment.case_number}\n"
            f"HOLDING & RATIO DECIDENDI:\n{judgment.holding}"
        )
        chunks.append(LegalChunk(
            chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
            document_id=doc_id,
            document_type="Judgment",
            strategy="section_level",
            content=holding_text,
            token_count=len(holding_text.split()),
            metadata={
                "court": judgment.court,
                "case_number": judgment.case_number,
                "year": judgment.year,
                "matter_id": judgment.matter_id or "",
                "section": "Holding & Ratio Decidendi",
                "chunk_index": chunk_idx
            }
        ))
        
        return chunks

    def chunk_contract(self, contract: ContractDocument) -> List[LegalChunk]:
        chunks = []
        doc_id = contract.document_id
        chunk_idx = 0
        
        # Preamble & Parties Chunk
        meta_text = (
            f"CONTRACT: {contract.contract_title}\n"
            f"TYPE: {contract.contract_type}\n"
            f"PARTIES: {' and '.join(contract.parties)}\n"
            f"EFFECTIVE DATE: {contract.effective_date}\n"
            f"GOVERNING LAW: {contract.governing_law}\n"
            f"DISPUTE RESOLUTION: {contract.dispute_resolution or 'N/A'}"
        )
        chunks.append(LegalChunk(
            chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
            document_id=doc_id,
            document_type="Contract",
            strategy="section_level",
            content=meta_text,
            token_count=len(meta_text.split()),
            metadata={
                "contract_title": contract.contract_title,
                "contract_type": contract.contract_type,
                "section": "Recitals & Parties",
                "governing_law": contract.governing_law,
                "chunk_index": chunk_idx
            }
        ))
        chunk_idx += 1
        
        # Clause Chunks
        for clause in contract.clauses:
            clause_content = (
                f"CONTRACT: {contract.contract_title}\n"
                f"{clause.clause_title}\n"
                f"{clause.text}"
            )
            chunks.append(LegalChunk(
                chunk_id=f"{doc_id}_SEC_{chunk_idx:03d}",
                document_id=doc_id,
                document_type="Contract",
                strategy="section_level",
                content=clause_content,
                token_count=len(clause_content.split()),
                metadata={
                    "contract_title": contract.contract_title,
                    "section": clause.clause_id,
                    "clause_title": clause.clause_title,
                    "governing_law": contract.governing_law,
                    "chunk_index": chunk_idx
                }
            ))
            chunk_idx += 1
            
        return chunks
