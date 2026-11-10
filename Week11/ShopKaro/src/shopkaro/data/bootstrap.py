"""
Fetch the prebuilt database + model files on a fresh deployment (e.g. Streamlit Community Cloud).

GitHub cannot store the 445 MB DuckDB file, so it is published as a zip on a GitHub Release
(`python scripts/build_deploy_bundle.py` creates it). Set DATA_BUNDLE_URL to the zip's download URL; on start,
if the database is missing, the zip is downloaded once and unpacked into the project folder.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from shopkaro.config.settings import PROJECT_ROOT, settings


def data_ready() -> bool:
    return settings.duckdb_path.exists()


_LOCK = threading.Lock()


def ensure_data(progress=None) -> str:
    """
    Download and unpack the data bundle if the database is missing. Returns a short status string.
    Thread-safe: concurrent callers (several visitors on a fresh server) wait and the download happens once.
    """
    if data_ready():
        return "data present"
    with _LOCK:
        if data_ready():  # another visitor finished the download while we waited
            return "data present"
        return _download_and_unpack(progress)


def _download_and_unpack(progress=None) -> str:
    url = os.getenv("DATA_BUNDLE_URL", "").strip()
    if not url:
        raise RuntimeError(
            f"Database not found at {settings.duckdb_path} and DATA_BUNDLE_URL is not set. Build the data locally "
            "(scripts/run_day1_pipeline.py ...) or set DATA_BUNDLE_URL to the bundle zip from the GitHub Release."
        )
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "bundle.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "shopkaro-bootstrap"})
        with urllib.request.urlopen(req, timeout=600) as resp, open(zip_path, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
        with zipfile.ZipFile(zip_path) as zf:
            root = PROJECT_ROOT.resolve()
            for member in zf.infolist():
                target = (root / member.filename).resolve()
                if root not in target.parents and target != root:  # refuse paths that escape the project
                    raise RuntimeError(f"Unsafe path in bundle: {member.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if not member.is_dir():
                    with zf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    if not data_ready():
        raise RuntimeError("Bundle unpacked but the database is still missing; check the bundle contents.")
    return "data downloaded"
