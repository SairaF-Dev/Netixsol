"""Central settings: every path and tunable lives here, not scattered in scripts.

Why: if a script hard-codes "data/raw/x.csv", tests can't redirect it to a temp
folder and will overwrite real data (that bug cost us a full drive in Week 11).
Everything reads paths from here, and tests override ILM_DATA_DIR.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("ILM_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VIDEOS_DIR = DATA_DIR / "videos"
SLIDES_DIR = DATA_DIR / "slides"
CHROMA_DIR = PROCESSED_DIR / "chroma"
MODELS_DIR = Path(os.getenv("ILM_MODELS_DIR", PROJECT_ROOT / "models"))
REPORTS_DIR = Path(os.getenv("ILM_REPORTS_DIR", PROJECT_ROOT / "reports"))

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY", "")   # never logged
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")

RANDOM_SEED = 42  # one seed for the whole project, so results reproduce

# --- Day 5: API ---
ILM_ENV = os.getenv("ILM_ENV", "dev")                        # dev | prod
JWT_SECRET = os.getenv("ILM_JWT_SECRET", "")                 # required in prod; dev makes one per run
DEMO_PASSWORD = os.getenv("ILM_DEMO_PASSWORD", "")           # demo accounts; dev default if empty
API_DB = Path(os.getenv("ILM_API_DB", DATA_DIR / "app" / "ilm.sqlite3"))
CORS_ORIGINS = [o for o in os.getenv("ILM_CORS_ORIGINS", "http://localhost:5173").split(",") if o]
