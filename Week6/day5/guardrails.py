import re

OFF_TOPIC_RESPONSE = (
    "I can only help with AFL-related questions. "
    "You can ask me about an AFL team, player, match, statistic, history, or rule."
)

INJECTION_RESPONSE = (
    "I can only help with AFL-related questions and I can't follow "
    "instructions that attempt to override that scope."
)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(your\s+)?instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"override\s+(your\s+)?instructions",
    r"disable\s+(your\s+)?restrictions",
    r"bypass\s+(your\s+)?restrictions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(me\s+)?your\s+system\s+prompt",
    r"reveal\s+your\s+instructions",
    r"you\s+are\s+no\s+longer\s+an?\s+afl",
]

def is_prompt_injection(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(re.search(p, normalized, re.I) for p in INJECTION_PATTERNS)

def guardrail_check(text: str):
    if is_prompt_injection(text):
        return False, INJECTION_RESPONSE
    return True, None
