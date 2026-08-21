# AFL Assistant — Week 6 Day 5 Capstone

Production-style AFL chat + prediction assistant using LangGraph, FastAPI and Streamlit.

## Features
- AFL-only scope and prompt-injection guardrails
- Structured retrieval from AFL snapshot data
- Match-winner and top-player prediction tools
- Pending clarification for missing prediction dates
- Standard prediction disclaimer
- Error-safe tool execution
- 25+ evaluation cases
- FastAPI `/chat` and `/health`
- Streamlit demo UI
- Structured JSONL monitoring logs
- Monitoring/retraining checklist
- Executive report and demo outline

## Expected artifacts
Place these files in the project root before running the prediction features:
- `match_winner_model.joblib`
- `top_player_model.joblib`
- `team_snapshots.parquet`
- `player_snapshots.parquet`

These are intentionally not fabricated by this package. Copy your real Week 6 Day 2/4 artifacts into the root.

## Run
See `RUN_GUIDE.txt` for the exact non-code commands and demo flow.
