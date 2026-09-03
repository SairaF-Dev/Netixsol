from sara_agent.edge_case_policy import EdgeCasePolicy


def test_strict_choice_rejects_embedded_location_and_money_digits():
    p = EdgeCasePolicy()

    assert p.strict_choice_index("DHA phase6") is None
    assert p.strict_choice_index("F-10") is None
    assert p.strict_choice_index("3 crore") is None
    assert p.strict_choice_index("3 bedroom") is None
    assert p.strict_choice_index("2") == 1
    assert p.strict_choice_index("second wali") == 1


def test_safe_fuzzy_choice_requires_clear_winner():
    p = EdgeCasePolicy()

    options = [
        "Bahria Town",
        "DHA Phase 6",
        "DHA Phase 8",
        "Gulberg III",
    ]

    assert p.fuzzy_match_verified_option(
        "Bagria Town",
        options,
    ) == "Bahria Town"

    # Too ambiguous between multiple DHA phases.
    assert p.fuzzy_match_verified_option(
        "DHA",
        options,
    ) is None
