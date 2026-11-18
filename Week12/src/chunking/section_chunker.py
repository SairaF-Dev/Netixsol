"""
Section-aware chunking for legal documents.

Chunks follow legal boundaries: statute sections/articles/rules, judgment
paragraphs (plus a header and a holding chunk), and contract clauses. A unit
longer than `max_words` is split into consecutive parts that keep the same
legal label, so no chunk crosses a boundary and none exceeds the embedding
model's input length. Every chunk carries the metadata required for filtering:
act / section / court / year / page / matter_id where applicable.
"""

from typing import Any, Dict, List, Optional

from src.utils.schemas import ContractDocument, JudgmentDocument, LegalChunk, StatuteDocument


def split_words(text: str, max_words: Optional[int]) -> List[str]:
    """Split text into consecutive pieces of at most max_words words (None = no split)."""
    words = text.split()
    if not max_words or len(words) <= max_words:
        return [" ".join(words)] if words else []
    # Spread words evenly so the last part is not a tiny remainder.
    parts = -(-len(words) // max_words)
    size = -(-len(words) // parts)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


class SectionLevelChunker:
    """Domain-aware chunker for statutory sections, judgment paragraphs and contract clauses."""

    def __init__(self, max_words: Optional[int] = 350, judgment_min_words: int = 80):
        self.max_words = max_words
        self.judgment_min_words = judgment_min_words

    def _emit(self, chunks: List[LegalChunk], doc_id: str, doc_type: str, header: str,
              body: str, metadata: Dict[str, Any]) -> None:
        """Append one chunk per part of body; header (a short label line) prefixes every part."""
        parts = split_words(body, self.max_words) or [""]
        for part_index, part in enumerate(parts):
            content = f"{header}\n{part}".strip()
            meta = dict(metadata)
            meta["chunk_index"] = len(chunks)
            if len(parts) > 1:
                meta["part"] = f"{part_index + 1}/{len(parts)}"
            chunks.append(LegalChunk(
                chunk_id=f"{doc_id}_SEC_{len(chunks):04d}",
                document_id=doc_id,
                document_type=doc_type,
                strategy="section_level",
                content=content,
                token_count=len(content.split()),
                metadata=meta,
            ))

    def chunk_statute(self, statute: StatuteDocument) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []
        doc_id = statute.document_id
        base = {"act": statute.act_name, "year": statute.year}
        if statute.language == "Urdu":
            # OCR'd Urdu law: one unit per page (see urdu_statute_extractor).
            for sec in (s for chapter in statute.chapters for s in chapter.sections):
                self._emit(chunks, doc_id, "Statute", f"{statute.act_name} | صفحہ {sec.page_start}", sec.content,
                           {**base, "language": "Urdu", "section": None, "page": sec.page_start})
            return chunks
        if statute.preamble:
            self._emit(chunks, doc_id, "Statute", f"{statute.act_name} - Preamble", statute.preamble,
                       {**base, "section": "Preamble", "chapter": "Preamble", "page": None})
        for chapter in statute.chapters:
            for sec in chapter.sections:
                body = " ".join([sec.content] + sec.subsections).strip()
                header = f"{statute.act_name} | {chapter.chapter_number} {chapter.chapter_title} | {sec.section_number}. {sec.title}"
                self._emit(chunks, doc_id, "Statute", header, body, {
                    **base, "chapter": chapter.chapter_number, "section": sec.section_number,
                    "section_title": sec.title, "page": sec.page_start,
                })
        return chunks

    def chunk_judgment(self, judgment: JudgmentDocument) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []
        doc_id = judgment.document_id
        base = {
            "court": judgment.court,
            "case_number": judgment.case_number,
            "year": judgment.year,
            "matter_id": judgment.matter_id or "",
            "citation": judgment.citations[0] if judgment.citations else "",
        }
        parties = f"{judgment.parties.appellant_or_petitioner} v. {judgment.parties.respondent}"
        label = f"{judgment.court} | {judgment.case_number} | {parties}"

        header = "\n".join(line for line in [
            f"COURT: {judgment.court}",
            f"CASE NUMBER: {judgment.case_number}",
            f"PARTIES: {parties}",
            f"BENCH: {', '.join(judgment.bench)}" if judgment.bench else "",
            f"DATE OF HEARING: {judgment.date_of_hearing}" if judgment.date_of_hearing else "",
            f"DATE OF DECISION: {judgment.date_of_judgment}" if judgment.date_of_judgment else "",
            f"CITATIONS: {', '.join(judgment.citations[:10])}" if judgment.citations else "",
            f"STATUTES CITED: {', '.join(judgment.statutes_cited[:10])}" if judgment.statutes_cited else "",
            f"OUTCOME: {judgment.outcome}" if judgment.outcome else "",
        ] if line)
        self._emit(chunks, doc_id, "Judgment", "", header, {**base, "section": "Header & Parties", "page": 1})

        # Group short numbered paragraphs so each chunk has enough context.
        group: List[Any] = []
        def flush() -> None:
            if not group:
                return
            numbers = [p.number for p in group if p.number]
            span = f"paras {numbers[0]}-{numbers[-1]}" if len(numbers) > 1 else (
                f"para {numbers[0]}" if numbers else "opening")
            self._emit(chunks, doc_id, "Judgment", f"{label} | {span}",
                       " ".join(p.text for p in group),
                       {**base, "section": span, "page": group[0].page})
            group.clear()

        for paragraph in judgment.paragraphs:
            group.append(paragraph)
            if sum(len(p.text.split()) for p in group) >= self.judgment_min_words:
                flush()
        flush()

        if judgment.holding:
            self._emit(chunks, doc_id, "Judgment", f"{label} | HOLDING", judgment.holding,
                       {**base, "section": "Holding", "outcome": judgment.outcome or "",
                        "page": judgment.holding_page})
        return chunks

    def chunk_contract(self, contract: ContractDocument) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []
        doc_id = contract.document_id
        base = {"contract_title": contract.contract_title, "contract_type": contract.contract_type,
                "governing_law": contract.governing_law or ""}
        summary = "\n".join(line for line in [
            f"CONTRACT: {contract.contract_title}",
            f"TYPE: {contract.contract_type}",
            f"PARTIES: {' and '.join(contract.parties)}" if contract.parties else "",
            f"EFFECTIVE DATE: {contract.effective_date}" if contract.effective_date else "",
            f"GOVERNING LAW: {contract.governing_law}" if contract.governing_law else "",
            f"DISPUTE RESOLUTION: {contract.dispute_resolution}" if contract.dispute_resolution else "",
        ] if line)
        self._emit(chunks, doc_id, "Contract", "", summary, {**base, "section": "Recitals & Parties", "page": 1})
        for clause in contract.clauses:
            self._emit(chunks, doc_id, "Contract", f"{contract.contract_title} | {clause.clause_id}. {clause.clause_title}",
                       clause.text, {**base, "section": clause.clause_id, "clause_title": clause.clause_title,
                                     "page": clause.page_number})
        return chunks
