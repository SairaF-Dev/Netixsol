"""
Centralized configuration and path settings for the ShopKaro platform.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Immutable application and pipeline settings."""

    app_name: str = os.getenv("APP_NAME", "ShopKaro")
    app_env: str = os.getenv("APP_ENV", "development")
    random_seed: int = 42

    # Directory Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    raw_retailrocket_dir: Path = PROJECT_ROOT / "data" / "raw" / "retailrocket"
    raw_olist_dir: Path = PROJECT_ROOT / "data" / "raw" / "olist"
    # Output locations are overridable (relative to the project root, or absolute) so the test
    # suite can run against a copy instead of overwriting real data, models and reports.
    processed_dir: Path = PROJECT_ROOT / os.getenv("PROCESSED_DIR", "data/processed")
    synthetic_dir: Path = PROJECT_ROOT / os.getenv("SYNTHETIC_DIR", "data/synthetic")
    models_dir: Path = PROJECT_ROOT / os.getenv("MODEL_DIR", "models")
    reports_dir: Path = PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports")
    figures_dir: Path = PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports") / "figures"
    docs_dir: Path = PROJECT_ROOT / "docs"

    # Database & Artifact Paths
    duckdb_path: Path = PROJECT_ROOT / os.getenv(
        "DUCKDB_PATH", "data/processed/shopkaro.duckdb"
    )

    # LLM shopping assistant (Day 4 Task 3).
    # ASSISTANT_ENGINE: "auto" = LLM when a key is configured, else rules; "llm"; "rules".
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    assistant_engine: str = os.getenv("ASSISTANT_ENGINE", "auto")

    # Search semantic retriever: "auto" = neural multilingual embeddings when sentence-transformers is installed
    # (Python 3.11 env), otherwise the TF-IDF + SVD (LSA) index; "neural" / "lsa" force one.
    search_embeddings: str = os.getenv("SEARCH_EMBEDDINGS", "auto")
    search_embedding_model: str = os.getenv("SEARCH_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    # Cross-encoder re-ranking of the top 50 search results: "auto" (on when sentence-transformers is installed),
    # "on" or "off".
    search_cross_encoder: str = os.getenv("SEARCH_CROSS_ENCODER", "auto")
    search_cross_encoder_model: str = os.getenv(
        "SEARCH_CROSS_ENCODER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    )

    # Homepage recommender: "item_cf" (default) or "two_tower" (neural two-tower; needs the batch artifact from
    # scripts/precompute_recommendations.py --two-tower, otherwise the API falls back to item-CF and reports why).
    recommender: str = os.getenv("RECOMMENDER", "item_cf")

    # Pipeline Parameters (Day 1 Specification)
    session_inactivity_minutes: int = 30
    bot_max_clicks_per_session: int = 1000
    churn_inactivity_days: int = 90
    brl_to_pkr_multiplier: float = 55.0  # Realistic scaling to PKR retail bands

    # Time-based split ratios (Chronological: 70% train, 15% val, 15% test)
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15


settings = Settings()

