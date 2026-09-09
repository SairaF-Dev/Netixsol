"""Generated frustration cases; see catalog.py for authored seeds."""
import pytest
from .catalog import frustration
from .harness import execute

from .supplemental import extra_cases

CASES = frustration() + extra_cases("frustration")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
