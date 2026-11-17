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


def test_budget_argument_reaches_the_search_engine() -> None:
    # The LLM sends the budget as an argument, not in the query text. Phones exist from ~24k; filtering only the
    # top-25 "mobile" hits afterwards used to return nothing for a 25k budget.
    serving_container.ensure_initialized()
    tools = serving_container.tool_registry
    assert tools is not None
    out = tools.search_products(query="mobile", max_price_pkr=25000, k=5)
    assert not out["constraints_relaxed"]
    assert out["results"] and all(p["price_pkr"] <= 25000 for p in out["results"])
    assert all(p["category"] == "Smartphones & Accessories" for p in out["results"])


def test_price_of_another_product_is_caught() -> None:
    # Transcript bug: the reply gave SK-00233 (a 165,600 phone) the price 24,250 of the cheapest phone.
    serving_container.ensure_initialized()
    tools = serving_container.tool_registry
    assert tools is not None
    first = tools.search_products(query="mobile", k=5)["results"][0]
    cheap = tools.search_products(query="mobile", max_price_pkr=25000, k=5)["results"][0]
    assert first["price_pkr"] != cheap["price_pkr"]
    wrong = f"Sab se sasta mobile **{first['product_id']}** hai, jiski price PKR {cheap['price_pkr']:,.0f} hai."
    right = f"Sab se sasta mobile **{cheap['product_id']}** hai, jiski price PKR {cheap['price_pkr']:,.0f} hai."

    agent, model = make_agent(
        [
            [ToolCall("search_products", {"query": "mobile"})],
            [ToolCall("search_products", {"query": "mobile", "max_price_pkr": 25000})],
            wrong,
            right,
        ]
    )
    turn = agent.chat("llm-pair", "mobile dikhao, 25 k budget hai", user_id="15442")
    assert turn.engine == "llm"
    assert turn.tool_outputs["_llm"]["corrected"] is True
    assert "gave a product another product's price" in model.histories[-1][-1]["text"]
    assert turn.assistant_reply_urdulish == right
    assert turn.hallucination_audit.passed_zero_hallucination_check

    # Budgets typed by the customer may still sit next to a product.
    ok = HallucinationAuditor.verify_response(
        f"Aap ke PKR 25,000 budget mein **{cheap['product_id']}** PKR {cheap['price_pkr']:,.0f} ka hai.",
        {cheap["product_id"]: cheap["price_pkr"]},
        {25000.0},
        paired_prices={cheap["product_id"]: {round(cheap["price_pkr"])}},
        free_amounts={25000.0},
    )
    assert ok.passed_zero_hallucination_check


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


def test_fallback_after_llm_turns_keeps_the_conversation() -> None:
    """LLM searched phones under 50,000; when the LLM then fails, the rule engine must stay on phones."""
    agent, _ = make_agent([
        [ToolCall("search_products", {"query": "mobile", "max_price_pkr": 50000})],
        list_products_reply,
        RuntimeError("LLM produced no reply"),
    ])
    agent.chat("llm-ctx", "mobile 50000 mein", user_id="15442")
    turn = agent.chat("llm-ctx", "max budget kitna hona chahey", user_id="15442")

    assert turn.engine == "rules_fallback"
    assert turn.detected_intent == "budget_advice"
    summary = turn.tool_outputs["search_products"]["price_summary"]
    assert "Smartphone" in summary["products_of_this_type"]
    assert f"PKR {summary['lowest_price_pkr']:,.0f}" in turn.assistant_reply_urdulish
    assert turn.hallucination_audit.passed_zero_hallucination_check


def test_budget_typed_in_an_earlier_turn_may_be_repeated() -> None:
    """'50,000' typed in turn 1 is the customer's own number, not a hallucination in turn 2."""
    agent, _ = make_agent([
        [ToolCall("search_products", {"query": "mobile", "max_price_pkr": 50000})],
        list_products_reply,
        "Ji, aap ka budget PKR 50,000 hai. Kya main pink color dhoondun?",
    ])
    agent.chat("llm-amt", "mobile 50000 mein", user_id="15442")
    turn = agent.chat("llm-amt", "theek hai", user_id="15442")
    assert turn.engine == "llm"
    assert turn.hallucination_audit.passed_zero_hallucination_check


