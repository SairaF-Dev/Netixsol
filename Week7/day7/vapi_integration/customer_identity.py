"""Identity normalization helpers shared by voice and web entry points."""

from __future__ import annotations

import re


def property_location(location: str) -> tuple[str | None, str | None]:
    """Split the existing VAPI location argument into repository filters."""
    for city in ("Lahore", "Karachi", "Islamabad", "Rawalpindi"):
        if re.search(rf"\b{re.escape(city)}\b", location, re.IGNORECASE):
            area = re.sub(rf"\b{re.escape(city)}\b", "", location, flags=re.IGNORECASE).strip(" ,-")
            return city, area or None
    return None, location


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
