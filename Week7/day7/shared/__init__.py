"""Channel-independent Sara capabilities shared with Day 3."""
import sys
from pathlib import Path

source = str(Path(__file__).resolve().parents[2] / "day3" / "src")
if source not in sys.path:
    sys.path.insert(0, source)