def test_rules_budget_advice_colour_and_price_questions() -> None:
    from shopkaro.assistant.shopping_agent import UrduLishShoppingAssistant

    serving_container.ensure_initialized()
    agent = UrduLishShoppingAssistant(tools=serving_container.tool_registry)

    ask = agent.chat("adv-1", "max budget kitna hona chahey", user_id="15442")
    assert ask.detected_intent == "budget_advice" and ask.invoked_tools == []  # asks what product first

    agent.chat("adv-1", "mobile dikhao", user_id="15442")
    agent.chat("adv-1", "50000 mein", user_id="15442")
    pink = agent.chat("adv-1", "pink color ka hona chahey", user_id="15442")
    check = pink.tool_outputs["search_products"]["colour_check"]
    assert check["available"] is False and "White" in check["available_colours"]
    assert "nahi hai" in pink.assistant_reply_urdulish

    advice = agent.chat("adv-1", "max budget kitna hona chahey", user_id="15442")
    assert advice.detected_intent == "budget_advice"
    assert "Smartphone" in advice.tool_outputs["search_products"]["price_summary"]["products_of_this_type"]
    assert advice.hallucination_audit.passed_zero_hallucination_check

    laptop = agent.chat("adv-1", "laptop ki price range kya hai", user_id="15442")
    assert "Rice" not in laptop.assistant_reply_urdulish  # "price" must not fuzzy-match "rice"

    agent.chat("adv-1", "mobile dikhao", user_id="15442")
    first = agent.sessions["adv-1"].last_shown_products[0]
    price = agent.chat("adv-1", "pehla kitne ka hai", user_id="15442")
    assert price.detected_intent == "product_price"
    assert first["product_id"] in price.assistant_reply_urdulish
    assert price.hallucination_audit.passed_zero_hallucination_check


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


def test_invented_budget_in_any_form_is_caught() -> None:
    """Transcript bug: for "ads mobile dikhao" the LLM guessed a budget, 'shayad aap "50 hazaar" (50,000) ...'."""
    allowed = {"SK-08908": 48600.0}
    guessed = (
        'Shayad aap "50 hazaar" (50,000) tak ka mobile kehna chah rahe hain? '
        "**SK-08908** Tecno 5G Smartphone (PKR 48,600) budget mein hai."
    )
    audit = HallucinationAuditor.verify_response(guessed, allowed)
    assert not audit.passed_zero_hallucination_check
    assert 50000.0 in audit.hallucinated_prices_pkr
    # The same sentence is fine when the customer did type that budget.
    assert HallucinationAuditor.verify_response(guessed, allowed, {50000.0}).passed_zero_hallucination_check

    # Other ways of writing money are checked too; counts and specs are not mistaken for prices.
    for text, value in (("1.5 lac tak", 150000.0), ("25k budget", 25000.0), ("(3,000)", 3000.0)):
        assert HallucinationAuditor.verify_response(text, {}).hallucinated_prices_pkr == [value]
    for text in ("1,715 units stock mein hain", "8GB/256GB, 20000mAh, 45W", "2,000 reviews"):
        assert HallucinationAuditor.verify_response(text, {}).passed_zero_hallucination_check


