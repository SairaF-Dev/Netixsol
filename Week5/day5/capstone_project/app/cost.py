"""
Centralized LLM token and cost tracking.
"""

from typing import Optional


# ============================================================
# MODEL PRICING
# ============================================================

# USD per 1 million tokens.
#
# openai/gpt-4o-mini standard pricing:
# Input  = $0.15 / 1M tokens
# Output = $0.60 / 1M tokens
#
# These values are used for ESTIMATED cost when the provider
# does not return an explicit cost.

MODEL_PRICING = {
    "openai/gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
    },
}


# ============================================================
# COST CALCULATION
# ============================================================

def calculate_llm_cost(
    model: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
) -> Optional[float]:
    """
    Calculate estimated LLM cost in USD.

    Returns None when:
    - token usage is unavailable
    - model pricing is unavailable
    """

    if input_tokens is None:
        return None

    if output_tokens is None:
        return None

    pricing = MODEL_PRICING.get(model)

    if pricing is None:
        return None

    input_cost = (
        input_tokens / 1_000_000
    ) * pricing["input_per_1m"]

    output_cost = (
        output_tokens / 1_000_000
    ) * pricing["output_per_1m"]

    return round(
        input_cost + output_cost,
        8,
    )


# ============================================================
# TOKEN TOTAL
# ============================================================

def calculate_total_tokens(
    input_tokens: Optional[int],
    output_tokens: Optional[int],
) -> Optional[int]:

    if input_tokens is None:
        return None

    if output_tokens is None:
        return None

    return (
        input_tokens
        + output_tokens
    )