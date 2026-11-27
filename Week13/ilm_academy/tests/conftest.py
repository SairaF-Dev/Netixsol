"""Test isolation: point all data/model/report paths at a temp folder.

This runs BEFORE any test imports ilm.config, so config picks up the temp
paths. Real data in ./data is never touched by tests.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Keep temp data on the project drive (D:), not C: (C: filled up in Week 11).
_TMP_PARENT = Path(os.getenv("ILM_TEST_TMP", ROOT / ".pytest_tmp"))  # git-ignored
_TMP_PARENT.mkdir(parents=True, exist_ok=True)
_TMP = Path(tempfile.mkdtemp(prefix="ilm_tests_", dir=_TMP_PARENT))
os.environ["ILM_DATA_DIR"] = str(_TMP / "data")
os.environ["ILM_MODELS_DIR"] = str(_TMP / "models")
os.environ["ILM_REPORTS_DIR"] = str(_TMP / "reports")
# Windows without Developer Mode can't symlink the HF cache; harmless, so silence it.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# One BLAS thread per process. pyBKT fits in ~12 worker processes; with a BLAS thread (and
# buffer) per core in each, memory ran out on a busy machine and the workers hung
# ("OpenBLAS: memory allocation failed", 2026-11-27). The work is already split across
# processes, so this changes no result. Workers inherit these at start-up.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")


def pytest_sessionfinish(session, exitstatus):
    # ignore_errors: on Windows a DB file can still be locked; never fail the run on cleanup
    shutil.rmtree(_TMP, ignore_errors=True)
    if _TMP.exists():
        print(f"\nWARNING: could not fully delete test temp dir {_TMP}")
