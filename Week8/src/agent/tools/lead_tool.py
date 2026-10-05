"""
lead_tool.py
------------
LangGraph tool for Lead Scoring and Tier Assignment.
Reuses the existing Task 1 LeadScorer and K-Means Persona models.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.predict_lead_scoring import LeadScorer

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

_lead_scorer: Optional[LeadScorer] = None


def get_lead_scorer() -> LeadScorer:
    global _lead_scorer
    if _lead_scorer is None:
        _lead_scorer = LeadScorer(models_dir=MODELS_DIR)
        _lead_scorer.load()
    return _lead_scorer


def lead_scorer_tool(
    preferred_city: str,
    budget_pkr: float,
    lead_source: str = "WhatsApp",
    purpose: str = "Buy",
    property_type: str = "House",
    number_of_calls: int = 1,
    total_call_duration_min: float = 3.0,
    visit_booked: int = 0,
    days_since_first_contact: int = 3,
    response_time_minutes: float = 30.0,
    preferred_location: str = "Unknown",
    follow_up_count: int = 0,
    budget_match_ratio: float = 1.0,
    objection_raised: str = "None",
) -> Dict[str, Any]:
    """
    Score a real estate customer lead, returning conversion probability, tier, and persona.

    Parameters:
    - preferred_city: 'Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad'
    - budget_pkr: Customer budget in PKR (must be > 0)
    - lead_source: 'WhatsApp', 'Call', 'Website', 'Facebook', 'Referral', etc.
    - purpose: 'Buy', 'Rent', 'Invest'
    - property_type: 'House', 'Flat', etc.
    - number_of_calls: Prior phone interaction count
    - total_call_duration_min: Cumulative call length in minutes
    - visit_booked: 1 if in-person site visit booked, else 0
    - days_since_first_contact: Days since initial inquiry
    - response_time_minutes: Agent response speed

    Returns structured lead scoring output.
    """
    if budget_pkr <= 0:
        return {
            "success": False,
            "error": "Budget must be greater than 0 PKR.",
        }

    valid_cities = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]
    matched_city = next((c for c in valid_cities if c.lower() == preferred_city.strip().lower()), None)
    if not matched_city:
        return {
            "success": False,
            "error": f"City '{preferred_city}' is not in the supported coverage area: {valid_cities}",
        }

    lead_input = {
        "preferred_city": matched_city,
        "preferred_location": str(preferred_location or "Unknown"),
        "budget_pkr": float(budget_pkr),
        "lead_source": lead_source.strip().title(),
        "purpose": purpose.strip().title(),
        "property_type": property_type.strip().title(),
        "number_of_calls": int(number_of_calls),
        "total_call_duration_min": float(total_call_duration_min),
        "visit_booked": int(visit_booked),
        "days_since_first_contact": int(days_since_first_contact),
        "response_time_minutes": float(response_time_minutes),
        "follow_up_count": int(follow_up_count),
        "budget_match_ratio": float(budget_match_ratio),
        "objection_raised": str(objection_raised or "None"),
    }

    try:
        scorer = get_lead_scorer()
        res = scorer.score_lead(lead_input)
        return {
            "success": True,
            "conversion_probability": res["conversion_probability"],
            "lead_score_pct": res["lead_score_pct"],
            "tier": res["tier"],
            "priority_rank": res["priority_rank"],
            "recommended_sla_action": res["recommended_sla_action"],
            "customer_persona": res["customer_persona"],
            "persona_cluster_id": res["persona_cluster_id"],
            "urdulish_explanation": res["urdulish_explanation"],
            "model_version": res.get("model_version", "lgbm_optuna_v1.0"),
        }
    except Exception as e:
        logger.error("Lead scoring tool error: %s", e, exc_info=True)
        return {
            "success": False,
            "error": f"Lead scoring failed: {str(e)}",
        }
