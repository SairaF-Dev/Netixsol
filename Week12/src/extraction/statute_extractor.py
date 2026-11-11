"""
Structure Extractor for Statutes (Act/Ordinance -> Chapters -> Sections -> Subsections).
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.utils.schemas import StatuteDocument, ChapterItem, SectionItem
from src.utils.logger import setup_logger
from src.utils.file_utils import read_text, load_json

logger = setup_logger("statute_extractor")

class StatuteStructureExtractor:
    """Extracts structured Act/Chapter/Section hierarchy from statutory documents."""

    def extract_from_text(self, text: str, doc_id: str = "STAT_UNKNOWN") -> StatuteDocument:
        lines = text.strip().split("\n")
        
        act_name = "Unknown Act"
        year = 2000
        preamble = ""
        raw_chapters = []
        
        current_chapter: Optional[Dict[str, Any]] = None
        current_section: Optional[Dict[str, Any]] = None
        reading_preamble = False
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            # Act Name detection
            if line_str.startswith("ACT:") or line_str.startswith("Act:"):
                act_name = line_str.split(":", 1)[1].strip()
                # Extract year from title if present
                year_match = re.search(r"\b(18\d\d|19\d\d|20\d\d)\b", act_name)
                if year_match:
                    year = int(year_match.group(1))
                continue
                
            if line_str.startswith("YEAR:") or line_str.startswith("Year:"):
                try:
                    year = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass
                continue
                
            if line_str.startswith("PREAMBLE:") or line_str.startswith("Preamble:"):
                reading_preamble = True
                continue
                
            # Chapter / Part detection
            if line_str.startswith("---") and ("Part" in line_str or "Chapter" in line_str):
                reading_preamble = False
                ch_title_clean = line_str.replace("---", "").strip()
                parts = ch_title_clean.split(":", 1)
                ch_num = parts[0].strip()
                ch_name = parts[1].strip() if len(parts) > 1 else ch_num
                
                current_chapter = {
                    "chapter_number": ch_num,
                    "chapter_title": ch_name,
                    "sections": []
                }
                raw_chapters.append(current_chapter)
                current_section = None
                continue
                
            # Section / Article detection (e.g. "Section 302: Punishment of Qatl-i-amd" or "Article 9: Security of person")
            sec_match = re.match(r"^(Section\s+[\dA-Za-z\-]+|Article\s+[\dA-Za-z\-]+)\s*[:\-]\s*(.*)$", line_str, re.IGNORECASE)
            if sec_match:
                reading_preamble = False
                sec_num = sec_match.group(1).strip()
                sec_title = sec_match.group(2).strip()
                
                if current_chapter is None:
                    current_chapter = {
                        "chapter_number": "General",
                        "chapter_title": "General Provisions",
                        "sections": []
                    }
                    raw_chapters.append(current_chapter)
                    
                current_section = {
                    "section_number": sec_num,
                    "title": sec_title,
                    "content": "",
                    "subsections": []
                }
                current_chapter["sections"].append(current_section)
                continue
                
            # Subsection or bullet
            if line_str.startswith("*") or line_str.startswith("-") or re.match(r"^\(\d+\)", line_str):
                if current_section is not None:
                    sub_clean = re.sub(r"^[\*\-]\s*", "", line_str).strip()
                    current_section["subsections"].append(sub_clean)
                    continue
                    
            if reading_preamble:
                preamble += (" " + line_str if preamble else line_str)
            elif current_section is not None:
                current_section["content"] += (" " + line_str if current_section["content"] else line_str)

        # Convert to Pydantic
        chapter_models = []
        for ch in raw_chapters:
            section_models = [
                SectionItem(
                    section_number=s["section_number"],
                    title=s["title"],
                    content=s["content"].strip(),
                    subsections=s["subsections"]
                )
                for s in ch["sections"]
            ]
            chapter_models.append(ChapterItem(
                chapter_number=ch["chapter_number"],
                chapter_title=ch["chapter_title"],
                sections=section_models
            ))

        return StatuteDocument(
            document_id=doc_id,
            act_name=act_name,
            year=year,
            preamble=preamble.strip(),
            chapters=chapter_models,
            raw_text=text
        )

    def extract_from_file(self, file_path: str | Path) -> StatuteDocument:
        path = Path(file_path)
        if path.suffix == ".json":
            data = load_json(path)
            return StatuteDocument.model_validate(data)
        elif path.suffix in [".txt", ".pdf"]:
            text = read_text(path) if path.suffix == ".txt" else ""
            if not text and path.suffix == ".pdf":
                import fitz
                doc = fitz.open(str(path))
                text = "\n".join([page.get_text() for page in doc])
                doc.close()
            return self.extract_from_text(text, doc_id=path.stem)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
