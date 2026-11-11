"""
Structure Extractor for Contracts (Title, Type, Parties, Dates, Clauses).
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.utils.schemas import ContractDocument, ContractClause
from src.utils.logger import setup_logger
from src.utils.file_utils import read_text, load_json

logger = setup_logger("contract_extractor")

class ContractStructureExtractor:
    """Extracts contractual clauses, parties, governing law, and key terms into structured JSON."""

    def extract_from_text(self, text: str, doc_id: str = "CONT_UNKNOWN") -> ContractDocument:
        lines = text.strip().split("\n")
        
        contract_title = "Commercial Agreement"
        contract_type = "Commercial Contract"
        parties = []
        governing_law = "Laws of the Islamic Republic of Pakistan"
        dispute_resolution = "Arbitration Act 1940"
        clauses = []
        
        current_clause: Optional[Dict[str, Any]] = None
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            if line_str.startswith("CONTRACT:") or line_str.startswith("AGREEMENT:"):
                contract_title = line_str.split(":", 1)[1].strip()
                continue
            if line_str.startswith("TYPE:"):
                contract_type = line_str.split(":", 1)[1].strip()
                continue
            if line_str.startswith("PARTIES:"):
                raw_parties = line_str.split(":", 1)[1].strip()
                parties = [p.strip() for p in raw_parties.split(" and ") if p.strip()]
                continue
                
            # Clause header detection (e.g. "Clause 1 - Definition" or "Clause 3 - Intellectual Property")
            clause_match = re.match(r"^(Clause\s+\d+|Article\s+\d+|Section\s+\d+)\s*[-:]\s*(.*)$", line_str, re.IGNORECASE)
            if clause_match:
                c_id = clause_match.group(1).strip()
                c_title = clause_match.group(2).strip()
                current_clause = {
                    "clause_id": c_id,
                    "clause_title": line_str,
                    "text": ""
                }
                clauses.append(current_clause)
                continue
                
            if current_clause is not None:
                current_clause["text"] += (" " + line_str if current_clause["text"] else line_str)
                if "Arbitration" in line_str:
                    dispute_resolution = "Arbitration in accordance with Arbitration Act 1940"
                if "Delaware" in line_str:
                    governing_law = "Laws of the State of Delaware, United States"

        clause_models = [
            ContractClause(
                clause_id=c["clause_id"],
                clause_title=c["clause_title"],
                text=c["text"].strip()
            )
            for c in clauses
        ]

        return ContractDocument(
            document_id=doc_id,
            contract_title=contract_title,
            contract_type=contract_type,
            parties=parties,
            effective_date="2024-01-01",
            governing_law=governing_law,
            dispute_resolution=dispute_resolution,
            clauses=clause_models,
            raw_text=text
        )

    def extract_from_file(self, file_path: str | Path) -> ContractDocument:
        path = Path(file_path)
        if path.suffix == ".json":
            data = load_json(path)
            return ContractDocument.model_validate(data)
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
