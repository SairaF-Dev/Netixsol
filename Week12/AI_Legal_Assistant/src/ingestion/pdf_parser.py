"""
PDF Parsing and Layout Extraction Engine for Khan & Associates Legal Assistant.
Supports:
- Digital vs Scanned PDF detection
- Text and Table extraction via PyMuPDF (fitz)
- Page layout analysis and reading order preservation
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF

from src.utils.logger import setup_logger

logger = setup_logger("pdf_parser")

# A page whose embedded text is mostly these code points has an unusable text
# layer: legacy Urdu typesetting (InPage-style fonts) maps glyph shapes to
# Private Use Area codes, so the page renders as Urdu but extracts as noise.
GARBLED_TEXT_THRESHOLD = 0.3


def garbled_char_ratio(text: str) -> float:
    """Share of non-whitespace characters that are Private Use Area codes or U+FFFD."""
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    garbled = sum(1 for ch in visible if "" <= ch <= "" or ch == "�")
    return garbled / len(visible)


class LegalPDFParser:
    """Enterprise parser for legal documents with digital/scanned classification and table detection."""
    
    def __init__(self, min_chars_per_page: int = 50, ocr_engine: Any = None):
        self.min_chars_per_page = min_chars_per_page
        self.ocr_engine = ocr_engine

    def classify_page(self, text: str, image_count: int) -> str:
        """Return 'digital', 'garbled_text_layer', 'scanned' or 'empty' for one page.

        'garbled_text_layer' pages have enough embedded characters to look digital,
        but those characters are font-private codes rather than readable text, so
        they must be OCR'd like scans.
        """
        if len(text) >= self.min_chars_per_page:
            if garbled_char_ratio(text) > GARBLED_TEXT_THRESHOLD:
                return "garbled_text_layer"
            return "digital"
        if image_count > 0:
            return "scanned"
        return "empty"

    def inspect_pdf(self, pdf_path: str | Path) -> Dict[str, Any]:
        """
        Classifies a PDF as digital, scanned, or hybrid based on text density and image coverage.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found at {path}")

        doc = fitz.open(str(path))
        page_count = len(doc)
        
        digital_pages = 0
        scanned_pages = 0
        garbled_pages = 0
        total_chars = 0
        total_images = 0
        
        pages_summary = []
        
        for pno in range(page_count):
            page = doc[pno]
            text = page.get_text().strip()
            images = page.get_images()
            char_count = len(text)
            image_count = len(images)
            
            total_chars += char_count
            total_images += image_count
            
            page_type = self.classify_page(text, image_count)
            if page_type == "digital":
                digital_pages += 1
            elif page_type == "scanned":
                scanned_pages += 1
            elif page_type == "garbled_text_layer":
                # Needs OCR exactly like a scan; counted as scanned for classification.
                scanned_pages += 1
                garbled_pages += 1

            pages_summary.append({
                "page_number": pno + 1,
                "char_count": char_count,
                "image_count": image_count,
                "page_type": page_type
            })

        avg_chars = total_chars / max(1, page_count)

        if scanned_pages == 0 and digital_pages > 0:
            classification = "digital"
        elif digital_pages == 0 and scanned_pages > 0:
            classification = "scanned"
        elif scanned_pages > 0 and digital_pages > 0:
            classification = "hybrid"
        else:
            classification = "digital" if avg_chars > 20 else "scanned"

        doc.close()
        
        return {
            "file_path": str(path),
            "filename": path.name,
            "page_count": page_count,
            "classification": classification,
            "total_chars": total_chars,
            "avg_chars_per_page": round(avg_chars, 2),
            "total_images": total_images,
            "garbled_text_pages": garbled_pages,
            "pages": pages_summary
        }

    def extract_page_texts(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        """Return per-page text without table detection (fast path for structure extraction).

        Scanned and garbled-text-layer pages are OCR'd when an engine is attached;
        otherwise their text is empty and ``needs_ocr`` is True.
        """
        path = Path(pdf_path)
        pages = []
        with fitz.open(str(path)) as doc:
            for pno in range(len(doc)):
                page = doc[pno]
                text = page.get_text("text").strip()
                page_type = self.classify_page(text, len(page.get_images()))
                text_source = "digital" if text else "none"
                if page_type in ("scanned", "garbled_text_layer"):
                    if page_type == "garbled_text_layer":
                        text = ""
                    text_source = "scan_unprocessed"
                    if self.ocr_engine is not None:
                        text = self.ocr_engine.extract_text(path, page_num=pno)["text"].strip()
                        text_source = "ocr"
                pages.append({
                    "page_number": pno + 1,
                    "text": text,
                    "page_type": page_type,
                    "text_source": text_source,
                    "needs_ocr": page_type in ("scanned", "garbled_text_layer") and text_source != "ocr",
                })
        return pages

    def extract_text_and_tables(self, pdf_path: str | Path) -> Dict[str, Any]:
        """
        Extracts structured text blocks and tables across all pages of the document.
        """
        path = Path(pdf_path)
        doc = fitz.open(str(path))
        
        extracted_pages = []
        all_tables = []
        full_text_parts = []
        
        for pno in range(len(doc)):
            page = doc[pno]
            page_text = page.get_text("text").strip()
            image_count = len(page.get_images())
            page_type = self.classify_page(page_text, image_count)
            text_source = "digital" if page_text else "none"
            if page_type in ("scanned", "garbled_text_layer"):
                if page_type == "garbled_text_layer":
                    # Never pass font-private codes downstream as if they were text.
                    page_text = ""
                text_source = "scan_unprocessed"
                if self.ocr_engine is not None:
                    ocr_result = self.ocr_engine.extract_text(path, page_num=pno)
                    page_text = ocr_result["text"].strip()
                    text_source = "ocr"
            
            # Extract tables using PyMuPDF table finder
            page_tables = []
            try:
                tabs = page.find_tables()
                for idx, t in enumerate(tabs):
                    df_table = t.extract()
                    table_info = {
                        "page_number": pno + 1,
                        "table_index": idx + 1,
                        "row_count": len(df_table),
                        "header": df_table[0] if df_table else [],
                        "rows": df_table[1:] if len(df_table) > 1 else [],
                        "bbox": t.bbox
                    }
                    page_tables.append(table_info)
                    all_tables.append(table_info)
            except Exception as e:
                logger.warning(f"Table detection skipped on page {pno + 1}: {e}")

            # Extract structured blocks (skipped when the text layer is unusable)
            blocks = page.get_text("blocks") if page_type == "digital" else []
            clean_blocks = []
            for b in blocks:
                # b format: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and b[4].strip():
                    clean_blocks.append({
                        "bbox": [round(coord, 1) for coord in b[:4]],
                        "text": b[4].strip()
                    })

            extracted_pages.append({
                "page_number": pno + 1,
                "text": page_text,
                "page_type": page_type,
                "text_source": text_source,
                "needs_ocr": page_type in ("scanned", "garbled_text_layer") and text_source != "ocr",
                "blocks": clean_blocks,
                "tables": page_tables
            })
            if page_text:
                full_text_parts.append(page_text)

        doc.close()
        
        return {
            "filename": path.name,
            "total_pages": len(extracted_pages),
            "full_text": "\n\n".join(full_text_parts),
            "pages": extracted_pages,
            "total_tables": len(all_tables),
            "tables": all_tables
        }
