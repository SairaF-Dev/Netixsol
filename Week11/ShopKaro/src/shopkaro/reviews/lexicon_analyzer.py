"""
Rule-based multilingual review analyzer (English, Roman Urdu, Urdu script).

Why rules and not a trained model: the only training data is a synthetic corpus built from 11 sentence templates,
so any trained model memorises those sentences and fails on real text (measured: 53% sentiment accuracy on the
hand-written benchmark, aspect model worse than predicting "not mentioned"). Rules built from general vocabulary
are transparent, fast, and measurably better on new text. A neural multilingual model (e.g. fine-tuned XLM-R)
trained on real labelled reviews is the proper next step.

How it works
1. Split the review into clauses at sentence punctuation, commas and contrast words (but / lekin / magar / مگر ...).
2. In each clause find polar words and phrases; a negator next to a polar word flips it ("not worth",
   "acha nahi", "اچھا نہیں"). Neutral phrases ("nothing special", "theek thaak") mark a clause as neutral.
3. Overall sentiment: positive clauses only -> Positive; negative only -> Negative; both -> Neutral (mixed);
   none -> Neutral.
4. Aspects: an aspect is mentioned when one of its keywords occurs in a clause. Its polarity comes from an
   aspect-specific word if there is one ("mehnga" -> price -1, "tang" -> size -1, "late" -> delivery -1),
   otherwise from the clause polarity.
5. Spam: promotional contact (URL, @handle, phone number together with a contact verb, referral / promo code,
   wholesale / earn-from-home offers, competitor promotion) or bot-like repetition.
"""

from __future__ import annotations

import re
from typing import Any

CLAUSE_SPLIT = re.compile(
    r"[.!?;,،۔]+|\b(?:but|however|though|although|whereas|yet|lekin|magar|albata)\b|(?<!time )(?<!waqt )\bpar\b"
    r"|لیکن|مگر|البتہ|(?<!وقت )\bپر\b",
    flags=re.IGNORECASE,
)
TOKEN = re.compile(r"[\w']+", flags=re.UNICODE)

NEGATORS = {"not", "never", "no", "nahi", "nahin", "nai", "na", "نہیں", "نہ", "isn't", "wasn't", "doesn't", "didn't", "don't"}

POSITIVE = [
    # English
    "good", "great", "excellent", "amazing", "awesome", "love", "loved", "lovely", "perfect", "perfectly", "nice",
    "within minutes", "beautiful", "happy", "satisfied", "recommend", "recommended", "worth", "premium", "sturdy", "comfortable",
    "intact", "neat", "helpful", "best", "superb", "fantastic", "impressed", "exceeded", "genuine", "durable",
    "reasonable", "affordable", "decent", "fine", "breathes well", "value for money", "great value", "on time",
    "arrived early", "a day early", "as shown", "true to size",
    # Roman Urdu
    "acha", "achha", "achi", "achhi", "ache", "zabardast", "kamaal", "kamal", "behtareen", "shandar", "lajawab",
    "pasand", "khoobsurat", "khubsurat", "mazboot", "munasib", "mehfooz", "shukriya", "maza", "aaramdeh",
    "asli", "sahi salamat", "paisa wasool", "foran", "theek thi", "theek hai", "perfect", "saaf", "waqt par", "time par",
    # Urdu script
    "اچھا", "اچھی", "اچھے", "بہترین", "شاندار", "لاجواب", "زبردست", "پسند", "خوبصورت", "مضبوط", "مناسب",
    "شکریہ", "مزہ", "آرام دہ", "اصلی", "سلامت", "ٹھیک تھی", "صاف", "وقت پر", "فوراً",
]
NEGATIVE = [
    # English
    "bad", "poor", "terrible", "horrible", "worst", "awful", "disappointed", "disappointing", "useless", "broken",
    "broke", "defective", "damaged", "torn", "crushed", "soaked", "late", "delayed", "slow", "wrong", "fake",
    "copy", "overpriced", "expensive", "waste", "return it", "returned", "faded", "fades", "peeling", "tight",
    "loose", "smaller", "never replied", "no reply", "ignored", "stopped working", "came apart", "heats up",
    "drains", "rip off", "not worth",
    # Roman Urdu
    "bura", "buri", "bekar", "bekaar", "bakwas", "ghatiya", "kharab", "toota", "tooti", "toot", "phata", "phati",
    "ghalat", "galat", "dair", "der se", "nakli", "patla", "patli", "halka", "mehnga", "mehngi", "tang", "khula",
    "chhota", "chota", "barbadi", "zaya", "garam", "band ho gaya", "khatam", "rang utar", "mat lena", "mat lo",
    "nahi uthata", "jawab nahi", "ur jati", "dobara nahi",
    # Urdu script
    "برا", "بری", "بیکار", "بکواس", "گھٹیا", "خراب", "ناقص", "ٹوٹا", "ٹوٹی", "پھٹا", "غلط", "دیر", "تاخیر",
    "نقلی", "پتلا", "مہنگا", "مہنگی", "تنگ", "کھلا", "چھوٹا", "ضیاع", "بند ہو گیا", "ختم", "گرم", "مت خریدیں",
    "رنگ اتر", "اڑ جاتی", "نہیں اٹھاتا", "دوبارہ نہیں",
]
NEUTRAL_PHRASES = [
    "nothing special", "it's okay", "its okay", "just okay", "theek thaak", "theek thak", "khas nahi",
    "ٹھیک ٹھاک", "خاص بات نہیں",
]

