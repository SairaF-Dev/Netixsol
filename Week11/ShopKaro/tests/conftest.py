"""
Shared pytest setup.

1. Isolation: several tests re-run pipeline steps that WRITE to the database, models and reports
   (often with smaller samples, e.g. 500 evaluation users instead of 5,000). To keep the real
   results intact, the whole suite runs on a temporary copy of data/processed, data/synthetic,
   models and reports. The paths are set through environment variables before any `shopkaro`
   import reads settings, and the copy is deleted when the session ends.
2. Determinism: the shopping assistant is forced to the rule-based engine so tests work offline.
   The LLM agent loop is tested with a scripted fake model in `test_llm_assistant.py`.

To run the opt-in live test against the real LLM:  RUN_LIVE_LLM=1 python -m pytest -m live
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="shopkaro_tests_"))

for env_var, rel in (
    ("PROCESSED_DIR", "data/processed"),
    ("SYNTHETIC_DIR", "data/synthetic"),
    ("MODEL_DIR", "models"),
    ("REPORTS_DIR", "reports"),
):
    src = PROJECT_ROOT / rel
    dst = _TEST_ROOT / rel
    if src.exists():
        shutil.copytree(src, dst)
    else:
        dst.mkdir(parents=True)
    os.environ[env_var] = str(dst)
os.environ["DUCKDB_PATH"] = str(_TEST_ROOT / "data/processed/shopkaro.duckdb")
os.environ.setdefault("ASSISTANT_ENGINE", "rules")


def pytest_configure(config) -> None:  # noqa: ANN001
    config.addinivalue_line("markers", "live: calls the real LLM API (needs LLM_API_KEY and RUN_LIVE_LLM=1)")


def pytest_unconfigure(config) -> None:  # noqa: ANN001, ARG001
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)
