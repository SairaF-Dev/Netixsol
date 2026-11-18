"""
Parent-child chunking for legal documents.

Parents are whole legal units (a full section, judgment paragraph group or
contract clause, not split by length). Children are ~`child_token_target`-word
pieces of a parent cut at sentence boundaries; each child carries `parent_id`
so a retriever can match the child and return the full parent.
"""

import re
from typing import List, Tuple

from src.chunking.section_chunker import SectionLevelChunker, split_words
from src.utils.schemas import ContractDocument, JudgmentDocument, LegalChunk, StatuteDocument

_SENTENCE_END = re.compile(r"(?<=[.;:?!])\s+(?=[A-Z(\[\"“])")


class ParentChildChunker:
    """Two-tier chunks: whole legal units as parents, sentence-window children."""

    def __init__(self, child_token_target: int = 80):
        self.child_token_target = child_token_target
        self.section_chunker = SectionLevelChunker(max_words=None)

    def _children(self, parent: LegalChunk) -> List[LegalChunk]:
        header, _, body = parent.content.partition("\n")
        if not body:
            header, body = "", parent.content
        sentences = []
        for sentence in _SENTENCE_END.split(body):
            # Tables and definition lists can run for pages without a sentence end.
            sentences.extend(split_words(sentence, self.child_token_target * 2))
        pieces: List[str] = []
        current: List[str] = []
        for sentence in sentences:
            current.append(sentence)
            if sum(len(s.split()) for s in current) >= self.child_token_target:
                pieces.append(" ".join(current))
                current = []
        if current:
            pieces.append(" ".join(current))

        children = []
        for index, piece in enumerate(pieces):
            content = f"{header}\n{piece}".strip() if header else piece
            meta = dict(parent.metadata)
            meta.update({"parent_id": parent.chunk_id, "is_child": True, "child_index": index})
            children.append(LegalChunk(
                chunk_id=f"{parent.chunk_id}_CHILD_{index:03d}",
                document_id=parent.document_id,
                document_type=parent.document_type,
                strategy="parent_child_child",
                content=content,
                token_count=len(content.split()),
                metadata=meta,
            ))
        return children

    def _split(self, parents: List[LegalChunk]) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        children: List[LegalChunk] = []
        for index, parent in enumerate(parents):
            parent.chunk_id = f"{parent.document_id}_PARENT_{index:04d}"
            parent.strategy = "parent_child_parent"
            children.extend(self._children(parent))
        return parents, children

    def chunk_statute(self, statute: StatuteDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        return self._split(self.section_chunker.chunk_statute(statute))

    def chunk_judgment(self, judgment: JudgmentDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        return self._split(self.section_chunker.chunk_judgment(judgment))

    def chunk_contract(self, contract: ContractDocument) -> Tuple[List[LegalChunk], List[LegalChunk]]:
        return self._split(self.section_chunker.chunk_contract(contract))
