"""Generated unclear cases; see catalog.py for authored seeds."""
import pytest
from .catalog import unclear
from .harness import execute

CASES = unclear()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
