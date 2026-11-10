"""
LLM tool-calling layer for the UrduLish shopping assistant (Day 4, Task 3).

One customer turn works like this:
1. The customer message, plus a short context note (cart, products shown so far), is sent to the
   LLM together with JSON-schema declarations of the 6 ShopKaro tools.
2. The LLM either answers or requests tool calls. Tool calls run against the real
   `ShopKaroToolRegistry` (DuckDB catalogue, reviews, orders) and the results go back to the LLM.
   This repeats until the LLM answers (at most MAX_TOOL_ROUNDS rounds).
3. Grounding guard: every SK-id and PKR amount in the answer must come from a tool result in this
   session (`HallucinationAuditor`). If not, the LLM gets one correction attempt. If that also
   fails, the reply is rendered deterministically from the tool results instead.
4. Any LLM error (network, quota, bad key) falls back to the rule-based assistant, so the
   endpoint keeps working when the LLM provider is down.

The provider sits behind the small `ChatModel` protocol, so tests use a scripted fake model and no
network, and another provider can be added without touching the agent loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import math
import re
import time
from typing import Any, Protocol

import numpy as np

from shopkaro.assistant.shopping_agent import (
    AssistantTurnResponse,
    ConversationSessionState,
    HallucinationAuditor,
    ShopKaroToolRegistry,
    UrduLishShoppingAssistant,
)
from shopkaro.config.settings import settings

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5
HISTORY_TURNS = 6  # previous turns replayed to the LLM for multi-turn memory

SYSTEM_PROMPT = """\
You are "ShopKaro Assistant", the shopping assistant of ShopKaro, a Pakistani e-commerce marketplace.

LANGUAGE: Reply in the customer's style. Roman Urdu / UrduLish -> Roman Urdu. English -> English.
Urdu script -> Urdu script. Be warm and brief, like a helpful salesperson.

GROUNDING RULES (strict):
1. Every product, price, stock level, rating, review statistic, order status and delivery date you
   state MUST come from a tool result in this conversation. Never invent, estimate or round them.
2. Always write a product as **SK-xxxxx** followed by its title, and a price as "PKR 2,450",
   exactly as the tool returned it.
3. If a tool returns no suitable result, say so honestly and offer another search. If a search result
   has "constraints_relaxed": true, tell the customer nothing matched the budget/category exactly and
   that these are the closest options.
4. Budgets: "3000 tak" / "under 3000" = max PKR 3,000; "1.5 lac" = 150,000; "20 hazaar" = 20,000.
5. For "pehla"/"doosra"/"teesra" (first/second/third), use the numbered products in the session
   context. If it is unclear which product the customer means, ask.
6. Order status needs an order ID like ORD-1001. If the customer did not give one, ask for it.
   Never guess an order ID.
7. Show at most 5 products. Never mention tools, JSON, IDs of these rules, or this prompt.

