import json
import re
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any, Tuple

# Ensure stdout uses UTF-8 to handle Urdu scripts and special symbols on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import BankingTicket

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BATCH1_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds.jsonl"
BATCH2_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch2.jsonl"
BATCH3_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch3.jsonl"
BATCH4_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch4.jsonl"
BATCH5_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch5.jsonl"
BATCH6_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch6.jsonl"
BATCH7_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_batch7.jsonl"
JSON_TASKS_FILE = PROJECT_ROOT / "data" / "seeds" / "seeds_json_tasks.jsonl"
HUMAN_LINES_BATCH7_FILE = PROJECT_ROOT / "data" / "seeds" / "human_lines_batch7.json"

# Regex for unverified promises
PROMISE_PATTERNS = [
    re.compile(r"\bmehfooz\s+hai\b", re.IGNORECASE),
    re.compile(r"\b(?:money|funds|amount)\s+(?:is|are)\s+safe\b", re.IGNORECASE),
    re.compile(r"\b(?:paise|raqam|funds?)\s+(?:wapas|refund)\b", re.IGNORECASE),
    re.compile(r"\brefund\s+will\b", re.IGNORECASE),
    re.compile(r"\b(?:jald|soon)\s+(?:hal|resolve|solved)\b", re.IGNORECASE),
    re.compile(r"\b(?:call|rabta)\s+(?:karenge|karega|will\s+call)\b", re.IGNORECASE),
    re.compile(r"\bmumken\s+hai\b", re.IGNORECASE),
    re.compile(r"\bhal\s+ho\s+jaye\s*ga\b", re.IGNORECASE),
    re.compile(r"\bresolve\s+ho\b", re.IGNORECASE),
    re.compile(r"\bcan\s+be\s+resolved\b", re.IGNORECASE),
    re.compile(r"\bwill\s+be\s+resolved\b", re.IGNORECASE),
    re.compile(r"\bwill\s+be\s+solved\b", re.IGNORECASE),
    re.compile(r"\bwill\s+be\s+fixed\b", re.IGNORECASE),
    re.compile(r"\bwill\s+be\s+completed\b", re.IGNORECASE),
    re.compile(r"\bcompleted\s+within\b", re.IGNORECASE),
    re.compile(r"\bkhud\s+ba\s+khud\b", re.IGNORECASE),
    re.compile(r"\bautomatically\b", re.IGNORECASE),
    re.compile(r"\bhal\s+ho\s+jati\b", re.IGNORECASE),
]

# Regex for dual requested items joined by "aur" or "and" inside questions
DUAL_REQUEST_PATTERNS = [
    re.compile(r"(?i)\b(?:transaction\s+id|id|number|account|amount|raqam|bank|name|details)\b\s+(?:aur|and)\s+\b(?:transaction\s+id|id|number|account|amount|raqam|bank|name|details)\b.*?[?؟]"),
    re.compile(r"(?i)\b(?:kya\s+aap|could\s+you|please\s+share|bata\s+sakte|bata\s+dein)\b.*?\b(id|number|amount|raqam|bank|account|name)\b.*?\b(?:aur|and)\b.*?\b(id|number|amount|raqam|bank|account|name)\b.*?[?؟]"),
]

# Regex patterns that flag forbidden date or clock formats in time_mentioned
DATE_CLOCK_PATTERNS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "ISO date pattern (YYYY-MM-DD)"),
    (re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"), "Slashed date pattern (DD/MM/YYYY)"),
    (re.compile(r"\b\d{1,2}\.\d{1,2}(?:\.\d{2,4})?\b"), "Dotted date pattern (DD.MM.YYYY)"),
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"), "Clock time pattern (HH:MM:SS)"),
    (re.compile(r"\b\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)\b", re.IGNORECASE), "12-hour clock pattern with AM/PM"),
    (re.compile(r"\b(?:19|20)\d{2}\b"), "Explicit 4-digit calendar year"),
    (re.compile(r"\b\d{1,2}\s*o'?clock\b", re.IGNORECASE), "Clock reference (o'clock)"),
    (re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})\b", re.IGNORECASE), "Calendar date with month name"),
]

# Regex patterns for procedure words in assistant replies
PROCEDURE_PATTERNS = [
    (re.compile(r"\bapp\b", re.IGNORECASE), "app"),
    (re.compile(r"\bmenu\b", re.IGNORECASE), "menu"),
    (re.compile(r"\bsection\b", re.IGNORECASE), "section"),
    (re.compile(r"\boption\b", re.IGNORECASE), "option"),
    (re.compile(r"\bdownload\b", re.IGNORECASE), "download"),
    (re.compile(r"\bclick\b", re.IGNORECASE), "click"),
    (re.compile(r"\bbranch\s+visit\b", re.IGNORECASE), "branch visit"),
    (re.compile(r"\bbranch\b", re.IGNORECASE), "branch"),
    (re.compile(r"\bscreen\b", re.IGNORECASE), "screen"),
    (re.compile(r"زریعہ"), "زریعہ (Urdu spelling)"),
    (re.compile(r"ایپ"), "ایپ (app)"),
    (re.compile(r"ڈاؤنلوڈ"), "ڈاؤنلوڈ (download)"),
    (re.compile(r"کلک"), "کلک (click)"),
    (re.compile(r"اسکرین"), "اسکرین (screen)"),
]


def extract_first_bot_sentence(seed: Dict[str, Any]) -> str:
    """Extracts the first sentence of the first assistant turn."""
    for msg in seed.get("messages", []):
        if msg.get("role") == "assistant":
            content = msg.get("content", "").strip()
            m = re.search(r"^(.*?(?:\.(?!\d)|[!?۔؟]))", content)
            if m:
                return m.group(1).strip()
            return content
    return ""


def validate_bot_openings(seeds: List[Dict[str, Any]], max_allowed: int = 3):
    """Fails if any first bot sentence appears more than max_allowed times."""
    openings = [extract_first_bot_sentence(s) for s in seeds if extract_first_bot_sentence(s)]
    counts = Counter(openings)
    violations = []
    for op, cnt in counts.items():
        if cnt > max_allowed:
            offending_seeds = [s.get("id") for s in seeds if extract_first_bot_sentence(s) == op]
            violations.append({
                "opening": op,
                "count": cnt,
                "max_allowed": max_allowed,
                "seeds": offending_seeds
            })
    return violations, counts


