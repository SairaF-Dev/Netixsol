# Release Validation

- Regression tests: **30/30 PASS**
- Pytest exit code: **0**
- Python import smoke: **PASS**
- Python source compile: **PASS**
- Secret scan: **PASS**
- Populated `.env` included: **NO**
- Virtualenv included: **NO**
- Python/pytest caches included: **NO**
- Chroma runtime database included: **NO**
- Finalized Day 2 data copied into Day 3: **NO** — Day 3 uses `DAY2_ROOT`.

## Important runtime dependency

Point `DAY2_ROOT` to the finalized Day 2 project containing:

- `02_rag`
- `03_structured_retrieval`
- optional `04_recommendation`

Run:

```powershell
python scripts\check_rag.py
pytest -q
```

API probes:

```text
GET /health
GET /ready
```
