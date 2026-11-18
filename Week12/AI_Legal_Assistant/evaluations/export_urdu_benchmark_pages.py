"""Export ten real Pakistan Code Urdu pages as image-only PDFs for the OCR CER benchmark.

The source PDFs (data/pakistani_urdu_code) either are scans or carry a garbled
InPage-style text layer (Private Use Area glyph codes), so their embedded text
cannot serve as ground truth. Each selected page is rasterised at 300 DPI into a
single-page PDF with no text layer, and an empty ``*_ground_truth.txt`` is created
for the hand-checked reference. Existing ground-truth files are never overwritten.

Run: python -m evaluations.export_urdu_benchmark_pages
"""

import csv
from pathlib import Path

import fitz

SOURCE_DIR = Path("data/pakistani_urdu_code")
OUTPUT_DIR = Path("data/scanned_urdu/benchmark_cer")
CATALOG = Path("data/source_catalog.csv")
DPI = 300

# (source file, 1-based page). Pages chosen for 10-20 printed lines across eight
# laws, including a table page, headings over the watermark, and two pages from
# the image-only Constitution scan.
PICKS = [
    ("administratorcurdua7f4f2b3b5b93d09a4aa34cd.pdf", 13),  # Qanun-e-Shahadat Order 1984
    ("administratorcurdua7f4f2b3b5b93d09a4aa9035.pdf", 12),  # Contract Act 1872
    ("administratorcurdua7f4f2b3b5b93d09a4aa78gh.pdf", 13),  # Limitation Act 1908
    ("administratorcurdua7f4f2b3b5b93d09ccss545.pdf", 9),    # Specific Relief Act 1877
    ("administratorcurdua7f4f2b3b5b93d09a4aa3802.pdf", 27),  # Control of Narcotic Substances Act 1997 (table)
    ("administratorcurdua7f4f2b3b5b93d09a4aa5683.pdf", 23),  # Investigation for Fair Trial Act 2013
    ("administratorcurdua7f4f2b3b5b93d09a4aa6045.pdf", 5),   # تصفیہ تجارتی تنازعہ ایکٹ 2022 (commercial disputes)
    ("administratorcurdua7f4f2b3b5b93d09a4aa4789.pdf", 7),   # Enforcement of Women's Property Rights Act 2020
    ("administratorcurdua7f4f2b3b5b93d09a4aa12ab.pdf", 11),  # Constitution 1973 (image-only scan)
    ("administratorcurdua7f4f2b3b5b93d09a4aa12ab.pdf", 12),  # Constitution 1973 (image-only scan)
]


def export_pages() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG.open(encoding="utf-8-sig") as handle:
        catalog = {row["publisher_document_id"]: row for row in csv.DictReader(handle)}

    rows = []
    for index, (filename, page_number) in enumerate(PICKS, start=1):
        stem = f"URDU_GT_{index:03d}"
        with fitz.open(SOURCE_DIR / filename) as source:
            page = source[page_number - 1]
            has_text_layer = bool(page.get_text().strip())
            pixmap = page.get_pixmap(dpi=DPI, alpha=False)
            with fitz.open() as output:
                new_page = output.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, pixmap=pixmap)
                output.save(OUTPUT_DIR / f"{stem}.pdf", deflate=True)

        ground_truth = OUTPUT_DIR / f"{stem}_ground_truth.txt"
        if not ground_truth.exists():
            ground_truth.write_text("", encoding="utf-8")

        entry = catalog.get(filename, {})
        rows.append(
            {
                "benchmark_id": stem,
                "source_file": filename,
                "source_page": page_number,
                "law_title": entry.get("title", ""),
                "source_kind": "garbled text layer (rasterised)" if has_text_layer else "image-only scan",
                "source_url": entry.get("document_url", ""),
                "ground_truth_method": "drafted by Claude from page image, corrected by hand",
            }
        )

    with (OUTPUT_DIR / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    for row in export_pages():
        print(row["benchmark_id"], row["source_page"], row["source_kind"])
