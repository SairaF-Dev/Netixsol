"""Generated system input cases; see catalog.py for authored seeds."""
import pytest
from .catalog import system_input
from .harness import execute

CASES = system_input()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
