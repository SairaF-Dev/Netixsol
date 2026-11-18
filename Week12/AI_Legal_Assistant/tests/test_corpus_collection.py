"""
Unit tests for Task 1: Corpus Collection and Inventory Generation.
"""
from pathlib import Path
import pandas as pd
import pytest

def test_inventory_file_exists():
    inv_path = Path("inventory.csv")
    assert inv_path.exists(), "inventory.csv was not generated"

def test_inventory_minimum_counts():
    df = pd.read_csv("inventory.csv")
    assert len(df) >= 290, f"Expected at least 290 documents, got {len(df)}"
    assert df["document_id"].is_unique, "Inventory document IDs must be unique"
    assert df["file_path"].map(lambda item: Path(item).exists()).all(), "Every inventory path must exist"
    
    # Check column names
    required_cols = {"document_id", "filename", "title", "type", "language", "pages", "source", "file_path"}
    assert required_cols.issubset(set(df.columns)), f"Missing required columns in inventory.csv"
    
    # Check specific counts
    statutes_count = len(df[df["type"] == "Statute"])
    judgments_count = len(df[df["type"] == "Judgment"])
    contracts_count = len(df[df["type"] == "Contract"])
    scanned_count = len(df[df["type"] == "Scanned/Urdu"])
    
    assert statutes_count >= 10, f"Expected >= 10 statutes, got {statutes_count}"
    assert judgments_count >= 200, f"Expected >= 200 judgments, got {judgments_count}"
    assert contracts_count >= 50, f"Expected >= 50 contracts, got {contracts_count}"
    assert scanned_count >= 30, f"Expected >= 30 scanned/Urdu documents, got {scanned_count}"

    # Only the 20 synthetic contracts the brief asks for may be generated.
    generated = df[df["source"].str.contains("synthetic|generated", case=False, na=False)]
    assert set(generated["type"]) <= {"Contract"}
    assert len(generated) == 20

    judgments = df[df["type"] == "Judgment"]
    courts = {"Supreme Court" if i.startswith("SC_") else "Lahore High Court" for i in judgments["document_id"]}
    assert courts == {"Supreme Court", "Lahore High Court"}

    real_cuad = df[(df["type"] == "Contract") & df["source"].str.contains("cuad", case=False, na=False)]
    assert len(real_cuad) >= 50

def test_benchmark_files_exist():
    benchmark_dir = Path("data/scanned_urdu/benchmark_cer")
    assert benchmark_dir.exists()
    gt_files = list(benchmark_dir.glob("*_ground_truth.txt"))
    assert len(gt_files) == 10, f"Expected exactly 10 Urdu ground truth files, found {len(gt_files)}"
