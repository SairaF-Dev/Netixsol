"""Generated negation cases; see catalog.py for authored seeds."""
import pytest
from .catalog import negation
from .harness import execute

from .supplemental import extra_cases

CASES = negation() + extra_cases("negation")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
