"""Compare Tesseract and EasyOCR on ten Urdu legal-document benchmark pages."""

from pathlib import Path
from typing import Dict, List

import pandas as pd
from tabulate import tabulate

from src.ingestion.ocr_engine import (
    EasyOCRUrduOCR,
    TesseractUrduOCR,
    compute_cer,
    compute_wer,
)
from src.utils.file_utils import ensure_directory, read_text, write_text
from src.utils.logger import setup_logger

logger = setup_logger("ocr_evaluation")
BENCHMARK_DIR = Path("data/scanned_urdu/benchmark_cer")
EVAL_DIR = Path("evaluations")


def load_available_engines() -> List[object]:
    """Instantiate only OCR engines that are available in the current environment."""
    available: List[object] = []
    for engine_factory in (TesseractUrduOCR, EasyOCRUrduOCR):
        try:
            available.append(engine_factory())
            logger.info("Loaded OCR engine: %s", engine_factory.__name__)
        except Exception as exc:  # pragma: no cover - environment-dependent runtime issues
            logger.warning("Skipping OCR engine %s: %s", engine_factory.__name__, exc)
    if not available:
        raise RuntimeError(
            "No OCR engines are available. Install Tesseract with Urdu/English language "
            "data and/or the optional 'easyocr' package before running the benchmark."
        )
    return available


def run_ocr_benchmark() -> pd.DataFrame:
    """Run available OCR engines and write per-page measurements and their summary."""
    benchmark = [
        (
            BENCHMARK_DIR / f"URDU_GT_{idx:03d}.pdf",
            BENCHMARK_DIR / f"URDU_GT_{idx:03d}_ground_truth.txt",
        )
        for idx in range(1, 11)
    ]
    missing = [str(path) for pair in benchmark for path in pair if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "The OCR benchmark requires all ten PDF/reference pairs; missing: "
            + ", ".join(missing)
        )

    engines = load_available_engines()
    results: List[Dict[str, object]] = []

    for pdf_path, reference_path in benchmark:
        reference = read_text(reference_path)
        if not reference.strip():
            raise ValueError(f"OCR ground truth is empty: {reference_path}")

        row: Dict[str, object] = {
            "doc_id": pdf_path.stem,
            "page_title": reference.splitlines()[0][:80],
            "char_count": len(reference),
        }
        for index, engine in enumerate(engines, start=1):
            output = engine.extract_text(pdf_path, page_num=0)
            row[f"tool{index}_name"] = output["engine"]
            row[f"tool{index}_cer"] = round(compute_cer(reference, output["text"]) * 100, 2)
            row[f"tool{index}_wer"] = round(compute_wer(reference, output["text"]) * 100, 2)
            row[f"tool{index}_latency_ms"] = output["latency_ms"]
        results.append(row)

    df = pd.DataFrame(results)
    for index in range(1, len(engines) + 1):
        for metric in ("cer", "wer", "latency_ms"):
            column = f"tool{index}_{metric}"
            if column in df.columns:
                df[column] = pd.to_numeric(df[column])

    ensure_directory(EVAL_DIR)
    csv_path = EVAL_DIR / "ocr_comparison_report.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    summary = []
    for index, engine in enumerate(engines, start=1):
        summary.append(
            [
                engine.name,
                f"{df[f'tool{index}_cer'].mean():.2f}%",
                f"{df[f'tool{index}_wer'].mean():.2f}%",
                f"{df[f'tool{index}_latency_ms'].mean():.1f} ms",
            ]
        )
    summary_md = tabulate(
        summary,
        headers=["OCR Engine", "Average CER", "Average WER", "Average Latency"],
        tablefmt="github",
    )

    detail_columns = ["doc_id", "char_count"]
    detail_headers = ["Document", "Reference chars"]
    for index, engine in enumerate(engines, start=1):
        detail_columns.extend([f"tool{index}_cer", f"tool{index}_wer"])
        detail_headers.extend([f"{engine.name} CER (%)", f"{engine.name} WER (%)"])
    detail_md = tabulate(
        df[detail_columns],
        headers=detail_headers,
        tablefmt="github",
        showindex=False,
    )
    engine_names = ", ".join(engine.name for engine in engines)
    report = f"""# Urdu OCR Benchmark

## Method

{engine_names} each receive a rendered image of the same PDF page.
Neither engine reads the ground-truth file. CER and WER compare each engine's
recognized text against the paired UTF-8 reference. Latency measures OCR inference
and excludes PDF rendering.

## Results

{summary_md}

## Per-page results

{detail_md}
"""
    md_path = EVAL_DIR / "ocr_comparison_report.md"
    write_text(report, md_path)
    logger.info("OCR benchmark complete. Reports written to %s and %s", csv_path, md_path)
    print(report)
    return df


if __name__ == "__main__":
    run_ocr_benchmark()