def test_named_product_is_searched_not_swapped_for_gift_ideas() -> None:
    """Transcript bug: "ammi k liye eid ka suit" returned the shawl / perfume / skincare gift picks."""
    from shopkaro.assistant.shopping_agent import UrduLishShoppingAssistant

    serving_container.ensure_initialized()
    tools = serving_container.tool_registry
    assert tools is not None
    rules = UrduLishShoppingAssistant(tools=tools)

    suit = rules.chat("suit-1", "ammi k liye eid ka suit lena hai", user_id="15442")
    assert suit.invoked_tools == ["search_products"]
    assert all("Suit" in p["title"] for p in suit.tool_outputs["search_products"]["results"][:3])

    gift = rules.chat("suit-2", "Ammi ke liye Eid gift chahiye, 3000 tak", user_id="15442")
    assert gift.invoked_tools == ["get_recommendations"]  # open gift ideas still use the curated picks

    # Even if the LLM picks get_recommendations with a category, the curated gifts must respect it.
    recs = tools.get_recommendations(
        occasion="Eid", recipient_hint="ammi", category="Women's Lawn & Unstitched", k=5
    )["recommendations"]
    assert recs and all(r["category"] == "Women's Lawn & Unstitched" for r in recs)


def test_out_of_domain_guardrail_refusal() -> None:
    from shopkaro.assistant.shopping_agent import UrduLishShoppingAssistant

    serving_container.ensure_initialized()
    assert serving_container.tool_registry is not None
    rules_agent = UrduLishShoppingAssistant(tools=serving_container.tool_registry)

    # 1. Direct off-topic query should be rejected politely with 0 tool calls
    turn1 = rules_agent.chat("ood-1", "mujhey python ki defination bto", user_id="15442")
    assert turn1.detected_intent == "out_of_domain_refusal"
    assert turn1.invoked_tools == []
    assert "sirf" in turn1.assistant_reply_urdulish or "shopping" in turn1.assistant_reply_urdulish.lower()
    assert turn1.hallucination_audit.passed_zero_hallucination_check

    # 2. Math off-topic query
    turn2 = rules_agent.chat("ood-2", "solve 25 + 75 =", user_id="15442")
    assert turn2.detected_intent == "out_of_domain_refusal"
    assert turn2.invoked_tools == []

    # 3. Legitimate shopping query containing the word 'python' should NOT be refused
    turn3 = rules_agent.chat("ood-3", "python print shirt dikhao", user_id="15442")
    assert turn3.detected_intent != "out_of_domain_refusal"
    assert "search_products" in turn3.invoked_tools


def test_follow_up_budget_keeps_the_search_subject() -> None:
    """'mobile chahey' then 'budget 50000 hai' must stay on phones (it used to jump to lawn suits)."""
    from shopkaro.assistant.shopping_agent import UrduLishShoppingAssistant

    serving_container.ensure_initialized()
    assert serving_container.tool_registry is not None
    agent = UrduLishShoppingAssistant(tools=serving_container.tool_registry)
    parser = serving_container.tool_registry.search_engine.parser
    assert parser.parse("budget 50000 hai").max_price_pkr == 50_000
    assert parser.parse("50000 ka budget").max_price_pkr == 50_000
    assert parser.parse("budget 50000 hai").sort_preference == "relevance"  # a ceiling, not "cheapest"

    first = agent.chat("ctx-1", "mobile chahey", user_id="15442")
    phones = {p["category"] for p in first.tool_outputs["search_products"]["results"]}
    assert phones == {"Smartphones & Accessories"}

    follow = agent.chat("ctx-1", "budget 50000 hai", user_id="15442")
    res = follow.tool_outputs["search_products"]["results"]
    assert {p["category"] for p in res} == {"Smartphones & Accessories"}
    assert all(float(p["price_pkr"]) <= 50_000 for p in res)
    assert follow.hallucination_audit.passed_zero_hallucination_check

    # The budget is remembered for the next refinement ...
    colour = agent.chat("ctx-1", "white color mein", user_id="15442")
    res = colour.tool_outputs["search_products"]["results"]
    assert all(float(p["price_pkr"]) <= 50_000 for p in res)
    assert {p["category"] for p in res} == {"Smartphones & Accessories"}

    # ... and a new product starts a new search without the old budget
    new = agent.chat("ctx-1", "laptop dikhao", user_id="15442")
    assert new.tool_outputs["search_products"]["effective_max_price_pkr"] is None
    assert {p["category"] for p in new.tool_outputs["search_products"]["results"]} == {"Laptops & Computing"}


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