def is_click_warning_occurrence(content: str, m) -> bool:
    before_text = content[:m.start()]
    words_before = re.findall(r"[a-zA-Z']+|[\u0600-\u06FF]+", before_text.lower())
    # Preceded: follows "hargiz, mat, na, never, do not" within 3 words (i.e. at most 3 words between warning word and click)
    warning_words = {"hargiz", "mat", "na", "never", "dont", "don't", "ہرگز", "مت", "نہ"}
    last_4_before = words_before[-4:]
    preceded = any(w in warning_words for w in last_4_before)
    if not preceded and len(words_before) >= 2:
        last_5_before = words_before[-5:]
        for idx in range(len(last_5_before) - 1):
            if last_5_before[idx] == "do" and last_5_before[idx + 1] == "not":
                preceded = True
                break

    # Followed: up to 2 words separate it from "na karein" or "mat karein" (Urdu: "نہ کریں", "مت کریں")
    after_text = content[m.end():]
    words_after = re.findall(r"[a-zA-Z']+|[\u0600-\u06FF]+", after_text.lower())
    followed = False
    negation_words = {"na", "mat", "نہ", "مت"}
    action_words = {"karein", "krain", "karen", "کریں"}
    max_check = min(3, len(words_after) - 1)
    for i in range(max_check):
        if words_after[i] in negation_words and words_after[i + 1] in action_words:
            followed = True
            break

    return preceded or followed


def is_verbatim_in_context(word_match: str, context: Optional[str]) -> bool:
    if not context or not isinstance(context, str):
        return False
    if re.match(r"^[a-zA-Z0-9_]+$", word_match):
        return bool(re.search(r"\b" + re.escape(word_match) + r"\b", context, re.IGNORECASE))
    return word_match.lower() in context.lower()


def validate_no_procedure_words(seeds: List[Dict[str, Any]]):
    """Flags assistant replies describing app menus, screens, download buttons or branch visits."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        context_str = seed.get("context", "")
        if not isinstance(context_str, str):
            context_str = ""
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for pat, word in PROCEDURE_PATTERNS:
                if "click" in word.lower() or "کلک" in word:
                    # Allow click only if every occurrence in content is part of a warning or verbatim in context
                    unwarned_matches = [
                        m for m in pat.finditer(content)
                        if not is_click_warning_occurrence(content, m)
                        and not (context_str and is_verbatim_in_context(m.group(0), context_str))
                    ]
                    if unwarned_matches:
                        violations.append({
                            "seed_id": seed_id,
                            "turn_idx": turn_idx,
                            "word": word,
                            "match": unwarned_matches[0].group(0),
                            "text": content
                        })
                        break
                else:
                    unmatched_matches = [
                        m for m in pat.finditer(content)
                        if not (context_str and is_verbatim_in_context(m.group(0), context_str))
                    ]
                    if unmatched_matches:
                        violations.append({
                            "seed_id": seed_id,
                            "turn_idx": turn_idx,
                            "word": word,
                            "match": unmatched_matches[0].group(0),
                            "text": content
                        })
                        break
    return violations


# Regex patterns for forbidden action claims (bot claiming to perform actions or checks)
ACTION_CLAIM_PATTERNS = [
    (re.compile(r"\bkar\s+dete\s+hain\b", re.IGNORECASE), "kar dete hain"),
    (re.compile(r"\b(?:hum|foran)\b(?!.*?\bnahi\b).*?\bkarte\s+hain\b", re.IGNORECASE), "hum/foran ... karte hain"),
    (re.compile(r"\bcheck\s+karte\b", re.IGNORECASE), "check karte"),
    (re.compile(r"\bjaanch\s+karte\b", re.IGNORECASE), "jaanch karte"),
    (re.compile(r"\bverify\s+karte\b", re.IGNORECASE), "verify karte"),
    (re.compile(r"\bki\s+ja\s+rahi\s+hai\b", re.IGNORECASE), "ki ja rahi hai"),
    (re.compile(r"\bkiya\s+ja\s+raha\s+hai\b", re.IGNORECASE), "kiya ja raha hai"),
    (re.compile(r"\b(?:check|jaanch|verify|block|freeze|process|investigate|darj|resolve|hal)\s+ho\s+raha\s+hai\b", re.IGNORECASE), "action verb + ho raha hai"),
    (re.compile(r"\b(?:ijazat\b.*?\bblock|block\b.*?\bijazat)\b", re.IGNORECASE), "ijazat + block"),
    (re.compile(r"\bwe\s+are\s+checking\b", re.IGNORECASE), "we are checking"),
    (re.compile(r"\bwe\s+will\s+block\b", re.IGNORECASE), "we will block"),
    (re.compile(r"\bwe\s+have\s+blocked\b", re.IGNORECASE), "we have blocked"),
    (re.compile(r"\b(?:we|i)\s+will\s+(?:check|verify|investigate|freeze)\b", re.IGNORECASE), "we/i will check/verify/investigate/freeze"),
    (re.compile(r"\b(?:we|i)\s+are\s+(?:checking|verifying|investigating)\b", re.IGNORECASE), "we/i are checking/verifying/investigating"),
    (re.compile(r"\bmere\s+paas\s+records?\b", re.IGNORECASE), "mere paas record"),
    (re.compile(r"\bhamare\s+records?\b", re.IGNORECASE), "hamare record"),
    (re.compile(r"\bour\s+records?\b", re.IGNORECASE), "our records"),
    (re.compile(r"\bmy\s+records?\b", re.IGNORECASE), "my records"),
]


def validate_no_action_claims(seeds: List[Dict[str, Any]]):
    """Flags any assistant turn claiming present tense actions (e.g. kar dete hain, check karte, we are checking)."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        context_str = seed.get("context", "")
        if not isinstance(context_str, str):
            context_str = ""
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for pat, pattern_name in ACTION_CLAIM_PATTERNS:
                m = pat.search(content)
                if m:
                    if pattern_name == "mere paas record" and context_str == "koi document nahi mila":
                        continue
                    if context_str and is_verbatim_in_context(m.group(0), context_str):
                        continue
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "pattern": pattern_name,
                        "match": m.group(0),
                        "text": content
                    })
                    break
    return violations


def validate_chat_no_json(seeds: List[Dict[str, Any]]):
    """Fails if any customer facing chat reply contains curly braces or json code fences."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if "{" in content or "}" in content:
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "rule": "NO JSON IN CHAT",
                    "reason": "Assistant chat reply contains curly brace '{' or '}'",
                    "text": content[:120]
                })
            if "```" in content:
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "rule": "NO CODE FENCE IN CHAT",
                    "reason": "Assistant chat reply contains markdown code fence (```)",
                    "text": content[:120]
                })
    return violations


def validate_bot_turns(seeds: List[Dict[str, Any]]):
    """Validates single question and no promises rules for assistant chat turns."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", "")
            # Check 1: Multiple question marks
            q_count = content.count("?") + content.count("؟")
            if q_count > 1:
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "rule": "ONE QUESTION",
                    "reason": f"Found {q_count} question marks in a single turn",
                    "text": content
                })

            # Check 2: 'aur' / 'and' joining two requested items
            for pat in DUAL_REQUEST_PATTERNS:
                if pat.search(content):
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "rule": "ONE THING",
                        "reason": "Found 'aur'/'and' joining two requested items in question",
                        "text": content
                    })
                    break

            # Check 3: Unverified promises
            for pat in PROMISE_PATTERNS:
                m = pat.search(content)
                if m:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "rule": "NO PROMISES",
                        "reason": f"Found promise/reassurance phrase matching '{m.group(0)}'",
                        "text": content
                    })
                    break

    return violations


