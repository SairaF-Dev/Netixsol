"""Generated off topic cases; see catalog.py for authored seeds."""
import pytest
from .catalog import off_topic
from .harness import execute

CASES = off_topic()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_contract(case, monkeypatch):
    execute(case, monkeypatch)
