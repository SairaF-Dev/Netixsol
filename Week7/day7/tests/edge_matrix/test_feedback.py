"""Generated feedback cases; see catalog.py for authored seeds."""
import pytest
from .catalog import feedback
from .harness import execute

CASES = feedback()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
