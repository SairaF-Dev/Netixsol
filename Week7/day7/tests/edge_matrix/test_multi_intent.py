"""Generated multi intent cases; see catalog.py for authored seeds."""
import pytest
from .catalog import multi_intent
from .harness import execute

CASES = multi_intent()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
