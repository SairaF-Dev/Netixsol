"""Generated greetings cases; see catalog.py for authored seeds."""
import pytest
from .catalog import greetings
from .harness import execute

CASES = greetings()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
