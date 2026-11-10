"""
Zip the files a deployed (lite) dashboard needs and that GitHub cannot store: the DuckDB database and the three
model files. Upload the zip to a GitHub Release and set DATA_BUNDLE_URL to its download link.

Usage:  python scripts/build_deploy_bundle.py        -> dist/shopkaro_data_bundle.zip
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "data/processed/shopkaro.duckdb",
    "models/item_cf_serving.joblib",  # recommender (item-CF) serving artifact
    "models/search_semantic_index.pkl",  # TF-IDF + SVD search index (lite search)
    "models/item_text_embeddings.npy",  # "similar products" vectors
]


def main() -> None:
    out = ROOT / "dist" / "shopkaro_data_bundle.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in FILES:
            src = ROOT / rel
            if not src.exists():
                raise SystemExit(f"missing {rel}: build the data / models first")
            zf.write(src, arcname=rel)
            print(f"  + {rel} ({src.stat().st_size / 1e6:.0f} MB)")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