ASPECT_KEYWORDS: dict[str, list[str]] = {
    "quality": [
        "quality", "fabric", "material", "stitching", "colour", "color", "battery", "leather", "zip", "zips",
        "smell", "perfume", "product", "item", "kapra", "kapda", "silai", "finishing", "rang", "cheez", "khushboo",
        "zip", "shoes", "joote", "working", "chala", "کوالٹی", "معیار", "کپڑا", "سلائی", "رنگ", "چیز", "پراڈکٹ",
        "خوشبو", "زپ", "جوتے", "بیٹری", "چلا",
    ],
    "price": [
        "price", "value", "money", "worth", "expensive", "overpriced", "affordable", "qeemat", "qimat", "paise",
        "paisa", "mehnga", "mehngi", "قیمت", "پیسوں", "پیسے", "مہنگا", "مہنگی",
    ],
    "delivery": [
        "delivery", "courier", "shipping", "shipped", "arrived", "rider", "on time", "early", "waqt par",
        "time par", "pohncha", "ڈلیوری", "کورئیر", "رائیڈر", "پہنچا", "وقت پر",
    ],
    "size_fit": [
        "size", "fit", "fits", "fitting", "tight", "loose", "medium", "large", "small", "tang", "khula", "chhota",
        "chota", "سائز", "فٹنگ", "تنگ", "کھلا", "چھوٹا", "میڈیم",
    ],
    "packaging": [
        "packaging", "packing", "box", "carton", "sealed", "wrapped", "dabba", "پیکنگ", "ڈبہ",
    ],
    "seller": [
        "seller", "replied", "reply", "chat", "exchange", "dukandar", "jawab", "دکاندار", "جواب", "تبدیل",
    ],
}

# Words that carry polarity for one aspect specifically (override the clause polarity for that aspect).
ASPECT_POLAR: dict[str, dict[str, int]] = {
    "price": {
        "expensive": -1, "overpriced": -1, "not worth": -1, "mehnga": -1, "mehngi": -1, "barbadi": -1,
        "مہنگا": -1, "مہنگی": -1, "ضیاع": -1, "worth": 1, "value": 1, "reasonable": 1, "affordable": 1,
        "munasib": 1, "kam qeemat": 1, "مناسب": 1, "کم قیمت": 1,
    },
    "size_fit": {
        "tight": -1, "loose": -1, "smaller": -1, "tang": -1, "khula": -1, "chhota": -1, "chota": -1,
        "تنگ": -1, "کھلا": -1, "چھوٹا": -1, "true to size": 1, "fits perfectly": 1, "perfect": 1,
    },
    "delivery": {
        "late": -1, "delayed": -1, "slow": -1, "dair": -1, "der se": -1, "baad": -1, "دیر": -1, "تاخیر": -1,
        "بعد": -1, "early": 1, "on time": 1, "fast": 1, "quick": 1, "jaldi": 1, "waqt par": 1, "time par": 1,
        "tez": 1, "وقت پر": 1, "جلدی": 1, "تیز": 1,
    },
}
LONG_WAIT = re.compile(
    r"\b(?:\d{2,}|[7-9]|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\s*(?:days?|din)\b"
    r"|\b(?:\d+|two|three|do|teen)\s*(?:weeks?|hafte)\b|\b(?:over|more than|took)\s+a\s+week\b|دو ہفتے|ہفتے بعد",
    flags=re.IGNORECASE,
)
ARRIVAL = re.compile(
    r"\b(?:arrived|came|received|delivered|aa gaya|aa gayi|aaya|aayi|mila|mili|pohncha|pohnchi)\b|آ گیا|آ گئی|آیا|ملا|ملی|پہنچا",
    flags=re.IGNORECASE,
)
SHORT_WAIT = re.compile(r"\b(?:[1-4]|one|two|three|four|ek|do|teen|char)\s*(?:days?|din)\b|تین دن|دو دن میں|ایک دن", flags=re.IGNORECASE)

