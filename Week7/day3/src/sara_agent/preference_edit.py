"""Transport-independent preference editing state, separate from search intent."""
import re

FIELDS = {
    "city": r"city|shehar|shahar",
    "budget": r"budget|price range",
    "property_type": r"property type|type",
    "purpose": r"purpose",
    "bedrooms": r"bedrooms?|rooms?",
    "area": r"area|location|ilaqa",
    "amenities": r"amenities|facilities",
}
QUESTIONS = {
    "city": "Theek hai. Aap ab kis city mein property dekhna chahti hain?",
    "budget": "Zaroor. Aapka naya budget kitna hai?",
    "property_type": "Aap ab kis property type mein dekhna chahti hain?",
    "purpose": "Aap purchase karna chahti hain ya rent par lena hai?",
    "bedrooms": "Aapko ab kitne bedrooms chahiye?",
    "area": "Aap ab kis area ya location mein dekhna chahti hain?",
    "amenities": "Kaunsi amenities ya doosri requirements chahiye?",
}
WHICH = "Bilkul. Aap kis preference ko change karna chahti hain — city, budget, property type, purpose, bedrooms, area, ya koi aur requirement?"


def saved_requirement_summary(values):
    details = []
    if values.get("city"):
        details.append(f"{values['city']} mein")
    budget = values.get("budget")
    if budget is not None:
        details.append(f"{budget / 10_000_000:g} crore tak" if budget >= 10_000_000 else f"{budget:,} PKR tak")
    details.extend(str(values[k]).lower() for k in ("property_type", "purpose") if values.get(k))
    return "Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne " + " ".join(details) + " ke liye pucha tha, kya wahi requirement hai ya kuch change karna chahengi?"


def edit_cues(message):
    """Conservative language fallback; semantic NLU can also supply action/fields."""
    raw = message.casefold().strip()
    fields = [key for key, pattern in FIELDS.items() if re.search(r"\b(?:" + pattern + r")\b", raw)]
    cancel = re.search(r"\b(?:cancel edit|cancel change|change nahi|change nahin|mat badlo)\b", raw)
    change = re.search(r"\b(?:change|badal\w*|tabdeel\w*|replace|ki jagah|kar do|kr do)\b", raw)
    continuing = re.fullmatch(r"(?:continue|same requirement|wahi|haan|yes|ji haan)(?:\s+(?:kar do|kr do|chahiye))?[.! ]*", raw)
    return ("cancel" if cancel else "edit" if change and not continuing else "continue" if continuing else None), fields


def advance_edit(saved, understanding, message):
    """Return a clarification, or let the caller validate/persist and search.

    Never finish an edit here: callers mark ready only after successful storage.
    """
    is_area_relaxation = bool(re.search(
        r"\b(?:dusre|dusray|doosre|doosray|other|different|aur|aor|mazeed|more|qareebi)\s+areas?\b|"
        r"\b(?:areas?|locations?)\s+(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|check|dekh)\b|"
        r"\b(?:kisi\s+(?:aur|aor|dusre|doosre)\s+area)\b|"
        r"\bkoi\s+bhi\s+(?:area|location)\b|"
        r"\b(?:area|location)\s+(?:flexible|koi\s+bhi|matter\s+nahi)\b",
        message, flags=re.IGNORECASE
    ))
    if is_area_relaxation:
        saved.pop("preference_state", None)
        saved.pop("preference_fields", None)
        understanding.relax = list(set(understanding.relax) | {"area"})
        understanding.required.pop("area", None)
        understanding.preferred.pop("area", None)
        understanding.preference_action = None
        understanding.preference_fields = [f for f in getattr(understanding, "preference_fields", []) if f != "area"]
        understanding.intent = "property_search"
        understanding.needs_clarification = False
        understanding.clarification_reason = None
        return None

    action, fields = edit_cues(message)
    action = getattr(understanding, "preference_action", None) or action
    fields = list(dict.fromkeys(getattr(understanding, "preference_fields", []) + fields))
    active = saved.get("preference_state") in {"editing_preferences", "selecting_preference_field", "providing_preference_value"}
    if understanding.intent in {"schedule_visit", "reschedule_visit", "cancel_visit", "property_details", "property_selection"} or understanding.interaction_action:
        return None
    # A generic imperative such as "visit book kar do" is not a profile edit.
    if action == "edit" and not fields and not understanding.required and not active and re.search(r"\b(?:kar|kr) do\b", message, re.I) and not re.search(r"\b(?:change|badal\w*|ki jagah)\b", message, re.I):
        return None
    if action == "cancel" and active:
        saved.pop("preference_fields", None)
        saved["preference_state"] = "continuing_saved_preferences"
        understanding.required.clear()
        understanding.preferred.clear()
        understanding.intent = "property_search"
        return None
    if not active and action != "edit":
        return None
    if understanding.intent == "off_topic":
        return "Main property preferences mein madad kar sakti hoon. " + (QUESTIONS[saved["preference_fields"][0]] if saved.get("preference_fields") else WHICH)
    saved["pending_returning_confirm"] = False
    saved.pop("pending_returning_confirm_question", None)
    saved["returning_customer_handled"] = True
    saved["preference_state"] = "editing_preferences"
    values = {**understanding.preferred, **understanding.required}
    if understanding.needs_clarification:
        from .query_planner import QueryPlanner
        ambiguous = QueryPlanner._AMBIGUOUS_FIELDS_BY_REASON.get(understanding.clarification_reason, set())
        values = {k: v for k, v in values.items() if k not in ambiguous}
        existing_fields = saved.get("preference_fields", [])
        if not existing_fields or any(f in existing_fields for f in ambiguous):
            fields = list(dict.fromkeys(fields + sorted(ambiguous)))
    pending = list(dict.fromkeys(saved.get("preference_fields", []) + fields))
    pending = [f for f in pending if f in FIELDS and f not in values and f not in understanding.relax]
    saved["preference_fields"] = pending
    understanding.intent = "property_search"
    if values or understanding.relax:
        return None
    saved["preference_state"] = "providing_preference_value" if pending else "selecting_preference_field"
    return QUESTIONS[pending[0]] if pending else WHICH


def finish_edit(saved, values):
    pending = saved.get("preference_fields", [])
    if pending:
        saved["preference_state"] = "providing_preference_value"
        return QUESTIONS[pending[0]]
    saved["preference_state"] = "ready_for_search"
    details = ", ".join(f"{key.replace('_', ' ')}: {value:,}" if isinstance(value, (int, float))
                        else f"{key.replace('_', ' ')}: {value}" for key, value in values.items() if value is not None)
    return f"Theek hai, requirement update ho gayi: {details}. "