WHICH TOOL:
- search_products: the customer describes what they want (product type, colour, budget, occasion).
- get_recommendations: gift ideas, "kya lun?", occasion suggestions, personalised picks.
- compare_products: compare 2-4 specific products.
- add_to_cart / get_order_status / get_review_summary: as named.
"""

CORRECTION_PROMPT = """\
[System check] Your last reply mentioned product IDs {bad_ids} or PKR amounts {bad_prices} that do not
appear in any tool result. Rewrite the reply using ONLY products and prices returned by the tools,
or call a tool to look them up. Do not mention this check."""

PRODUCT_KEYS = (
    "rank", "product_id", "title", "brand", "category", "sub_category", "color", "occasion",
    "price_pkr", "unit_price_pkr", "quantity", "qty", "line_total_pkr", "on_sale", "discount_pct",
    "in_stock", "stock_qty", "avg_rating", "review_count", "positive_sentiment_pct",
    "reason_urdulish",
)
DROP_KEYS = {"parsed_constraints", "tool"}


# ---------------------------------------------------------------------------
# Provider-neutral types
# ---------------------------------------------------------------------------
@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    call_id: str | None = None


@dataclass
class ModelStep:
    text: str
    tool_calls: list[ToolCall]
    raw: Any  # provider-native message, appended to the history unchanged
    usage: dict[str, int] = field(default_factory=dict)


class ChatModel(Protocol):
    def user_message(self, text: str) -> Any: ...

    def tool_results(self, results: list[tuple[ToolCall, dict[str, Any]]]) -> Any: ...

    def step(self, system_prompt: str, history: list[Any], tools: list[dict[str, Any]]) -> ModelStep: ...


class GeminiChatModel:
    """`ChatModel` backed by Google Gemini function calling (google-genai SDK)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
        temperature: float = 0.3,
    ) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
        self.model = model
        self.temperature = temperature
        self._tools_key: int | None = None
        self._tools_obj: Any = None

    def user_message(self, text: str) -> Any:
        t = self._types
        return t.Content(role="user", parts=[t.Part.from_text(text=text)])

    def tool_results(self, results: list[tuple[ToolCall, dict[str, Any]]]) -> Any:
        t = self._types
        parts = [
            t.Part(function_response=t.FunctionResponse(id=call.call_id, name=call.name, response=result))
            for call, result in results
        ]
        return t.Content(role="user", parts=parts)

    def _tools(self, tools: list[dict[str, Any]]) -> Any:
        key = id(tools)
        if key != self._tools_key:
            t = self._types
            self._tools_obj = [
                t.Tool(
                    function_declarations=[
                        t.FunctionDeclaration(
                            name=spec["name"],
                            description=spec["description"],
                            parameters_json_schema=spec["parameters"],
                        )
                        for spec in tools
                    ]
                )
            ]
            self._tools_key = key
        return self._tools_obj

    def step(self, system_prompt: str, history: list[Any], tools: list[dict[str, Any]]) -> ModelStep:
        t = self._types
        config = t.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=self._tools(tools),
            # We run the tool loop ourselves so every call can be logged and grounded.
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
            temperature=self.temperature,
            max_output_tokens=1024,
        )
        resp = self._client.models.generate_content(model=self.model, contents=history, config=config)
        if not resp.candidates or resp.candidates[0].content is None:
            reason = resp.candidates[0].finish_reason if resp.candidates else "no candidates"
            raise RuntimeError(f"Gemini returned no content (finish_reason={reason})")

        # Keep the model's Content object as-is: Gemini 3 attaches thought signatures to tool
        # calls, and rebuilding the message would drop them and break the next request.
        content = resp.candidates[0].content
        calls = [
            ToolCall(name=fc.name, args=dict(fc.args or {}), call_id=getattr(fc, "id", None))
            for fc in (resp.function_calls or [])
        ]
        text = "".join(
            p.text for p in (content.parts or []) if getattr(p, "text", None) and not getattr(p, "thought", False)
        )
        usage = {}
        if resp.usage_metadata is not None:
            usage = {
                "prompt_tokens": int(resp.usage_metadata.prompt_token_count or 0),
                "output_tokens": int(resp.usage_metadata.candidates_token_count or 0),
            }
        return ModelStep(text=text.strip(), tool_calls=calls, raw=content, usage=usage)


