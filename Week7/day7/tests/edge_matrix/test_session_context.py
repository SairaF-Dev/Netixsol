"""Generated session context cases; see catalog.py for authored seeds."""
import pytest
from .catalog import session_context
from .harness import execute

CASES = session_context()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
