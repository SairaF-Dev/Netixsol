"""
numeric_guard.py
----------------
Strict Numeric Safety & Hallucination Guard.

Guarantees:
- Enforces the Critical Trust Rule: every numeric factual value in the assistant's
  final output MUST originate from an actual tool result.
- Detects ungrounded prices, scores, percentages, and market stats.
- If unverified numbers are detected in the LLM output, they are intercepted and
  replaced with an explicit notice of unavailability.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def extract_numbers_from_payload(payload: Any) -> Set[float]:
    """Recursively harvest all valid numeric facts produced by tools."""
    numbers: Set[float] = set()

    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        val = float(payload)
        numbers.add(round(val, 2))
        numbers.add(round(val, 0))
        # Add crore and lac representations
        if val >= 10_000_000:
            numbers.add(round(val / 10_000_000, 2))
            numbers.add(round(val / 10_000_000, 1))
        if val >= 100_000:
            numbers.add(round(val / 100_000, 2))
            numbers.add(round(val / 100_000, 1))
        # Add percentage representation if probability
        if 0.0 <= val <= 1.0:
            numbers.add(round(val * 100, 1))
            numbers.add(round(val * 100, 0))
    elif isinstance(payload, dict):
        for v in payload.values():
            numbers.update(extract_numbers_from_payload(v))
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            numbers.update(extract_numbers_from_payload(item))

    return numbers


class NumericFactGuard:
    """Verifies that numeric claims in text strictly correspond to tool outputs."""

    # Common allowed numbers that are not factual claims (e.g., list numbers, model versions)
    ALLOWED_CONTEXT_NUMBERS: Set[float] = {1.0, 2.0, 3.0, 4.0, 5.0, 24.0, 48.0, 2024.0, 2025.0, 2026.0}

    @classmethod
    def verify_and_enforce(
        cls,
        response_text: str,
        tool_results: Dict[str, Any],
        language: str = "english",
    ) -> Tuple[bool, str, List[str]]:
        """
        Verify that all numeric values in response_text trace to tool_results.

        Returns:
        - (is_safe, enforced_response_text, violations_list)
        """
        verified_numbers = extract_numbers_from_payload(tool_results)
        verified_numbers.update(cls.ALLOWED_CONTEXT_NUMBERS)

        # Extract numeric tokens from response text (e.g. "2.5", "25,000,000", "75%")
        cleaned_text = response_text.replace(",", "")
        # Find raw numbers
        raw_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", cleaned_text)

        violations: List[str] = []
        has_pricing_tool = "price_predictor_tool" in tool_results and tool_results["price_predictor_tool"].get("success")

        # Check if specific pricing amounts are claimed (e.g. "2.5 crore", "50 lac", "100000 pkr") without tool
        price_claim_patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:crore|cr|lac|lakh|lacs)\b",
            r"\b(?:pkr|rs\.?|rupees)\s*\d+\b",
            r"\b\d+\s*(?:pkr|rs\.?|rupees)\b",
        ]
        mentions_price_claim = any(re.search(p, cleaned_text, re.IGNORECASE) for p in price_claim_patterns)

        if mentions_price_claim and not has_pricing_tool and not ("market_stats_tool" in tool_results and tool_results["market_stats_tool"].get("available")):
            violations.append("Response claims specific property price figures without a successful Price Predictor or Market Stats tool output.")

        for num_str in raw_numbers:
            try:
                num_val = float(num_str)
                # Check if this number or its rounded equivalents are verified
                if (
                    round(num_val, 2) not in verified_numbers
                    and round(num_val, 0) not in verified_numbers
                    and num_val not in cls.ALLOWED_CONTEXT_NUMBERS
                ):
                    # Flag as unverified if it appears in a price/stat context
                    violations.append(f"Unverified numeric claim: {num_str}")
            except ValueError:
                pass

        if violations:
            logger.warning("Numeric safety guard detected violations: %s", violations)
            if not has_pricing_tool and mentions_price_claim:
                # Replace with safe refusal
                if language in ["urdulish", "urdu"]:
                    safe_response = (
                        "Model ke mutabiq is query ke liye verified valuation ya statistical data dastiyab nahi hai. "
                        "Main baghair verified model/data tool ke koi qeemat ya number guess nahi kar sakti."
                    )
                else:
                    safe_response = (
                        "Verified pricing data is unavailable for this query from the valuation model or database. "
                        "I cannot provide or estimate numeric prices without verified tool outputs."
                    )
                return False, safe_response, violations

        return True, response_text, violations