def validate_time_mentioned(seeds: List[Dict[str, Any]]):
    """Validates that time_mentioned uses customer wording and avoids date/clock patterns."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        ticket = seed.get("ticket")
        if not ticket:
            continue

        if "time_reported" in ticket:
            violations.append({
                "seed_id": seed_id,
                "location": "ticket dictionary",
                "reason": "Found legacy field 'time_reported' instead of 'time_mentioned'",
                "value": str(ticket.get("time_reported"))
            })
        val = ticket.get("time_mentioned")
        if val is not None:
            if not isinstance(val, str):
                violations.append({
                    "seed_id": seed_id,
                    "location": "ticket.time_mentioned",
                    "reason": f"time_mentioned must be string or None, got {type(val).__name__}",
                    "value": str(val)
                })
            else:
                for pat, desc in DATE_CLOCK_PATTERNS:
                    m = pat.search(val)
                    if m:
                        violations.append({
                            "seed_id": seed_id,
                            "location": "ticket.time_mentioned",
                            "reason": f"Contains forbidden {desc}: '{m.group(0)}'",
                            "value": val
                        })
                        break
    return violations


# =========================================================================
# GROUNDED CONTEXT & RETIRED [FROM_RAG] VALIDATORS
# =========================================================================

def validate_no_from_rag(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if any seed contains the literal string '[FROM_RAG]' anywhere."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        raw_str = json.dumps(seed, ensure_ascii=False)
        if "[FROM_RAG]" in raw_str:
            violations.append({
                "seed_id": seed_id,
                "reason": "Seed contains retired literal placeholder '[FROM_RAG]'"
            })
    return violations


def extract_numbers(text: str | None) -> set:
    """Extracts all numeric tokens from text, normalizing integers and decimals."""
    if not text:
        return set()
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", str(text))
    tokens = re.findall(r"\d+(?:\.\d+)?", cleaned)
    num_set = set()
    for tok in tokens:
        num_set.add(tok)
        try:
            val = float(tok)
            if val.is_integer():
                num_set.add(str(int(val)))
            num_set.add(f"{val:.1f}")
        except ValueError:
            pass
    return num_set


def validate_number_grounding(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validates that every number uttered by the assistant appears in context, user turns, or ticket amount.
    For no-document seeds, the assistant must utter ZERO numbers.
    """
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        context_str = seed.get("context") or ""
        is_no_doc = (seed.get("context") == "koi document nahi mila")

        # Allowed numbers
        allowed_nums = set()
        if context_str and not is_no_doc:
            allowed_nums |= extract_numbers(context_str)

        # Numbers from all customer turns
        for msg in seed.get("messages", []):
            if msg.get("role") == "user":
                allowed_nums |= extract_numbers(msg.get("content", ""))

        # Numbers from ticket amount
        ticket = seed.get("ticket")
        if ticket and ticket.get("amount") is not None:
            allowed_nums |= extract_numbers(str(ticket["amount"]))

        # Check each assistant turn
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            bot_nums = extract_numbers(content)

            if is_no_doc:
                if bot_nums:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "reason": f"No-document seed must utter 0 numbers, but found: {sorted(list(bot_nums))}",
                        "text": content
                    })
            else:
                unpermitted = bot_nums - allowed_nums
                if unpermitted:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "reason": f"Ungrounded numbers uttered by assistant: {sorted(list(unpermitted))} (allowed: {sorted(list(allowed_nums))})",
                        "text": content
                    })
    return violations


