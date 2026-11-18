"""
Unit tests for Task 4: chunking strategies.
"""
from evaluations.chunking_evaluation import fixed_chunks_with_boundaries
from src.chunking.fixed_chunker import FixedSizeChunker
from src.chunking.parent_child_chunker import ParentChildChunker
from src.chunking.section_chunker import SectionLevelChunker, split_words
from src.utils.schemas import (
    ChapterItem, JudgmentDocument, JudgmentParagraph, JudgmentParties, SectionItem, StatuteDocument,
)


def _statute(long_words: int = 900) -> StatuteDocument:
    return StatuteDocument(
        document_id="ACT1", act_name="Sample Act, 2010", year=2010, preamble="WHEREAS it is expedient.",
        chapters=[ChapterItem(chapter_number="Chapter I", chapter_title="Preliminary", sections=[
            SectionItem(section_number="Section 1", title="Short title", content="This Act may be called the Sample Act.",
                        page_start=2),
            SectionItem(section_number="Section 2", title="Definitions", content=("word " * long_words).strip(),
                        page_start=3),
        ])],
    )


def _judgment() -> JudgmentDocument:
    return JudgmentDocument(
        document_id="J1", case_number="C.P. 1/2024", court="Supreme Court of Pakistan", year=2024,
        parties=JudgmentParties(appellant_or_petitioner="A", respondent="B"), matter_id="SC:C-P-1-2024",
        holding="The petition is dismissed.", holding_page=4, outcome="dismissed",
        paragraphs=[JudgmentParagraph(number=str(i), text=f"Paragraph {i} " + "text " * 30, page=i) for i in range(1, 5)],
    )


def test_fixed_chunker():
    chunks = FixedSizeChunker(chunk_size=50, chunk_overlap=10).chunk_text("word " * 120, "DOC_TEST", "TestDoc")
    assert len(chunks) >= 2
    assert chunks[0].strategy == "fixed_size"
    assert chunks[0].metadata["chunk_index"] == 0


def test_split_words_balances_parts():
    parts = split_words("w " * 701, 350)
    assert len(parts) == 3 and max(len(p.split()) for p in parts) <= 350
    assert split_words("a b c", None) == ["a b c"]


def test_section_chunker_statute_keeps_labels_pages_and_size_limit():
    chunks = SectionLevelChunker(max_words=350).chunk_statute(_statute())
    sections = [c.metadata["section"] for c in chunks]
    assert sections[0] == "Preamble" and sections[1] == "Section 1"
    long_parts = [c for c in chunks if c.metadata["section"] == "Section 2"]
    assert len(long_parts) == 3 and [c.metadata["part"] for c in long_parts] == ["1/3", "2/3", "3/3"]
    assert all(c.metadata["page"] == 3 and c.metadata["act"] == "Sample Act, 2010" for c in long_parts)
    assert max(len(c.content.split()) for c in chunks) <= 350 + 20  # body limit + label line


def test_section_chunker_judgment_groups_paragraphs_with_metadata():
    chunks = SectionLevelChunker(judgment_min_words=60).chunk_judgment(_judgment())
    assert chunks[0].metadata["section"] == "Header & Parties"
    assert [c.metadata["section"] for c in chunks[1:]] == ["paras 1-2", "paras 3-4", "Holding"]
    assert chunks[1].metadata["page"] == 1 and chunks[-1].metadata["page"] == 4
    assert all(c.metadata["court"] == "Supreme Court of Pakistan" and c.metadata["matter_id"] == "SC:C-P-1-2024"
               for c in chunks)


def test_parent_child_chunker_links_children_to_whole_parents():
    parents, children = ParentChildChunker(child_token_target=80).chunk_statute(_statute(long_words=500))
    long_parent = next(p for p in parents if p.metadata["section"] == "Section 2")
    assert "part" not in long_parent.metadata  # parents are whole units
    kids = [c for c in children if c.metadata["parent_id"] == long_parent.chunk_id]
    assert len(kids) >= 3 and all(c.metadata["is_child"] for c in kids)
    assert max(len(c.content.split()) for c in children) <= 160 + 20


def test_fixed_size_boundary_crossings_are_counted():
    chunks, crossings = fixed_chunks_with_boundaries(_statute(long_words=30), FixedSizeChunker(chunk_size=20, chunk_overlap=0))
    assert crossings >= 1 and crossings < len(chunks)
