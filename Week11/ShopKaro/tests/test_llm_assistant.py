"""
Tests for the LLM tool-calling shopping assistant (Day 4, Task 3).

The LLM is replaced by `ScriptedModel`, which plays back pre-written steps (tool calls or replies).
That exercises the real agent loop, the real ShopKaro tools and the real DuckDB catalogue, with no
network calls. One opt-in test (`-m live`, RUN_LIVE_LLM=1) talks to the real Gemini API.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import pytest

from shopkaro.api.main import serving_container
from shopkaro.assistant.llm_agent import (
    LLMShoppingAssistant,
    ModelStep,
    ToolCall,
    amounts_in_user_text,
)
from shopkaro.assistant.shopping_agent import HallucinationAuditor

Step = list[ToolCall] | str | Callable[[list[Any]], str] | Exception


class ScriptedModel:
    """Fake `ChatModel`: each `step()` returns the next scripted tool calls / reply / error."""

    model = "scripted-fake"

    def __init__(self, steps: list[Step]) -> None:
        self.steps = list(steps)
        self.histories: list[list[Any]] = []

    def user_message(self, text: str) -> Any:
        return {"role": "user", "text": text}

    def tool_results(self, results: list[tuple[ToolCall, dict[str, Any]]]) -> Any:
        return {"role": "tool", "results": [(c.name, r) for c, r in results]}

    def step(self, system_prompt: str, history: list[Any], tools: list[dict[str, Any]]) -> ModelStep:
        assert {t["name"] for t in tools} == {
            "search_products", "get_recommendations", "compare_products",
            "add_to_cart", "get_order_status", "get_review_summary",
        }
        self.histories.append(list(history))
        nxt = self.steps.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        if isinstance(nxt, list):
            return ModelStep(text="", tool_calls=nxt, raw={"role": "model", "calls": nxt})
        text = nxt(history) if callable(nxt) else nxt
        return ModelStep(text=text, tool_calls=[], raw={"role": "model", "text": text})


def last_tool_products(history: list[Any]) -> list[dict[str, Any]]:
    for item in reversed(history):
        if item.get("role") == "tool":
            for _name, result in item["results"]:
                for key in ("results", "recommendations", "compared_products"):
                    if result.get(key):
                        return result[key]
    return []


def list_products_reply(history: list[Any]) -> str:
    products = last_tool_products(history)[:3]
    lines = ["Ji zaroor! Yeh options hain:"]
    for i, p in enumerate(products, start=1):
        lines.append(f"{i}. **{p['product_id']}** — {p['title']} | PKR {p['price_pkr']:,.0f}")
    return "\n".join(lines)


def make_agent(steps: list[Step]) -> tuple[LLMShoppingAssistant, ScriptedModel]:
    serving_container.ensure_initialized()
    assert serving_container.tool_registry is not None
    model = ScriptedModel(steps)
    return LLMShoppingAssistant(tools=serving_container.tool_registry, model=model), model


def test_grounded_search_turn_uses_tool_results() -> None:
    agent, _ = make_agent(
        [[ToolCall("search_products", {"query": "eid ke liye lawn suit", "max_price_pkr": 5000})], list_products_reply]
    )
    turn = agent.chat("llm-t1", "eid ke liye lawn suit under 5000", user_id="15442")

    assert turn.engine == "llm" and turn.fallback_reason is None
    assert turn.invoked_tools == ["search_products"]
    assert turn.hallucination_audit.passed_zero_hallucination_check
    assert len(turn.shown_product_ids) >= 1
    search = turn.tool_outputs["search_products"]
    if not search["constraints_relaxed"]:
        assert all(p["price_pkr"] <= 5000 for p in search["results"])
    session = agent.sessions["llm-t1"]
    assert [p["product_id"] for p in session.last_shown_products] == [p["product_id"] for p in search["results"]]


def test_invented_product_triggers_one_correction() -> None:
    agent, model = make_agent(
        [
            [ToolCall("search_products", {"query": "school bag bachon ke liye"})],
            "Best option: **SK-99999** Magic Bag sirf PKR 1,234 mein!",  # invented
            list_products_reply,
        ]
    )
    turn = agent.chat("llm-t2", "bachon ke liye school bag", user_id="15442")

    assert turn.engine == "llm"
    assert turn.tool_outputs["_llm"]["corrected"] is True
    assert "SK-99999" not in turn.assistant_reply_urdulish
    assert turn.hallucination_audit.passed_zero_hallucination_check
    assert "[System check]" in model.histories[-1][-1]["text"]


def test_repeated_hallucination_falls_back_to_tool_rendered_reply() -> None:
    bad = "Yeh lein **SK-99999** sirf PKR 999 mein."
    agent, _ = make_agent([[ToolCall("search_products", {"query": "khussa"})], bad, bad])
    turn = agent.chat("llm-t3", "khussa dikhao", user_id="15442")

    assert turn.engine == "rules_fallback"
    assert "grounding" in (turn.fallback_reason or "")
    assert "SK-99999" not in turn.assistant_reply_urdulish
    assert turn.hallucination_audit.passed_zero_hallucination_check
    assert turn.shown_product_ids  # real products rendered from the tool output


def test_cart_side_effect_is_not_repeated_on_fallback() -> None:
    agent, _ = make_agent([[ToolCall("search_products", {"query": "perfume gift set"})], list_products_reply])
    agent.chat("llm-t4", "perfume gift set dikhao", user_id="15442")
    first = agent.sessions["llm-t4"].last_shown_products[0]

    bad = "Done! Total PKR 1 hai."
    agent.model.steps = [[ToolCall("add_to_cart", {"product_id": first["product_id"]})], bad, bad]
    turn = agent.chat("llm-t4", "pehla wala cart mein daal do", user_id="15442")

    cart = agent.sessions["llm-t4"].cart
    assert len(cart) == 1 and cart[0]["quantity"] == 1, "add_to_cart must run exactly once"
    assert turn.engine == "rules_fallback"
    assert first["product_id"] in turn.assistant_reply_urdulish


def test_llm_provider_error_falls_back_to_rule_engine() -> None:
    agent, _ = make_agent([RuntimeError("503 model overloaded")])
    turn = agent.chat("llm-t5", "Ammi ke liye Eid gift chahiye, 3000 tak", user_id="15442")

    assert turn.engine == "rules_fallback"
    assert "503" in (turn.fallback_reason or "")
    assert turn.assistant_reply_urdulish
    assert turn.hallucination_audit.passed_zero_hallucination_check


def test_multi_turn_history_and_context_reach_the_model() -> None:
    agent, model = make_agent([[ToolCall("search_products", {"query": "red lehenga"})], list_products_reply])
    agent.chat("llm-t6", "shaadi ke liye red lehenga", user_id="15442")
    shown_first = agent.sessions["llm-t6"].last_shown_products[0]["product_id"]

    agent.model.steps = ["Kaunsa product compare karna hai? Pehla ya doosra?"]
    agent.chat("llm-t6", "inke baare mein batao", user_id="15442")

    second_turn_history = model.histories[-1]
    user_texts = [h["text"] for h in second_turn_history if h.get("role") == "user"]
    assert any("shaadi ke liye red lehenga" in t for t in user_texts), "previous turn must be replayed"
    assert shown_first in user_texts[-1], "numbered shown products must be in the context note"


def test_tools_report_missing_data_honestly() -> None:
    serving_container.ensure_initialized()
    tools = serving_container.tool_registry
    assert tools is not None

    order = tools.get_order_status("ORD-0000")
    assert order["found"] is False and "order" not in order

    reviewed = set(tools.reviews_df["product_id"])
    unreviewed = next(pid for pid in tools.catalog_map if pid not in reviewed)
    summary = tools.get_review_summary(unreviewed)
    assert summary["total_reviews"] == 0
    assert summary["avg_rating"] is None and summary["sample_quotes"] == []

    assert tools.get_review_summary("SK-99999999")["found"] is False


def test_auditor_catches_suffix_prices_and_budget_parsing() -> None:
    audit = HallucinationAuditor.verify_response("Yeh 2,450 rupay ka hai", allowed_products={})
    assert audit.hallucinated_prices_pkr == [2450.0]
    audit_ok = HallucinationAuditor.verify_response("Yeh 2,450 rupay ka hai", allowed_products={"SK-00010": 2450.0})
    assert audit_ok.passed_zero_hallucination_check

    assert 150_000 in amounts_in_user_text("laptop for coding under 1.5 lac")
    assert 20_000 in amounts_in_user_text("red lehenga 20 hazaar tak")
    assert 3_000 in amounts_in_user_text("3000 tak")


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1", reason="set RUN_LIVE_LLM=1 to call the real LLM")
def test_live_gemini_conversation() -> None:
    from shopkaro.assistant.llm_agent import GeminiChatModel
    from shopkaro.config.settings import settings

    serving_container.ensure_initialized()
    assert serving_container.tool_registry is not None
    agent = LLMShoppingAssistant(
        tools=serving_container.tool_registry,
        model=GeminiChatModel(settings.llm_api_key, settings.llm_model),
    )
    t1 = agent.chat("live-1", "Ammi ke liye Eid gift chahiye, 3000 tak", user_id="15442")
    assert t1.engine == "llm", t1.fallback_reason
    assert t1.invoked_tools and t1.hallucination_audit.passed_zero_hallucination_check

    t2 = agent.chat("live-1", "pehla wala cart mein daal do", user_id="15442")
    assert t2.engine == "llm", t2.fallback_reason
    assert "add_to_cart" in t2.invoked_tools
    assert len(agent.sessions["live-1"].cart) == 1
