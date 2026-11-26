"""The LLM helper fails clearly (not mysteriously) when it is not configured. Offline."""
from __future__ import annotations

import pytest

from ilm import config, llm


@pytest.fixture(autouse=True)
def fresh_client():
    llm._client.cache_clear()
    yield
    llm._client.cache_clear()


def test_missing_key_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    with pytest.raises(llm.LLMUnavailable, match="LLM_API_KEY"):
        llm.ask("hi")


def test_unknown_provider_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "nope")
    with pytest.raises(llm.LLMUnavailable, match="not supported"):
        llm.ask("hi")


def test_rate_limits_are_retried_but_bad_requests_are_not():
    class E(Exception):
        def __init__(self, code):
            self.code = code
    assert llm._retryable(E(429)) and llm._retryable(E(503))
    assert not llm._retryable(E(400))
