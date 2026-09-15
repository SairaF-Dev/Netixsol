"""Identity normalization helpers shared by voice and web entry points."""

from __future__ import annotations

import re


def property_location(location: str | None) -> tuple[str | None, str | None]:
    """Split and normalize the VAPI location argument into repository filters."""
    if not location or not str(location).strip():
        return None, None

    raw = str(location).strip()
    try:
        from sara_agent.transcript_normalizer import normalize_transcript
        text = normalize_transcript(raw)
    except Exception:
        text = raw

    # 1. Normalize Urdu digits if any remain
    text = re.sub(r"[\u0660-\u0669]", lambda m: str(ord(m.group(0)) - ord("\u0660")), text)
    text = re.sub(r"[\u06F0-\u06F9]", lambda m: str(ord(m.group(0)) - ord("\u06F0")), text)

    # 2. Extract City
    city = None
    city_patterns = [
        ("Lahore", r"\b(?:Lahore|لاہور)\b"),
        ("Karachi", r"\b(?:Karachi|کراچی)\b"),
        ("Islamabad", r"\b(?:Islamabad|اسلام\s*آباد|اسلامآباد)\b"),
        ("Rawalpindi", r"\b(?:Rawalpindi|راولپنڈی)\b"),
    ]
    for c_name, pattern in city_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            city = c_name
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip(" ,-")
            break

    # 3. Detect known areas
    # DHA Phases (e.g. DHA Phase 2, 5, 6, 8)
    dha_phase_match = re.search(
        r"(?:\b(?:DHA|DHAAS|DHAA|DHA\s*AAA|DHAAA|DAH|D\.H\.A\.?|ڈی\s*ایچ\s*اے|ڈی۔ایچ۔اے|ڈیفنس|Defence|Defense)\b\s*)?"
        r"(?:\b(?:phase|face|faze|fiz|fes|faiss|fais|faise|feiz|fees|فیز|فیس)\b\s*)?"
        r"(?:(?:phase|face|faze|fiz|fes|faiss|fais|faise|feiz|fees|فیز|فیس)\s*)?"
        r"\b(2|5|6|8|two|five|six|eight|do|panch|paanch|chay|che|chheh|siks|aath|ath|دو|پانچ|چھ|آٹھ)\b",
        text,
        re.IGNORECASE,
    )
    if dha_phase_match:
        num_word = dha_phase_match.group(1).lower()
        num_map = {
            "2": "2", "two": "2", "do": "2", "دو": "2",
            "5": "5", "five": "5", "panch": "5", "paanch": "5", "پانچ": "5",
            "6": "6", "six": "6", "chay": "6", "che": "6", "chheh": "6", "siks": "6", "چھ": "6",
            "8": "8", "eight": "8", "aath": "8", "ath": "8", "آٹھ": "8",
        }
        num = num_map.get(num_word)
        if num:
            full_match = dha_phase_match.group(0)
            if re.search(r"dha|phase|face|faze|fiz|fes|فیز|فیس", full_match, re.IGNORECASE) or len(text.split()) <= 3:
                return city, f"DHA Phase {num}"

    # Pure DHA without a specific phase
    if re.search(r"\b(?:DHA|DHAAS|DHAA|DHA\s*AAA|DHAAA|DAH|D\.H\.A\.?|ڈی\s*ایچ\s*اے|ڈی۔ایچ۔اے|ڈیفنس|Defence|Defense)\b", text, re.IGNORECASE):
        return city, "DHA"

    # Bahria Town
    if re.search(r"\b(?:Bahria\s*Town|Bahria|بحریہ\s*ٹاؤن|بحریہ)\b", text, re.IGNORECASE):
        return city, "Bahria Town"

    # Gulberg III
    if re.search(r"\b(?:Gulberg(?:\s*(?:III|3|three|teen|تھری))?|گلبرگ(?:\s*تھری)?)\b", text, re.IGNORECASE):
        return city, "Gulberg III"

    # Model Town
    if re.search(r"\b(?:Model\s*Town|ماڈل\s*ٹاؤن)\b", text, re.IGNORECASE):
        return city, "Model Town"

    # Clifton
    if re.search(r"\b(?:Clifton|کلفٹن)\b", text, re.IGNORECASE):
        return city, "Clifton"

    # Gulshan-e-Iqbal
    if re.search(r"\b(?:Gulshan(?:-e-|\s+e\s+|\s+)?Iqbal|گلشن(?:\s*ِ|\s*ای|\s*)?اقبال)\b", text, re.IGNORECASE):
        return city, "Gulshan-e-Iqbal"

    # Ghauri Town
    if re.search(r"\b(?:Ghauri\s*Town|Gauri\s*Town|غوری\s*ٹاؤن)\b", text, re.IGNORECASE):
        return city, "Ghauri Town"

    # Blue Area
    if re.search(r"\b(?:Blue\s*Area|بلیو\s*ایریا)\b", text, re.IGNORECASE):
        return city, "Blue Area"

    # Sectors F-11, F-10, E-11, B-17
    if re.search(r"\b(?:F-?11|F\s*eleven|ایف\s*11|ایف\s*گیارہ)\b", text, re.IGNORECASE):
        return city, "F-11"
    if re.search(r"\b(?:F-?10|F\s*ten|ایف\s*10|ایف\s*دس)\b", text, re.IGNORECASE):
        return city, "F-10"
    if re.search(r"\b(?:E-?11|E\s*eleven|ای\s*11|ای\s*گیارہ)\b", text, re.IGNORECASE):
        return city, "E-11"
    if re.search(r"\b(?:B-?17|B\s*seventeen|بی\s*17|بی\s*سترہ)\b", text, re.IGNORECASE):
        return city, "B-17"

    # Saddar
    if re.search(r"\b(?:Saddar|Sadar|صدر)\b", text, re.IGNORECASE):
        return city, "Saddar"

    area = text.strip(" ,-") or None
    return city, area


def normalize_phone(phone: str | None) -> str | None:
    """Normalize a Pakistani mobile number to the +92 international form.

    Invalid, placeholder, and non-mobile values return ``None`` so callers do
    not accidentally create an identity for test or garbage input.
    """
    if not phone:
        return None

    value = str(phone).strip()
    if not value or value.lower() in {"unknown", "null", "none", "anonymous"}:
        return None

    digits = re.sub(r"\D", "", value)
    if digits.startswith("0092"):
        digits = digits[2:]
    elif digits.startswith("92"):
        pass
    elif digits.startswith("0"):
        digits = "92" + digits[1:]
    else:
        return None

    if not re.fullmatch(r"923\d{9}", digits):
        return None
    return f"+{digits}"
