"""
Automated Corpus Collector for Khan & Associates Legal Assistant Pipeline.
Lists (real documents are read from data/, never generated):
- Statutes: official Pakistan Code PDFs (data/raw/pakistani_laws) + REAL_STAT_001
- Judgments: Supreme Court and Lahore High Court PDFs (data/scp_judgments_pdfs)
- Contracts: 30 downloaded REAL_CUAD + one CUAD contract per remaining category
  (data/contracts/cuad, see cuad_real_manifest.csv) + 20 generated synthetic contracts
- Scanned / Urdu: 10 real Pakistan Code Urdu benchmark pages + 40 Pakistan Code Urdu laws
Generates inventory.csv listing document_id, title, type, language, pages, source, file_path.
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import fitz
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Unicode-capable font for Urdu and English legal scripts
try:
    pdfmetrics.registerFont(TTFont("Tahoma", "C:/Windows/Fonts/tahoma.ttf"))
    FONT_NAME = "Tahoma"
except Exception:
    FONT_NAME = "Helvetica"

from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory, save_json, write_text

logger = setup_logger("corpus_collector")

DATA_DIR = Path("data")
CONTRACTS_DIR = DATA_DIR / "contracts"
CUAD_DIR = CONTRACTS_DIR / "cuad"
SYNTHETIC_CONTRACTS_DIR = CONTRACTS_DIR / "synthetic"
SCANNED_URDU_DIR = DATA_DIR / "scanned_urdu"
BENCHMARK_DIR = SCANNED_URDU_DIR / "benchmark_cer"
URDU_LAWS_DIR = DATA_DIR / "pakistani_urdu_code"
SOURCE_CATALOG = DATA_DIR / "source_catalog.csv"
REAL_LAWS_DIR = DATA_DIR / "raw" / "pakistani_laws"
REAL_JUDGMENTS_DIR = DATA_DIR / "scp_judgments_pdfs"
CUAD_REAL_MANIFEST = CUAD_DIR / "cuad_real_manifest.csv"

# Official law PDFs and their titles. The Constitution copy in that folder is not
# listed because REAL_STAT_001 (National Assembly PDF) already covers it.
REAL_STATUTE_TITLES = {
    "ANTI_MONEY_LAUNDERING_ACT_2010.pdf": "Anti-Money Laundering Act, 2010",
    "Defense_Forces_of_Pakistan_Act_2026.pdf": "Defense Forces of Pakistan Act, 2026",
    "Federal_Board_of_Revenue_Act_2007.pdf": "Federal Board of Revenue Act, 2007",
    "INCOME_TAX_ORDINANCE_2001.pdf": "Income Tax Ordinance, 2001 (Income Tax Manual, amended up to 30 June 2026)",
    "National_Command_Authority_(NCA)_Act_2010.pdf": "National Command Authority Act, 2010",
    "National_Security_Council_Act_2004.pdf": "National Security Council Act, 2004",
    "THE_CIVIL_SERVANTS_ACT_1973.pdf": "Civil Servants Act, 1973",
    "THE_CODE_OF_CIVIL_PROCEDURE_1908.pdf": "Code of Civil Procedure, 1908",
    "THE_MUSLIM_FAMILY_LAWS_ORDINANCE_1961.pdf": "Muslim Family Laws Ordinance, 1961",
    "administrator92ada0936848e501425591b4ad0cd417.pdf": "Pakistan Penal Code, 1860",
    "the_anti_terrorism_act_1997.pdf": "Anti-Terrorism Act, 1997",
}

def generate_pdf_from_text(text: str, output_path: Path, is_scanned_look: bool = False) -> None:
    """Generate a PDF; rasterize pages when creating a scanned-document fixture."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Optional scan noise/background
    if is_scanned_look:
        c.setFillColor(colors.HexColor("#FBF9F1"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#222222"))
    else:
        c.setFillColor(colors.black)
    
    # Title / Header
    c.setFont(FONT_NAME, 13)
    c.drawString(50, height - 50, "KHAN & ASSOCIATES - LEGAL REPOSITORY")
    c.setLineWidth(1)
    c.line(50, height - 55, width - 50, height - 55)
    
    c.setFont(FONT_NAME, 9)
    lines = text.split("\n")
    y = height - 80
    
    for line in lines:
        # Wrap long lines simply
        while len(line) > 95:
            segment = line[:95]
            line = line[95:]
            c.drawString(50, y, segment)
            y -= 14
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont(FONT_NAME, 9)
        if line.strip():
            c.drawString(50, y, line)
            y -= 14
        else:
            y -= 8
            
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont(FONT_NAME, 9)
            
    c.save()

    if is_scanned_look:
        rasterized_path = output_path.with_name(f"{output_path.stem}.rasterized.pdf")
        with fitz.open(str(output_path)) as source, fitz.open() as rasterized:
            for source_page in source:
                pixmap = source_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                page = rasterized.new_page(
                    width=source_page.rect.width,
                    height=source_page.rect.height,
                )
                page.insert_image(page.rect, pixmap=pixmap)
            rasterized.save(str(rasterized_path), garbage=4, deflate=True)
        rasterized_path.replace(output_path)

def collect_synthetic_contracts() -> List[Dict[str, Any]]:
    """Builds the 20 synthetic Pakistani contracts the brief asks for (PDF + TXT + JSON)."""
    ensure_directory(SYNTHETIC_CONTRACTS_DIR)
    records = []

    logger.info("Generating 20 Synthetic Pakistani corporate commercial contracts...")
    for idx in range(1, 21):
        doc_id = f"CONT_SYNTH_{idx:03d}"
        ctype = "Service Level Agreement" if idx % 2 == 0 else "Commercial Supply Agreement"
        title = f"Pakistani Corporate {ctype} (Agreement #{idx})"
        parties = [f"M/s Indus Infotech Solutions (Pvt) Ltd, Karachi", f"Pak Telecom Enterprises #{idx}, Islamabad"]
        
        clauses = [
            {"clause_id": "CL_01", "clause_title": "Recitals and Preamble", "text": "WHEREAS the Client desires to procure specialized engineering and information technology services, and the Contractor represents that it possesses the requisite expertise, equipment, and personnel to deliver the same under Pakistani regulatory standards."},
            {"clause_id": "CL_02", "clause_title": "Services and Scope of Work", "text": "The Contractor shall faithfully execute the tasks stipulated in Schedule A in compliance with Pakistani technical standards, ISO certifications, and applicable guidelines."},
            {"clause_id": "CL_03", "clause_title": "Payment Terms, Invoicing & Withholding Tax", "text": "Invoices shall be submitted monthly and paid within thirty (30) days in Pakistani Rupees (PKR). Payments shall be subject to deduction of applicable withholding income tax and provincial sales tax on services in accordance with Income Tax Ordinance 2001 and Provincial Revenue Authorities."},
            {"clause_id": "CL_04", "clause_title": "Confidentiality and Data Protection", "text": "Both parties agree to protect all business proprietary secrets and customer data. Neither party shall disclose confidential materials without prior written consent, surviving termination for seven (7) years."},
            {"clause_id": "CL_05", "clause_title": "Indemnification and Limitation of Liability", "text": "The Contractor shall indemnify and hold harmless the Client against any third-party claims arising from negligence, willful misconduct, or infringement of intellectual property rights in Pakistan."},
            {"clause_id": "CL_06", "clause_title": "Governing Law and Dispute Resolution", "text": "This Agreement shall be governed by and construed in accordance with the Laws of the Islamic Republic of Pakistan. Any dispute arising out of or in connection with this contract shall be referred to arbitration in Karachi/Lahore in accordance with the Arbitration Act, 1940."}
        ]
        
        contract_data = {
            "document_id": doc_id,
            "contract_title": title,
            "contract_type": ctype,
            "parties": parties,
            "effective_date": f"2024-{(idx % 12) + 1:02d}-01",
            "governing_law": "Laws of the Islamic Republic of Pakistan",
            "dispute_resolution": "Arbitration Act 1940 (Karachi / Lahore Seat)",
            "clauses": clauses
        }
        
        full_text = f"AGREEMENT: {title}\nTYPE: {ctype}\nPARTIES: {' and '.join(parties)}\n\n"
        for c in clauses:
            full_text += f"{c['clause_title']}\n{c['text']}\n\n"
            
        json_path = SYNTHETIC_CONTRACTS_DIR / f"{doc_id}.json"
        txt_path = SYNTHETIC_CONTRACTS_DIR / f"{doc_id}.txt"
        pdf_path = SYNTHETIC_CONTRACTS_DIR / f"{doc_id}.pdf"
        
        save_json(contract_data, json_path)
        write_text(full_text, txt_path)
        generate_pdf_from_text(full_text, pdf_path, is_scanned_look=False)
        
        records.append({
            "document_id": doc_id,
            "filename": f"{doc_id}.pdf",
            "title": title,
            "type": "Contract",
            "language": "English",
            "pages": max(1, len(full_text) // 1600),
            "source": "Khan & Associates Synthetic Corporate Repository",
            "file_path": str(pdf_path)
        })
        
    return records

def collect_scanned_and_urdu_docs() -> List[Dict[str, Any]]:
    """Lists the 10 real Urdu OCR benchmark pages and the 40 Pakistan Code Urdu laws.

    The benchmark pages are image-only exports of Pakistan Code Urdu laws with
    hand-checked ground truth (see evaluations/export_urdu_benchmark_pages.py and
    the folder's manifest.csv). They are read, never regenerated, here.
    """
    ensure_directory(SCANNED_URDU_DIR)
    records = []

    manifest_path = BENCHMARK_DIR / "manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Real Urdu OCR benchmark manifest not found: {manifest_path}. "
            "Run `python -m evaluations.export_urdu_benchmark_pages` first."
        )
    with manifest_path.open(encoding="utf-8-sig") as handle:
        manifest_rows = list(csv.DictReader(handle))
    logger.info("Listing %d real Urdu OCR benchmark pages...", len(manifest_rows))
    for row in manifest_rows:
        doc_id = row["benchmark_id"]
        records.append({
            "document_id": doc_id,
            "filename": f"{doc_id}.pdf",
            "title": f"[Urdu Benchmark] {row['law_title']} (page {row['source_page']})",
            "type": "Scanned/Urdu",
            "language": "Urdu",
            "pages": 1,
            "source": f"Pakistan Code, Ministry of Law and Justice ({row['source_kind']}); {row['source_url']}",
            "file_path": str(BENCHMARK_DIR / f"{doc_id}.pdf")
        })

    records.extend(collect_real_urdu_laws())
    return records


def collect_real_urdu_laws() -> List[Dict[str, Any]]:
    """Lists the Pakistan Code Urdu law PDFs in data/pakistani_urdu_code.

    IDs and titles come from data/source_catalog.csv (PKCODE_URDU_*). All of these
    need OCR: one is an image-only scan and the rest carry an unusable
    InPage-style text layer (see LegalPDFParser.classify_page).
    """
    from src.ingestion.pdf_parser import LegalPDFParser

    if not URDU_LAWS_DIR.is_dir():
        logger.warning("Urdu law folder not found: %s", URDU_LAWS_DIR)
        return []
    with SOURCE_CATALOG.open(encoding="utf-8-sig") as handle:
        catalog = {
            row["publisher_document_id"]: row
            for row in csv.DictReader(handle)
            if row["document_type"] == "Urdu legislation"
        }

    parser = LegalPDFParser()
    records = []
    for pdf_path in sorted(URDU_LAWS_DIR.glob("*.pdf")):
        entry = catalog.get(pdf_path.name)
        if entry is None:
            logger.warning("Skipping Urdu PDF not listed in source catalog: %s", pdf_path.name)
            continue
        with fitz.open(str(pdf_path)) as doc:
            page_count = doc.page_count
            sample_types = {
                parser.classify_page(doc[i].get_text().strip(), len(doc[i].get_images()))
                for i in range(min(3, page_count))
            }
        kind = "garbled text layer, needs OCR" if "garbled_text_layer" in sample_types else "image-only scan"
        records.append({
            "document_id": entry["document_id"],
            "filename": pdf_path.name,
            "title": entry["title"],
            "type": "Scanned/Urdu",
            "language": "Urdu",
            "pages": page_count,
            "source": f"Pakistan Code, Ministry of Law and Justice ({kind}); {entry['document_url']}",
            "file_path": str(pdf_path),
        })
    records.sort(key=lambda record: record["document_id"])
    logger.info("Listed %d real Pakistan Code Urdu laws", len(records))
    return records

def _sample_page_kind(pdf_path: Path, sample_pages: int = 3) -> str:
    """Return 'digital', 'scanned' or 'hybrid' from the first few pages of a PDF."""
    from src.ingestion.pdf_parser import LegalPDFParser

    parser = LegalPDFParser()
    with fitz.open(str(pdf_path)) as doc:
        kinds = {
            parser.classify_page(doc[i].get_text().strip(), len(doc[i].get_images()))
            for i in range(min(sample_pages, doc.page_count))
        }
    kinds.discard("empty")
    if kinds <= {"digital"}:
        return "digital"
    if "digital" in kinds:
        return "hybrid"
    return "scanned"


def collect_real_statutes() -> List[Dict[str, Any]]:
    """Lists the official Pakistani law PDFs in data/raw/pakistani_laws."""
    records = []
    for filename, title in REAL_STATUTE_TITLES.items():
        pdf_path = REAL_LAWS_DIR / filename
        if not pdf_path.is_file():
            logger.warning("Statute PDF missing: %s", pdf_path)
            continue
        with fitz.open(str(pdf_path)) as doc:
            page_count = doc.page_count
        records.append({
            "document_id": f"PKLAW_{len(records) + 1:03d}",
            "filename": filename,
            "title": title,
            "type": "Statute",
            "language": "English",
            "pages": page_count,
            "source": "Pakistan Code, Ministry of Law and Justice (pakistancode.gov.pk)",
            "file_path": str(pdf_path),
        })
    logger.info("Listed %d official Pakistani statutes", len(records))
    return records


def _judgment_title(case_id: str) -> str:
    """Turn a file stem such as 'c.p._2972_2022' into 'C.P. 2972/2022'."""
    parts = case_id.split("_")
    numbers = [p for p in parts[1:] if p]
    if len(numbers) >= 2:
        return f"{parts[0].upper()} {'-'.join(numbers[:-1]).upper()}/{numbers[-1]}"
    return case_id


def collect_real_judgments() -> List[Dict[str, Any]]:
    """Lists Supreme Court and Lahore High Court judgment PDFs in data/scp_judgments_pdfs."""
    catalog: Dict[str, Dict[str, str]] = {}
    if SOURCE_CATALOG.is_file():
        with SOURCE_CATALOG.open(encoding="utf-8-sig") as handle:
            catalog = {
                row["publisher_document_id"]: row
                for row in csv.DictReader(handle)
                if row["document_type"] == "Judgment"
            }

    records = []
    for pdf_path in sorted(REAL_JUDGMENTS_DIR.glob("*.pdf")):
        stem = pdf_path.stem
        if re.match(r"^\d{4}LHC\d+$", stem):
            court, case_id = "Lahore High Court", stem
            doc_id = f"LHC_{stem}"
            source = "Lahore High Court judgment PDF"
        else:
            case_id = re.sub(r"^\d+_", "", stem)
            court = "Supreme Court of Pakistan"
            doc_id = f"SC_{case_id}"
            source = "Supreme Court of Pakistan judgment PDF (supremecourt.gov.pk)"
        entry = catalog.get(case_id)
        title = entry["title"] if entry else (
            f"{court}: {case_id}" if court == "Lahore High Court" else f"{court}: {_judgment_title(case_id)}"
        )
        if entry:
            source += f"; {entry['document_url']}"
        kind = _sample_page_kind(pdf_path)
        if kind != "digital":
            source += f" ({kind} PDF, needs OCR)"
        with fitz.open(str(pdf_path)) as doc:
            page_count = doc.page_count
        records.append({
            "document_id": doc_id,
            "filename": pdf_path.name,
            "title": title,
            "type": "Judgment",
            "language": "English",
            "pages": page_count,
            "source": source,
            "file_path": str(pdf_path),
        })
    logger.info("Listed %d real judgments", len(records))
    return records


def collect_additional_cuad_contracts() -> List[Dict[str, Any]]:
    """List the 23 real CUAD contracts recorded in data/contracts/cuad/cuad_real_manifest.csv.

    The 30 REAL_CUAD downloads cover only two CUAD categories (Affiliate,
    Co-Branding). One contract from each of the other 23 categories (first by file
    name, Part I before II and III, from CUAD v1 full_contract_pdf) was copied next
    to them so that all 25 categories are represented; `cuad_path` in the manifest
    records where each came from in the CUAD release.
    """
    if not CUAD_REAL_MANIFEST.is_file():
        logger.warning("CUAD manifest not found: %s", CUAD_REAL_MANIFEST)
        return []
    with CUAD_REAL_MANIFEST.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    records = [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "title": row["title"],
            "type": "Contract",
            "language": "English",
            "pages": int(row["pages"]),
            "source": f"CUAD v1 full_contract_pdf (The Atticus Project) / SEC EDGAR; {row['cuad_path']}",
            "file_path": str(CUAD_DIR / row["filename"]),
        }
        for row in rows
    ]
    logger.info("Listed %d additional CUAD contracts (one per uncovered category)", len(records))
    return records


def run_corpus_collection() -> pd.DataFrame:
    """Lists the real corpus plus 20 synthetic contracts and writes inventory.csv.

    """
    logger.info("=== Starting Task 1: Corpus Collection & Inventory Creation ===")

    statute_records = collect_real_statutes()
    judgment_records = collect_real_judgments()
    contract_records = collect_synthetic_contracts()
    scanned_records = collect_scanned_and_urdu_docs()
    
    all_records = statute_records + judgment_records + contract_records + scanned_records

    # Keep downloaded official statute and CUAD PDFs in the inventory when the
    # locally generated instructional corpus is rebuilt.
    inventory_path = Path("inventory.csv")
    generated_ids = {record["document_id"] for record in all_records}
    if inventory_path.is_file():
        existing = pd.read_csv(inventory_path)
        if {"document_id", "file_path"}.issubset(existing.columns):
            external_records = existing[
                existing["document_id"].astype(str).str.startswith("REAL_")
                & ~existing["document_id"].astype(str).isin(generated_ids)
            ]
            for record in external_records.to_dict(orient="records"):
                if Path(str(record["file_path"])).is_file():
                    all_records.append(record)

    all_records.extend(collect_additional_cuad_contracts())

    df = pd.DataFrame(all_records)
    df = df.drop_duplicates(subset=["document_id"], keep="last")
    df.to_csv(inventory_path, index=False, encoding="utf-8")
    
    logger.info(f"Inventory written to {inventory_path.resolve()} with {len(df)} total documents:")
    summary = df.groupby(["type", "language"])["document_id"].count()
    logger.info(f"\n{summary}")
    
    return df

if __name__ == "__main__":
    run_corpus_collection()
