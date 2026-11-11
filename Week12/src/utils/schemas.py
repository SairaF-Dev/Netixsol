"""
Pydantic schemas and data models for Khan & Associates Legal Assistant Pipeline.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AliasChoices

class InventoryRecord(BaseModel):
    """Schema for document inventory catalog."""
    document_id: str = Field(validation_alias=AliasChoices("document_id", "doc_id"))
    title: str
    type: str  # Statute, Judgment, Contract, Scanned/Urdu
    language: str  # English, Urdu, Bilingual
    pages: int
    source: str
    file_path: str

class SectionItem(BaseModel):
    """Statute section or sub-section model."""
    section_number: str
    title: str
    content: str
    subsections: List[str] = Field(default_factory=list)

class ChapterItem(BaseModel):
    """Statute chapter model."""
    chapter_number: str
    chapter_title: str
    sections: List[SectionItem] = Field(default_factory=list)

class StatuteDocument(BaseModel):
    """Structured representation of a Statute (Act/Ordinance)."""
    document_id: str = Field(validation_alias=AliasChoices("document_id", "doc_id"))
    act_name: str
    act_number: Optional[str] = None
    year: int
    jurisdiction: str = "Federal / Pakistan"
    preamble: str
    chapters: List[ChapterItem] = Field(default_factory=list)
    raw_text: Optional[str] = None

class JudgmentParties(BaseModel):
    """Parties in a judicial decision."""
    appellant_or_petitioner: str
    respondent: str

class JudgmentDocument(BaseModel):
    """Structured representation of a Case Law Judgment."""
    document_id: str = Field(validation_alias=AliasChoices("document_id", "doc_id"))
    case_number: str
    court: str
    year: int
    date_of_judgment: str
    bench: List[str] = Field(default_factory=list)
    parties: JudgmentParties
    citations: List[str] = Field(default_factory=list)
    matter_id: Optional[str] = None
    legal_topics: List[str] = Field(default_factory=list)
    statutes_cited: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    holding: str
    full_text: str

class ContractClause(BaseModel):
    """Individual clause within a legal contract."""
    clause_id: str
    clause_title: str
    text: str
    page_number: Optional[int] = None

class ContractDocument(BaseModel):
    """Structured representation of a commercial legal contract."""
    document_id: str = Field(validation_alias=AliasChoices("document_id", "doc_id"))
    contract_title: str
    contract_type: str  # NDA, MSA, SLA, Employment, Lease, License
    parties: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    governing_law: str = "Laws of the Islamic Republic of Pakistan"
    dispute_resolution: Optional[str] = None
    clauses: List[ContractClause] = Field(default_factory=list)
    raw_text: Optional[str] = None

class LegalChunk(BaseModel):
    """Legal chunk model supporting fixed, section, and parent-child chunking."""
    chunk_id: str
    document_id: str
    document_type: str  # Statute, Judgment, Contract, Scanned
    strategy: str  # fixed_size, section_level, parent_child
    content: str
    token_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # metadata includes: act, section, court, year, page, matter_id, parent_id