def validate_no_document_behavior(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if a no-document seed does not state it cannot confirm, fails to direct to helpline, or invents a phone number."""
    violations = []
    cannot_confirm_patterns = [
        re.compile(r"\b(?:tasdeeq|confirm)\b(?:\s+\S+){0,3}\s+\bnahi\s+kar\s+sakt[ai]\b", re.IGNORECASE),
        re.compile(r"\bmaloom\s+nahi\b", re.IGNORECASE),
        re.compile(r"\b(?:cannot|can't|unable\s+to|not\s+able\s+to)\s+confirm\b", re.IGNORECASE),
        re.compile(r"تصدیق(?:\s+\S+){0,3}\s+نہیں\s+کر\s+سکتی"),
        re.compile(r"تصدیق\s+نہیں"),
    ]
    helpline_patterns = [
        re.compile(r"\bhelpline\b", re.IGNORECASE),
        re.compile(r"ہیلپ\s*لائن"),
    ]
    phone_number_pattern = re.compile(r"\b(?:\+?92|0\d{2,3})[-\s]?\d{7,8}\b|\b\d{4}[-\s]?\d{7}\b|\b111[-\s]?\d{3}[-\s]?\d{3}\b")

    for seed in seeds:
        if seed.get("context") != "koi document nahi mila":
            continue
        seed_id = seed.get("id", "unknown")
        messages = seed.get("messages", [])
        assistant_texts = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
        combined_assistant = " ".join(assistant_texts)

        # Check 'cannot confirm'
        has_cannot_confirm = any(pat.search(combined_assistant) for pat in cannot_confirm_patterns)
        if not has_cannot_confirm:
            violations.append({
                "seed_id": seed_id,
                "reason": "No-document seed assistant replies must explicitly state inability to confirm ('cannot confirm' / 'tasdeeq nahi kar sakti')",
                "text": combined_assistant
            })

        # Check 'helpline' mention
        has_helpline = any(pat.search(combined_assistant) for pat in helpline_patterns)
        if not has_helpline:
            violations.append({
                "seed_id": seed_id,
                "reason": "No-document seed assistant replies must refer the customer to helpline",
                "text": combined_assistant
            })

        # Check zero numbers uttered
        for m in messages:
            if m.get("role") == "assistant":
                m_nums = extract_numbers(m.get("content", ""))
                if m_nums:
                    violations.append({
                        "seed_id": seed_id,
                        "reason": f"No-document seed assistant replies must state zero numbers, but found: {sorted(list(m_nums))}",
                        "text": m.get("content", "")
                    })

        # Check NO phone number
        if phone_number_pattern.search(combined_assistant):
            violations.append({
                "seed_id": seed_id,
                "reason": "No-document seed must NOT invent a helpline phone number",
                "text": combined_assistant
            })

    return violations


def validate_context_safety(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validates that context policies do not instruct customer credential entry or include USSD/SMS short codes."""
    violations = []

    # Pattern 1: OTP, PIN, password, CVV together with instruction for customer to enter, say, or send it
    cred_instruction_patterns = [
        re.compile(r"(?i)\b(?:otp|pin|password|cvv)\b.*?\b(?:enter|say|send)\w*\b"),
        re.compile(r"(?i)\b(?:enter|say|send)\w*\b.*?\b(?:otp|pin|password|cvv)\b"),
    ]

    # Pattern 2: USSD pattern (star digits hash e.g. *884#)
    ussd_pattern = re.compile(r"\*\d+#")

    # Pattern 3: 4-digit short code after 'SMS' or 'sms to'
    sms_shortcode_pattern = re.compile(r"(?i)\bsms\b.*?\b\d{4}\b")

    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        context_str = seed.get("context")
        if not context_str or context_str == "koi document nahi mila":
            continue

        for pat in cred_instruction_patterns:
            m = pat.search(context_str)
            if m:
                violations.append({
                    "seed_id": seed_id,
                    "reason": f"Context contains credential word with enter/say/send instruction: '{m.group(0)}'",
                    "context": context_str
                })
                break

        m_ussd = ussd_pattern.search(context_str)
        if m_ussd:
            violations.append({
                "seed_id": seed_id,
                "reason": f"Context contains forbidden USSD pattern: '{m_ussd.group(0)}'",
                "context": context_str
            })

        m_sms = sms_shortcode_pattern.search(context_str)
        if m_sms:
            violations.append({
                "seed_id": seed_id,
                "reason": f"Context contains forbidden 4-digit SMS short code: '{m_sms.group(0)}'",
                "context": context_str
            })

    return violations


# Regex patterns for forbidden assistant credential requests
CREDENTIAL_REQUEST_PATTERNS = [
    # English request patterns
    re.compile(
        r"(?i)\b(?:please\s+)?(?<!never\s)(?<!not\s)(?<!t\s)(?<!did\syou\s)(?<!did\syou\salready\s)(?<!have\syou\s)(?<!have\syou\salready\s)(?:send|share|tell|provide|give|enter)\s+(?:me\s+|us\s+)?(?:your\s+|the\s+)?(?:otp|pin|password|cvv|card\s+number)\b"
    ),
    re.compile(r"(?i)\bwhat\s+is\s+your\s+(?:otp|pin|password|cvv)\b"),

    # Roman Urdu and UrduLish request patterns
    re.compile(
        r"(?i)\b(?:apna\s+)?(?:otp|pin|password|cvv|card\s+number)\b\s+(?:mujhe\s+|humein\s+)?(?<!\bna\s)(?<!\bmat\s)(?<!\bnahi\s)(?:batayein|bata\s+dein|share\s+karein|bhej\s+dein|likh\s+dein)\b"
    ),
    re.compile(
        r"(?i)\b(?<!\bna\s)(?<!\bmat\s)(?<!\bnahi\s)(?:bata\s+dein|batayein|share\s+karein|bhejein)\b\s+(?:apna\s+)?(?:otp|pin|password|cvv|card\s+number)\b"
    ),

    # Urdu Script request patterns
    re.compile(
        r"(?<!نہ\s)(?<!مت\s)(?<!نہیں\s)\b(?:او ٹی پی|پن|پاسورڈ|سی وی وی|کارڈ نمبر)\s+(?:بتائیں|شیئر کریں|بھیجیں|لکھیں)\b"
    ),
    re.compile(
        r"(?<!نہ\s)(?<!مت\s)(?<!نہیں\s)\b(?:بتائیں|شیئر کریں|بھیجیں|لکھیں)\s+(?:اپنا\s+)?(?:او ٹی پی|پن|پاسورڈ|سی وی وی|کارڈ نمبر)\b"
    ),
]


def validate_no_credential_requests(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flags assistant turns requesting customer credentials like OTP, PIN, password, CVV, or card number.
    Assistant turns warning against sharing or asking if already shared are permitted.
    """
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for pat in CREDENTIAL_REQUEST_PATTERNS:
                m = pat.search(content)
                if m:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "match": m.group(0),
                        "reason": f"Assistant requested customer credentials: '{m.group(0)}'",
                        "text": content
                    })
                    break
    return violations


# Regex patterns for bot turns confirming bank fault/error
FAULT_CONFIRMING_PATTERNS = [
    re.compile(r"\b(?:hamari|bank\s+ki)\s+ghalti\b", re.IGNORECASE),
    re.compile(r"\bghalat\s+(?:deduction|katauti|charge)\b", re.IGNORECASE),
    re.compile(r"\b(?:our|the\s+bank\'?s?)\s+(?:mistake|error|fault)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+made\s+a\s+mistake\b", re.IGNORECASE),
    re.compile(r"\bwe\s+erroneously\b", re.IGNORECASE),
    re.compile(r"\bapologize\s+for\s+(?:our|the\s+bank\'?s?)\s+(?:error|mistake)\b", re.IGNORECASE),
    re.compile(r"\b(?:do\s+dafa|duplicate)\s+(?:deduction|katauti)\s+par\s+hum\s+maazrat\b", re.IGNORECASE),
]


def validate_no_fault_confirmations(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if any bot sentence confirms an error or fault by the bank (e.g. ghalat deduction, hamari ghalti)."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for pat in FAULT_CONFIRMING_PATTERNS:
                m = pat.search(content)
                if m:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "reason": f"Assistant confirms bank error/fault matching '{m.group(0)}'",
                        "text": content
                    })
                    break
    return violations


# Regex patterns for forbidden offers or permission requests to perform actions the bot cannot perform
UNPERFORMABLE_ACTION_OFFER_PATTERNS = [
    (re.compile(r"(?i)\b(?:would\s+you\s+like|can\s+i|may\s+i)\s+(?:offer\s+)?assistance\s+with\s+opening\b"), "assistance with opening"),
    (re.compile(r"(?i)\bassist\s+you\s+with\s+opening\b"), "assist you with opening"),
    (re.compile(r"(?i)\brequest\s+confirm\s+karna\b"), "request confirm karna"),
    (re.compile(r"(?i)\bissue\s+karne\s+ki\s+request\b"), "issue karne ki request"),
    (re.compile(r"(?i)\bkholne\s+(?:mein|ki)\s+madad\b"), "kholne mein/ki madad"),
    (re.compile(r"(?i)\b(?:ijazat\b.*?\bblock|block\b.*?\bijazat)\b"), "ijazat with block"),
    (re.compile(r"(?i)\bshall\s+i\b"), "shall I"),
    (re.compile(r"(?i)\bshould\s+i\s+proceed\b"), "should I proceed"),
    (re.compile(r"(?i)\bwould\s+you\s+like\s+me\s+to\s+(?:block|unblock|open|issue|transfer|cancel|freeze)\b"), "would you like me to <action>"),
    (re.compile(r"(?i)\bkya\s+main\s+(?:card\s+)?(?:block|unblock|khol|issue|transfer)\b"), "kya main <action>"),
]


def validate_no_unperformable_action_offers(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if any bot turn offers or asks permission to perform an action the bot cannot perform."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for pat, pattern_name in UNPERFORMABLE_ACTION_OFFER_PATTERNS:
                m = pat.search(content)
                if m:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "pattern": pattern_name,
                        "match": m.group(0),
                        "text": content
                    })
                    break
    return violations


UNAUTHORIZED_POLICY_PHRASES = [
    "security policy",
    "bank policy",
    "policy ke tehat",
    "according to bank policy",
    "policy ke mutabiq",
    "hamari policy",
    "our policy",
    "according to policy",
]

EXEMPT_ZB_WARNING_SENTENCES = [
    "zarya bank kabhi bhi call ya sms par aap ka otp ya pin nahi maangta",
    "zarya bank will never ask for your otp or pin over a call or sms",
    "zarya bank kabhi bhi call ya sms par aap ka card number, otp ya pin nahi maangta",
    "zarya bank کبھی بھی کال یا ایس ایم ایس پر آپ کا کارڈ نمبر، او ٹی پی یا پن نہیں مانگتا",
]


def validate_no_unauthorized_policy_claims(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if a bot turn contains 'security policy', 'bank policy', 'policy ke tehat',
    or 'according to bank policy' unless that exact phrase appears in that seed's context.
    Also fails if a null context seed states what Zarya Bank does not do.
    """
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        ctx = seed.get("context") or ""
        ctx_lower = ctx.lower()
        is_null_context = (seed.get("context") is None)

        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            content_lower = content.lower()
            found_violation = False

            for phrase in UNAUTHORIZED_POLICY_PHRASES:
                if phrase in content_lower:
                    if phrase not in ctx_lower:
                        violations.append({
                            "seed_id": seed_id,
                            "turn_idx": turn_idx,
                            "reason": f"Assistant turn contains unauthorized policy phrase '{phrase}' not in context",
                            "text": content
                        })
                        found_violation = True
                        break

            if found_violation:
                continue

            if is_null_context:
                sentences = re.split(r"[.!?\n]", content)
                for sent in sentences:
                    sent_clean = sent.strip()
                    if not sent_clean:
                        continue
                    sent_lower = sent_clean.lower()
                    if any(ex in sent_lower for ex in EXEMPT_ZB_WARNING_SENTENCES):
                        continue

                    if re.search(r"\bZarya Bank\b.*?\bnahi\b", sent_clean, re.IGNORECASE):
                        violations.append({
                            "seed_id": seed_id,
                            "turn_idx": turn_idx,
                            "reason": f"Assistant turn states unauthorized 'Zarya Bank ... nahi': '{sent_clean}'",
                            "text": content
                        })
                        break
                    elif re.search(r"\bZarya Bank\s+(?:will\s+never|does\s+not|doesn\'t)\b", sent_clean, re.IGNORECASE):
                        violations.append({
                            "seed_id": seed_id,
                            "turn_idx": turn_idx,
                            "reason": f"Assistant turn states unauthorized Zarya Bank negation: '{sent_clean}'",
                            "text": content
                        })
                        break
    return violations


def validate_no_maazrat_khwah(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if any bot turn contains 'maazrat khwah'."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if re.search(r"\bmaazrat\s+khwah\b", content, re.IGNORECASE):
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "reason": "Assistant turn contains forbidden phrase 'maazrat khwah'",
                    "text": content
                })
    return violations


FORBIDDEN_URDU_BANK_PATTERNS = [
    re.compile(r"ذریعے\s+بینک"),
    re.compile(r"زریعہ\s+بینک"),
    re.compile(r"ذریعہ\s+بینک"),
    re.compile(r"زریعے\s+بینک"),
]

DELAY_WORDS_PATTERN = re.compile(r"\b(?:delay|takheer|dair)\b", re.IGNORECASE)


def validate_batch7_human_lines(seeds: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Validates that every customer message in seeds_batch7.jsonl is character for character equal to human_lines_batch7.json."""
    violations = []
    if not HUMAN_LINES_BATCH7_FILE.exists():
        violations.append({
            "seed_id": "file_missing",
            "reason": f"human_lines_batch7.json not found at {HUMAN_LINES_BATCH7_FILE}"
        })
        return violations, 0

    with open(HUMAN_LINES_BATCH7_FILE, "r", encoding="utf-8") as f:
        human_lines = json.load(f)

    lines_compared = 0
    seeds_dict = {s["id"]: s for s in seeds if s.get("id") in human_lines}

    for seed_id, expected_lines in human_lines.items():
        if seed_id not in seeds_dict:
            continue
        seed = seeds_dict[seed_id]
        actual_user_lines = [
            m.get("content", "")
            for m in seed.get("messages", [])
            if m.get("role") == "user"
        ]

        if len(actual_user_lines) != len(expected_lines):
            violations.append({
                "seed_id": seed_id,
                "reason": f"Mismatched number of user turns: expected {len(expected_lines)}, got {len(actual_user_lines)}"
            })
            continue

        for turn_idx, (exp, act) in enumerate(zip(expected_lines, actual_user_lines)):
            lines_compared += 1
            if exp != act:
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "reason": "Customer message does not match human_lines_batch7.json exactly",
                    "expected": exp,
                    "actual": act
                })

    return violations, lines_compared


def validate_no_urdu_bank_spellings(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if any seed text (customer or bot) contains Urdu script spellings of bank name."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            content = msg.get("content", "")
            role = msg.get("role", "")
            for pat in FORBIDDEN_URDU_BANK_PATTERNS:
                m = pat.search(content)
                if m:
                    violations.append({
                        "seed_id": seed_id,
                        "turn_idx": turn_idx,
                        "role": role,
                        "match": m.group(0),
                        "reason": f"Contains forbidden Urdu script bank spelling '{m.group(0)}' (must be 'Zarya Bank')",
                        "text": content
                    })
                    break
    return violations


def validate_no_unsupported_delay_words(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fails if a bot turn contains 'delay', 'takheer' or 'dair' when the seed has no context stating a delay."""
    violations = []
    for seed in seeds:
        seed_id = seed.get("id", "unknown")
        ctx = seed.get("context") or ""
        has_delay_in_ctx = bool(DELAY_WORDS_PATTERN.search(ctx))
        if has_delay_in_ctx:
            continue
        for turn_idx, msg in enumerate(seed.get("messages", [])):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            m = DELAY_WORDS_PATTERN.search(content)
            if m:
                violations.append({
                    "seed_id": seed_id,
                    "turn_idx": turn_idx,
                    "match": m.group(0),
                    "reason": f"Assistant turn mentions '{m.group(0)}' but seed has no context stating a delay",
                    "text": content
                })
    return violations


def validate_type_b_tasks(tasks: List[Dict[str, Any]]):
    """Validates that Type B assistant messages are strictly pure, parseable JSON tickets."""
    violations = []
    for task in tasks:
        task_id = task.get("id", "unknown")
        messages = task.get("messages", [])
        if len(messages) < 3:
            violations.append({
                "task_id": task_id,
                "reason": f"Expected at least 3 messages (system, user, assistant), got {len(messages)}"
            })
            continue

        assistant_msg = messages[2].get("content", "")
        # Rule: No markdown code fences
        if "```" in assistant_msg:
            violations.append({
                "task_id": task_id,
                "reason": "Assistant message contains markdown code fence (must be pure JSON only)",
                "sample": assistant_msg[:60]
            })

        # Rule: Must be pure JSON parseable directly
        try:
            parsed = json.loads(assistant_msg)
            if not isinstance(parsed, dict):
                violations.append({
                    "task_id": task_id,
                    "reason": f"Parsed JSON must be an object/dict, got {type(parsed).__name__}",
                    "sample": assistant_msg[:60]
                })
                continue

            # Must pass Pydantic validation
            BankingTicket(**parsed)

            # Check time_mentioned in parsed ticket
            time_val = parsed.get("time_mentioned")
            if time_val is not None:
                for pat, desc in DATE_CLOCK_PATTERNS:
                    m = pat.search(time_val)
                    if m:
                        violations.append({
                            "task_id": task_id,
                            "reason": f"Parsed ticket time_mentioned contains forbidden {desc}: '{m.group(0)}'",
                            "sample": time_val
                        })
                        break

        except Exception as e:
            violations.append({
                "task_id": task_id,
                "reason": f"Assistant message is not pure parseable JSON: {e}",
                "sample": assistant_msg[:60]
            })

    return violations


def load_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    records = []
    if not filepath.exists():
        return records
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def print_type_a_stats(seeds: List[Dict[str, Any]], title: str):
    print("=" * 70)
    print(f"DATASET STATISTICS: TYPE A (CHAT INTERFACES) - {title}")
    print(f"Total Type A Examples: {len(seeds)}")
    print("=" * 70)

    if not seeds:
        print("No seed records found.")
        return True

    # Counts per Category
    category_counts = Counter(s.get("category", "unknown") for s in seeds)
    print("\n--- Counts Per Category ---")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(seeds)) * 100
        print(f"  {cat:<20}: {count:>3} ({pct:>5.1f}%)")

    # Counts Per Language
    lang_counts = Counter(s.get("language", "unknown") for s in seeds)
    print("\n--- Counts Per Language ---")
    for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(seeds)) * 100
        print(f"  {lang:<20}: {count:>3} ({pct:>5.1f}%)")

    # Counts Per Turn Type
    turn_counts = Counter("Multi-turn" if s.get("is_multi_turn") else "Single-turn" for s in seeds)
    print("\n--- Counts Per Turn Type ---")
    for turn_type, count in sorted(turn_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(seeds)) * 100
        print(f"  {turn_type:<20}: {count:>3} ({pct:>5.1f}%)")

    # Ticket Metadata Presence (Source for Type B)
    ticket_count = sum(1 for s in seeds if s.get("ticket"))
    ticket_pct = (ticket_count / len(seeds)) * 100
    print("\n--- Top-Level Ticket Metadata (Source for Type B Tasks) ---")
    print(f"  {'With Ticket Meta':<20}: {ticket_count:>3} ({ticket_pct:>5.1f}%)")
    print(f"  {'Conversational only':<20}: {len(seeds) - ticket_count:>3} ({(100 - ticket_pct):>5.1f}%)")

    # Grounded Context Distribution
    with_context = [s for s in seeds if s.get("context") and s.get("context") != "koi document nahi mila"]
    no_doc = [s for s in seeds if s.get("context") == "koi document nahi mila"]
    without_context = [s for s in seeds if not s.get("context")]

    print("\n--- Grounded Context Distribution ---")
    print(f"  {'With Grounded Context':<25}: {len(with_context):>3} ({(len(with_context)/len(seeds)*100):>5.1f}%)")
    print(f"  {'No Document (koi doc)':<25}: {len(no_doc):>3} ({(len(no_doc)/len(seeds)*100):>5.1f}%)")
    print(f"  {'Without Context':<25}: {len(without_context):>3} ({(len(without_context)/len(seeds)*100):>5.1f}%)")
    print(f"  {'Total Seeds':<25}: {len(seeds):>3} (100.0%)")

    # Validation 1: Customer-facing chat replies must NEVER contain JSON or code fences
    print("\n--- Clean Chat Replies Validation (No JSON / No Braces) ---")
    no_json_violations = validate_chat_no_json(seeds)
    if not no_json_violations:
        print("  [PASS] All assistant chat replies are 100% pure natural language.")
        print("  [PASS] Zero curly braces '{' or '}' and zero markdown code fences in chat replies.")
    else:
        print(f"  [FAIL] Detected {len(no_json_violations)} chat replies with JSON/braces/fences:")
        for v in no_json_violations:
            print(f"    - Seed '{v['seed_id']}' Turn {v['turn_idx']}: {v['reason']}")
            print(f"      Text: \"{v['text']}...\"")

    # Validation 2: Bot Persona Rules
    print("\n--- Bot Persona Rules Validation ---")
    violations = validate_bot_turns(seeds)
    if not violations:
        print("  [PASS] All bot turns strictly satisfy ONE QUESTION, ONE THING (0 multi-question/multi-item turns).")
        print("  [PASS] All bot turns strictly satisfy NO PROMISES (0 unverified reassurance/promise phrases).")
    else:
        print(f"  [FAIL] Detected {len(violations)} rule violations:")
        for v in violations:
            print(f"    - [{v['rule']}] Seed '{v['seed_id']}' Turn {v['turn_idx']}: {v['reason']}")

    # Validation 3: Time Mentioned Rules
    print("\n--- Time Mentioned Validation ---")
    time_violations = validate_time_mentioned(seeds)
    if not time_violations:
        print("  [PASS] All ticket metadata strictly adheres to customer natural wording or null.")
        print("  [PASS] Zero date or clock patterns detected in time_mentioned.")
        print("  [PASS] Zero legacy 'time_reported' references found.")
    else:
        print(f"  [FAIL] Detected {len(time_violations)} time_mentioned rule violations:")
        for tv in time_violations:
            print(f"    - Seed '{tv['seed_id']}': {tv['reason']} (value: '{tv['value']}')")

    # Validation 4: Procedure Words / Menus / Buttons Validation
    print("\n--- Procedure Words / UI Features Validation ---")
    proc_violations = validate_no_procedure_words(seeds)
    if not proc_violations:
        print("  [PASS] All assistant turns avoid hardcoding app menus, screens, download buttons or branch visits.")
        print("  [PASS] Zero procedure words detected (app, menu, section, option, download, click, branch visit).")
    else:
        print(f"  [FAIL] Detected {len(proc_violations)} assistant turns containing procedure words:")
        for pv in proc_violations:
            print(f"    - Seed '{pv['seed_id']}' Turn {pv['turn_idx']}: found '{pv['word']}' in text:")
            print(f"      \"{pv['text'][:100]}...\"")

    # Validation 5: Bot Openings Variety Validation (Max <= 3)
    print("\n--- Bot Openings Variety & Frequency Validation (Max <= 3) ---")
    opening_violations, opening_counts = validate_bot_openings(seeds, max_allowed=3)
    if not opening_violations:
        print("  [PASS] All first bot sentences satisfy variety constraint (max <= 3 occurrences across seeds).")
    else:
        print(f"  [FAIL] Found {len(opening_violations)} opening phrases exceeding max limit of 3:")
        for ov in opening_violations:
            print(f"    - '{ov['opening']}' appears {ov['count']} times in seeds: {ov['seeds']}")

    print("\n--- Top 5 Most Common Bot Openings ---")
    for rank, (op, count) in enumerate(opening_counts.most_common(5), start=1):
        pct = (count / len(seeds)) * 100 if seeds else 0
        print(f"  {rank}. [{count}x - {pct:>4.1f}%] \"{op}\"")

    # Validation 6: No Action Claims Validation (LLM Has No Tools)
    print("\n--- Action Claims Validation (LLM Has No Tools) ---")
    action_violations = validate_no_action_claims(seeds)
    if not action_violations:
        print("  [PASS] All assistant turns strictly avoid active bank/system action claims.")
        print("  [PASS] Zero hits for 'kar dete hain', 'check karte', 'jaanch karte', 'we are checking', etc.")
    else:
        print(f"  [FAIL] Detected {len(action_violations)} turns with forbidden action claims:")
        for av in action_violations:
            print(f"    - Seed '{av['seed_id']}' Turn {av['turn_idx']} [{av['pattern']}]: matched '{av['match']}'")
            print(f"      Text: \"{av['text']}\"")

    # Validation 7: Retirement of [FROM_RAG] Placeholder
    print("\n--- Retirement of [FROM_RAG] Placeholder Validation ---")
    from_rag_violations = validate_no_from_rag(seeds)
    if not from_rag_violations:
        print("  [PASS] All seeds strictly retired '[FROM_RAG]' (0 occurrences across dataset).")
    else:
        print(f"  [FAIL] Detected {len(from_rag_violations)} occurrences of '[FROM_RAG]':")
        for frv in from_rag_violations:
            print(f"    - Seed '{frv['seed_id']}': {frv['reason']}")

    # Validation 8: Number Grounding in Context / Customer Turns
    print("\n--- Number Grounding Validation (0 Hallucinated Figures) ---")
    number_violations = validate_number_grounding(seeds)
    if not number_violations:
        print("  [PASS] All assistant numbers are strictly grounded in policy context, customer turns, or ticket amount.")
        print("  [PASS] Zero ungrounded figures, fees, limits, or durations uttered by assistant.")
    else:
        print(f"  [FAIL] Detected {len(number_violations)} ungrounded number violations:")
        for nv in number_violations:
            print(f"    - Seed '{nv['seed_id']}' Turn {nv['turn_idx']}: {nv['reason']}")
            print(f"      Text: \"{nv['text']}\"")

    # Validation 9: No-Document Grounding Behavior
    print("\n--- No-Document Grounding Behavior Validation ---")
    no_doc_violations = validate_no_document_behavior(seeds)
    if not no_doc_violations:
        print("  [PASS] All no-document seeds correctly state inability to confirm ('cannot confirm' / 'tasdeeq nahi kar sakti').")
        print("  [PASS] All no-document seeds direct customer to helpline with zero phone numbers invented.")
    else:
        print(f"  [FAIL] Detected {len(no_doc_violations)} no-document behavior violations:")
        for ndv in no_doc_violations:
            print(f"    - Seed '{ndv['seed_id']}': {ndv['reason']}")
            print(f"      Text: \"{ndv['text']}\"")

    # Validation 10: Context Safety Rules (No customer credential entry instruction / No USSD / No SMS short codes)
    print("\n--- Context Safety Validation (No Credential Prompts / No USSD / No Short Codes) ---")
    context_safety_violations = validate_context_safety(seeds)
    if not context_safety_violations:
        print("  [PASS] All context policies strictly avoid instructing customer entry of OTP/PIN/password/CVV.")
        print("  [PASS] Zero USSD (*digits#) or SMS 4-digit short codes in policy contexts.")
    else:
        print(f"  [FAIL] Detected {len(context_safety_violations)} context safety violations:")
        for csv in context_safety_violations:
            print(f"    - Seed '{csv['seed_id']}': {csv['reason']}")
            print(f"      Context: \"{csv['context']}\"")

    # Validation 11: Credential Request Validation (0 Credential Demands)
    print("\n--- Credential Request Validation (0 Credential Demands) ---")
    cred_violations = validate_no_credential_requests(seeds)
    if not cred_violations:
        print("  [PASS] All assistant turns strictly avoid requesting customer credentials (OTP, PIN, password, CVV, card number).")
        print("  [PASS] Warnings against sharing and past sharing triage inquiries correctly allowed.")
    else:
        print(f"  [FAIL] Detected {len(cred_violations)} credential request violations:")
        for cv in cred_violations:
            print(f"    - Seed '{cv['seed_id']}' Turn {cv['turn_idx']}: {cv['reason']}")
            print(f"      Text: \"{cv['text']}\"")

    # Validation 12: No Bank Fault / Error Confirmations
    print("\n--- Bank Fault / Error Confirmation Validation (0 Fault Confirmations) ---")
    fault_violations = validate_no_fault_confirmations(seeds)
    if not fault_violations:
        print("  [PASS] All assistant turns strictly avoid confirming bank error or fault.")
    else:
        print(f"  [FAIL] Detected {len(fault_violations)} fault confirmation violations:")
        for fv in fault_violations:
            print(f"    - Seed '{fv['seed_id']}' Turn {fv['turn_idx']}: {fv['reason']}")
            print(f"      Text: \"{fv['text']}\"")

    # Validation 13: No Offers of Unperformable Actions / Permission Requests
    print("\n--- Unperformable Action Offer Validation (0 Action Offers / Permission Requests) ---")
    action_offer_violations = validate_no_unperformable_action_offers(seeds)
    if not action_offer_violations:
        print("  [PASS] All assistant turns strictly avoid offering or requesting permission to perform unperformable actions.")
    else:
        print(f"  [FAIL] Detected {len(action_offer_violations)} action offer violations:")
        for aov in action_offer_violations:
            print(f"    - Seed '{aov['seed_id']}' Turn {aov['turn_idx']}: matched pattern '{aov['pattern']}' ('{aov['match']}')")
            print(f"      Text: \"{aov['text']}\"")

    # Validation 14: No Unauthorized Policy Claims in Null Context Seeds
    print("\n--- Unauthorized Policy Claims Validation (Null Context Seeds) ---")
    policy_violations = validate_no_unauthorized_policy_claims(seeds)
    if not policy_violations:
        print("  [PASS] All null context assistant turns strictly avoid unauthorized policy statements or negations.")
    else:
        print(f"  [FAIL] Detected {len(policy_violations)} unauthorized policy claim violations:")
        for pv in policy_violations:
            print(f"    - Seed '{pv['seed_id']}' Turn {pv['turn_idx']}: {pv['reason']}")
            print(f"      Text: \"{pv['text']}\"")

    # Validation 15: No maazrat khwah Apologies
    print("\n--- No Maazrat Khwah Validation (0 maazrat khwah) ---")
    maazrat_violations = validate_no_maazrat_khwah(seeds)
    if not maazrat_violations:
        print("  [PASS] All assistant turns strictly avoid 'maazrat khwah' phrasing.")
    else:
        print(f"  [FAIL] Detected {len(maazrat_violations)} maazrat khwah violations:")
        for mv in maazrat_violations:
            print(f"    - Seed '{mv['seed_id']}' Turn {mv['turn_idx']}: {mv['reason']}")
            print(f"      Text: \"{mv['text']}\"")

    # Validation 16: No Urdu Script Bank Spellings
    print("\n--- No Urdu Bank Spellings Validation (Must Be Latin 'Zarya Bank') ---")
    urdu_bank_violations = validate_no_urdu_bank_spellings(seeds)
    if not urdu_bank_violations:
        print("  [PASS] All messages strictly avoid Urdu script bank spellings (zero occurrences).")
    else:
        print(f"  [FAIL] Detected {len(urdu_bank_violations)} forbidden Urdu script bank spellings:")
        for ubv in urdu_bank_violations:
            print(f"    - Seed '{ubv['seed_id']}' Turn {ubv['turn_idx']} ({ubv['role']}): {ubv['reason']}")
            print(f"      Text: \"{ubv['text']}\"")

    # Validation 17: No Unsupported Delay Words (Without Context Delay)
    print("\n--- Unsupported Delay Words Validation (Context Stating Delay Required) ---")
    delay_violations = validate_no_unsupported_delay_words(seeds)
    if not delay_violations:
        print("  [PASS] All assistant turns avoid 'delay', 'takheer' or 'dair' when context does not state a delay.")
    else:
        print(f"  [FAIL] Detected {len(delay_violations)} unsupported delay word violations:")
        for dv in delay_violations:
            print(f"    - Seed '{dv['seed_id']}' Turn {dv['turn_idx']}: {dv['reason']}")
            print(f"      Text: \"{dv['text']}\"")

    # Validation 18: Batch 7 Human Lines Exact Match
    human_line_violations = []
    has_b7 = any(s.get("id", "").startswith("seed_08") or s.get("id", "").startswith("seed_09") or s.get("id", "") == "seed_100" for s in seeds)
    if has_b7:
        print("\n--- Batch 7 Human Lines Exact Match Validation ---")
        human_line_violations, lines_compared = validate_batch7_human_lines(seeds)
        print(f"  Lines compared: {lines_compared}")
        if not human_line_violations:
            print(f"  [PASS] All {lines_compared} customer lines in Batch 7 exactly match human_lines_batch7.json.")
        else:
            print(f"  [FAIL] Detected {len(human_line_violations)} human line mismatches in Batch 7:")
            for hlv in human_line_violations:
                print(f"    - Seed '{hlv['seed_id']}': {hlv['reason']}")

    print("=" * 70)
    all_ok = (
        len(no_json_violations) == 0 and
        len(violations) == 0 and
        len(time_violations) == 0 and
        len(proc_violations) == 0 and
        len(opening_violations) == 0 and
        len(action_violations) == 0 and
        len(from_rag_violations) == 0 and
        len(number_violations) == 0 and
        len(no_doc_violations) == 0 and
        len(context_safety_violations) == 0 and
        len(cred_violations) == 0 and
        len(fault_violations) == 0 and
        len(action_offer_violations) == 0 and
        len(policy_violations) == 0 and
        len(maazrat_violations) == 0 and
        len(urdu_bank_violations) == 0 and
        len(delay_violations) == 0 and
        len(human_line_violations) == 0
    )
    return all_ok