ASPECTS = tuple(ASPECT_KEYWORDS)


def _compile(phrases: list[str]) -> list[tuple[str, tuple[str, ...]]]:
    return [(p, tuple(TOKEN.findall(p.lower()))) for p in phrases]


_POS = _compile(POSITIVE)
_NEG = _compile(NEGATIVE)
_NEUTRAL = _compile(NEUTRAL_PHRASES)
_ASPECT_KW = {a: _compile(v) for a, v in ASPECT_KEYWORDS.items()}
_ASPECT_POLAR = {a: [(p, toks, v) for (p, toks), v in zip(_compile(list(d)), d.values())] for a, d in ASPECT_POLAR.items()}


def _find(tokens: list[str], phrase: tuple[str, ...]) -> list[int]:
    n = len(phrase)
    if n == 0:
        return []
    return [i for i in range(len(tokens) - n + 1) if tuple(tokens[i : i + n]) == phrase]


def _negated(tokens: list[str], start: int, length: int) -> bool:
    """Negator up to 2 tokens before (English order) or right after (Urdu order) the matched phrase."""
    before = tokens[max(0, start - 2) : start]
    after = tokens[start + length : start + length + 2]
    return any(t in NEGATORS for t in before) or any(t in NEGATORS for t in after)


def split_clauses(text: str) -> list[str]:
    parts = [p.strip() for p in CLAUSE_SPLIT.split(text) if p and p.strip()]
    return parts or [text.strip()]


def _clause_aspects(clause: str, toks: list[str]) -> dict[str, int]:
    """Aspects mentioned in the clause -> aspect-specific polarity (0 = mentioned without a specific word)."""
    found: dict[str, int] = {}
    for asp in ASPECTS:
        mentioned = any(_find(toks, ph) for _, ph in _ASPECT_KW[asp])
        specific = 0
        for _, ph, v in _ASPECT_POLAR.get(asp, []):
            for i in _find(toks, ph):
                specific = -v if (not (set(ph) & NEGATORS) and _negated(toks, i, len(ph))) else v
        if asp == "delivery":
            # Waiting time counts as a delivery comment only with a delivery word or an arrival verb
            # ("2 hafte baad mila"), not in "do din chala" (it worked for two days).
            if LONG_WAIT.search(clause) and (mentioned or ARRIVAL.search(clause)):
                mentioned, specific = True, -1
            elif SHORT_WAIT.search(clause) and ARRIVAL.search(clause):
                mentioned, specific = True, specific or 1
        if mentioned:
            found[asp] = specific
    return found


def analyze_clause(clause: str) -> tuple[int, dict[str, int]]:
    """(clause polarity, {mentioned aspect: aspect-specific polarity})."""
    toks = [t.lower() for t in TOKEN.findall(clause)]
    aspects = _clause_aspects(clause, toks)
    pol = _general_polarity(toks)
    if pol == 0:  # e.g. "2 hafte baad mila": no general polar word but a clear delivery complaint
        total = sum(aspects.values())
        pol = (total > 0) - (total < 0)
    return pol, aspects


def clause_polarity(clause: str) -> int:
    return analyze_clause(clause)[0]


def _general_polarity(toks: list[str]) -> int:
    for _, ph in _NEUTRAL:
        if _find(toks, ph):
            return 0
    score = 0
    used: set[int] = set()
    # Longer phrases first so "not worth" wins over "worth".
    for lexicon, sign in ((_NEG, -1), (_POS, 1)):
        for _, ph in sorted(lexicon, key=lambda x: -len(x[1])):
            for i in _find(toks, ph):
                span = set(range(i, i + len(ph)))
                if span & used:
                    continue
                used |= span
                polarity = sign
                # A negator flips a polar word unless the phrase itself already contains the negation.
                if not (set(ph) & NEGATORS) and _negated(toks, i, len(ph)):
                    polarity = -sign
                score += polarity
    return (score > 0) - (score < 0)


