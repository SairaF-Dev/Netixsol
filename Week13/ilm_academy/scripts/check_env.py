"""Check that the environment is usable: every library imports, versions, timing.

Run:  .venv311/Scripts/python.exe scripts/check_env.py
Exit code 1 if anything fails, so CI / Docker builds can use it too.
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODULES = [
    "numpy", "pandas", "matplotlib", "seaborn", "scipy",
    "faster_whisper", "ctranslate2", "pymupdf", "pptx",
    "chromadb", "sentence_transformers", "torch",
    "networkx", "pyvis", "yaml", "pydantic", "dotenv", "pytest",
]


def main() -> int:
    print(f"Python {sys.version.split()[0]} at {sys.executable}")
    failed = []
    for name in MODULES:
        start = time.time()
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", "?")
            print(f"OK   {name:22s} {version:14s} {time.time() - start:5.1f}s", flush=True)
        except Exception as exc:  # report every failure, don't stop at the first
            failed.append(name)
            print(f"FAIL {name:22s} {type(exc).__name__}: {exc}", flush=True)

    from ilm import config
    print(f"config PROJECT_ROOT = {config.PROJECT_ROOT}")
    print(f"config DATA_DIR     = {config.DATA_DIR}")

    if failed:
        print(f"\n{len(failed)} module(s) failed: {', '.join(failed)}")
        return 1
    print("\nAll modules import.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
