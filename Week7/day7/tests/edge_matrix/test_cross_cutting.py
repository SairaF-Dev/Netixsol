"""Generated cross cutting cases; see catalog.py for authored seeds."""
import pytest
from .catalog import cross_cutting
from .harness import execute

from .supplemental import extra_cases

CASES = cross_cutting() + extra_cases("cross_cutting")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
