"""Generated references cases; see catalog.py for authored seeds."""
import pytest
from .catalog import references
from .harness import execute

CASES = references()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
