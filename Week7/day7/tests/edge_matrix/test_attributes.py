"""Generated attributes cases; see catalog.py for authored seeds."""
import pytest
from .catalog import attributes
from .harness import execute

CASES = attributes()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
