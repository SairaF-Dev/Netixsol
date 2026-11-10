# ShopKaro — Automation & CLI Scripts

This directory houses standalone, reusable command-line scripts for pipeline execution, data preprocessing, model training, and batch evaluation.

---

## Intended Purpose

Scripts serve as operational entry points to automate end-to-end workflows without launching interactive notebooks or API servers:

- `ingest_raw_data.py`: Validates and loads raw datasets into structured DuckDB tables.
- `train_recommenders.py`: Executes training loops for collaborative filtering and hybrid recommender models.
- `train_forecaster.py`: Runs rolling-window demand forecasting models across inventory SKUs.
- `build_search_index.py`: Generates BM25 token indexes and vector embeddings for hybrid catalog search.
- `run_ab_simulation.py`: Simulates user experiment traffic and computes statistical significance.

---

## Execution Guidelines

Always execute scripts from the workspace root directory with your virtual environment activated:

```powershell
# Example: Running an ingestion script via module execution
python -m scripts.ingest_raw_data

# Or directly invoking the script
python scripts/ingest_raw_data.py
```

