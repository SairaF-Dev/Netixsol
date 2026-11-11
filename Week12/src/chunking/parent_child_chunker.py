"""
Parent-Child Chunking Strategy for Legal Documents.
Creates 2-tier hierarchy:
- Parent: Full semantic context (Chapter/Section/Clause)
- Child: Highly targeted subsections/paragraphs carrying parent_id
"""

from typing import List, Dict, Any, Tuple
from src.utils.schemas import LegalChunk, StatuteDocument, JudgmentDocument, ContractDocument
from src.chunking.section_chunker import SectionLevelChunker

class ParentChildChunker:
    """Implements hierarchical parent-child indexing for precise retrieval with rich context."""

    def __init__(self, child_token_target: int = 80):
        self.child_token_target = child_token_target
        self.section_chunker = SectionLevelChunker()

    def chunk_statute(self, statute: StatuteDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        """Returns (parents, children)."""
        parents = []
        children = []
        doc_id = statute.document_id
        
        # Base parent chunks from section chunker
        section_parents = self.section_chunker.chunk_statute(statute)
        for p_idx, p in enumerate(section_parents):
            parent_id = f"{doc_id}_PARENT_{p_idx:03d}"
            p.chunk_id = parent_id
            p.strategy = "parent_child_parent"
            parents.append(p)
            
            # Split parent into child chunks (subsections / sentences)
            sub_units = [line.strip() for line in p.content.split("\n") if line.strip() and not line.startswith("ACT:")]
            child_idx = 0
            for unit in sub_units:
                child_id = f"{parent_id}_CHILD_{child_idx:02d}"
                child_meta = dict(p.metadata)
                child_meta.update({
                    "parent_id": parent_id,
                    "is_child": True,
                    "child_index": child_idx
                })
                children.append(LegalChunk(
                    chunk_id=child_id,
                    document_id=doc_id,
                    document_type="Statute",
                    strategy="parent_child_child",
                    content=unit,
                    token_count=len(unit.split()),
                    metadata=child_meta
                ))
                child_idx += 1
                
        return parents, children

    def chunk_judgment(self, judgment: JudgmentDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        parents = []
        children = []
        doc_id = judgment.document_id
        
        sec_parents = self.section_chunker.chunk_judgment(judgment)
        for p_idx, p in enumerate(sec_parents):
            parent_id = f"{doc_id}_PARENT_{p_idx:03d}"
            p.chunk_id = parent_id
            p.strategy = "parent_child_parent"
            parents.append(p)
            
            # Paragraph / statement children
            paras = [para.strip() for para in p.content.split("\n\n") if para.strip()]
            child_idx = 0
            for para in paras:
                child_id = f"{parent_id}_CHILD_{child_idx:02d}"
                child_meta = dict(p.metadata)
                child_meta.update({
                    "parent_id": parent_id,
                    "is_child": True,
                    "child_index": child_idx
                })
                children.append(LegalChunk(
                    chunk_id=child_id,
                    document_id=doc_id,
                    document_type="Judgment",
                    strategy="parent_child_child",
                    content=para,
                    token_count=len(para.split()),
                    metadata=child_meta
                ))
                child_idx += 1
                
        return parents, children

    def chunk_contract(self, contract: ContractDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        parents = []
        children = []
        doc_id = contract.document_id
        
        sec_parents = self.section_chunker.chunk_contract(contract)
        for p_idx, p in enumerate(sec_parents):
            parent_id = f"{doc_id}_PARENT_{p_idx:03d}"
            p.chunk_id = parent_id
            p.strategy = "parent_child_parent"
            parents.append(p)
            
            lines = [l.strip() for l in p.content.split("\n") if l.strip() and not l.startswith("CONTRACT:")]
            child_idx = 0
            for line in lines:
                child_id = f"{parent_id}_CHILD_{child_idx:02d}"
                child_meta = dict(p.metadata)
                child_meta.update({
                    "parent_id": parent_id,
                    "is_child": True,
                    "child_index": child_idx
                })
                children.append(LegalChunk(
                    chunk_id=child_id,
                    document_id=doc_id,
                    document_type="Contract",
                    strategy="parent_child_child",
                    content=line,
                    token_count=len(line.split()),
                    metadata=child_meta
                ))
                child_idx += 1
                
        return parents, children
