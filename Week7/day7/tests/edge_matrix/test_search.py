"""Generated search cases; see catalog.py for authored seeds."""
import pytest
from .catalog import search
from .harness import execute

from .supplemental import extra_cases

CASES = search() + extra_cases("search")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