def print_type_b_stats(filepath: Path):
    tasks = load_jsonl(filepath)
    print("=" * 70)
    print("DATASET STATISTICS: TYPE B (TICKET EXTRACTION / JSON TASKS)")
    print(f"File path: {filepath}")
    print(f"Total Type B Tasks: {len(tasks)}")
    print("=" * 70)

    if not tasks:
        print("No Type B records found.")
        return True

    # Counts per Category
    category_counts = Counter(t.get("category", "unknown") for t in tasks)
    print("\n--- Counts Per Category ---")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(tasks)) * 100
        print(f"  {cat:<20}: {count:>3} ({pct:>5.1f}%)")

    # Counts Per Language
    lang_counts = Counter(t.get("language", "unknown") for t in tasks)
    print("\n--- Counts Per Language ---")
    for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(tasks)) * 100
        print(f"  {lang:<20}: {count:>3} ({pct:>5.1f}%)")

    # Validation: Assistant messages must be pure, valid JSON
    print("\n--- Pure JSON Output Validation ---")
    b_violations = validate_type_b_tasks(tasks)
    if not b_violations:
        print("  [PASS] All Type B assistant messages are 100% pure, parseable JSON.")
        print("  [PASS] Zero code fences or extraneous text in assistant messages.")
        print("  [PASS] All output tickets strictly conform to Pydantic BankingTicket schema.")
        print("  [PASS] Zero date or clock patterns in time_mentioned.")
    else:
        print(f"  [FAIL] Detected {len(b_violations)} Type B violations:")
        for v in b_violations:
            print(f"    - Task '{v['task_id']}': {v['reason']}")
    print("=" * 70)
    return len(b_violations) == 0


