# ShopKaro — Automated Test Suite

This directory contains automated unit, integration, and performance tests for the ShopKaro platform.

---

## Intended Purpose & Structure

The test suite ensures code quality, numerical accuracy, and contract stability across all machine learning and data engineering components:

```
tests/
├── unit/                   # Fast, isolated unit tests for individual functions and classes
├── integration/            # End-to-end data pipeline, model loading, and API endpoint tests
├── conftest.py             # Shared pytest fixtures, temporary directories, and mock objects
└── README.md               # Test documentation (this file)
```

---

## Running Tests

From the project root with the virtual environment activated:

```powershell
# Run the complete test suite
pytest

# Run tests with detailed verbosity and print statements
pytest -v -s

# Run unit tests only
pytest tests/unit

# Run with code coverage reporting
pytest --cov=src/shopkaro --cov-report=term-missing
```

---

## Testing Guidelines

1. **Isolation:** Unit tests must not depend on live external networks, LLM endpoints, or production database instances.
2. **Mocking:** Use `unittest.mock` or pytest monkeypatching for external LLM API calls, embedding generation, and Redis connections.
3. **Small Fixtures:** Test data transformations using small synthetic in-memory DataFrames rather than gigabyte-scale raw files.
4. **Deterministic Assertions:** Set random seeds (`random.seed`, `np.random.seed`) whenever testing stochastic ML algorithms.

