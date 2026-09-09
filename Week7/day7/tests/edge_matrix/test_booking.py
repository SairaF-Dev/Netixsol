"""Generated booking cases; see catalog.py for authored seeds."""
import pytest
from .catalog import booking
from .harness import execute

from .supplemental import extra_cases

CASES = booking() + extra_cases("booking")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