def main():
    batch1_seeds = load_jsonl(BATCH1_FILE)
    batch2_seeds = load_jsonl(BATCH2_FILE)
    batch3_seeds = load_jsonl(BATCH3_FILE)
    batch4_seeds = load_jsonl(BATCH4_FILE)
    batch5_seeds = load_jsonl(BATCH5_FILE)
    batch6_seeds = load_jsonl(BATCH6_FILE)
    batch7_seeds = load_jsonl(BATCH7_FILE)
    combined_seeds = batch1_seeds + batch2_seeds + batch3_seeds + batch4_seeds + batch5_seeds + batch6_seeds + batch7_seeds

    all_passed = True
    b1_passed = print_type_a_stats(batch1_seeds, "Batch 1 (seeds.jsonl)")
    if not b1_passed:
        all_passed = False

    if batch2_seeds:
        print()
        b2_passed = print_type_a_stats(batch2_seeds, "Batch 2 (seeds_batch2.jsonl)")
        if not b2_passed:
            all_passed = False

    if batch3_seeds:
        print()
        b3_passed = print_type_a_stats(batch3_seeds, "Batch 3 (seeds_batch3.jsonl)")
        if not b3_passed:
            all_passed = False

    if batch4_seeds:
        print()
        b4_passed = print_type_a_stats(batch4_seeds, "Batch 4 (seeds_batch4.jsonl)")
        if not b4_passed:
            all_passed = False

    if batch5_seeds:
        print()
        b5_passed = print_type_a_stats(batch5_seeds, "Batch 5 (seeds_batch5.jsonl)")
        if not b5_passed:
            all_passed = False

    if batch6_seeds:
        print()
        b6_passed = print_type_a_stats(batch6_seeds, "Batch 6 (seeds_batch6.jsonl)")
        if not b6_passed:
            all_passed = False

    if batch7_seeds:
        print()
        b7_passed = print_type_a_stats(batch7_seeds, "Batch 7 (seeds_batch7.jsonl)")
        if not b7_passed:
            all_passed = False

    print()
    comb_passed = print_type_a_stats(combined_seeds, f"Combined Batches 1 to 7 (All {len(combined_seeds)} Seeds)")
    if not comb_passed:
        all_passed = False

    if JSON_TASKS_FILE.exists():
        print()
        b_passed = print_type_b_stats(JSON_TASKS_FILE)
        if not b_passed:
            all_passed = False

    if not all_passed:
        print("\n[ERROR] One or more validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
