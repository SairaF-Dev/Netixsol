#  AFL LangGraph Integration



A LangGraph-based AFL assistant that integrates **factual answers, dataset retrieval, and ML predictions** through explicit intent routing, validation, clarification, and fallback handling.

## Features

* **Intent routing:** `factual`, `retrieval`, `prediction`, `off_topic`
* **AFL retrieval:** recent results, head-to-head records, player/team statistics
* **Match prediction:** predicts the winner with probability
* **Top-player prediction:** ranks predicted top players
* **Team alias resolution:** e.g. `Pies → Collingwood Magpies`, `Cats → Geelong Cats`
* **Validation:** checks tool results before formatting
* **Clarification:** handles missing team/date information across turns
* **Fallback:** handles unsupported prediction requests
* **Off-topic guardrail:** refuses non-AFL questions
* **State persistence:** `MemorySaver` for multi-turn conversations
* **Trace logging:** displays intent, tool, and validation status

## Architecture

```text
START
  ↓
Pending Clarification?
  ├── Yes → Pending Clarification → Prediction
  └── No  → Router
              ├── Factual → Formatter
              ├── Retrieval → Validation
              ├── Prediction → Validation
              └── Off-topic → Formatter

Validation
  ├── Valid → Formatter → END
  ├── Needs Clarification → Clarification → END
  └── Error → Fallback → END
```

## Project Structure
```
week6_day4/
│
├── day4_graph.py
├── state.py
├── router.py
├── predict.py
├── README.md
├── requirements.txt
├── routing_accuracy_results.csv
│
├── match_winner_model.joblib
├── top_player_model.joblib
├── player_snapshots.parquet
├── team_snapshots.parquet
│
├── data/
│   ├── afl_players_round_by_round_stats_raw.csv
│   └── team_matches_home_away_raw.csv
│
├── nodes/
│   ├── clarification_node.py
│   ├── factual_node.py
│   ├── fallback_node.py
│   ├── formatter_node.py
│   ├── off_topic_node.py
│   ├── pending_clarification_node.py
│   ├── prediction_node.py
│   ├── retrieval_node.py
│   ├── router_node.py
│   ├── validation_node.py
│   └── __init__.py
│
├── tools/
│   ├── prediction_tools.py
│   ├── retrieval_tools.py
│   ├── team_resolver.py
│   └── __init__.py
│
├── tests/
│   ├── test_e2e.py
│   └── test_router.py
│
└── traces/
    ├── clarification_trace.md
    ├── prediction_trace.md
    └── retrieval_trace.md
```

## Example Queries

```text
What were the Pies' last 5 results?
```

```text
What is a mark in AFL?
```

```text
Who will win Pies vs Cats on 2026-08-22?
```

```text
Predict the top player for Pies on 2026-08-22.
```

```text
What is the weather today?
```

For incomplete prediction requests:

```text
User: Who will win Pies vs Cats?

Assistant: Please provide the match date in YYYY-MM-DD format.

User: 2026-08-22
```

Predictions are always presented as **probabilistic model outputs, not certainties**.

## Setup

Create `.env`:

```env
OPENROUTER_API_KEY=your_api_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
ROUTER_MODEL=openai/gpt-oss-120b
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python day4_graph.py
```

## Testing

The application was tested across:

* Factual AFL questions
* Historical retrieval
* Match predictions
* Top-player predictions
* Missing-date clarification
* Unsupported predictions
* Off-topic requests
* Multi-turn conversations
* Team aliases

## Key Design Decision

LangGraph provides explicit control over routing and validation instead of allowing a single generic agent to freely choose actions. This makes prediction handling more consistent, improves error recovery, and reduces the risk of unsupported or hallucinated predictions.

## Known Limitation

The current implementation does **not** include a live AFL fixture/date resolver. Therefore, requests such as `Pies vs Cats this week` require the user to provide the match date explicitly.
