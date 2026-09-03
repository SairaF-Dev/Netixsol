# Day 5 Setup Guide

## Prerequisites

- Python 3.9+
- PostgreSQL 14+ (optional, uses SQLite for dev)
- Redis 7+ (optional, uses in-memory for dev)
- OpenAI API key (for LLM)
- Day 4 API running on localhost:8004

## Local Setup

### 1. Create Virtual Environment

```bash
cd day5
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy and customize `.env.example`:

```bash
cp .env.example .env
```

Key variables:

```env
# LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_TIMEOUT=30

# Day 4 API Integration
DAY4_API_URL=http://localhost:8004
DAY4_API_KEY=your-api-key
DAY4_API_TIMEOUT=10

# RAG Configuration
RAG_ENABLED=true
RAG_DB_PATH=./chroma_db
RAG_EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Database
DB_TYPE=sqlite  # or postgres
DB_SQLITE_PATH=./data.db
DB_POSTGRES_URL=postgresql://user:pass@localhost/day5

# Memory
MEMORY_TYPE=in_memory  # or redis
MEMORY_REDIS_URL=redis://localhost:6379
MEMORY_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Agent Configuration
AGENT_NAME=Sara
AGENT_LANGUAGE=urduLish
AGENT_PERSONALITY=warm_professional
```

### 4. Verify Installation

```bash
# Run state tests
python -m pytest tests/test_state.py -v

# Check imports
python -c "from day5_langgraph import AgentState, AgentConfig; print('OK')"
```

## Development Workflow

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_state.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Creating New Nodes

1. Add node function to `nodes.py`
2. Add to `AgentNodes` class
3. Register in `graph.py`
4. Add tests in `tests/test_nodes.py`

### Adding New Tools

1. Add tool input model to `tools.py`
2. Add async method to `ToolExecutor`
3. Register tool in `TOOLS_DEFINITION`
4. Add integration tests

### Database Schema

For PostgreSQL, run:

```bash
psql -U postgres -d day5 -f schema.sql
```

For SQLite:

```bash
python -c "from src.day5_langgraph import init_db; init_db()"
```

## Production Deployment

### Docker

```bash
docker build -t day5-agent .
docker run -p 8005:8005 \
  -e OPENAI_API_KEY=sk-... \
  -e DAY4_API_URL=http://localhost:8004 \
  day5-agent
```

### Environment Variables

In production, set these:
- All API keys (OPENAI_API_KEY, DAY4_API_KEY)
- Database credentials (DB_POSTGRES_URL)
- Redis URL (MEMORY_REDIS_URL)
- Agent configuration (AGENT_LANGUAGE, AGENT_PERSONALITY)

### Health Checks

```bash
curl http://localhost:8005/health
# {"status": "healthy", "version": "0.1.0"}
```

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`, ensure:
1. Virtual environment is activated
2. Dependencies installed: `pip install -r requirements.txt`
3. Python path includes `src/`: check `pyproject.toml`

### Database Connection Issues

```bash
# Test SQLite
sqlite3 data.db ".tables"

# Test PostgreSQL
psql -U postgres -d day5 -c "SELECT 1"
```

### Day 4 API Connection

```bash
# Check if Day 4 is running
curl http://localhost:8004/health

# Check from Python
python -c "import httpx; print(httpx.get('http://localhost:8004/health').json())"
```

### LLM API Issues

```bash
# Verify OpenAI key
python -c "import os; print(os.getenv('OPENAI_API_KEY', 'NOT SET'))"

# Test LLM connection
python -c "from langchain_openai import ChatOpenAI; ChatOpenAI().invoke('test')"
```

## Next Steps

1. [Read Architecture Guide](docs/ARCHITECTURE.md)
2. [Review State Machine Design](docs/STATE_DESIGN.md)
3. [Check Node Reference](docs/NODE_REFERENCE.md)
4. [Run Example Conversations](docs/EXAMPLES.md)

---

**Questions?** See README.md for feature overview and quick start.
