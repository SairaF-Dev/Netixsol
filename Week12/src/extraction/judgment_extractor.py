"""
Structure Extractor for Judgments (Court, Parties, Citations, Bench, Holding, Ratio Decidendi).
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.utils.schemas import JudgmentDocument, JudgmentParties
from src.utils.logger import setup_logger
from src.utils.file_utils import read_text, load_json

logger = setup_logger("judgment_extractor")

class JudgmentStructureExtractor:
    """Extracts judicial metadata, litigants, citations, and holding from court decisions."""

    def extract_from_text(self, text: str, doc_id: str = "JUD_UNKNOWN") -> JudgmentDocument:
        lines = text.strip().split("\n")
        
        court = "High Court / Supreme Court"
        case_number = "Unknown Case No."
        citation = ""
        matter_id = None
        petitioner = "Unknown Appellant"
        respondent = "Unknown Respondent"
        topic = "General Civil/Criminal Matter"
        statutes_cited = []
        bench = []
        holding = ""
        
        reading_bench = False
        reading_holding = False
        holding_lines = []
        
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
                
            # Court
            if line_str.startswith("IN THE "):
                court = line_str.replace("IN THE ", "").strip().title()
                continue
                
            # Case No
            if "Appeal No." in line_str or "Petition No." in line_str:
                case_number = line_str
                continue
                
            # Citation
            if line_str.startswith("Citation:") or line_str.startswith("CITATION:"):
                citation = line_str.split(":", 1)[1].strip()
                continue
                
            # Matter ID
            if line_str.startswith("Matter ID:") or line_str.startswith("MATTER ID:"):
                matter_id = line_str.split(":", 1)[1].strip()
                continue
                
            # Topic & Statutes
            if line_str.startswith("LEGAL TOPIC:"):
                topic = line_str.split(":", 1)[1].strip()
                continue
            if line_str.startswith("STATUTES CITED:"):
                raw_stats = line_str.split(":", 1)[1].strip()
                statutes_cited = [s.strip() for s in raw_stats.split(",") if s.strip()]
                continue
                
            # Parties
            if "... Appellant" in line_str or "... Petitioner" in line_str:
                petitioner = line_str.split("...")[0].strip()
                continue
            if "... Respondent" in line_str:
                respondent = line_str.split("...")[0].strip()
                continue
                
            # Bench
            if line_str.startswith("Present:"):
                reading_bench = True
                continue
            if reading_bench:
                if line_str.startswith("*"):
                    bench.append(line_str.replace("*", "").strip())
                elif "No." in line_str or "BETWEEN" in line_str:
                    reading_bench = False
                    
            # Holding
            if "HOLDING & RATIO DECIDENDI:" in line_str:
                reading_holding = True
                continue
            if reading_holding:
                if line_str.startswith("Decided on:"):
                    reading_holding = False
                else:
                    holding_lines.append(line_str)
                    
        holding = " ".join(holding_lines).strip()
        
        # Determine year
        year = 2023
        year_match = re.search(r"\b(20\d\d|19\d\d)\b", f"{citation} {case_number}")
        if year_match:
            year = int(year_match.group(1))

        return JudgmentDocument(
            document_id=doc_id,
            case_number=case_number,
            court=court,
            year=year,
            date_of_judgment=f"{year}-10-15",
            bench=bench,
            parties=JudgmentParties(
                appellant_or_petitioner=petitioner,
                respondent=respondent
            ),
            citations=[citation] if citation else [],
            matter_id=matter_id,
            legal_topics=[topic],
            statutes_cited=statutes_cited,
            issues=[
                "Whether the impugned decision conforms to statutory mandates and principles of due process?"
            ],
            holding=holding,
            full_text=text
        )

    def extract_from_file(self, file_path: str | Path) -> JudgmentDocument:
        path = Path(file_path)
        if path.suffix == ".json":
            data = load_json(path)
            return JudgmentDocument.model_validate(data)
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
