"""Generated returning user cases; see catalog.py for authored seeds."""
import pytest
from .catalog import returning_user
from .harness import execute

from .supplemental import extra_cases

CASES = returning_user() + extra_cases("returning_user")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
