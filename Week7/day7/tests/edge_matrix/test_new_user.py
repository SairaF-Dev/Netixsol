"""Generated new user cases; see catalog.py for authored seeds."""
import pytest
from .catalog import new_user
from .harness import execute

CASES = new_user()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