def analyze_sentiment(text: str) -> dict[str, Any]:
    clauses = split_clauses(text)
    pols = [clause_polarity(c) for c in clauses]
    has_pos, has_neg = any(p > 0 for p in pols), any(p < 0 for p in pols)
    if has_pos and has_neg:
        label = "Neutral"
    elif has_pos:
        label = "Positive"
    elif has_neg:
        label = "Negative"
    else:
        label = "Neutral"
    names = {1: "Positive (+1)", -1: "Negative (-1)", 0: "Neutral (0)"}
    return {
        "sentiment": label,
        "is_mixed_sentiment": bool(has_pos and has_neg),
        "clauses": [{"clause": c, "polarity": names[p]} for c, p in zip(clauses, pols)],
    }


def analyze_aspects(text: str) -> dict[str, int]:
    scores = {a: 0 for a in ASPECTS}
    unresolved: set[str] = set()
    clause_pols = []
    for clause in split_clauses(text):
        pol, aspects = analyze_clause(clause)
        clause_pols.append(pol)
        for asp, specific in aspects.items():
            value = specific or pol
            if value:
                scores[asp] = value
            else:
                unresolved.add(asp)
    # An aspect mentioned without any polar word takes the review's verdict when the review is one-sided
    # ("Size L fits like a medium, had to return it" -> size_fit -1).
    has_pos, has_neg = any(p > 0 for p in clause_pols), any(p < 0 for p in clause_pols)
    if has_pos != has_neg:
        for asp in unresolved:
            if scores[asp] == 0:
                scores[asp] = 1 if has_pos else -1
    return scores


# ----------------------------------------------------------------------------- spam
URL_OR_HANDLE = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|pk|biz|net|org|shop|store)\b|(?<!\w)@\w{3,}", re.IGNORECASE)
PHONE = re.compile(r"(?:\+92|0)3\d{2}[-\s]?\d{7}|\b03\d{2}\b")
CONTACT_VERB = re.compile(
    r"\bwhats\s?app\b|\bcontact\b|\bcall\s+(?:karein|karen|now|us)\b|\bdm\b|\binsta(?:gram)?\b|واٹس ایپ|رابطہ|کال کریں",
    re.IGNORECASE,
)
PROMO = re.compile(
    r"\breferral\b|\bpromo\s+code\b|\bcode\s+[A-Z0-9]{4,}\b|\bwholesale\b|\bbulk orders?\b|\bearn\s+rs\b|\bfrom home\b"
    r"|\blink (?:in )?bio\b|\bhamari dukaan\b|\bhamare paas\b|\bour (?:shop|store|website)\b|\bvisit\b"
    r"|\b\d{2}%\s*off\b|ویب سائٹ|ہماری دکان",
    re.IGNORECASE,
)
BOT_PHRASES = re.compile(r"100%\s*a\+\+\+|must\s*buy\s*best\s*seller|fake\s+fake\s+fake|competitor\s+store", re.IGNORECASE)


def repetition_ratio(text: str) -> float:
    toks = [t.lower() for t in TOKEN.findall(text)]
    return len(set(toks)) / len(toks) if len(toks) >= 4 else 1.0


def spam_signals(text: str) -> dict[str, bool]:
    return {
        "url_or_handle": bool(URL_OR_HANDLE.search(text)),
        "phone_with_contact_verb": bool(PHONE.search(text) and CONTACT_VERB.search(text)),
        "contact_verb_promo": bool(CONTACT_VERB.search(text) and PROMO.search(text)),
        "promo_offer": bool(PROMO.search(text)),
        "bot_phrase": bool(BOT_PHRASES.search(text)),
        "repetitive": repetition_ratio(text) <= 0.5,
    }


def classify_spam(text: str) -> dict[str, Any]:
    s = spam_signals(text)
    if (s["bot_phrase"] and "fake" not in text.lower()) or s["repetitive"]:
        reason = "duplicate_bot"
    elif s["url_or_handle"] or s["phone_with_contact_verb"] or s["contact_verb_promo"] or s["promo_offer"]:
        reason = "promo_link"
    elif s["bot_phrase"]:
        reason = "extreme_burst"
    else:
        reason = "none"
    return {"is_fake_spam": reason != "none", "spam_reason": reason, "signals": s}
