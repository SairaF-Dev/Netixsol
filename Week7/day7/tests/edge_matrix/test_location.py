"""Generated location cases; see catalog.py for authored seeds."""
import pytest
from .catalog import location
from .harness import execute

from .supplemental import extra_cases

CASES = location() + extra_cases("location")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
