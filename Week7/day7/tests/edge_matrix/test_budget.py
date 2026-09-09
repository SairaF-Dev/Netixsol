"""Generated budget cases; see catalog.py for authored seeds."""
import pytest
from .catalog import budget
from .harness import execute

CASES = budget()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