# ---------------------------------------------------------------------------
# Tool declarations
# ---------------------------------------------------------------------------
def build_tool_specs(categories: list[str]) -> list[dict[str, Any]]:
    """JSON-schema declarations of the 6 ShopKaro tools, as sent to the LLM."""
    category_prop = {
        "type": "string",
        "enum": categories,
        "description": "Optional catalogue category filter. Only set it when clearly implied.",
    }
    return [
        {
            "name": "search_products",
            "description": (
                "Search the ShopKaro catalogue (hybrid keyword + semantic search, understands Roman Urdu, "
                "English and Urdu, personalised for the customer). Returns in-stock products with price."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the customer wants, in their words."},
                    "max_price_pkr": {"type": "number", "description": "Maximum price in PKR, if a budget was given."},
                    "category": category_prop,
                    "k": {"type": "integer", "description": "Number of results (1-8). Default 5."},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_recommendations",
            "description": "Gift and occasion recommendations (e.g. Eid gift for ammi, shaadi outfit) within a budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "occasion": {"type": "string", "description": "e.g. Eid, Shaadi, Ramadan, Back to School."},
                    "max_budget_pkr": {"type": "number", "description": "Maximum price in PKR."},
                    "recipient_hint": {"type": "string", "description": "Who it is for, e.g. ammi, abbu, bhai, bachay."},
                    "category": category_prop,
                    "k": {"type": "integer", "description": "Number of items (1-8). Default 3."},
                },
            },
        },
        {
            "name": "compare_products",
            "description": "Compare 2-4 products side by side: price, sale, stock, rating and review sentiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string", "description": "Product ID like SK-00010."},
                        "description": "2 to 4 product IDs.",
                    }
                },
                "required": ["product_ids"],
            },
        },
        {
            "name": "add_to_cart",
            "description": "Add a product to the customer's cart after a live stock check. Returns the cart total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID like SK-00010."},
                    "quantity": {"type": "integer", "description": "Units to add (1-10). Default 1."},
                },
                "required": ["product_id"],
            },
        },
        {
            "name": "get_order_status",
            "description": "Look up an order's delivery status, courier, tracking number and ETA.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "Order ID like ORD-1001."}},
                "required": ["order_id"],
            },
        },
        {
            "name": "get_review_summary",
            "description": "Summary of verified (non-spam) customer reviews: rating, sentiment, aspect scores, quotes.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string", "description": "Product ID like SK-00010."}},
                "required": ["product_id"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_jsonable(obj: Any) -> Any:
    """Convert numpy / NaN values so tool results serialise cleanly for the LLM API."""
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _compact(obj: Any) -> Any:
    """Shrink tool output for the LLM: keep only customer-relevant product fields (saves tokens)."""
    if isinstance(obj, dict):
        if "product_id" in obj and ("title" in obj or "price_pkr" in obj):
            return {k: _compact(v) for k, v in obj.items() if k in PRODUCT_KEYS}
        return {k: _compact(v) for k, v in obj.items() if k not in DROP_KEYS}
    if isinstance(obj, list):
        return [_compact(v) for v in obj]
    return obj


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def amounts_in_user_text(text: str) -> set[float]:
    """Budget figures the customer typed ("3000 tak", "1.5 lac", "20 hazaar") may be repeated back."""
    found: set[float] = set()
    for num, unit in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(lac|lakh|lacs|hazaar|hazar|k)?\b", text, flags=re.I):
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        unit = unit.lower()
        if unit in ("lac", "lakh", "lacs"):
            value *= 100_000
        elif unit in ("hazaar", "hazar", "k"):
            value *= 1_000
        found.add(round(value, 0))
    return found


@dataclass
class _Grounding:
    """Products and PKR amounts the assistant is allowed to mention (all from tool results)."""

    products: dict[str, float] = field(default_factory=dict)
    prices: set[float] = field(default_factory=set)

    def absorb(self, obj: Any) -> None:
        if isinstance(obj, dict):
            pid = obj.get("product_id")
            price = _num(obj.get("price_pkr", obj.get("unit_price_pkr")))
            if isinstance(pid, str) and price is not None:
                self.products[pid] = price
            for key, value in obj.items():
                if key.endswith("_pkr") and _num(value) is not None:
                    self.prices.add(round(float(value), 0))
                self.absorb(value)
        elif isinstance(obj, list):
            for value in obj:
                self.absorb(value)


def _products_in(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("results", "recommendations", "compared_products"):
        if isinstance(result.get(key), list):
            return [p for p in result[key] if isinstance(p, dict) and "product_id" in p]
    return []


def render_tool_outputs(tool_log: list[tuple[str, dict[str, Any], dict[str, Any]]]) -> str:
    """Deterministic, grounded-by-construction reply built only from tool results."""
    lines: list[str] = []
    for name, _args, result in tool_log:
        if result.get("error"):
            lines.append(f"Maazrat! {result['error']}")
            continue
        if name in ("search_products", "get_recommendations", "compare_products"):
            products = _products_in(result)
            if not products:
                lines.append("Maazrat, is talash ke mutabiq koi product nahi mila.")
                continue
            if result.get("constraints_relaxed"):
                lines.append("Aap ke budget/category mein exact match nahi mila, yeh sab se qareeb options hain:")
            for i, p in enumerate(products[:5], start=1):
                lines.append(f"{i}. **{p['product_id']}** — {p.get('title', '')} | PKR {float(p['price_pkr']):,.0f}")
        elif name == "add_to_cart" and result.get("success"):
            a = result["added_product"]
            lines.append(
                f"**{a['product_id']}** ({a['title']} — PKR {a['price_pkr']:,.0f}) cart mein add ho gaya. "
                f"Cart total: PKR {result['cart_total_pkr']:,.0f}."
            )
        elif name == "get_order_status" and result.get("found"):
            o = result["order"]
            lines.append(
                f"Order **{o['order_id']}**: {o['order_status']} via {o['courier_partner']} "
                f"(Tracking: {o['tracking_number']}). Expected delivery: {o['estimated_delivery']}."
            )
        elif name == "get_review_summary" and result.get("found"):
            if result["total_reviews"] == 0:
                lines.append(f"**{result['product_id']}** ke abhi tak koi verified reviews nahi hain.")
            else:
                lines.append(
                    f"**{result['product_id']}**: {result['total_reviews']} verified reviews, "
                    f"average rating {result['avg_rating']}/5 ({result['positive_pct']}% positive)."
                )
    return "\n".join(lines) or "Maazrat, main abhi yeh request poori nahi kar saka. Dobara koshish karein."


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class LLMShoppingAssistant:
    """LLM-driven UrduLish shopping assistant. Same `chat()` interface as `UrduLishShoppingAssistant`."""

    def __init__(
        self,
        tools: ShopKaroToolRegistry,
        model: ChatModel,
        fallback: UrduLishShoppingAssistant | None = None,
    ) -> None:
        self.tools = tools
        self.model = model
        self.fallback = fallback or UrduLishShoppingAssistant(tools=tools)
        # Share session state with the rule-based assistant so carts survive a fallback.
        self.sessions = self.fallback.sessions
        self._llm_history: dict[str, list[list[Any]]] = {}
        categories = sorted({str(m["category"]) for m in tools.catalog_map.values() if m.get("category")})
        self.tool_specs = build_tool_specs(categories)

    def get_or_create_session(self, session_id: str, user_id: str = "USR-DEMO-01") -> ConversationSessionState:
        return self.fallback.get_or_create_session(session_id=session_id, user_id=user_id)

    # -- public ------------------------------------------------------------
    def chat(self, session_id: str, user_message: str, user_id: str = "USR-DEMO-01") -> AssistantTurnResponse:
        session = self.get_or_create_session(session_id=session_id, user_id=user_id)
        try:
            return self._chat_llm(session, user_message, user_id)
        except Exception as exc:  # network, quota, auth, malformed response...
            reason = f"{type(exc).__name__}: {str(exc)[:300]}"
            logger.warning("LLM assistant failed, using rule-based fallback: %s", reason)
            turn = self.fallback.chat(session_id=session_id, user_message=user_message, user_id=user_id)
            turn.engine = "rules_fallback"
            turn.fallback_reason = reason
            return turn

    # -- internals ---------------------------------------------------------
    def _context_note(self, session: ConversationSessionState, user_id: str) -> str:
        lines = ["[Session context — not visible to the customer]", f"customer user_id: {user_id}"]
        if session.cart:
            total = sum(float(i["line_total_pkr"]) for i in session.cart)
            items = ", ".join(f"{i['product_id']} x{i['quantity']}" for i in session.cart)
            lines.append(f"cart: {items} (total PKR {total:,.0f})")
        else:
            lines.append("cart: empty")
        if session.last_shown_products:
            lines.append("products shown most recently (numbered for pehla/doosra/teesra):")
            for i, p in enumerate(session.last_shown_products[:5], start=1):
                lines.append(f"  {i}. {p['product_id']} — {p.get('title', '')} | PKR {float(p['price_pkr']):,.0f}")
        return "\n".join(lines)

    def _execute_tool(self, call: ToolCall, session: ConversationSessionState, user_id: str) -> dict[str, Any]:
        a = call.args
        k = lambda default: max(1, min(int(_num(a.get("k")) or default), 8))  # noqa: E731
        try:
            if call.name == "search_products":
                out = self.tools.search_products(
                    query=str(a.get("query", "")),
                    user_id=user_id,
                    max_price_pkr=_num(a.get("max_price_pkr")),
                    category=a.get("category") or None,
                    k=k(5),
                )
            elif call.name == "get_recommendations":
                out = self.tools.get_recommendations(
                    occasion=a.get("occasion") or None,
                    max_budget_pkr=_num(a.get("max_budget_pkr")),
                    recipient_hint=a.get("recipient_hint") or None,
                    category=a.get("category") or None,
                    k=k(3),
                )
            elif call.name == "compare_products":
                ids = [str(x).strip().upper() for x in (a.get("product_ids") or [])]
                out = self.tools.compare_products(ids)
                if not out["compared_products"]:
                    out["error"] = f"None of these product IDs exist: {ids}"
            elif call.name == "add_to_cart":
                qty = max(1, min(int(_num(a.get("quantity")) or 1), 10))
                out = self.tools.add_to_cart(session, product_id=str(a.get("product_id", "")).strip().upper(), quantity=qty)
            elif call.name == "get_order_status":
                out = self.tools.get_order_status(str(a.get("order_id", "")))
            elif call.name == "get_review_summary":
                out = self.tools.get_review_summary(str(a.get("product_id", "")).strip().upper())
            else:
                out = {"error": f"Unknown tool '{call.name}'."}
        except Exception as exc:
            logger.exception("Tool %s failed", call.name)
            out = {"error": f"Tool {call.name} failed: {type(exc).__name__}"}

        out = _to_jsonable(out)
        shown = _products_in(out)
        if shown:
            session.last_shown_products = shown
        return out

    def _chat_llm(self, session: ConversationSessionState, user_message: str, user_id: str) -> AssistantTurnResponse:
        t0 = time.perf_counter()
        grounding = _Grounding()
        grounding.absorb(session.last_shown_products)
        grounding.absorb(session.cart)
        grounding.prices.update(amounts_in_user_text(user_message))

        past_turns = self._llm_history.setdefault(session.session_id, [])
        turn_items: list[Any] = [
            self.model.user_message(f"{self._context_note(session, user_id)}\n\nCustomer: {user_message}")
        ]
        tool_log: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        usage = {"prompt_tokens": 0, "output_tokens": 0, "llm_calls": 0}
        reply: str | None = None
        correction_used = False
        fallback_reason: str | None = None

        for _ in range(MAX_TOOL_ROUNDS + 2):
            history = [item for turn in past_turns for item in turn] + turn_items
            step = self.model.step(SYSTEM_PROMPT, history, self.tool_specs)
            usage["llm_calls"] += 1
            for key in ("prompt_tokens", "output_tokens"):
                usage[key] += step.usage.get(key, 0)
            turn_items.append(step.raw)

            if step.tool_calls:
                results = []
                for call in step.tool_calls:
                    result = self._execute_tool(call, session, user_id)
                    logger.info("assistant tool %s(%s)", call.name, json.dumps(call.args, default=str)[:200])
                    tool_log.append((call.name, call.args, result))
                    grounding.absorb(result)
                    results.append((call, _compact(result)))
                turn_items.append(self.model.tool_results(results))
                continue

            audit = HallucinationAuditor.verify_response(step.text, grounding.products, grounding.prices)
            if step.text and audit.passed_zero_hallucination_check:
                reply = step.text
                break
            if correction_used or not step.text:
                fallback_reason = "LLM reply was empty" if not step.text else "LLM reply failed grounding check twice"
                break
            correction_used = True
            turn_items.append(
                self.model.user_message(
                    CORRECTION_PROMPT.format(
                        bad_ids=audit.hallucinated_product_ids or "none",
                        bad_prices=audit.hallucinated_prices_pkr or "none",
                    )
                )
            )
        else:
            fallback_reason = f"LLM did not finish within {MAX_TOOL_ROUNDS} tool rounds"

        if reply is None:
            if not tool_log:
                raise RuntimeError(fallback_reason or "LLM produced no reply")
            # Tools already ran (maybe add_to_cart), so don't re-run the rule engine and
            # double-apply side effects: render the reply straight from the tool results.
            reply = render_tool_outputs(tool_log)
            engine = "rules_fallback"
        else:
            engine = "llm"
            past_turns.append(turn_items)
            del past_turns[:-HISTORY_TURNS]

        audit = HallucinationAuditor.verify_response(reply, grounding.products, grounding.prices)
        tool_outputs: dict[str, Any] = {}
        for name, _args, result in tool_log:
            key = name if name not in tool_outputs else f"{name}#{sum(1 for k in tool_outputs if k.startswith(name))+1}"
            tool_outputs[key] = result
        invoked = [name for name, _a, _r in tool_log]
        tool_outputs["_llm"] = {
            "model": getattr(self.model, "model", type(self.model).__name__),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "corrected": correction_used,
            **usage,
        }

        turn = AssistantTurnResponse(
            session_id=session.session_id,
            turn_index=len(session.turn_history) + 1,
            user_message=user_message,
            detected_intent="+".join(dict.fromkeys(invoked)) or "conversation",
            invoked_tools=invoked,
            tool_outputs=tool_outputs,
            assistant_reply_urdulish=reply,
            shown_product_ids=list(dict.fromkeys(audit.valid_product_ids)),
            cart_item_count=sum(int(i["quantity"]) for i in session.cart),
            cart_total_pkr=sum(float(i["line_total_pkr"]) for i in session.cart),
            hallucination_audit=audit,
            engine=engine,
            fallback_reason=fallback_reason,
        )
        session.turn_history.append(turn)
        return turn


def build_shopping_assistant(
    tools: ShopKaroToolRegistry,
    engine: str | None = None,
) -> UrduLishShoppingAssistant | LLMShoppingAssistant:
    """
    Pick the assistant engine from settings:
    - "rules": rule-based assistant only.
    - "llm":   LLM assistant; error if no API key is configured.
    - "auto":  LLM assistant when LLM_API_KEY is set, otherwise rule-based.
    """
    engine = (engine or settings.assistant_engine).lower()
    rules = UrduLishShoppingAssistant(tools=tools)
    if engine == "rules":
        return rules

    problem = None
    if not settings.llm_api_key:
        problem = "LLM_API_KEY is empty"
    elif settings.llm_provider.lower() != "gemini":
        problem = f"LLM_PROVIDER '{settings.llm_provider}' is not supported (only 'gemini')"
    if problem:
        if engine == "llm":
            raise RuntimeError(f"ASSISTANT_ENGINE=llm but {problem}")
        logger.info("Using rule-based assistant: %s", problem)
        return rules

    model = GeminiChatModel(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    logger.info("Using LLM assistant (%s / %s)", settings.llm_provider, settings.llm_model)
    return LLMShoppingAssistant(tools=tools, model=model, fallback=rules)
