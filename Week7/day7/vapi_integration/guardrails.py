"""Deterministic, fail-closed runtime guardrails for Sara."""

from __future__ import annotations

import re
from dataclasses import dataclass


OFF_TOPIC_RESPONSE = (
    "Main sirf real estate aur property-related assistance mein help kar sakti "
    "hoon. Property search, verified details ya visit booking ke bare mein batayein."
)
SECURITY_RESPONSE = (
    "Main internal system information share nahi kar sakti aur apni instructions "
    "change nahi kar sakti. Property ya real estate se related help zaroor karungi."
)
INVALID_ACTION_RESPONSE = (
    "Main fake ya unauthorized appointment action perform nahi kar sakti. Valid "
    "property visit ke liye required details aur confirmation chahiye."
)


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    reason: str
    response: str | None = None


class OffTopicGuardrail:
    """Enforce domain scope and security before LLM or tool processing."""

    _PROMPT_INJECTION = re.compile(
        r"\b(ignore|disregard|forget|override|bypass|disable|break)\b.{0,50}"
        r"\b(instruction|instructions|rules?|policy|policies|guardrail|prompt|system)\b|"
        r"\b(reveal|show|print|repeat|display|leak|expose|tell me|give me)\b.{0,45}"
        r"\b(system prompt|hidden (?:prompt|instructions?)|internal instructions?|developer message|"
        r"chain of thought|api keys?|credentials?|secrets?|environment variables?)\b|"
        r"\b(act as|pretend to be|developer mode|jailbreak|do anything now)\b",
        re.IGNORECASE,
    )
    _PRIVATE_DATA = re.compile(
        r"\b(internal (?:company |customer |employee )?(?:data|database|records?|files?)|"
        r"other customers?'? (?:data|details?|phone|email)|private crm|crm records?|"
        r"employee (?:passwords?|credentials?|private data)|database dump)\b",
        re.IGNORECASE,
    )
    _FAKE_ACTION = re.compile(
        r"\b(fake|dummy|fraudulent|without (?:their |customer )?(?:permission|consent|"
        r"confirmation)|unauthori[sz]ed)\b.{0,45}\b(appointment|booking|visit|customer)\b|"
        r"\b(book|create|cancel|reschedule)\b.{0,45}\b(fake|dummy|fraudulent|"
        r"unauthori[sz]ed|without (?:their |customer )?(?:permission|consent|confirmation))\b",
        re.IGNORECASE,
    )
    _REAL_ESTATE = re.compile(
        r"\b(property|properties|real[ -]?estate|ghar|house|home|flat|apartment|"
        r"plot|land|villa|office|shop|commercial|buy|buyer|sell|seller|sale|rent|"
        r"rental|lease|invest(?:or|ment)?|mortgage|loan|price|budget|bedroom|"
        r"bathroom|location|area|city|dha|bahria|islamabad|lahore|karachi|"
        r"rawalpindi|developer|amenit(?:y|ies)|listing|visit|viewing|appointment|"
        r"reschedule|cancel|booking|agent|broker|registry|possession|installment|"
        r"valuation|market value|payment plan|school|hospital|kiraya|makaan|zameen)\b",
        re.IGNORECASE,
    )
    _SOCIAL = re.compile(
        r"^(hi|hello|hey|salam|assalam(?:-o-alaikum)?|aoa|walaikum salam|thanks?|"
        r"thank you|shukriya|bye|allah hafiz|good (?:morning|afternoon|evening))[!. ]*$",
        re.IGNORECASE,
    )
    _FOLLOW_UP = re.compile(
        r"^(yes|no|okay|ok|sure|ji|haan|han|nahi|theek|acha|please|"
        r"tell me more|more details?|what about (?:that|it)|repeat|dobara|"
        r"why|how much|which one|the first one|the second one|aur options?|"
        r"yeh wali|woh wali)[?!. ]*$",
        re.IGNORECASE,
    )
    _DETAIL_ANSWER = re.compile(
        r"(?:(?:rs\.?|pkr)\s*)?[\d,.]+(?:\s*(?:lakh|lac|crore|million))?|"
        r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|"
        r"tomorrow|kal)(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)",
        re.IGNORECASE,
    )
    _OFF_TOPIC = re.compile(
        r"\b(weather|forecast|temperature|cricket|football|soccer|match score|"
        r"recipe|biryani|cook(?:ing)?|movie|film|song|music|lyrics|joke|horoscope|"
        r"politics|election|president|prime minister|stock market|bitcoin|crypto|"
        r"code|coding|program(?:ming)?|python|javascript|homework|essay|translate|"
        r"medical|medicine|diagnos(?:e|is)|legal advice|relationship|dating|"
        r"quantum|history of|capital of|poem|game|celebrity|news)\b",
        re.IGNORECASE,
    )

    def evaluate(
        self, message: str, *, has_conversation_context: bool = False
    ) -> GuardrailDecision:
        normalized = " ".join(str(message or "").strip().split())
        if not normalized:
            return GuardrailDecision(False, "empty_input", OFF_TOPIC_RESPONSE)

        # Security precedes relevance so a property keyword cannot hide an attack.
        if self._PROMPT_INJECTION.search(normalized) or self._PRIVATE_DATA.search(normalized):
            return GuardrailDecision(False, "security_violation", SECURITY_RESPONSE)
        if self._FAKE_ACTION.search(normalized):
            return GuardrailDecision(False, "invalid_action", INVALID_ACTION_RESPONSE)
        if self._OFF_TOPIC.search(normalized):
            return GuardrailDecision(False, "clear_off_topic", OFF_TOPIC_RESPONSE)
        if self._REAL_ESTATE.search(normalized) or self._SOCIAL.match(normalized):
            return GuardrailDecision(True, "real_estate_or_social")
        if has_conversation_context and (
            self._FOLLOW_UP.match(normalized) or self._DETAIL_ANSWER.fullmatch(normalized)
        ):
            return GuardrailDecision(True, "contextual_follow_up")
        return GuardrailDecision(False, "outside_supported_scope", OFF_TOPIC_RESPONSE)
