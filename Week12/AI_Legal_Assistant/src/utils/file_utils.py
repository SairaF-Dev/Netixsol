"""
File handling and serialization utilities for the legal pipeline.
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

def ensure_directory(path: str | Path) -> Path:
    """Ensures directory exists and returns Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_json(data: Any, file_path: str | Path, indent: int = 2) -> None:
    """Safely saves data to JSON file."""
    path = Path(file_path)
    ensure_directory(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def load_json(file_path: str | Path) -> Any:
    """Loads data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_csv(records: List[Dict[str, Any]], file_path: str | Path) -> None:
    """Saves records list of dicts to CSV."""
    df = pd.DataFrame(records)
    path = Path(file_path)
    ensure_directory(path.parent)
    df.to_csv(path, index=False, encoding="utf-8")

def read_text(file_path: str | Path) -> str:
    """Reads UTF-8 text from file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_text(text: str, file_path: str | Path) -> None:
    """Writes text to file."""
    path = Path(file_path)
    ensure_directory(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
