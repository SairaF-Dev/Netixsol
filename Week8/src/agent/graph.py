"""
graph.py
--------
LangGraph Real Estate Assistant StateGraph implementation.

Workflow:
START
  │
  ▼
[extract_and_plan]
  │
  ├─(missing required fields)──────────────┐
  │                                        ▼
  ▼                                [synthesize_response]
[execute_tools]                            ▲
  │                                        │
  └────────────────────────────────────────┘
  │
  ▼
[verify_numeric_safety]
  │
  ▼
END
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from langgraph.graph import END, START, StateGraph

from src.agent.numeric_guard import NumericFactGuard, extract_numbers_from_payload
from src.agent.state import AgentState
from src.agent.tools.comparables_tool import comparable_properties_tool
from src.agent.tools.explainer_tool import explainer_tool
from src.agent.tools.lead_tool import lead_scorer_tool
from src.agent.tools.market_stats_tool import market_stats_tool
from src.agent.tools.price_tool import price_predictor_tool
from src.models.predict_valuation import format_pkr_currency

logger = logging.getLogger(__name__)

SUPPORTED_CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]


def detect_language(query: str) -> str:
    """Detect if the query is in Urdu / Roman Urdu / UrduLish or English."""
    q_lower = query.lower()
    urdulish_tokens = [
        "mein", "ka", "ki", "ke", "ghar", "jana", "chahiye", "kitne", "hai", "hain",
        "batao", "bataen", "hoga", "kya", "dafa", "rabta", "karein", "shukriya",
        "kiraya", "kiraye", "kothi", "makan", "marla", "kanal", "qemat", "qeemat"
    ]
    matches = sum(1 for token in urdulish_tokens if re.search(rf"\b{token}\b", q_lower))
    return "urdulish" if matches >= 2 else "english"


def parse_area_marla(text: str) -> Optional[float]:
    """Parse area expressions like '1 kanal', '2 kanal', '10 marla', '5 marla'."""
    text_lower = text.lower()
    # Check for kanal (1 kanal = 20 marla)
    kanal_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kanal|kanals)", text_lower)
    if kanal_match:
        return float(kanal_match.group(1)) * 20.0

    # Check for marla
    marla_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:marla|marlas)", text_lower)
    if marla_match:
        return float(marla_match.group(1))

    return None


def parse_budget_pkr(text: str) -> Optional[float]:
    """Parse PKR budgets from text (crore, lac, lakh, million)."""
    text_lower = text.lower().replace(",", "")
    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crore|cr)", text_lower)
    if crore_match:
        return float(crore_match.group(1)) * 10_000_000.0

    lac_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lac|lakh|lacs)", text_lower)
    if lac_match:
        return float(lac_match.group(1)) * 100_000.0

    pkr_match = re.search(r"pkr\s*(\d+)", text_lower)
    if pkr_match:
        return float(pkr_match.group(1))

    # Raw numbers > 100,000
    num_matches = re.findall(r"\b\d{6,12}\b", text_lower)
    if num_matches:
        return float(num_matches[0])

    return None


def extract_entities(query: str) -> Dict[str, Any]:
    """Extract property and lead parameters from query."""
    q_lower = query.lower()
    entities: Dict[str, Any] = {}

    # City extraction
    for city in SUPPORTED_CITIES:
        if city.lower() in q_lower:
            entities["city"] = city
            break

    # Purpose
    if any(k in q_lower for k in ["rent", "kiraya", "kiraye", "kiraye par"]):
        entities["purpose"] = "For Rent"
    else:
        entities["purpose"] = "For Sale"

    # Property type
    if any(k in q_lower for k in ["flat", "apartment"]):
        entities["property_type"] = "Flat"
    elif any(k in q_lower for k in ["upper portion"]):
        entities["property_type"] = "Upper Portion"
    elif any(k in q_lower for k in ["lower portion"]):
        entities["property_type"] = "Lower Portion"
    elif any(k in q_lower for k in ["farmhouse", "farm house"]):
        entities["property_type"] = "Farm House"
    else:
        entities["property_type"] = "House"

    # Area Marla
    area = parse_area_marla(query)
    if area is not None:
        entities["area_marla"] = area

    # Location / Society extraction
    known_locations = [
        "dha phase 6", "dha phase 5", "dha phase 8", "dha phase 1", "dha defence", "dha",
        "bahria town", "bahria", "clifton", "gulberg", "johar town", "askari", "f-7", "f-6", "f-8", "f-10",
        "g-11", "cantt", "model town", "scheme 33", "korangi", "surjani"
    ]
    for loc in known_locations:
        if loc in q_lower:
            entities["location"] = loc.title()
            # If city was not explicitly named, infer city for uniquely identifiable locations
            if "city" not in entities:
                if "clifton" in loc or "scheme 33" in loc or "korangi" in loc:
                    entities["city"] = "Karachi"
                elif "f-7" in loc or "f-6" in loc or "f-8" in loc or "f-10" in loc or "g-11" in loc:
                    entities["city"] = "Islamabad"
                elif "dha" in loc and "city" not in entities:
                    # In Pakistan real estate DHA defaults to Lahore unless specified
                    entities["city"] = "Lahore"
            break

    # Bedrooms and Baths
    bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|kamray)", q_lower)
    if bed_match:
        entities["bedrooms"] = int(bed_match.group(1))

    bath_match = re.search(r"(\d+)\s*(?:bath|bathroom)", q_lower)
    if bath_match:
        entities["baths"] = int(bath_match.group(1))

    # Lead parameters
    budget = parse_budget_pkr(query)
    if budget is not None:
        entities["budget_pkr"] = budget

    if "visit" in q_lower:
        entities["visit_booked"] = 1

    return entities


# ==============================================================================
# Graph Node 1: Extract & Plan
# ==============================================================================
def extract_and_plan(state: AgentState) -> Dict[str, Any]:
    query = state.get("query", "")
    language = state.get("language") or detect_language(query)
    entities = extract_entities(query)

    q_lower = query.lower()
    tool_calls: List[str] = []
    missing_fields: List[str] = []

    is_lead_query = any(k in q_lower for k in ["lead", "client", "customer", "rabta", "inquirer", "investor lead"])
    is_stats_query = any(k in q_lower for k in ["average", "avg", "stats", "rate kya", "market average", "per marla rate", "price per marla"])
    is_comparable_query = any(k in q_lower for k in ["comparable", "similar", "dusri properties", "milti julti"])
    is_price_query = any(k in q_lower for k in ["kitne ka", "price", "valuation", "worth", "cost", "fair price", "qemat", "qeemat"]) or (not is_lead_query and not is_stats_query)

    if is_lead_query:
        intent = "lead_scoring"
        tool_calls.append("lead_scorer_tool")
        tool_calls.append("explainer_tool")
        if not entities.get("budget_pkr"):
            missing_fields.append("budget_pkr")
        if not entities.get("city"):
            missing_fields.append("preferred_city")
    elif is_stats_query:
        intent = "market_stats"
        tool_calls.append("market_stats_tool")
        if not entities.get("city"):
            missing_fields.append("city")
    else:
        intent = "valuation"
        # Mandatory requirements for price prediction: city, area_marla
        if not entities.get("city"):
            missing_fields.append("city")
        if not entities.get("area_marla"):
            missing_fields.append("area_marla")

        if not missing_fields:
            tool_calls.append("price_predictor_tool")
            tool_calls.append("explainer_tool")
            if is_comparable_query or "dha" in q_lower or entities.get("location"):
                tool_calls.append("comparable_properties_tool")

    return {
        "intent": intent,
        "language": language,
        "extracted_entities": entities,
        "tool_calls": tool_calls,
        "missing_fields": missing_fields,
        "tool_results": {},
    }


# ==============================================================================
# Graph Node 2: Execute Tools
# ==============================================================================
def execute_tools(state: AgentState) -> Dict[str, Any]:
    tool_calls = state.get("tool_calls", [])
    entities = state.get("extracted_entities", {})
    results: Dict[str, Any] = {}

    city = entities.get("city", "Lahore")
    location = entities.get("location", "DHA Defence")
    area_marla = entities.get("area_marla", 10.0)
    purpose = entities.get("purpose", "For Sale")
    property_type = entities.get("property_type", "House")
    bedrooms = entities.get("bedrooms", 3)
    baths = entities.get("baths", 3)

    if "price_predictor_tool" in tool_calls:
        results["price_predictor_tool"] = price_predictor_tool(
            city=city,
            location=location,
            area_marla=area_marla,
            purpose=purpose,
            property_type=property_type,
            bedrooms=bedrooms,
            baths=baths,
        )

    if "comparable_properties_tool" in tool_calls:
        results["comparable_properties_tool"] = comparable_properties_tool(
            city=city,
            purpose=purpose,
            property_type=property_type,
            area_marla=area_marla,
            location=location,
            limit=3,
        )

    if "market_stats_tool" in tool_calls:
        results["market_stats_tool"] = market_stats_tool(
            city=city,
            location=location,
            purpose=purpose,
        )

    if "lead_scorer_tool" in tool_calls:
        budget = entities.get("budget_pkr", 15_000_000.0)
        results["lead_scorer_tool"] = lead_scorer_tool(
            preferred_city=city,
            budget_pkr=budget,
            visit_booked=entities.get("visit_booked", 0),
            preferred_location=entities.get("location", "Unknown"),
            number_of_calls=entities.get("number_of_calls", 1),
            total_call_duration_min=entities.get("total_call_duration_min", 5.0),
            days_since_first_contact=entities.get("days_since_first_contact", 2),
        )

    if "explainer_tool" in tool_calls:
        if state.get("intent") == "lead_scoring":
            lead_payload = {
                "preferred_city": city,
                "preferred_location": entities.get("location", "Unknown"),
                "budget_pkr": entities.get("budget_pkr", 15_000_000.0),
                "lead_source": entities.get("lead_source", "WhatsApp"),
                "purpose": entities.get("purpose", "Buy"),
                "property_type": entities.get("property_type", "House"),
                "number_of_calls": entities.get("number_of_calls", 1),
                "total_call_duration_min": entities.get("total_call_duration_min", 5.0),
                "visit_booked": entities.get("visit_booked", 0),
                "days_since_first_contact": entities.get("days_since_first_contact", 2),
                "response_time_minutes": entities.get("response_time_minutes", 30.0),
                "follow_up_count": entities.get("follow_up_count", 0),
                "budget_match_ratio": 1.0,
                "objection_raised": "None",
            }
            results["explainer_tool"] = explainer_tool(target="lead", lead_payload=lead_payload)
        else:
            results["explainer_tool"] = explainer_tool(
                target="price",
                property_payload={
                    "city": city,
                    "location": location,
                    "area_marla": area_marla,
                    "purpose": purpose,
                    "property_type": property_type,
                    "bedrooms": bedrooms,
                    "baths": baths,
                },
            )

    verified_nums = extract_numbers_from_payload(results)
    return {
        "tool_results": results,
        "verified_numbers": list(verified_nums),
    }


# ==============================================================================
# Graph Node 3: Synthesize Response
# ==============================================================================
def synthesize_response(state: AgentState) -> Dict[str, Any]:
    missing = state.get("missing_fields", [])
    lang = state.get("language", "english")
    results = state.get("tool_results", {})
    entities = state.get("extracted_entities", {})

    # Handle missing information request (Do NOT guess)
    if missing:
        if lang in ["urdulish", "urdu"]:
            fields_str = ", ".join(missing)
            resp = (
                f"Barah-e-karam matlooba maloomat faraham karein ({fields_str}) "
                "taake model ke mutabiq sahi calculation ki ja sakay. Main baghair verified data ke qeemat ya score guess nahi karti."
            )
        else:
            fields_str = ", ".join(missing)
            resp = (
                f"Please provide the required details ({fields_str}) to compute a verified valuation or score. "
                "I cannot estimate or guess values without verified inputs."
            )
        return {"final_response": resp}

    lines: List[str] = []

    # 1. Price Prediction
    if "price_predictor_tool" in results:
        p_res = results["price_predictor_tool"]
        if p_res.get("success"):
            fair = p_res["predicted_fair_price_pkr"]
            p_min = p_res["lower_bound_pkr"]
            p_max = p_res["upper_bound_pkr"]
            fair_fmt = format_pkr_currency(fair)
            p_min_fmt = format_pkr_currency(p_min)
            p_max_fmt = format_pkr_currency(p_max)
            loc = p_res["location"]
            city = p_res["city"]
            area = p_res["area_marla"]
            purp = p_res["purpose"]

            if lang in ["urdulish", "urdu"]:
                lines.append(
                    f"Model ke mutabiq {loc}, {city} mein {area:.0f} marla property ({purp}) ki fair value "
                    f"{fair:,.0f} PKR ({fair_fmt}) hai. Iski estimated range {p_min:,.0f} PKR ({p_min_fmt}) se "
                    f"{p_max:,.0f} PKR ({p_max_fmt}) ke darmiyan hai."
                )
            else:
                lines.append(
                    f"According to the valuation model, the estimated fair price for a {area:.0f} Marla property in {loc}, {city} ({purp}) "
                    f"is {fair:,.0f} PKR ({fair_fmt}), with a verified range of {p_min:,.0f} PKR ({p_min_fmt}) to {p_max:,.0f} PKR ({p_max_fmt})."
                )
        else:
            lines.append(f"Price Predictor error: {p_res.get('error')}")

    # 2. Market Stats
    if "market_stats_tool" in results:
        m_res = results["market_stats_tool"]
        if m_res.get("available"):
            avg_ppm = m_res["average_price_per_marla_pkr"]
            med_ppm = m_res["median_price_per_marla_pkr"]
            count = m_res["record_count"]
            loc = m_res["location"]
            city = m_res["city"]

            if lang in ["urdulish", "urdu"]:
                lines.append(
                    f"Market data ke mutabiq {loc}, {city} mein average price per marla {avg_ppm:,.0f} PKR hai "
                    f"(Median: {med_ppm:,.0f} PKR, {count} verified listings par mabni)."
                )
            else:
                lines.append(
                    f"According to actual market data, the average price per marla in {loc}, {city} is {avg_ppm:,.0f} PKR "
                    f"(Median: {med_ppm:,.0f} PKR, based on {count} verified listings)."
                )
        else:
            lines.append("Market statistics are currently unavailable for this specific locality due to insufficient records.")

    # 3. Comparables
    if "comparable_properties_tool" in results:
        c_res = results["comparable_properties_tool"]
        if c_res.get("found"):
            props = c_res["properties"]
            if lang in ["urdulish", "urdu"]:
                lines.append(f"Database mein {len(props)} genuine matching listings mili hain:")
                for p in props:
                    lines.append(f"- ID #{p['property_id']}: {p['location']}, {p['area_marla']} Marla, Price: {p['price_pkr']:,.0f} PKR")
            else:
                lines.append(f"Retrieved {len(props)} actual comparable listings from database records:")
                for p in props:
                    lines.append(f"- ID #{p['property_id']}: {p['location']}, {p['area_marla']} Marla, Listed at: {p['price_pkr']:,.0f} PKR")

    # 4. Lead Scorer
    if "lead_scorer_tool" in results:
        l_res = results["lead_scorer_tool"]
        if l_res.get("success"):
            prob = l_res["conversion_probability"] * 100.0
            tier = l_res["tier"]
            action = l_res["recommended_sla_action"]
            persona = l_res["customer_persona"]
            if lang in ["urdulish", "urdu"]:
                lines.append(
                    f"Yeh lead '{tier}' category mein classify hui hai (Conversion Probability: {prob:.1f}%, Persona: '{persona}'). "
                    f"Recommended Action: {action}."
                )
            else:
                lines.append(
                    f"Lead classified as '{tier}' tier with a {prob:.1f}% conversion probability (Persona: '{persona}'). "
                    f"Recommended Action: {action}."
                )

    # 5. Explainer
    if "explainer_tool" in results:
        e_res = results["explainer_tool"]
        if e_res.get("target") == "lead" and e_res.get("explanation_available"):
            lines.append(f"Rationale: {e_res.get('urdulish_summary', '')}")
        elif e_res.get("target") == "price" and e_res.get("explanation_available"):
            lines.append(f"Price drivers: {e_res.get('urdulish_summary', '')}")

    # Valuation disclaimer propagation (Task 5 requirement)
    if "price_predictor_tool" in results and results["price_predictor_tool"].get("success"):
        if lang in ["urdulish", "urdu"]:
            lines.append("Disclaimer: Yeh sirf takhmina (estimated price) hai — koi official valuation, appraisal ya guaranteed market qeemat nahi hai.")
        else:
            lines.append("Disclaimer: Estimated price only — not an official valuation, appraisal, or guaranteed market price.")

    final_text = "\n\n".join(lines) if lines else "No tool outputs available to formulate a response."
    return {"final_response": final_text}


# ==============================================================================
# Graph Node 4: Verify Numeric Safety
# ==============================================================================
def verify_numeric_safety(state: AgentState) -> Dict[str, Any]:
    response = state.get("final_response", "")
    tool_results = state.get("tool_results", {})
    lang = state.get("language", "english")

    is_safe, enforced_resp, violations = NumericFactGuard.verify_and_enforce(
        response_text=response,
        tool_results=tool_results,
        language=lang,
    )

    return {
        "final_response": enforced_resp,
        "guard_triggered": not is_safe,
        "status": "success" if is_safe else "sanitized_hallucination",
    }


# ==============================================================================
# Graph Conditional Router
# ==============================================================================
def route_after_planning(state: AgentState) -> str:
    if state.get("missing_fields"):
        return "synthesize_response"
    if not state.get("tool_calls"):
        return "synthesize_response"
    return "execute_tools"


# ==============================================================================
# Build & Compile StateGraph
# ==============================================================================
def build_real_estate_graph():
    builder = StateGraph(AgentState)

    builder.add_node("extract_and_plan", extract_and_plan)
    builder.add_node("execute_tools", execute_tools)
    builder.add_node("synthesize_response", synthesize_response)
    builder.add_node("verify_numeric_safety", verify_numeric_safety)

    builder.add_edge(START, "extract_and_plan")
    builder.add_conditional_edges(
        "extract_and_plan",
        route_after_planning,
        {
            "execute_tools": "execute_tools",
            "synthesize_response": "synthesize_response",
        },
    )
    builder.add_edge("execute_tools", "synthesize_response")
    builder.add_edge("synthesize_response", "verify_numeric_safety")
    builder.add_edge("verify_numeric_safety", END)

    return builder.compile()


# Shared compiled graph instance
real_estate_assistant = build_real_estate_graph()
