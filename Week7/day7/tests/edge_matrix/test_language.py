"""Generated language cases; see catalog.py for authored seeds."""
import pytest
from .catalog import language
from .harness import execute

from .supplemental import extra_cases

CASES = language() + extra_cases("language")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
