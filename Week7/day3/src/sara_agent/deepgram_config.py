"""Shared Deepgram configuration for prerecorded and streaming UrduLish."""

from __future__ import annotations

import os


# UrduLish regularly switches between Hindustani and English within one turn.
# Multilingual Nova-3 is therefore the default. Urdu-only deployments can
# explicitly set DEEPGRAM_LANGUAGE=ur.
DEFAULT_DEEPGRAM_LANGUAGE = "multi"


DEFAULT_DEEPGRAM_KEYTERMS = (
    "purchase",
    "property",
    "rent",
    "budget",
    "crore",
    "lakh",
    "apartment",
    "flat",
    "house",
    "plot",
    "bedroom",
    "DHA",
    "Lahore",
    "Islamabad",
    "Karachi",
    "Bahria Town",
    "Gulberg",
    "flexible",
    "developer",
    "parking",
    "gym",
    # Phrase prompts help disambiguate Urdu number words from similar English
    # sounds and retain the surrounding real-estate intent.
    "teen crore",
    "do crore",
    "char crore",
    "paanch crore",
    "ghar khareedna",
    "property purchase",
    "property rent",
    "monthly rent",
    "payment plan",
    "ready possession",
    "DHA Phase 1",
    "DHA Phase 2",
    "DHA Phase 3",
    "DHA Phase 4",
    "DHA Phase 5",
    "DHA Phase 6",
    "DHA Phase 7",
    "DHA Phase 8",
    "DHA Phase 9",
)


def load_deepgram_keyterms() -> list[str]:
    """Load up to Deepgram's supported 100 independently prompted terms."""

    configured = os.getenv("DEEPGRAM_KEYTERMS")
    source = (
        configured.split(",")
        if configured is not None
        else DEFAULT_DEEPGRAM_KEYTERMS
    )
    return [term.strip() for term in source if term.strip()][:100]
