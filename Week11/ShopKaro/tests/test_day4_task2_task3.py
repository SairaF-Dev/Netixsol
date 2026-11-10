"""
Automated tests for Day 4 — Tasks 2 & 3: Personalized Search Re-Ranking & Tool-Calling UrduLish Assistant.
"""

from __future__ import annotations

from shopkaro.assistant.shopping_agent import (
    run_day4_task2_task3_personalizer_and_assistant,
)


def test_day4_task2_task3_personalizer_and_assistant() -> None:
    """Verify Personalized Search Re-Ranking divergence, all 6 agent tools, and 0 hallucinations."""
    pers_summary, turns, assistant = run_day4_task2_task3_personalizer_and_assistant()

    # 1. Verify Task 2: Luxury Persona receives higher average price & preferred brand uplift vs Budget Persona
    assert pers_summary.queries_tested == 6
    assert pers_summary.luxury_persona_avg_top5_price_pkr > pers_summary.budget_persona_avg_top5_price_pkr
    assert pers_summary.personalized_brand_hit_rate_uplift_pct > 0.0
    assert pers_summary.avg_top5_overlap_luxury_vs_budget_pct < 80.0

    # 2. Verify Task 3: All 6 tools invoked across the 6-turn conversation
    assert len(turns) == 6
    all_tools_invoked = {tool for t in turns for tool in t.invoked_tools}
    expected_tools = {
        "get_recommendations",
        "compare_products",
        "get_review_summary",
        "add_to_cart",
        "search_products",
        "get_order_status",
    }
    assert all_tools_invoked == expected_tools

    # 3. Verify Zero-Hallucination Guardrail across all 6 turns (0 fabricated SKUs or prices)
    for t in turns:
        assert t.hallucination_audit.passed_zero_hallucination_check is True
        assert len(t.hallucination_audit.hallucinated_product_ids) == 0
        assert len(t.hallucination_audit.hallucinated_prices_pkr) == 0

    # 4. Verify multi-turn session cart state after Turn 4
    session = assistant.sessions["SES-CAPSTONE-DEMO"]
    assert len(session.cart) == 1
    assert session.cart[0]["product_id"] == "SK-00010"
    assert session.cart[0]["unit_price_pkr"] == 2450.0

