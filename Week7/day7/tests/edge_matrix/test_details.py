"""Generated details cases; see catalog.py for authored seeds."""
import pytest
from .catalog import details
from .harness import execute

CASES = details()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
