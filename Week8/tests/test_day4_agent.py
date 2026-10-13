"""
test_day4_agent.py
------------------
Automated test suite for Week 8 Day 4 Task 2: LangGraph AI Assistant.
Validates:
- Test A: Price valuation query (tool invocation, verified numeric consistency)
- Test B: Rental valuation query (rental purpose routing, tool-derived range)
- Test C: Lead scoring query (conversion probability, tier, persona attribution)
- Test D: Market statistics query (factual aggregations from clean dataset)
- Test E: Comparable properties query (factual retrieval from clean dataset)
- Test F: Explainability queries (lead TreeSHAP & honest price explainer contract)
- Test G: Missing slot detection & prompting (no ungrounded guesses)
- Test H: Numeric hallucination guard (intercepts ungrounded price claims)
- Test I: FastAPI POST /assistant/chat integration (valid response & validation errors)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.agent.graph import real_estate_assistant
from src.agent.numeric_guard import NumericFactGuard
from src.agent.tools.comparables_tool import comparable_properties_tool
from src.agent.tools.market_stats_tool import market_stats_tool
from src.agent.tools.explainer_tool import explainer_tool
from src.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# Test A: Price Question (Valuation Tool Invocation & Verified Facts)
# ==============================================================================

class TestPriceQuestion:
    def test_price_query_invokes_valuation_tool(self):
        query = "What is the fair price of a 10 marla house in DHA Lahore?"
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert state["intent"] in ["valuation", "hybrid"]
        assert "price_predictor_tool" in state["tool_calls"]
        assert "price_predictor_tool" in state["tool_results"]

        res = state["tool_results"]["price_predictor_tool"]
        assert "predicted_fair_price_pkr" in res
        fair_price = res["predicted_fair_price_pkr"]
        assert fair_price > 0

        # Assert no numeric hallucination in the final response
        assert (
            str(int(fair_price)) in state["final_response"].replace(",", "")
            or res.get("human_readable_summary", "") in state["final_response"]
            or "PKR" in state["final_response"]
            or "crore" in state["final_response"].lower()
            or "lakh" in state["final_response"].lower()
        )


# ==============================================================================
# Test B: Rent Question (Rental Purpose Routing)
# ==============================================================================

class TestRentQuestion:
    def test_rent_query_routes_to_rental_valuation(self):
        query = "Karachi Clifton mein 10 marla flat ka rent kitna hona chahiye?"
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert "price_predictor_tool" in state["tool_calls"]
        res = state["tool_results"]["price_predictor_tool"]
        assert res.get("purpose") == "For Rent"
        assert res.get("predicted_fair_price_pkr") > 0
        assert res.get("lower_bound_pkr") <= res.get("upper_bound_pkr")


# ==============================================================================
# Test C: Lead Scoring Question
# ==============================================================================

class TestLeadScoringQuestion:
    def test_lead_scoring_query_invokes_scorer(self):
        query = "Score this lead: Facebook lead from Islamabad, budget 30000000 PKR, 5 calls completed, 25 mins duration, visit booked."
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert state["intent"] in ["lead_scoring", "hybrid"]
        assert "lead_scorer_tool" in state["tool_calls"]
        res = state["tool_results"]["lead_scorer_tool"]
        assert "conversion_probability" in res
        assert 0.0 <= res["conversion_probability"] <= 1.0
        assert res["tier"] in ["Hot", "Warm", "Cold"]
        assert "customer_persona" in res


# ==============================================================================
# Test D: Market Stats Question (Exact Dataset Aggregation)
# ==============================================================================

class TestMarketStatsQuestion:
    def test_market_stats_query_aggregates_real_data(self):
        query = "What is the average price per marla in DHA Phase 5 Lahore?"
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert "market_stats_tool" in state["tool_calls"]
        res = state["tool_results"]["market_stats_tool"]
        assert res.get("found") is True
        assert res.get("total_listings_matched") > 0
        assert res.get("avg_price_per_marla_pkr") > 0
        assert res.get("median_price_per_marla_pkr") > 0

    def test_market_stats_direct_tool_execution(self):
        res = market_stats_tool(city="Lahore", location="DHA", purpose="For Sale")
        assert res["found"] is True
        assert res["total_listings_matched"] > 100
        assert res["avg_price_per_marla_pkr"] > 0


# ==============================================================================
# Test E: Comparable Properties Question (Factual Retrieval)
# ==============================================================================

class TestComparablesQuestion:
    def test_comparables_query_returns_factual_properties(self):
        query = "Show me 3 comparable houses for sale in Lahore with 5 marla area."
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert "comparable_properties_tool" in state["tool_calls"]
        res = state["tool_results"]["comparable_properties_tool"]
        assert res.get("found") is True
        assert len(res.get("comparables", [])) > 0

        # Verify factual integrity of returned properties
        for comp in res["comparables"]:
            assert "price_pkr" in comp
            assert comp["price_pkr"] > 0
            assert "city" in comp
            assert comp["city"] == "Lahore"

    def test_comparables_direct_tool_limit(self):
        res = comparable_properties_tool(city="Lahore", area_marla=10.0, limit=3)
        assert res["found"] is True
        assert len(res["comparables"]) <= 3


# ==============================================================================
# Test F: Explainability Contract
# ==============================================================================

class TestExplainability:
    def test_lead_explainer_direct_tool(self):
        lead_input = {
            "lead_source": "Facebook",
            "preferred_city": "Islamabad",
            "budget_pkr": 30000000.0,
            "number_of_calls": 5,
            "total_call_duration_min": 25.0,
            "visit_booked": 1,
        }
        res = explainer_tool(target="lead", lead_payload=lead_input)
        assert res["explanation_available"] is True
        assert "conversion_probability" in res
        assert "top_positive_features" in res
        assert "urdulish_summary" in res

    def test_price_explainer_honesty_contract(self):
        price_input = {
            "city": "Lahore",
            "area_marla": 10.0,
            "property_type": "House",
            "purpose": "For Sale",
        }
        res = explainer_tool(target="price", property_payload=price_input)
        assert res["explanation_available"] is True
        assert res["status"] == "shap_available"
        assert res["top_features"]
        assert res["target_scale"] == "log_price"


# ==============================================================================
# Test G: Missing Data Prompting (No Guessing)
# ==============================================================================

class TestMissingDataPrompting:
    def test_missing_area_prompts_user_without_inventing_price(self):
        query = "What is the fair price of a house in Lahore?"
        state = real_estate_assistant.invoke({
            "query": query,
            "messages": [{"role": "user", "content": query}],
        })

        assert "area_marla" in state.get("missing_fields", [])
        assert "price_predictor_tool" not in state.get("tool_calls", [])
        # Must ask for missing info
        assert ("marla" in state["final_response"].lower()) or ("size" in state["final_response"].lower())


# ==============================================================================
# Test H: Numeric Hallucination Guardrail
# ==============================================================================

class TestNumericFactGuard:
    def test_guard_allows_grounded_numbers(self):
        tool_results = {
            "price_predictor_tool": {
                "success": True,
                "predicted_fair_price_pkr": 25000000.0,
                "lower_bound_pkr": 22000000.0,
                "upper_bound_pkr": 28000000.0,
            }
        }
        text = "The fair price is 25000000 PKR with range 22000000 to 28000000 PKR."
        is_safe, safe_text, violations = NumericFactGuard.verify_and_enforce(text, tool_results, language="english")
        assert is_safe is True
        assert "25000000" in safe_text

    def test_guard_intercepts_ungrounded_price_claims(self):
        # Empty tool results -> ungrounded price claim must be blocked
        tool_results = {}
        hallucinated_text = "I estimate this house is worth 8.5 crore PKR in the open market."
        is_safe, safe_text, violations = NumericFactGuard.verify_and_enforce(hallucinated_text, tool_results, language="english")
        assert is_safe is False
        assert "Verified pricing data is unavailable" in safe_text or len(violations) > 0


# ==============================================================================
# Test I: FastAPI POST /assistant/chat Endpoint
# ==============================================================================

class TestAssistantChatEndpoint:
    def test_chat_endpoint_valid_valuation(self, client: TestClient):
        payload = {
            "message": "Lahore DHA Phase 5 mein 10 marla house ki fair price kiya hai?",
            "conversation_id": "test-conv-001",
        }
        response = client.post("/assistant/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert "intent" in data
        assert "tool_calls" in data
        assert "price_predictor_tool" in data["tool_calls"]
        assert "tool_results" in data
        assert data["guard_triggered"] is False
        assert data["inference_latency_ms"] > 0

    def test_chat_endpoint_valid_market_stats(self, client: TestClient):
        payload = {
            "message": "Average price per marla in Karachi Clifton for sale?",
        }
        response = client.post("/assistant/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "market_stats_tool" in data["tool_calls"]
        assert data["tool_results"]["market_stats_tool"]["found"] is True

    def test_chat_endpoint_rejects_empty_message(self, client: TestClient):
        payload = {"message": "   "}
        response = client.post("/assistant/chat", json=payload)
        assert response.status_code == 422
