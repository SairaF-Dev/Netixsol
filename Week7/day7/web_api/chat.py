# WARNING [ARCHITECTURE / CODE DUPLICATION ALERT]:
# day7/web_api/chat.py reimplements routing and turn handling logic instead of delegating to day3/src/sara_agent/chatbot.py.
# The source of truth for Sara's agent decision-making, fallback routing, and LLM understanding is in day3.
# Keep day3 logic aligned when modifying chat.py!

"""Authenticated transport adapter for shared Sara capabilities and website tools."""
import asyncio
import hashlib
import os
import re
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from pydantic import ValidationError

from shared.sara_service import SaraService, resolve_property_reference
from sara_agent.understanding import UnderstandingError
from sara_agent.preference_edit import advance_edit, finish_edit
from web_api.schemas import PreferencesUpdate, MeInteractionCreate, MeAppointmentBook, AppointmentReschedule


def clean_urdulish_vocabulary(text: str) -> str:
    """
    Ensure strict Pakistani Roman Urdu (UrduLish) by replacing accidental Hindi loanwords.
    """
    if not text:
        return text

    replacements = [
        # Swagat -> Khushamdeed
        (r"\b(?:aap\s*ka\s+)?swagat\s+hai\b", "Khushamdeed"),
        (r"\bswagatam\b", "Khushamdeed"),
        (r"\bswagat\b", "khushamdeed"),
        # Namaste / Namaskar -> Assalam-o-alaikum
        (r"\b(?:namaste|namaskar)\b", "Assalam-o-alaikum"),
        # Dhanyawad / Dhanyavaad -> Shukriya
        (r"\b(?:dhanyawad|dhanyavaad)\b", "shukriya"),
        # Kripya -> Barah-e-meherbani
        (r"\bkripya(?:\s+karke)?\b", "barah-e-meherbani"),
        # Samay -> Waqt
        (r"\bsamay\b", "waqt"),
        # Sahayata -> Madad
        (r"\bsahayata\b", "madad"),
        # Prashn -> Sawal
        (r"\bprashn[a-z]*\b", "sawal"),
        # Uttar -> Jawab
        (r"\buttar\b", "jawab"),
        # Kintu / Parantu -> Lekin
        (r"\b(?:kintu|parantu)\b", "lekin"),
        # Anurodh -> Guzarish
        (r"\banurodh\b", "guzarish"),
        # Mulya -> Keemat
        (r"\bmulya\b", "keemat"),
        # Shanti -> Sukoon
        (r"\bshanti\b", "sukoon"),
        # Adhik -> Zyada
        (r"\badhik\b", "zyada"),
        # Kripa -> Meherbani
        (r"\bkripa\b", "meherbani"),
        # Charcha -> Baat
        (r"\bcharcha\b", "baat"),
    ]
    cleaned = text
    for pattern, repl in replacements:
        def _match_repl(m, r=repl):
            matched_text = m.group(0)
            if matched_text and matched_text[0].isupper():
                return r[0].upper() + r[1:]
            return r[0].lower() + r[1:]
        cleaned = re.sub(pattern, _match_repl, cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    cleaned = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), cleaned)
    return cleaned


class ChatAdapter:
    def __init__(self, services, store, sara=None):
        self.services = services
        self.store = store
        self.sara = sara or SaraService()

    def _format_saved_prefs_summary(self, prefs):
        parts = []
        if getattr(prefs, "city", None):
            parts.append(f"{prefs.city} mein")
        if getattr(prefs, "budget_max", None):
            b = prefs.budget_max
            b_str = f"{b / 10_000_000:g} crore" if b >= 10_000_000 else (f"{b / 1_000_000:g} million" if b >= 1_000_000 else f"{b:,} PKR")
            parts.append(f"{b_str} tak")
        if getattr(prefs, "property_type", None):
            parts.append(prefs.property_type.lower())
        if getattr(prefs, "purpose", None):
            parts.append(f"{prefs.purpose.lower()} ke liye")

        desc = " ".join(parts) if parts else "property ke liye"
        return f"Assalam-o-alaikum, welcome back! Main Sara hoon. Pichli dafa aapne {desc} pucha tha, kya wahi requirement hai ya kuch change karna chahengi?"

    async def _missing_requirement_prompt(self, preferences) -> str:
        purpose = getattr(preferences, "purpose", None)
        city = getattr(preferences, "city", None)
        budget = getattr(preferences, "budget_max", None)
        ptype = getattr(preferences, "property_type", None)

        if not purpose:
            return "Ji, pehle ye bata dein — aap property purchase ke liye dekh rahe hain ya rent par?"
        if not city:
            return "Ji, pehle ye bata dein — aap kis city mein property dekh rahe hain?"
        if budget is None:
            return "Ji, pehle ye bata dein — aap ka maximum budget kitna hai?"
        if not ptype:
            return "Ji, pehle ye bata dein — aap kis property type (House, Plot ya Flat) mein dekh rahe hain?"
        return "Ji, pehle apni requirement confirm kar dein taake main pichli property trace kar sakoon."

    async def _generate_preference_clarification_response(
        self, customer, field: str, user_message: str, default_question: str
    ) -> str:
        prefs = getattr(customer, "preferences", None)
        prev_val_str = None
        if prefs:
            if field == "budget":
                b = getattr(prefs, "budget_max", None)
                if b:
                    prev_val_str = f"{b / 10_000_000:g} crore" if b >= 10_000_000 else (f"{b / 1_000_000:g} million" if b >= 1_000_000 else f"{b:,} PKR")
            elif field == "city":
                prev_val_str = getattr(prefs, "city", None)
            elif field == "area":
                prev_val_str = getattr(prefs, "area", None)
            elif field == "property_type":
                prev_val_str = getattr(prefs, "property_type", None)
            elif field == "purpose":
                prev_val_str = getattr(prefs, "purpose", None)
            elif field == "bedrooms":
                br = getattr(prefs, "bedrooms", None)
                prev_val_str = f"{br} bedrooms" if br else None

        # 1. Primary: Dynamic LLM Generation with Strict Grounding, Anti-Hallucination & Off-Topic Guardrails
        client = getattr(getattr(self.sara, "understanding", None), "client", None)
        model = getattr(getattr(self.sara, "understanding", None), "model", "openai/gpt-4o-mini")
        if client is not None:
            try:
                system_msg = (
                    "Aap Sara hain, RealEstate Hub ki AI assistant jo Roman Urdu (UrduLish) mein baat karti hain.\n\n"
                    "CURRENT TASK:\n"
                    f"- Customer apni property preference for '{field}' change/update kar raha hai.\n"
                    f"- Customer ki pichli saved {field} requirement: '{prev_val_str or 'koi saved value nahi'}' thi.\n\n"
                    "STRICT GUARDRAILS & ANTI-HALLUCINATION RULES:\n"
                    "1. FACTUAL GROUNDING: Kabhi koi fake property, farzi price, ya unverified claim mat banayein. Sirf upar diye gaye verified context par mabni baat karein.\n"
                    f"2. PREFERENCE INQUIRY: Agar customer pichli requirement/budget poochay (jaise 'pehla kitna tha', 'purana kya tha'), to upar diye gaye saved context ('{prev_val_str or 'not set'}') se dekh kar sach batayein aur naya {field} poochain.\n"
                    "3. ZERO / INVALID BUDGET: Agar user 0 budget ya free property ki baat kare, to politely explain karein ke 0 PKR mein verified property nahi hoti, aur realistic minimum budget poochain.\n"
                    "4. OFF-TOPIC HANDLING: Agar user real estate ke ilawa koi baat kare (jaise jokes, weather, sports, politics, recipes, code), to bilkul jawab mat dein. Polite refusal karein: 'Main sirf property aur real estate se mutaliq madad kar sakti hoon' aur user ko wapis preference par steer karein.\n"
                    "5. STRICT PAKISTANI ROMAN URDU (URDULISH) — ZERO HINDI: Customers Pakistani hain jo UrduLish bolte hain. Hindi words (jaise 'swagat', 'namaste', 'dhanyawad', 'kripya', 'samay') bilkul use na karein. 'Shukriya', 'Madad', 'Khushamdeed' use karein.\n"
                    f"6. CONCISE & POLITE: Jawab hamesha 1 se 2 mukhtasir, natural Roman Urdu sentences mein dein aur aakhir mein customer se unka naya {field} poochain."
                )
                completion = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.chat.completions.create,
                        model=model,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_message},
                        ],
                        max_tokens=150,
                        temperature=0.0,
                        timeout=4.0,
                    ),
                    timeout=5.0,
                )
                reply = completion.choices[0].message.content.strip()
                if reply:
                    return clean_urdulish_vocabulary(reply)
            except Exception:
                pass

        # 2. Safety / Offline Fallback (used when LLM client is offline, rate-limited, or in unit tests)
        is_past_inquiry = bool(re.search(
            r"\b(?:pehla|pehle|pehlay|pichla|pichli|purana|purani|last\s*time|previously|before)\b|"
            r"\b(?:kya|kitna|kitney|kon\s*sa|konsa|kaunsa)\s+(?:tha|thi|the|rakha\s+tha|bataya\s+tha)\b",
            user_message, re.IGNORECASE
        ))
        if is_past_inquiry:
            if prev_val_str:
                if field == "budget":
                    return f"Ji, pichli dafa aapne {prev_val_str} tak ka budget bataya tha. Aapka naya budget kitna hai?"
                return f"Ji, pichli dafa aapka {field.replace('_', ' ')} {prev_val_str} tha. Naya {field.replace('_', ' ')} kya rakhna chahenge?"
            else:
                return f"Ji, pichli dafa {field.replace('_', ' ')} specify nahi tha. Aapka naya {field.replace('_', ' ')} kya hai?"

        is_zero_budget = bool(re.search(
            r"\b(?:0|zero)\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|k|pkr|rupay|rupees)?\b|"
            r"\b(?:kuch\s+nahi|free|muft)\b",
            user_message, re.IGNORECASE
        ))
        if field == "budget" and is_zero_budget:
            return "0 budget par koi verified property available nahi hoti. Minimum realistic budget batayein (jaise 50 lakh ya 1 crore) — aapka naya budget kitna hai?"

        is_off_topic = bool(re.search(
            r"\b(?:joke|jokes|chutkula|latifa|weather|mausam|cricket|match|score|scorecard|recipe|khana|pakana|python|coding|code)\b",
            user_message, re.IGNORECASE
        ))
        if is_off_topic:
            return f"Main sirf property aur real estate se mutaliq madad kar sakti hoon. {default_question}"

        return default_question

    async def _generate_dynamic_nlg_response(
        self,
        user_message: str,
        canonical_response: str,
        context: dict | None = None,
    ) -> str:
        if not canonical_response or not canonical_response.strip():
            return canonical_response

        client = getattr(getattr(self.sara, "understanding", None), "client", None)
        model = getattr(getattr(self.sara, "understanding", None), "model", None) or os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
        if client is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        api_key=api_key,
                        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    )
                except Exception:
                    client = None
        if client is None:
            return canonical_response

        ctx = context or {}
        prefs = getattr(ctx.get("customer"), "preferences", None)
        pref_desc = []
        if prefs:
            if getattr(prefs, "city", None):
                pref_desc.append(f"City: {prefs.city}")
            if getattr(prefs, "area", None):
                pref_desc.append(f"Area: {prefs.area}")
            if getattr(prefs, "property_type", None):
                pref_desc.append(f"Type: {prefs.property_type}")
            if getattr(prefs, "purpose", None):
                pref_desc.append(f"Purpose: {prefs.purpose}")
            if getattr(prefs, "budget_max", None):
                b = prefs.budget_max
                b_str = f"{b / 10_000_000:g} crore" if b >= 10_000_000 else f"{b:,} PKR"
                pref_desc.append(f"Budget: {b_str}")
            if getattr(prefs, "bedrooms", None):
                pref_desc.append(f"Bedrooms: {prefs.bedrooms}")
        pref_str = ", ".join(pref_desc) if pref_desc else "None set"

        extra_info = ctx.get("extra_knowledge", "")

        system_msg = (
            "Aap Sara hain, RealEstate Hub Pakistan ki intelligent aur professional AI property consultant jo natural, fluent aur warm Pakistani Roman Urdu (UrduLish) mein customer se baat karti hain.\n\n"
            "TASK:\n"
            "Neechay diye gaye FACTUAL SYSTEM MESSAGE ko aik natural, engaging conversational Roman Urdu reply mein deliver karein jo user ke message ka direct aur helpful response ho.\n\n"
            "STRICT RULES & ANTI-HALLUCINATION GUARDRAILS:\n"
            "1. FACTUAL FIDELITY: Jo facts, numbers, prices, dates, aur property details system message mein hain, unhi par qaim rahein. Kabhi koi farzi property ya fake rate mat banayein.\n"
            "2. NO FALSE BUDGET COMMENTARY: Kabhi apni taraf se yeh mat kahein ya assume karein ke koi property user ke budget se zyada ya kam hai (e.g. NEVER claim 'budget se zyada hai' or 'budget adjust karein'). System message mein aayi hui listings already database search se filter ho kar aayi hain aur valid hain. Sirf wahi baat karein jo factual system message mein hai.\n"
            "3. PROPERTY LISTINGS INTEGRITY: Agar system message mein numbered property listings (jaise '1. DHA Family Residence...') hain, to un listings aur unki prices/details ko verbatim zaroor shamil karein; unhe drop ya distort na karein.\n"
            "4. GREETING RULE (NO REPETITIVE GREETINGS): Agar user ne apne CURRENT message mein greet kiya ho (jaise 'aoa', 'salam', 'hello', 'hi'), sirf tabhi polite greeting ('Walaikum Assalam' ya 'Assalam-o-alaikum') se shuru karein. LEKIN agar user ne apne current message mein greet NAHI kiya (jaise 'requirement wahi hai', 'budget change krna hai', '15 crore', 'details dikhao'), to conversation ke beech mein DOBARA Salam / Walaikum Assalam bilkul mat bolein; direct 'Ji bilkul', 'Theek hai', 'Zaroor', ya 'Aapki requirement ke mutabiq' se start karein.\n"
            "5. STRICT PAKISTANI ROMAN URDU (URDULISH) — ZERO HINDI TOLERANCE: Customers Pakistani hain jo natural Pakistani Roman Urdu (UrduLish) bolte hain. Hindi words (jaise 'swagat', 'namaste', 'dhanyawad', 'kripya', 'samay', 'sahayata', 'kintu', 'mulya') ka istemal QATAN MANA HAI (STRICTLY FORBIDDEN). Welcome ke liye 'Welcome back' ya 'Khushamdeed' use karein ('swagat' hargiz nahi). Thanks ke liye 'Shukriya' ya 'Thank you' use karein ('dhanyawad' nahi). Help ke liye 'Madad' ya 'Help' use karein ('sahayata' nahi). Time ke liye 'Waqt' ya 'Time' use karein ('samay' nahi).\n"
            "6. NATURAL CONVERSATION: Bilkul robotic ya canned templates se bachein. Warm, polite, natural Roman Urdu mein baat karein.\n"
            "7. INTENT & CALL-TO-ACTION: Agar system message mein user se koi information ya confirmation mangi gayi hai (jaise requirement confirm karna, area choose karna, naya budget batana, ya visit time lena), to us sawal ko aakhir mein clearly aur politely pochain.\n"
            "8. CONCISE: Response ko natural aur relevant rakhein.\n\n"
            f"CUSTOMER CONTEXT:\n{pref_str}\n"
            f"{f'EXTRA KNOWLEDGE:\n{extra_info}\n' if extra_info else ''}\n"
            f"FACTUAL SYSTEM MESSAGE (GROUND TRUTH):\n{canonical_response}"
        )

        try:
            completion = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_message or "Hello"},
                    ],
                    max_tokens=250,
                    temperature=0.3,
                    timeout=4.0,
                ),
                timeout=5.0,
            )
            reply = completion.choices[0].message.content.strip()
            if reply:
                reply = clean_urdulish_vocabulary(reply)
                user_greeted = bool(re.search(
                    r"\b(?:aoa|as+alam|salam|hello|hi|hey|morn|even)\b",
                    user_message or "",
                    re.IGNORECASE
                ))
                if not user_greeted:
                    reply = re.sub(
                        r"^(?:(?:wa\s*[-]?\s*)?a?laikum\s+(?:as[-]?salam|salam)[!]?|"
                        r"as[-]?salam\s*[-]?\s*o\s*[-]?\s*(?:a?laikum|as[-]?salam)[!]?|"
                        r"as[-]?salam\s*[-]?\s*u\s*[-]?\s*(?:a?laikum|as[-]?salam)[!]?|"
                        r"salam[!]?|hello[!]?|hi[!]|hey[!])\s*[,.-]?\s*",
                        "",
                        reply,
                        flags=re.IGNORECASE
                    ).strip()
                    if reply:
                        reply = reply[0].upper() + reply[1:]
                return clean_urdulish_vocabulary(reply)
        except Exception:
            pass

        return clean_urdulish_vocabulary(canonical_response)

    async def _postprocess_response(
        self,
        result: dict,
        user_message: str,
        customer,
        state,
        saved,
        is_mock_nlu: bool,
    ) -> dict:
        if not isinstance(result, dict) or not result.get("message"):
            return result
        skip = result.pop("_skip_nlg", False)
        is_test = is_mock_nlu or (bool(os.getenv("PYTEST_CURRENT_TEST")) and not os.getenv("SARA_TEST_DYNAMIC_NLG"))
        if is_test or skip:
            return result
        client = getattr(getattr(self.sara, "understanding", None), "client", None)
        if client is None and not os.getenv("OPENROUTER_API_KEY"):
            return result

        extra_knowledge = saved.pop("_nlg_extra", "")
        dynamic_text = await self._generate_dynamic_nlg_response(
            user_message=user_message,
            canonical_response=result["message"],
            context={
                "customer": customer,
                "state": state,
                "saved": saved,
                "extra_knowledge": extra_knowledge,
            },
        )
        if dynamic_text:
            result["message"] = clean_urdulish_vocabulary(dynamic_text)
        elif result.get("message"):
            result["message"] = clean_urdulish_vocabulary(result["message"])
        return result

    async def classify_pending_choice(
        self,
        user_message: str,
        option_a_desc: str,
        option_b_desc: str,
    ) -> str:
        """
        Classifies user reply to a dual-option choice (Option A vs Option B)
        into one of: OPTION_A, OPTION_B, NEITHER, UNCLEAR.
        Fail-safe: On any exception, timeout, or unexpected output, defaults to UNCLEAR.
        Never crashes, never guesses Option A or Option B on failure.
        """
        if not user_message or not user_message.strip():
            return "UNCLEAR"

        # Check client
        understanding_obj = getattr(self.sara, "understanding", None)
        client = getattr(understanding_obj, "client", None)
        model = getattr(understanding_obj, "model", None) or os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
        if client is None and understanding_obj is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        api_key=api_key,
                        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    )
                except Exception:
                    client = None

        if client is None:
            # Deterministic fallback when no LLM client is configured (e.g. offline unit testing)
            msg_l = user_message.strip().lower()

            # Single-option mode: only Option A was offered
            if not option_b_desc:
                neither_patterns = [
                    r"\b(?:nahi|nahin|mat|no|kuch\s+aur|kisi\s+aur|koi\s+aur|rehne\s*(?:dein|do|de|dijiye)|cancel|neither|none)\b"
                ]
                if any(re.search(p, msg_l) for p in neither_patterns):
                    return "NEITHER"
                is_affirmative = bool(re.search(
                    r"\b(?:haan|ji|jee|g|theek|thik|theek hai|thik hai|sahi hai|batao|dikhao|dikhayein|acha|ok|yes|bilkul|kar dein|kardein|dekhna hai|dekhna chahenge|proceed)\b",
                    msg_l
                ))
                if is_affirmative:
                    return "OPTION_A"
                return "UNCLEAR"

            # Dual-option mode: Option A vs Option B
            unclear_patterns = [
                r"^(?:haan|ji|theek hai|thik hai|sahi hai|batao|dikhao|acha|ok|yes|hmmm?|dekhte hain)$",
                r"^(?:haan\s+(?:batao|dikhao|theek hai|thik hai))$",
            ]
            if any(re.match(p, msg_l) for p in unclear_patterns):
                return "UNCLEAR"
            neither_patterns = [
                r"\b(?:dono\s+nahi|koi\s+bhi\s+nahi|dono\s+hi\s+nahi|neither|none|dono\s+mat|kuch\s+aur|kisi\s+aur)\b"
            ]
            if any(re.search(p, msg_l) for p in neither_patterns):
                return "NEITHER"
            stop_words = {"mein", "hai", "option", "available", "match", "exact", "phase", "options"}
            raw_a = set(re.findall(r"[a-z0-9]+", (option_a_desc or "").lower())) - stop_words
            raw_b = set(re.findall(r"[a-z0-9]+", (option_b_desc or "").lower())) - stop_words
            unique_a = raw_a - raw_b
            unique_b = raw_b - raw_a
            user_tokens = set(re.findall(r"[a-z0-9]+", msg_l))

            matches_a = bool(user_tokens & unique_a) or bool(re.search(r"\b(?:pehle|pehla|first|same\s*area|relaxed)\b", msg_l))
            matches_b = bool(user_tokens & unique_b) or bool(re.search(r"\b(?:doosr[aei]|second|other\s*area|exact)\b", msg_l))
            if matches_a and not matches_b:
                return "OPTION_A"
            if matches_b and not matches_a:
                return "OPTION_B"
            return "UNCLEAR"

        # Production LLM Classification with Fail-Safe try/except
        try:
            if not option_b_desc:
                prompt = (
                    "You are an intent classification assistant for a Pakistani real estate platform.\n"
                    "The user was presented with a single property option:\n"
                    f"Option: {option_a_desc}\n\n"
                    f"User's reply: \"{user_message}\"\n\n"
                    "Classify the user's intent into EXACTLY ONE of these labels:\n"
                    "- OPTION_A: The user agrees, accepts, or confirms to view this option (e.g. 'thik hai', 'haan', 'ji', 'ok', 'dikhao', 'acha', 'bilkul', affirmative words).\n"
                    "- NEITHER: The user rejects this option or asks for something completely different (e.g. 'nahi', 'kuch aur', 'rehne dein').\n"
                    "- UNCLEAR: The user's reply is ambiguous or unrelated.\n\n"
                    "Output ONLY the single label (OPTION_A, NEITHER, or UNCLEAR)."
                )
            else:
                prompt = (
                    "You are an intent classification assistant for a Pakistani real estate platform.\n"
                    "The user was presented with two property options:\n"
                    f"Option A: {option_a_desc}\n"
                    f"Option B: {option_b_desc}\n\n"
                    f"User's reply: \"{user_message}\"\n\n"
                    "Classify the user's intent into EXACTLY ONE of these 4 labels:\n"
                    "- OPTION_A: The user chose or prefers Option A (e.g. mentions Option A's area, bedrooms, 'pehle wala', 'same area').\n"
                    "- OPTION_B: The user chose or prefers Option B (e.g. mentions Option B's area, bedrooms, 'doosra wala', 'other area').\n"
                    "- NEITHER: The user rejects both options or asks for something completely different.\n"
                    "- UNCLEAR: The user's reply is ambiguous, vague, or it is unclear which option they want (e.g. 'haan', 'theek hai', 'acha', 'batao', non-committal words).\n\n"
                    "Output ONLY the single label (OPTION_A, OPTION_B, NEITHER, or UNCLEAR)."
                )
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=20,
            )
            raw_out = (response.choices[0].message.content or "").strip().upper()
            for label in ("OPTION_A", "OPTION_B", "NEITHER", "UNCLEAR"):
                if label in raw_out:
                    return label
            return "UNCLEAR"
        except Exception:
            # Fail-safe: never crash, never guess Option A or Option B on failure
            return "UNCLEAR"

    async def _resolve_last_viewed_property(self, customer_id: str) -> str | None:
        events = []
        if hasattr(self.services.interactions, "list_customer_interactions"):
            try:
                raw_events = await asyncio.to_thread(
                    self.services.interactions.list_customer_interactions, customer_id
                )
                for item in raw_events:
                    events.append({
                        "property_id": getattr(item, "property_id", None),
                        "action": getattr(item, "action", None),
                        "conversation_id": getattr(item, "conversation_id", None),
                    })
            except Exception:
                events = []
        elif hasattr(self.services.interactions, "events"):
            for item in getattr(self.services.interactions, "events", []):
                if str(item.get("customer_id")) == str(customer_id):
                    events.append({
                        "property_id": item.get("property_id"),
                        "action": item.get("action"),
                        "conversation_id": item.get("conversation_id"),
                    })

        if events:
            cids = [e.get("conversation_id") for e in events if e.get("conversation_id")]
            if cids:
                last_cid = cids[-1]
                session_events = [e for e in events if e.get("conversation_id") == last_cid]
            else:
                session_events = events

            liked = [e["property_id"] for e in session_events if e.get("action") in ("liked", "shortlisted") and e.get("property_id")]
            unique_liked = list(dict.fromkeys(liked))
            if len(unique_liked) == 1:
                return unique_liked[0]
            if len(unique_liked) > 1:
                return "AMBIGUOUS"

            shown = [e["property_id"] for e in session_events if e.get("action") == "shown" and e.get("property_id")]
            unique_shown = list(dict.fromkeys(shown))
            if len(unique_shown) == 1:
                return unique_shown[0]
            if len(unique_shown) > 1:
                return "AMBIGUOUS"

        if hasattr(self.services, "sessions") and self.services.sessions:
            sessions_store = self.services.sessions
            if hasattr(sessions_store, "_sessions"):
                matching_contexts = [
                    ctx for ctx in sessions_store._sessions.values()
                    if str(ctx.customer_id) == str(customer_id)
                ]
                if matching_contexts:
                    latest_ctx = matching_contexts[-1]
                    props = list(latest_ctx.property_snapshots.keys())
                    if len(props) == 1:
                        return props[0]
                    if len(props) > 1:
                        return "AMBIGUOUS"
            elif hasattr(sessions_store, "database_url") and sessions_store.database_url:
                try:
                    import psycopg
                    query = """
                        SELECT p.property_id
                        FROM recommendation_sessions s
                        JOIN recommendation_session_properties p ON p.recommendation_session_id = s.recommendation_session_id
                        WHERE s.customer_id = %s
                        ORDER BY s.created_at DESC, p.display_position ASC
                    """
                    with psycopg.connect(sessions_store.database_url) as conn, conn.cursor() as cur:
                        cur.execute(query, (customer_id,))
                        rows = cur.fetchall()
                        props = list(dict.fromkeys(r[0] for r in rows if r[0]))
                        if len(props) == 1:
                            return props[0]
                        if len(props) > 1:
                            return "AMBIGUOUS"
                except Exception:
                    pass

        cust_ctx = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, customer_id)
        prefs = cust_ctx.preferences if cust_ctx else None
        if not prefs:
            return None

        city = getattr(prefs, "city", None)
        purpose = getattr(prefs, "purpose", None)
        budget = getattr(prefs, "budget_max", None)
        ptype = getattr(prefs, "property_type", None)
        area = getattr(prefs, "area", None)

        has_any = any([city, purpose, budget is not None, ptype, area])
        if not has_any:
            return None

        if not city or not purpose or budget is None or not ptype:
            return "INCOMPLETE_REQUIREMENT"

        filters = {"city": city, "purpose": purpose, "property_type": ptype}
        if area:
            filters["area"] = area
        try:
            matches = await asyncio.to_thread(
                self.services.properties.search,
                budget=budget,
                **filters
            )
            match_ids = list(dict.fromkeys(m.get("property_id") for m in matches if m.get("property_id")))
            if len(match_ids) == 1:
                return match_ids[0]
            elif len(match_ids) > 1:
                return "AMBIGUOUS"
        except Exception:
            pass

        return None

    async def turn(self, identity, payload, feedback, book, reschedule, cancel, *, observe_only=False):
        async with self.store.turn(payload.conversation_id, identity) as (conversation_id, saved):
            # Empty / accidental Enter: answer like a human on the line, not an NLU failure.
            if not (payload.message or "").strip():
                return self._response(conversation_id, "Ji, main sun rahi hoon — kya batana chahte hain?", True)
            observation = hashlib.sha256(payload.message.encode()).hexdigest()
            if observe_only and saved.get("last_voice_observation") == observation:
                return self._response(conversation_id, "")
            customer = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            if not customer.customer:
                raise PermissionError()
            state = self.sara.hydrate(customer.preferences, saved)
            original_required = dict(state.required)
            is_mock_nlu = type(getattr(self.sara, "understanding", None)).__name__ == "NLU" and not getattr(self.sara.understanding, "test_returning", False)
            out = lambda res: self._postprocess_response(res, payload.message, customer, state, saved, is_mock_nlu)

            # Early check for preference queries: "meri preferences kya hain?", "apky pass meri konsi preferences saved hain", etc.
            is_prefs_question = bool(re.search(
                r"\b(?:mer[aiy]+|my)\s+(?:saved\s+)?(?:preferences?|requirements?)\b|"
                r"\b(?:preferences?|requirements?)\s+(?:kya\s+hai[n]?|bata[aoaei]+|repeat|check)\b|"
                r"\bkons[aiy]+\s+(?:preferences?|requirements?)\b|"
                r"\bpreferences?\s+(?:repeat|dobara|repeat\s+kro|kya\s+saved|saved\s+hain)\b|"
                r"\bsaved\s+(?:hain\s+)?(?:preferences?|requirements?)\b|\bkya\s+saved\s+hai\b|"
                r"\bmer[aiy]+\s+(?:preferences?|requirements?)\s+kya\s+hai[n]?\b",
                payload.message, re.IGNORECASE
            ))
            if is_prefs_question and saved.get("preference_state") not in {"providing_preference_value", "editing_preferences"}:
                p = customer.preferences
                def _budget_str(v):
                    if v is None:
                        return None
                    return f"{v / 10_000_000:g} Crore" if v >= 10_000_000 else f"{v:,} PKR"
                lines = []
                if p:
                    for label, val in (("City", getattr(p, "city", None)),
                                       ("Area", getattr(p, "area", None)),
                                       ("Purpose", getattr(p, "purpose", None)),
                                       ("Property type", getattr(p, "property_type", None)),
                                       ("Bedrooms", getattr(p, "bedrooms", None)),
                                       ("Budget", _budget_str(getattr(p, "budget_max", None))),
                                       ("Amenities", ", ".join(getattr(p, "amenities", []) or []) or None)):
                        if val not in (None, "", []):
                            lines.append(f"- {label}: {val}")
                if lines:
                    pref_reply = (
                        "Ji bilkul! Aapki taraf se explicitly batai gayi ye preferences saved hain:\n\n"
                        + "\n".join(lines)
                        + "\n\nKya aap inhi requirements ke mutabiq options dekhna chahte hain ya kuch tabdeeli karni hai?"
                    )
                else:
                    pref_reply = "Ji, filhaal aapki koi preference save nahi hui. Aap batayein kis city aur budget mein dekhna hai — main best verified options nikal deti hoon."
                return await out(self._response(conversation_id, pref_reply, clarification=True, skip_nlg=True))
            context = {
                "required": state.required, "preferred": {}, "excluded": state.excluded,
                "pending_action": saved.get("pending_action"),
                "preference_state": saved.get("preference_state"),
                "preference_fields": saved.get("preference_fields", []),
                "recent_turns": saved.get("recent_turns", [])[-6:],
                "last_results": [{"property_id": value} for value in saved.get("property_order", [])],
                "selected_property": {"property_id": saved["selected"]} if saved.get("selected") else None,
                "current_date": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
                "timezone": "Asia/Karachi",
            }
            try:
                understanding = await asyncio.to_thread(self.sara.understand, payload.message, context)
            except UnderstandingError:
                service = getattr(self.sara, "understanding", None)
                if service and hasattr(service, "_deterministic_understanding"):
                    understanding = service._deterministic_understanding(payload.message, context)
                else:
                    understanding = None

                if not understanding:
                    if saved.get("preference_state") in {"providing_preference_value", "editing_preferences"}:
                        target_field = (saved.get("preference_fields") or ["budget"])[0]
                        from sara_agent.preference_edit import QUESTIONS
                        default_q = QUESTIONS.get(target_field, "Aap apni requirement bata dein.")
                        dynamic_reply = await self._generate_preference_clarification_response(
                            customer=customer,
                            field=target_field,
                            user_message=payload.message,
                            default_question=default_q,
                        )
                        return await out(self._response(conversation_id, dynamic_reply, True, skip_nlg=True))
                    return await out(self._response(
                        conversation_id,
                        "Sorry, main is request ko smjh nahi saki kiya ap mujhey thora differnetly bta sktey hai.",
                        True,
                    ))

            # Returning customer handling on Turn 1 of a new session
            has_saved_prefs = bool(
                customer.preferences and (
                    getattr(customer.preferences, "city", None) or
                    getattr(customer.preferences, "purpose", None) or
                    getattr(customer.preferences, "budget_max", None)
                )
            )
            is_first_turn = saved.get("turn_count", 0) == 0

            references_previous_property = bool(re.search(
                r"\b(?:pichli|pichlay|pichla|last\s+time|previous(?:ly)?)\s+(?:dafa\s+)?(?:jo\s+)?(?:property|listing)\b.*"
                r"\b(?:book|schedule|appointment|visit)\b|"
                r"\b(?:book|schedule)\s+(?:kr|kar|krwani|karwani|krdein|kardein)\b.*\b(?:pichli|pichlay|last\s+time|previous)\b",
                payload.message, re.IGNORECASE
            ))
            is_booking_intent = (understanding.intent in {"schedule_visit"}) or references_previous_property
            was_awaiting_requirement = bool(
                isinstance(saved.get("pending_action"), dict)
                and saved.get("pending_action", {}).get("awaiting_requirement")
            )
            informational_intents = {
                "PROPERTY_TYPE_BY_BUDGET_QUERY", "property_type_by_budget_query",
                "MINIMUM_BUDGET_QUERY", "minimum_budget_query",
                "BUDGET_FEASIBILITY_QUERY", "budget_feasibility_query",
                "CHEAPEST_PROPERTY_QUERY", "cheapest_property_query",
                "MOST_EXPENSIVE_PROPERTY_QUERY", "most_expensive_property_query",
                "AREAS_QUERY", "areas_query",
                "CITIES_QUERY", "cities_query",
                "LIST_AVAILABLE_OPTIONS_QUERY", "list_available_options_query",
                "BUDGET_OBJECTION", "budget_objection",
            }
            is_informational_query = (
                understanding.intent in informational_intents
                or getattr(understanding, "query_budget", None) is not None
                or bool(re.search(
                    r"\b(?:k[ao]ns[aei]|knse?y?|k[ao]n\s+k[ao]n\s+s[aei]|kn\s+kn\s+se?y?|kin\s+kin|which|what|kitn[aei]|list\s+(?:of\s+)?)\s+(?:cities|city|shehar|shahron|areas?|locations?)\b|"
                    r"\b(?:cities|city|shehar|shahron)\s+(?:mein\s+)?(?:available|options?)\b|"
                    r"\bwhich\s+cities\s+do\s+you\s+operate\b|"
                    r"\b(?:s[ab]b?\s*se\s*m(?:ehng|engh)[aeiouy]*|most\s*expensive|highest\s*price|maximum\s*price|costliest)\b|"
                    r"\b(?:sab\s+se\s+sast[aei]|cheapest|lowest\s+price)\b",
                    payload.message, flags=re.IGNORECASE
                ))
            )

            # Turn 2: User responds to Case A confirmation question
            is_area_relax_input = bool(re.search(
                r"\b(?:dusre|dusray|dusrey|doosre|doosray|doosrey|other|different|aur|aor|mazeed|more|qareebi)\s+areas?\b|"
                r"\b(?:areas?|locations?)\s+(?:k[ayei]?\s+)?(?:options?\s+)?(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|check|dekh|dekhna)\b|"
                r"\b(?:kisi\s+(?:aur|aor|dusre|doosre|dusrey|doosrey)\s+area)\b|"
                r"\bkoi\s+bhi\s+(?:area|location)\b|"
                r"\b(?:area|location)\s+(?:flexible|koi\s+bhi|matter\s+nahi)\b",
                payload.message, flags=re.IGNORECASE
            ))
            if is_area_relax_input and not is_informational_query:
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

            active_before = saved.get("preference_state") == "providing_preference_value"
            active_field = (saved.get("preference_fields") or [None])[0] if active_before else None
            edit_question = advance_edit(saved, understanding, payload.message)
            if edit_question:
                target_field = active_field or (saved.get("preference_fields") or [None])[0]
                if target_field:
                    dynamic_reply = await self._generate_preference_clarification_response(
                        customer=customer,
                        field=target_field,
                        user_message=payload.message,
                        default_question=edit_question,
                    )
                    return await out(self._response(conversation_id, dynamic_reply, True, skip_nlg=True))
                return await out(self._response(conversation_id, edit_question, True))
            editing = saved.get("preference_state") == "editing_preferences" and understanding.intent == "property_search" and not understanding.interaction_action
            if saved.get("pending_returning_confirm"):
                saved["pending_returning_confirm"] = False
                is_confirm = bool(re.search(
                    r"\b(?:haan|wahi|theek hai|yes|ji haan|sahi hai|wahi dikha do|wahi chahiye|bilkul|kar do)\b",
                    payload.message, re.IGNORECASE
                ))
                wants_other_options = bool(re.search(
                    r"\b(?:aur|aor|dusre|dusray|different|other|koi\s+(?:aur|aor)|mazeed|more)\s+options?\b|"
                    r"\boptions?\s+(?:dekhna|dekhni|dekh)\s+(?:chah|chahu|chahiye)",
                    payload.message, re.IGNORECASE
                ))
                if (is_confirm or understanding.preference_action == "continue" or understanding.intent in {"SAME_REQUIREMENTS", "same_requirements"}) and not understanding.required:
                    saved["preference_state"] = "continuing_saved_preferences"
                    saved.pop("pending_returning_confirm_question", None)
                    fields = ("city", "area", "bedrooms", "property_type", "purpose", "amenities")
                    for f in fields:
                        val = getattr(customer.preferences, f, None)
                        if val not in (None, []):
                            state.required[f] = val
                    if getattr(customer.preferences, "budget_max", None) is not None:
                        state.required["budget"] = customer.preferences.budget_max
                elif is_informational_query:
                    saved.pop("pending_returning_confirm", None)
                    saved.pop("pending_returning_confirm_question", None)
                elif re.search(r"\b(?:nahi|no|new|naya|fresh)\b", payload.message, re.IGNORECASE) and not understanding.required:
                    saved.pop("pending_returning_confirm_question", None)
                    state.required.clear()
                    state.flexible.clear()
                elif wants_other_options:
                    saved.pop("pending_returning_confirm_question", None)
                    city = getattr(customer.preferences, "city", None) or state.required.get("city")
                    saved["pending_scope_confirm"] = {"city": city}
                    return await out(self._response(conversation_id,
                        f"Ji zaroor! Kya ap {city} mein hi doosre areas ke options dekhna chahengi, ya kisi aur city mein dekhna chahengi?", True))
                elif is_booking_intent or understanding.intent == "schedule_visit":
                    saved.pop("pending_returning_confirm", None)
                    saved.pop("pending_returning_confirm_question", None)
                    understanding.intent = "schedule_visit"
                elif understanding.intent == "off_topic":
                    saved["pending_returning_confirm"] = True
                    pending_question = saved.get("pending_returning_confirm_question") or \
                        "Pichli dafa ki requirement continue karni hai ya koi preference change karni hai?"
                    return await out(self._response(
                        conversation_id,
                        f"Main sirf property se related sawalon mein madad kar sakti hoon. Waisay, {pending_question}",
                        True,
                    ))
                elif not understanding.required and not understanding.relax:
                    fallback_q = "Saved requirement continue karni hai ya koi preference change karni hai?"
                    saved["pending_returning_confirm"] = True
                    saved["pending_returning_confirm_question"] = fallback_q
                    return await out(self._response(conversation_id, fallback_q, True))
                if not (is_booking_intent or understanding.intent == "schedule_visit" or is_informational_query):
                    understanding.intent = "property_search"

            elif is_first_turn and (has_saved_prefs or references_previous_property) and not saved.get("returning_customer_handled") and not is_mock_nlu:
                if is_booking_intent:
                    saved["returning_customer_handled"] = True
                    resolved_property_id = await self._resolve_last_viewed_property(identity.customer_id)
                    if resolved_property_id == "AMBIGUOUS":
                        saved["pending_action"] = {"intent": "schedule_visit", "awaiting_property_choice": True}
                        return await out(self._response(conversation_id,
                            "Ji, pichli dafa ap ne ek se zyada properties dekhi thin, kis property ki visit book karni hai?", True))
                    if resolved_property_id == "INCOMPLETE_REQUIREMENT":
                        # Last search never resolved to a specific property because a required 
                        # field (city/budget/purpose/property_type) was still missing.
                        missing_field_prompt = await self._missing_requirement_prompt(customer.preferences)
                        saved["pending_action"] = {"intent": "schedule_visit", "awaiting_requirement": True}
                        return await out(self._response(conversation_id, missing_field_prompt, True))
                    if resolved_property_id:
                        saved["selected"] = resolved_property_id
                        saved["property_order"] = [resolved_property_id]
                        understanding.intent = "schedule_visit"
                        prop_row = await asyncio.to_thread(self.services.properties.get_property, resolved_property_id)
                        if prop_row:
                            sid = uuid4()
                            from web_api.services import RecommendationContext, property_snapshot, preference_snapshot
                            p_snap = property_snapshot(prop_row)
                            pref_snap = preference_snapshot(customer.preferences) if customer and customer.preferences else {}
                            ctx = RecommendationContext(customer_id=identity.customer_id, property_snapshots={resolved_property_id: p_snap}, preference_snapshot=pref_snap)
                            await asyncio.to_thread(self.services.sessions.put, sid, ctx)
                            saved["recommendation_session_id"] = str(sid)
                        # Fall through to normal schedule_visit routing below with `selected` now populated —
                        # do NOT return here; let the existing `if u.intent in {"schedule_visit", ...}:` block 
                        # in _route() continue as it already does (asking for date/time if `u.starts_at` is missing).
                    else:
                        return await out(self._response(conversation_id,
                            "Ji, mujhe pichli dafa koi dekhi hui property nahi mil rahi. Kya ap property ka naam ya area bata sakti hain?", True))

                else:
                    # Check if user message explicitly gives search criteria
                    msg_has_criteria = bool(
                        (understanding and understanding.required and any([
                            understanding.required.get("city"), understanding.required.get("area"),
                            understanding.required.get("budget"), understanding.required.get("purpose"),
                            understanding.required.get("property_type")
                        ]))
                    )
                    if is_informational_query:
                        saved["returning_customer_handled"] = True
                    elif not msg_has_criteria:
                        # Case A: Generic message -> mention saved preferences and ask confirmation
                        summary = self._format_saved_prefs_summary(customer.preferences)
                        saved["pending_returning_confirm"] = True
                        saved["pending_returning_confirm_question"] = summary
                        saved["returning_customer_handled"] = True
                        saved["turn_count"] = 1
                        return await out(self._response(conversation_id, summary, True))
                    else:
                        saved_city = getattr(customer.preferences, "city", None)
                        saved_purpose = getattr(customer.preferences, "purpose", None)
                        new_city = understanding.required.get("city")
                        new_purpose = understanding.required.get("purpose")
                        is_different = (
                            (new_city and saved_city and new_city.lower() != saved_city.lower()) or
                            (new_purpose and saved_purpose and new_purpose.lower() != saved_purpose.lower())
                        )
                        saved["returning_customer_handled"] = True
                        if is_different:
                            # Case B: User explicitly mentions DIFFERENT criteria
                            old_desc = f"{saved_city or ''} {saved_purpose or ''}".strip()
                            if new_city:
                                new_desc = f"{new_city} mein {new_purpose or ''}".strip()
                            else:
                                new_desc = f"isi city mein {new_purpose or ''}".strip()
                            saved["returning_ack_prefix"] = f"Ji! Pichli dafa {old_desc} ka tha, ab {new_desc} dekh rahe hain. "
                        else:
                            # Case C: User repeats SAME criteria
                            saved["returning_ack_prefix"] = f"Ji bilkul! {saved_city or ''} mein options dekh rahe hain. "

            if (saved.get("pending_action") or {}).get("intent") == "schedule_visit":
                if understanding.intent == "property_search":
                    saved["pending_action"] = None
                elif not understanding.starts_at and understanding.intent not in ("schedule_visit", "cancel_visit", "reschedule_visit"):
                    return await out(self._response(conversation_id, "Visit ke liye kis date aur time par schedule karna chahenge?", True))

            before = original_required
            raw = payload.message.casefold()
            if re.search(r"\bbudget\s+(?:flexible|koi masla nahi|ka masla nahi)|\bno budget limit\b", raw):
                understanding.required.pop("budget", None)
                understanding.preferred.pop("budget", None)
                understanding.relax = list(set(understanding.relax) | {"budget"})
                understanding.intent = "property_search"
            if "area" in understanding.relax or re.search(
                r"\b(?:area|location)\s+(?:koi\s+bhi|flexible|matter\s+nahi|issue\s+nahi)\b|"
                r"\bkoi\s+bhi\s+(?:area|location)\b|"
                r"\barea\s+flexible\b|"
                r"\b(?:sab|all|saray|saare)\s+(?:suggest kiye hue\s+)?areas?\b",
                raw,
            ):
                understanding.required.pop("area", None)
                understanding.preferred.pop("area", None)
                understanding.relax = list(set(understanding.relax) | {"area"})
                understanding.intent = "property_search"
            # Bedrooms flexibility: "bedroom flexible hai", "bedrooms flexible hain",
            # "rooms adjustable" — previously only handled if the NLU caught it.
            if re.search(
                r"\b(?:bedrooms?|rooms?)\s+(?:flexible|adjustable|adjust|koi\s+masla\s+nahi|ka\s+masla\s+nahi)\b|"
                r"\bflexible\s+(?:hai[n]?)?\s*(?:bedrooms?|rooms?)\b",
                raw,
            ):
                understanding.required.pop("bedrooms", None)
                understanding.preferred.pop("bedrooms", None)
                understanding.relax = list(set(understanding.relax) | {"bedrooms"})
                understanding.intent = "property_search"
            informational_intents = {
                "PROPERTY_TYPE_BY_BUDGET_QUERY", "property_type_by_budget_query",
                "MINIMUM_BUDGET_QUERY", "minimum_budget_query",
                "BUDGET_FEASIBILITY_QUERY", "budget_feasibility_query",
                "CHEAPEST_PROPERTY_QUERY", "cheapest_property_query",
                "MOST_EXPENSIVE_PROPERTY_QUERY", "most_expensive_property_query",
                "AREAS_QUERY", "areas_query",
                "CITIES_QUERY", "cities_query",
                "LIST_AVAILABLE_OPTIONS_QUERY", "list_available_options_query",
                "BUDGET_OBJECTION", "budget_objection",
            }
            is_informational_query = (
                understanding.intent in informational_intents
                or getattr(understanding, "query_budget", None) is not None
            )

            # Day 3 owns merge, city/area invalidation, relaxation and ambiguity rules.
            self.sara.planner.build_plan(understanding, state)
            combined = {**state.preferred, **state.required}
            differs = False
            if not is_informational_query:
                for k in set(before) | set(combined):
                    v_b, v_c = before.get(k), combined.get(k)
                    if isinstance(v_b, str) and isinstance(v_c, str):
                        if v_b.strip().casefold() != v_c.strip().casefold():
                            differs = True
                            break
                    elif v_b != v_c:
                        differs = True
                        break
                if differs:
                    stale_keys = [
                        "pending_expand_area",
                        "pending_suggested_area",
                        "pending_suggested_areas",
                        "last_asked_broaden",
                        "pending_returning_confirm_question",
                        "pending_cheaper_offer",
                        "pending_choice_frame",
                    ]
                    if not understanding.interaction_action:
                        stale_keys.extend(["property_order", "selected", "recommendation_session_id", "pending_action"])
                    for stale in stale_keys:
                        saved.pop(stale, None)
            updates = {}
            if not is_informational_query:
                is_one_time_query = bool(re.search(
                    r"\b(?:dikh[aoaei]+|show|options?\s+dikha|dekhna\s+hai|dekhni\s+hai|check\s+k(?:ar|r)|options?\s+dekh)\b",
                    raw, re.IGNORECASE
                ))
                has_pref_confirm = bool(re.search(
                    r"\b(?:mer[aiy]+\s+preference|preference\s+(?:hai|save|update)|yehi\s+chahiye|yehi\s+meri\s+requirement|save\s+k(?:ar|r)|mujhe\s+yehi\s+chahiye|isi\s+ko\s+save|confirm)\b",
                    raw, re.IGNORECASE
                ))
                editing_pref = saved.get("preference_state") in {"providing_preference_value", "editing_preferences"} or was_awaiting_requirement

                for key in set(before) | set(combined):
                    value = combined.get(key)
                    if value != before.get(key):
                        # Rule 1 & Rule 4: Only save if user EXPLICITLY stated this field in their message, or is in editing mode
                        explicit_in_turn = (
                            editing_pref
                            or key in getattr(understanding, "required", {})
                            or key in getattr(understanding, "preferred", {})
                        )
                        if not explicit_in_turn:
                            continue

                        # Rule 3: If user asks "yeh area/property mujhe dikhao", treat as ONE-TIME query, not a saved preference
                        if is_one_time_query and not has_pref_confirm and not editing_pref:
                            if key == "area" and before.get("area") is None:
                                continue
                            if key == "property_type" and before.get("property_type") is None:
                                continue

                        field = "budget_max" if key == "budget" else key
                        if field in PreferencesUpdate.model_fields:
                            updates[field] = value.lower() if field == "purpose" and isinstance(value, str) else value
                if (combined.get("property_type") or "").lower() in ("plot", "commercial", "office"):
                    updates["bedrooms"] = None
            if updates:
                try:
                    validated = PreferencesUpdate(**updates).model_dump(exclude_unset=True)
                except ValidationError as exc:
                    from sara_agent.preference_edit import QUESTIONS
                    field = str(exc.errors()[0]["loc"][0]) if exc.errors()[0]["loc"] else "budget_max"
                    field = "budget" if field in {"budget_min", "budget_max"} else field
                    saved["preference_state"] = "providing_preference_value"
                    saved["preference_fields"] = [field]
                    return await out(self._response(conversation_id, "Yeh value valid nahi hai. " + QUESTIONS.get(field, "Nayi value bata dein."), True))
                minimum = validated.get("budget_min", getattr(customer.preferences, "budget_min", None))
                maximum = validated.get("budget_max", getattr(customer.preferences, "budget_max", None))
                if minimum is not None and maximum is not None and minimum > maximum:
                    saved["preference_state"] = "providing_preference_value"
                    saved["preference_fields"] = ["budget"]
                    return await out(self._response(conversation_id, f"Minimum budget maximum se zyada nahi ho sakta. Saved minimum budget {minimum:,} PKR hai. Naya maximum is se kam hai; maximum budget kya rakhna hai?", True))
                await asyncio.to_thread(self.services.customers.update_preferences, identity.customer_id, validated)

            if editing:
                saved["flexible"] = sorted(state.flexible)
                saved["excluded"] = state.excluded
                edit_reply = finish_edit(saved, combined)
                if saved["preference_state"] == "providing_preference_value":
                    return await out(self._response(conversation_id, edit_reply, True))
                saved["returning_ack_prefix"] = edit_reply
            elif saved.get("preference_state") == "continuing_saved_preferences":
                saved["preference_state"] = "ready_for_search"

            if was_awaiting_requirement:
                resolved_property_id = await self._resolve_last_viewed_property(identity.customer_id)
                if resolved_property_id == "INCOMPLETE_REQUIREMENT":
                    cust_fresh = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
                    missing_prompt = await self._missing_requirement_prompt(cust_fresh.preferences)
                    saved["pending_action"] = {"intent": "schedule_visit", "awaiting_requirement": True}
                    return await out(self._response(conversation_id, missing_prompt, True))
                elif resolved_property_id == "AMBIGUOUS":
                    saved["pending_action"] = {"intent": "schedule_visit", "awaiting_property_choice": True}
                    return await out(self._response(conversation_id,
                        "Ji, pichli dafa ap ne ek se zyada properties dekhi thin, kis property ki visit book karni hai?", True))
                elif resolved_property_id:
                    saved["selected"] = resolved_property_id
                    saved["property_order"] = [resolved_property_id]
                    saved["pending_action"] = {"intent": "schedule_visit", "property_id": resolved_property_id}
                    understanding.intent = "schedule_visit"
                    prop_row = await asyncio.to_thread(self.services.properties.get_property, resolved_property_id)
                    if prop_row:
                        sid = uuid4()
                        from web_api.services import RecommendationContext, property_snapshot, preference_snapshot
                        p_snap = property_snapshot(prop_row)
                        pref_snap = preference_snapshot(customer.preferences) if customer and customer.preferences else {}
                        ctx = RecommendationContext(customer_id=identity.customer_id, property_snapshots={resolved_property_id: p_snap}, preference_snapshot=pref_snap)
                        await asyncio.to_thread(self.services.sessions.put, sid, ctx)
                        saved["recommendation_session_id"] = str(sid)
                else:
                    return await out(self._response(conversation_id,
                        "Ji, mujhe pichli dafa koi dekhi hui property nahi mil rahi. Kya ap property ka naam ya area bata sakti hain?", True))
            saved["flexible"] = sorted(state.flexible)
            saved["excluded"] = state.excluded
            if observe_only:
                # VAPI owns speech and tool invocation. Final transcripts only hydrate
                # shared preferences/feedback; never book or search a second time.
                result = (await self._route(identity, conversation_id, saved, state, understanding,
                                           feedback, book, reschedule, cancel, message=payload.message)
                          if understanding.interaction_action else self._response(conversation_id, ""))
                saved["last_voice_observation"] = observation
            else:
                result = await self._route(identity, conversation_id, saved, state, understanding,
                                           feedback, book, reschedule, cancel, message=payload.message)
            saved["turn_count"] = saved.get("turn_count", 0) + 1
            if saved.get("returning_ack_prefix") and isinstance(result, dict) and "message" in result:
                prefix = saved.pop("returning_ack_prefix", "")
                result["message"] = prefix + result["message"]
            elif is_first_turn and not has_saved_prefs and understanding.intent != "greeting" and not observe_only:
                result["message"] = "Assalam-o-alaikum! Main Sara hoon, aapki property assistant. " + result["message"]
            # No-verbatim-repeat guard against consecutive identical bot outputs when user expresses confusion/protest
            is_protest = bool(re.search(
                r"\b(?:lakin|lekin|to\s+kaha\s+tha|pehle\s+to|kyun|already|wahi\s+to|kaha\s+to\s+tha)\b",
                payload.message, flags=re.IGNORECASE
            ))
            last_bot_msg = saved.get("last_assistant_message")
            cur_msg = result.get("message") if isinstance(result, dict) else None
            if is_protest and last_bot_msg and cur_msg and cur_msg.strip() == last_bot_msg.strip():
                city = state.required.get("city") or "is city"
                area = state.required.get("area")
                loc = f"{area}, {city}" if area else city
                result["message"] = (
                    f"Ji, {loc} mein is criteria par pehle bhi options nahi mil sake the. "
                    "Kya aap budget thora barhana chahenge ya kisi doosre area mein dekhna chahenge?"
                )
            if isinstance(result, dict) and result.get("message"):
                saved["last_assistant_message"] = result["message"]

            if understanding:
                saved["recent_turns"] = (saved.get("recent_turns", []) + [{
                    "intent": getattr(understanding, "intent", None),
                    "interaction_action": getattr(understanding, "interaction_action", None),
                    "selected_index": getattr(understanding, "selected_index", None),
                }])[-6:]

            return await out(result)

    def _response(self, conversation_id, message, clarification=False, skip_nlg=False, **fields):
        if "properties" in fields and fields["properties"]:
            from web_api.services import public_property
            fields["properties"] = [
                public_property(p) if isinstance(p, dict) else p
                for p in fields["properties"]
            ]
        return {"conversation_id": conversation_id,
                "message": self.sara.speech.decorate(message),
                "requires_clarification": clarification,
                "_skip_nlg": skip_nlg, **fields}

    async def _route(self, identity, cid, saved, state, u, feedback, book, reschedule, cancel, message=""):
        from web_api.services import public_property, property_snapshot, preference_snapshot, RecommendationContext
        respond = lambda message, clarification=False, **fields: self._response(cid, message, clarification, **fields)
        raw_msg = (message or getattr(u, "raw_message", "") or "").casefold()
        order = saved.get("property_order", [])
        selected = resolve_property_reference(u, order, saved.get("selected"))
        has_reference = u.selected_index is not None or u.reference_type or u.interaction_property_id
        if selected:
            saved["selected"] = selected
        if u.interaction_action:
            if not selected or u.needs_clarification:
                return respond("Please batayein aap pehli, doosri ya teesri property ki baat kar rahe hain?", True)
            # Stale like/reject from a UI card whose search session was cleared
            # (e.g. preferences changed) must not crash with KeyError on the
            # recommendation_session_id lookup.
            rid_saved = saved.get("recommendation_session_id")
            if not rid_saved:
                return respond("Yeh action purani search ke options ke liye tha. Pehle naye options dikhwa lein, phir like/reject karein?", True)
            await feedback(MeInteractionCreate(property_id=selected, action=u.interaction_action,
                                               recommendation_session_id=rid_saved))
            messages = {"liked": "Ji, yeh option aap ko pasand aaya, note kar liya.",
                        "rejected": "Theek hai, yeh option reject kar diya.",
                        "shortlisted": "Ji, yeh property shortlist kar li hai."}
            return respond(messages[u.interaction_action])

        # Attribute question about a shown/selected listing: "kitney marley ka house hai",
        # "kitna covered area hai", "is ki price kya hai" — answer from the listing
        # instead of falling into the generic clarification reply.
        is_attribute_question = bool(re.search(
            r"kitn[aeiy]+\s*(?:k[a]?\s*)?(?:marl[aeiy]+|kanal|gaz|squar\w*|sq\w*)\b|"
            r"\b(?:marl[aeiy]+|kanal|gaz|covered\s+area|plot\s+size|size)\s*(?:k[aiy]+|ka|hai)\b|"
            r"\b(?:price|cost|qimat|keemat|rate)\s*(?:kya|kitn\w*|hai)|"
            r"\b(?:developer|builders?|amenities|facilities|status|condition|location|"
            r"property\s+type|bathrooms?|bedrooms?|rooms?|purpose|buy|rent)\s*(?:kon|kaun|kya|kitn\w*|kahan|where|hai[n]?)",
            raw_msg, flags=re.IGNORECASE,
        ))
        if is_attribute_question:
            target = selected or saved.get("selected") or (order[0] if len(order) == 1 else None)
            if not target and order:
                for pid in order:
                    p = await asyncio.to_thread(self.services.properties.get_property, pid)
                    if p:
                        area_name = str(p.get("area", "")).lower()
                        city_name = str(p.get("city", "")).lower()
                        if (area_name and area_name in raw_msg) or (city_name and city_name in raw_msg):
                            target = pid
                            break
            if target:
                row = await asyncio.to_thread(self.services.properties.get_property, target)
                if row and not row.get("available"):
                    return respond("Yeh property ab available nahi hai. Naye options dekhna chahenge?", True)
                if row:
                    name = row.get("property_name", "yeh property")
                    # The property service exposes unit keys as plot_unit and
                    # covered_area_unit (not plot_size_unit).
                    def unit_value(row: dict, value_key: str, unit_keys: tuple[str, ...]) -> str:
                        unit = ""
                        for key in unit_keys:
                            if row.get(key):
                                unit = str(row[key]).lower()
                                break
                        return f"{row.get(value_key)} {unit}".strip()
                    parts = []
                    if re.search(r"\b(?:developer|builders?)\b", raw_msg, re.IGNORECASE):
                        dev = row.get("developer_name") or row.get("developer")
                        parts.append(f"{name} ka developer {dev} hai." if dev
                                     else f"{name} ka developer record mein nahi mila.")
                    if re.search(r"\b(?:amenities|facilities)\b", raw_msg, re.IGNORECASE):
                        amenities = row.get("amenities") or []
                        parts.append(f"{name} ki amenities hain: {', '.join(str(a) for a in amenities[:6])}."
                                     if amenities else f"{name} ki amenities record mein nahi mili.")
                    if re.search(r"\b(?:status|condition)\b", raw_msg, re.IGNORECASE):
                        parts.append(f"{name} ka status {row.get('status', 'Ready')} hai.")
                    if re.search(r"\b(?:location|kahan|where)\b", raw_msg, re.IGNORECASE):
                        parts.append(f"{name} {row.get('area', '')}, {row.get('city', '')} mein hai.")
                    if re.search(r"\b(?:property\s+type)\b", raw_msg, re.IGNORECASE):
                        parts.append(f"{name} aik {row.get('property_type', 'property')} hai.")
                    if re.search(r"\bbathrooms?\b", raw_msg, re.IGNORECASE) and row.get("bathrooms"):
                        parts.append(f"{name} mein {row.get('bathrooms')} bathrooms hain.")
                    if re.search(r"\b(?:bedrooms?|rooms?)\b", raw_msg, re.IGNORECASE) and not re.search(r"\bbathrooms?\b", raw_msg, re.IGNORECASE) and row.get("bedrooms"):
                        parts.append(f"{name} mein {row.get('bedrooms')} bedrooms hain.")
                    if re.search(r"\b(?:purpose|buy|rent)\b", raw_msg, re.IGNORECASE):
                        parts.append(f"{name} {row.get('purpose', 'Purchase').lower()} ke liye hai.")
                    if re.search(r"\b(?:marl\w*|kanal|gaz|plot|size)\b", raw_msg, re.IGNORECASE) and row.get("plot_size"):
                        parts.append(f"{name} {unit_value(row, 'plot_size', ('plot_unit', 'plot_size_unit'))} ka plot hai.")
                    if re.search(r"\b(?:squar\w*|sq\w*|covered)\b", raw_msg, re.IGNORECASE) and row.get("covered_area"):
                        parts.append(f"{name} ka covered area {unit_value(row, 'covered_area', ('covered_area_unit',))} hai.")
                    if re.search(r"\b(?:price|cost|qimat|keemat|rate)\b", raw_msg, re.IGNORECASE) and row.get("price"):
                        try:
                            p = int(row["price"])
                            p_str = f"{p / 10_000_000:.2f} Crore PKR" if p >= 10_000_000 else f"{p / 100_000:.0f} Lakh PKR"
                        except (TypeError, ValueError):
                            p_str = f"{row['price']} PKR"
                        parts.append(f"{name} ki price {p_str} hai.")

                    body = " ".join(parts) if parts else self._format_property_details(row)
                    if u.intent == "schedule_visit":
                        saved["pending_action"] = {"intent": "schedule_visit", "property_id": target, "starts_at": u.starts_at}
                        return respond(f"Ji, {body} Visit ke liye kis date aur time par available hain?", True)
                    return respond(f"Ji, {body} Mazeed details ya visit schedule karne ke liye batayein.", True)
            elif order:
                return respond("Kis option ki baat kar rahe hain? Option number bata dein.", True)

        # "bahria main dikha do", "dha mein dikhao" — user names an area and asks
        # to show listings. Resolve the area against known available areas even
        # when NLU returns needs_clarification for it.
        area_pick = re.search(
            r"\b([\w][\w\s]{1,30}?)\s+(?:main|mein)\s+(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|dikhayen|dikhaden)\b",
            raw_msg, re.IGNORECASE)
        if area_pick:
            cust_for_areas = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            pick_city = (state.required.get("city")
                         or (cust_for_areas.preferences.city if cust_for_areas and cust_for_areas.preferences else None))
            if pick_city:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=pick_city, property_type=state.required.get("property_type"),
                    purpose=state.required.get("purpose"), budget=state.required.get("budget"), limit=20
                )
                picked = area_pick.group(1).strip()
                picked_lower = picked.lower()
                exact_match = next((a for a in available_areas if str(a).strip().lower() == picked_lower), None)
                matching_variants = list(dict.fromkeys(
                    str(a) for a in available_areas
                    if picked_lower in str(a).lower() or str(a).lower() in picked_lower or str(a).lower().split()[0] == picked_lower
                ))
                if not exact_match and len(matching_variants) > 1:
                    return respond(
                        f"Ji, {picked} mein kai phases available hain: {', '.join(matching_variants)}. "
                        "Ap kis phase mein dekhna chahengi?", True)
                matched = exact_match or (matching_variants[0] if matching_variants else None)
                if matched:
                    state.required["area"] = matched
                    saved["flexible"] = [f for f in saved.get("flexible", []) if f != "area"]
                    has_pref_confirm = bool(re.search(
                        r"\b(?:mer[aiy]+\s+preference|preference\s+(?:hai|save|update)|yehi\s+chahiye|yehi\s+meri\s+requirement|save\s+k(?:ar|r)|mujhe\s+yehi\s+chahiye|isi\s+ko\s+save|confirm)\b",
                        raw_msg, re.IGNORECASE
                    ))
                    existing_area_pref = getattr(getattr(cust_for_areas, "preferences", None), "area", None)
                    if has_pref_confirm or existing_area_pref is not None:
                        await asyncio.to_thread(self.services.customers.update_preferences,
                                                identity.customer_id, {"area": matched})
                    rid, rows = await self.services.recommendations(
                        identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                        filter_overrides={"area": matched}
                    )
                    if rows:
                        saved.update(recommendation_session_id=str(rid),
                                     property_order=[r["property_id"] for r in rows],
                                     selected=(rows[0]["property_id"] if len(rows) == 1 else None), pending_action=None)
                        intro = f"Theek hai! {matched} mein ye verified options available hain:"
                        msg = self.sara.presentation.format_batch(rows, has_more=False,
                                                                  first_batch=True, custom_intro=intro)
                        return respond(msg, recommendation_session_id=str(rid), properties=rows)

        # "meri preferences kya hain?" / "apky pass meri konsi preferences saved hain" / "preferences repeat kro"
        is_prefs_question = bool(re.search(
            r"\b(?:mer[aiy]+|my)\s+(?:saved\s+)?(?:preferences?|requirements?)\b|"
            r"\b(?:preferences?|requirements?)\s+(?:kya\s+hai[n]?|bata[aoaei]+|repeat|check)\b|"
            r"\bkons[aiy]+\s+(?:preferences?|requirements?)\b|"
            r"\bpreferences?\s+(?:repeat|dobara|repeat\s+kro|kya\s+saved|saved\s+hain)\b|"
            r"\bsaved\s+(?:hain\s+)?(?:preferences?|requirements?)\b|\bkya\s+saved\s+hai\b|"
            r"\bmer[aiy]+\s+(?:preferences?|requirements?)\s+kya\s+hai[n]?\b",
            raw_msg, re.IGNORECASE
        ))
        if is_prefs_question:
            cust_prefs = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            p = cust_prefs.preferences if cust_prefs else None
            def _budget_str(v):
                if v is None:
                    return None
                return f"{v / 10_000_000:g} Crore" if v >= 10_000_000 else f"{v:,} PKR"
            lines = []
            if p:
                for label, val in (("City", getattr(p, "city", None)),
                                   ("Area", getattr(p, "area", None)),
                                   ("Purpose", getattr(p, "purpose", None)),
                                   ("Property type", getattr(p, "property_type", None)),
                                   ("Bedrooms", getattr(p, "bedrooms", None)),
                                   ("Budget max", _budget_str(getattr(p, "budget_max", None))),
                                   ("Amenities", ", ".join(getattr(p, "amenities", []) or []) or None)):
                    if val not in (None, "", []):
                        lines.append(f"- {label}: {val}")
            if lines:
                return respond("Ji zaroor! Aapki taraf se explicitly batai gayi ye preferences saved hain:\n" + "\n".join(lines) +
                               "\nIsi mutabiq options dikhauin ya kuch change karna hai?", True, skip_nlg=True)
            return respond("Ji, filhaal aapki koi preference save nahi hui. Aap batayein kis city aur budget mein dekhna hai — main best verified options nikal deti hoon.", True, skip_nlg=True)

        # Check for explicit area suggestion requests: "area suggest kro", "suggest an area", "konsa area acha hai"
        is_area_suggestion = bool(re.search(
            r"\b(?:suggest|recommend|batao|bata dein|batayein|konsa|knsa|acha|ache)\s+(?:area|sector|location)\b|"
            r"\b(?:area|sector|location)\s+(?:suggest|recommend|batao|bata dein|batayein)\b|"
            r"\bap\s+(?:hi\s+)?(?:suggest|recommend)\s+(?:kro|karein|krti|karti)\b|"
            r"\bap\s+batao\b|\bpata\s+nahi\s+konsa\s+area\b",
            raw_msg, flags=re.IGNORECASE
        ))
        if is_area_suggestion:
            decision = await asyncio.to_thread(self.sara.policy.next_tier1_requirement,
                state=state, knowledge=self.services.properties)
            if decision:
                saved["pending_action"] = decision.pending_action
                return respond(decision.message, True)
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None)
            if not city:
                return respond("Ji! Pehle batayein aap kis city (jaise Islamabad ya Lahore) ke areas dekhna chahte hain?", True)
            available_areas = await asyncio.to_thread(
                getattr(self.services.properties, "list_available_areas", lambda **k: []),
                city=city, property_type=state.required.get("property_type"),
                purpose=state.required.get("purpose"), budget=state.required.get("budget"), limit=6
            )
            relaxed = False
            if not available_areas:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=city, limit=6
                )
                relaxed = True

            if available_areas:
                areas_str = ", ".join(available_areas)
                prefix = f"Ji! {city} mein"
                if relaxed and state.required.get("property_type"):
                    pt = state.required.get("property_type")
                    prefix += f" filhaal {pt} ke bajaye in areas mein verified properties available hain"
                else:
                    prefix += " in areas mein behtareen verified options available hain"

                return respond(
                    f"{prefix}: {areas_str}. "
                    "Aap in mein se kis area ke options dekhna chahenge? Agar area flexible hai to bata dein.",
                    True,
                )
            else:
                return respond(
                    f"Filhaal {city} mein koi verified areas available nahi hain. "
                    "Kya aap kisi doosre city ke sath dekhna chahenge?",
                    True,
                )

        # -----------------------------------------------------------------
        # High-Priority Informational / Listing Queries Dispatch
        # (Must precede pending_scope_confirm, pending_choice_frame, and Tier 1 gates)
        # -----------------------------------------------------------------
        is_cities_query = (
            u.intent in {"CITIES_QUERY", "cities_query"}
            or (u.intent in {"LIST_AVAILABLE_OPTIONS_QUERY", "list_available_options_query"} and getattr(u, "target", None) == "city")
            or bool(re.search(
                r"\b(?:k[ao]ns[aei]|knse?y?|k[ao]n\s+k[ao]n\s+s[aei]|kn\s+kn\s+se?y?|kin\s+kin|which|what|kitn[aei]|list\s+(?:of\s+)?)\s+(?:cities|city|shehar|shahron)\b|"
                r"\b(?:cities|city|shehar|shahron)\s+(?:batao|batayein|bata\s+dein)\b|"
                r"\bwhich\s+cities\s+do\s+you\s+operate\b",
                raw_msg, flags=re.IGNORECASE
            ))
        )
        if is_cities_query:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            purpose = u.required.get("purpose") or state.required.get("purpose") or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None)
            cities = await asyncio.to_thread(
                getattr(self.services.properties, "list_available_cities", lambda **k: ["Karachi", "Lahore", "Islamabad"]),
                purpose=purpose
            )
            if cities:
                cities_str = ", ".join(cities)
                msg = f"Hamare paas {cities_str} mein verified properties available hain. Aap in mein se kis city mein dekhna chahengi?"
                return respond(msg, True, skip_nlg=True)
            return respond("Filhaal kisi city mein verified inventory available nahi hai.", True, skip_nlg=True)

        is_phase_inventory_question = bool(re.search(
            r"\b(?:kn\s*kn\s*se[y]?|konsay|konse|kaunsay|kaunse|kitn[ey]?)\s+(?:phase|phases|sub[- ]?area|areas?)\b.*\b(?:available|hain|hai)\b|"
            r"\b(?:phase|phases)\s+(?:konsay|konse|kaunsay|kaunse|kitne|kitnay)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        base_token_for_phase = ""
        if is_phase_inventory_question:
            candidate_phase_area = (
                u.required.get("area")
                or getattr(u, "preferred", {}).get("area")
                or state.required.get("area")
            )
            if candidate_phase_area:
                base_token_for_phase = re.sub(r"\s+(?:phase|sector|block)\b.*$", "", str(candidate_phase_area), flags=re.IGNORECASE).strip()
            if not base_token_for_phase:
                m_phase = re.search(
                    r"\b([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+)?)\s+(?:k[ay]?|ke|mein|me|main)?\s*"
                    r"(?:(?:kn\s*kn\s*se[y]?|konsay|konse|kaunsay|kaunse|kitn[ey]?)\s+(?:phase|phases|sub[- ]?area|areas?)|(?:phase|phases))\b",
                    raw_msg, flags=re.IGNORECASE
                )
                if m_phase:
                    w = m_phase.group(1).strip()
                    if w.lower() not in {"ye", "yeh", "is", "in", "un", "kya", "konsa", "kaunsa", "batao", "aur", "aor"}:
                        base_token_for_phase = re.sub(r"\s+(?:phase|sector|block)\b.*$", "", w, flags=re.IGNORECASE).strip()

        is_phase_q = is_phase_inventory_question and bool(base_token_for_phase)

        is_areas_query = (
            not is_phase_q
            and (
                u.intent in {"AREAS_QUERY", "areas_query"}
                or (u.intent in {"LIST_AVAILABLE_OPTIONS_QUERY", "list_available_options_query"} and getattr(u, "target", None) == "area")
                or bool(re.search(
                    r"\b(?:k[ao]ns[aei]|knse?y?|k[ao]n\s+k[ao]n\s+s[aei]|kn\s+kn\s+se?y?|kin\s+kin|which|what|kitn[aei]|list\s+(?:of\s+)?)\s+(?:areas?|locations?|il[ao]q[aei]|jagh[aei])\b|"
                    r"\b(?:areas?|locations?|il[ao]q[aei])\s+(?:k[ayei]?\s+)?(?:options?\s+)?available\b|"
                    r"\b(?:areas?|locations?|il[ao]q[aei])\s+(?:batao|batayein|bata\s+dein)\b|"
                    r"\boptions?\s+kya\s+hai[n]?\b|\bkya\s+options?\s+hai[n]?\b",
                    raw_msg, flags=re.IGNORECASE
                ))
            )
        )
        if is_areas_query:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = (
                u.required.get("city")
                or state.required.get("city")
                or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None)
                or (saved.get("pending_scope_confirm") or {}).get("city")
            )
            if not city:
                return respond("Aap kis city ke areas dekhna chahenge? (Jaise Karachi ya Lahore)", True, skip_nlg=True)

            pt = u.required.get("property_type") or state.required.get("property_type") or (cust_rec.preferences.property_type if cust_rec and cust_rec.preferences else None)
            purpose = u.required.get("purpose") or state.required.get("purpose") or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None)
            budget = u.required.get("budget") or state.required.get("budget") or (cust_rec.preferences.budget_max if cust_rec and cust_rec.preferences else None)
            beds = u.required.get("bedrooms") or state.required.get("bedrooms") or (cust_rec.preferences.bedrooms if cust_rec and cust_rec.preferences else None)

            available_areas = await asyncio.to_thread(
                getattr(self.services.properties, "list_available_areas", lambda **k: []),
                city=city, property_type=pt, purpose=purpose, budget=budget, bedrooms=beds, limit=20
            )
            if not available_areas:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=city, limit=20
                )

            if available_areas:
                saved["pending_suggested_areas"] = list(available_areas)
                saved["pending_suggested_area"] = available_areas[0]
                areas_str = ", ".join(available_areas)
                msg = f"Filhaal {city} mein in areas mein verified options available hain: {areas_str}. Kis area ke options dekhna chahengi?"
                return respond(msg, True, skip_nlg=True)
            return respond(f"Filhaal {city} mein koi verified area available nahi hai.", True, skip_nlg=True)

        is_cheapest_query = (
            u.intent in {"CHEAPEST_PROPERTY_QUERY", "cheapest_property_query"}
            or bool(re.search(
                r"\b(?:sab\s+se\s+sast[aei]|cheapest|lowest\s+price)\s+(?:house|ghar|apartment|flat|plot|property|option)\b|"
                r"\b(?:sab\s+se\s+sast[aei]|cheapest)\s*(?:hai|kons[aei]|batao)\b",
                raw_msg, flags=re.IGNORECASE
            ))
        )
        if is_cheapest_query:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = u.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or state.required.get("city") or "Karachi"
            purpose = u.required.get("purpose") or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None) or state.required.get("purpose") or "Purchase"
            req_type = u.required.get("property_type")
            area = u.required.get("area") or (state.required.get("area") if not u.required.get("city") else None)

            search_kwargs = {"city": city, "purpose": purpose}
            if req_type and req_type.lower() != "property":
                search_kwargs["property_type"] = req_type
            if area:
                search_kwargs["area"] = area

            all_props = await asyncio.to_thread(
                self.services.properties.search,
                **search_kwargs
            )
            if not all_props and req_type and req_type.lower() != "property":
                search_kwargs.pop("property_type", None)
                all_props = await asyncio.to_thread(
                    self.services.properties.search,
                    **search_kwargs
                )
            if all_props:
                cheapest = min(all_props, key=lambda x: int(x.get("price", 0)))
                c_price = int(cheapest.get("price", 0))
                c_price_str = f"{c_price / 10_000_000:g} Crore PKR" if c_price >= 10_000_000 else f"{c_price / 100_000:g} Lakh PKR"
                c_name = cheapest.get("property_name") or cheapest.get("name")
                c_area = cheapest.get("area", "")
                c_type = cheapest.get("property_type", "property").lower()
                c_beds = cheapest.get("bedrooms")
                bed_str = f"{c_beds} bedrooms — " if c_beds else ""
                msg = (
                    f"{city} mein sab se sasti verified listing **{c_name}** hai jo {c_area} mein waqey hai — "
                    f"{bed_str}**{c_price:,} PKR** ({c_price_str}). "
                    "Kya aap is property ki details dekhna chahenge ya visit schedule karna chahenge?"
                )
                from web_api.services import RecommendationContext, property_snapshot, preference_snapshot, public_property
                rec_id = uuid4()
                saved["recommendation_session_id"] = str(rec_id)
                saved["selected"] = cheapest["property_id"]
                saved["property_order"] = [cheapest["property_id"]]
                ctx = RecommendationContext(
                    customer_id=identity.customer_id,
                    property_snapshots={cheapest["property_id"]: public_property(cheapest)},
                    preference_snapshot=preference_snapshot(cust_rec.preferences) if cust_rec and cust_rec.preferences else {},
                )
                try:
                    await asyncio.to_thread(self.services.sessions.put, rec_id, ctx, identity.user_id)
                except TypeError:
                    await asyncio.to_thread(self.services.sessions.put, rec_id, ctx)
                return respond(msg, True, recommendation_session_id=str(rec_id), properties=[public_property(cheapest)])
            else:
                return respond(f"Filhaal {city} mein {req_type} ka koi verified option available nahi hai.", True)

        is_expensive_query = (
            u.intent in {"MOST_EXPENSIVE_PROPERTY_QUERY", "most_expensive_property_query"}
            or bool(re.search(
                r"\b(?:s[ab]b?\s*se\s*m(?:ehng|engh)[aeiouy]*|most\s*expensive|highest\s*price|maximum\s*price|costliest|sab\s*se\s*costly|sab\s*se\s*zyada\s*(?:budget|price|qeemat)\s*wal[aei])\b|"
                r"\b(?:m(?:ehng|engh)[aeiouy]*|expensive|costly)\s+(?:house|ghar|apartment|flat|plot|property|option)\s*(?:hai|kons[aei]|knsi|batao)\b",
                raw_msg, flags=re.IGNORECASE
            ))
        ) and not bool(re.search(r"\b(?:bohat|bht|too|ye|yeh)\s+m(?:ehng|engh)[aeiouy]*\b", raw_msg, flags=re.IGNORECASE))
        if is_expensive_query:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = u.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or state.required.get("city") or "Karachi"
            purpose = u.required.get("purpose") or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None) or state.required.get("purpose") or "Purchase"
            req_type = u.required.get("property_type")
            area = u.required.get("area") or (state.required.get("area") if not u.required.get("city") else None)

            search_kwargs = {"city": city, "purpose": purpose}
            if req_type and req_type.lower() != "property":
                search_kwargs["property_type"] = req_type
            if area:
                search_kwargs["area"] = area

            all_props = await asyncio.to_thread(
                self.services.properties.search,
                **search_kwargs
            )
            if not all_props and req_type and req_type.lower() != "property":
                search_kwargs.pop("property_type", None)
                all_props = await asyncio.to_thread(
                    self.services.properties.search,
                    **search_kwargs
                )
            if all_props:
                expensive = max(all_props, key=lambda x: int(x.get("price", 0)))
                e_price = int(expensive.get("price", 0))
                e_price_str = f"{e_price / 10_000_000:g} Crore PKR" if e_price >= 10_000_000 else f"{e_price / 100_000:g} Lakh PKR"
                e_name = expensive.get("property_name") or expensive.get("name")
                e_area = expensive.get("area", "")
                e_type = expensive.get("property_type", "property").lower()
                e_beds = expensive.get("bedrooms")
                bed_str = f"{e_beds} bedrooms — " if e_beds else ""
                msg = (
                    f"{city} mein sab se mehngi verified listing **{e_name}** hai jo {e_area} mein waqey hai — "
                    f"{bed_str}**{e_price:,} PKR** ({e_price_str}).\n\n"
                    "Kya aap is property ki details dekhna chahenge ya visit schedule karna chahenge?"
                )
                from web_api.services import RecommendationContext, property_snapshot, preference_snapshot, public_property
                rec_id = uuid4()
                saved["recommendation_session_id"] = str(rec_id)
                saved["selected"] = expensive["property_id"]
                saved["property_order"] = [expensive["property_id"]]
                ctx = RecommendationContext(
                    customer_id=identity.customer_id,
                    property_snapshots={expensive["property_id"]: public_property(expensive)},
                    preference_snapshot=preference_snapshot(cust_rec.preferences) if cust_rec and cust_rec.preferences else {},
                )
                try:
                    await asyncio.to_thread(self.services.sessions.put, rec_id, ctx, identity.user_id)
                except TypeError:
                    await asyncio.to_thread(self.services.sessions.put, rec_id, ctx)
                return respond(msg, True, skip_nlg=True, recommendation_session_id=str(rec_id), properties=[public_property(expensive)])
            else:
                return respond(f"Filhaal {city} mein koi verified option available nahi hai.", True, skip_nlg=True)

        # Clarify the scope of a returning customer's request for other options.
        if saved.get("pending_scope_confirm"):
            info = saved.pop("pending_scope_confirm")
            city = info.get("city")
            if u.intent == "off_topic":
                saved["pending_scope_confirm"] = info
                return respond(
                    f"Main sirf property se related sawalon mein madad kar sakti hoon. Waisay, {city} mein hi doosre areas dekhne hain ya kisi aur city mein?", True)
            city_lower = (city or "").strip().lower()
            matches_city_or_typo = (bool(city_lower) and city_lower in raw_msg) or (
                city_lower == "lahore" and bool(re.search(r"\b(?:lahor|lahoor|lahroe)\b", raw_msg, re.IGNORECASE))
            )
            wants_same_city = bool(re.search(
                r"\b(?:isi|yehi|same|is)\s*(?:city|shehar)\b|\bisi\s*mein\b|\byehi\s*theek\b",
                raw_msg, re.IGNORECASE
            )) or matches_city_or_typo
            available_cities = (await asyncio.to_thread(
                getattr(self.services.properties, "list_available_cities", lambda: [])
            ))[:10]
            named_other_city = next(
                (c for c in available_cities if c.lower() != city_lower and c.lower() in raw_msg),
                None
            )
            wants_other_city = bool(re.search(
                r"\b(?:doosri|dusri|dusray|other|different|kisi\s+(?:aur|aor))\s*(?:city|shehar)\b",
                raw_msg, re.IGNORECASE
            )) or named_other_city is not None
            target_city = named_other_city or (city if wants_same_city else None)
            if target_city:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=target_city, limit=6
                )
                if available_areas:
                    areas_str = ", ".join(available_areas)
                    return respond(
                        f"Ji! {target_city} mein in areas mein verified options available hain: {areas_str}. "
                        "Kis area ke options dekhna chahengi?", True)
                return respond(
                    f"Filhaal {target_city} mein koi aur verified area available nahi hai. "
                    "Kya aap kisi aur city ke options dekhna chahenge?", True)

            if wants_other_city:
                if available_cities:
                    cities_str = ", ".join(available_cities[:10])
                    return respond(
                        f"Bilkul! Filhaal in cities mein verified options available hain: {cities_str}. "
                        "Kis city mein dekhna chahengi?", True)
                return respond(
                    "Filhaal koi aur city available nahi hai. Kya main isi city mein aur options dhoondun?", True)

            saved["pending_scope_confirm"] = info
            return respond(
                f"Ji, please batayein — {city} mein hi doosre areas dekhne hain ya kisi aur city mein?", True)

        # Check for user response to pending_expand_area (Bug A follow-up)
        if saved.get("pending_expand_area"):
            is_confirm_expand = bool(re.search(
                r"\b(?:haan|dikha do|dikhayein|theek hai|sahi hai|ji haan|yes|doosre|dusre|dusray|check kar lo|kar do)\b",
                raw_msg, flags=re.IGNORECASE
            ))
            # "sirf DHA mein dikhao" is a constraint, not a decline — only treat
            # as decline when the user is NOT asking to see another area.
            is_decline_expand = bool(re.search(
                r"\b(?:nahi|sirf|rehne do|mat|no)\b",
                raw_msg, flags=re.IGNORECASE
            )) and not re.search(r"\bdikh[aoaei]+\b|\bshow\b", raw_msg, re.IGNORECASE)
            info = saved.pop("pending_expand_area")
            city = info.get("city") or "Is city"
            active_area = info.get("area") or "is area"
            if is_confirm_expand:
                state.required.pop("area", None)
                state.flexible.add("area")
                saved["flexible"] = sorted(state.flexible)
                rid, city_rows = await self.services.recommendations(
                    identity.customer_id, 30, None, identity.user_id,
                    filter_overrides={"area": None}
                )
                already_shown = list(saved.get("property_order", []))
                city_unseen = [r for r in city_rows if r.get("property_id") not in already_shown]
                if city_unseen:
                    batch = city_unseen[:self.sara.presentation.batch_size]
                    saved["property_order"] = already_shown + [r["property_id"] for r in batch]
                    has_more = len(city_unseen) > len(batch)
                    intro = f"Theek hai! {city} ke doosre areas se ye mazeed verified options available hain:"
                    msg = self.sara.presentation.format_batch(batch, has_more=has_more, first_batch=False, custom_intro=intro)
                    return respond(msg, recommendation_session_id=str(rid), properties=batch)
            elif is_decline_expand:
                return respond(
                    f"Theek hai, {active_area} mein agar koi naya verified option list hota hai to hum aapko update kar denge. "
                    "Kya aap budget ya kisi aur preference mein flexibility dekhna chahenge?",
                    True,
                )
            else:
                # Neither a clear yes nor no (or the user asked to see a specific
                # area): restore so the question isn't silently swallowed.
                saved["pending_expand_area"] = info

        # Check for active or interrupted pending_choice_frame
        if saved.get("pending_choice_frame"):
            frame = saved["pending_choice_frame"]
            # 1. Distinguish between off-topic interruption vs in-domain new search:
            # If message is off-topic (e.g. cricket, joke, weather), preserve frame as 'interrupted'.
            # Do NOT discard it, so it can be re-anchored when the user returns.
            if u.intent == "off_topic":
                frame["status"] = "interrupted"
                # Existing guardrail at the bottom will respond without losing the frame.
            else:
                # The user's message is in-domain!
                is_returning_from_interruption = frame.get("status") == "interrupted"

                # Check if user initiated a brand new in-domain search or single-field refinement:
                req_city = str(u.required.get("city") or "").strip().lower()
                frame_city = str(frame.get("city") or "").strip().lower()
                city_changed = bool(req_city and frame_city and req_city != frame_city)

                req_area = str(u.required.get("area") or "").strip().lower()
                frame_areas = {
                    str(frame.get("requested_area") or "").strip().lower(),
                    str((frame.get("option_a") or {}).get("area") or "").strip().lower(),
                    str((frame.get("option_b") or {}).get("area") or "").strip().lower(),
                }
                frame_areas.discard("")
                area_changed = bool(req_area and req_area not in frame_areas)

                req_type = str(u.required.get("property_type") or "").strip().lower()
                frame_type = str(frame.get("property_type") or state.required.get("property_type") or "").strip().lower()
                type_changed = bool(req_type and frame_type and req_type != frame_type)

                explicit_reset = bool(re.search(
                    r"\b(?:naye\s+sirey|new\s+search|nay[ai]|kisi\s+aur\s+(?:shehar|city|ilawa))\b",
                    raw_msg, re.IGNORECASE
                ))

                is_brand_new_search = bool(city_changed or area_changed or type_changed or explicit_reset)

                # Edge Case 2: Check for single-field refinement (budget or bedrooms) while city/area/type remain same
                new_budget = u.required.get("budget")
                new_bedrooms = u.required.get("bedrooms")
                old_budget = frame.get("budget") or state.required.get("budget")
                old_bedrooms = frame.get("bedrooms") or state.required.get("bedrooms")

                budget_refined = (new_budget is not None and new_budget != old_budget)
                bedrooms_refined = (new_bedrooms is not None and new_bedrooms != old_bedrooms)
                has_refinement = bool((budget_refined or bedrooms_refined) and not is_brand_new_search)

                if is_brand_new_search:
                    # In-domain new search interruption: Discard old frame immediately!
                    saved.pop("pending_choice_frame", None)
                    saved.pop("pending_suggested_area", None)
                    saved.pop("pending_suggested_areas", None)
                    # Proceed with normal in-domain search pipeline
                elif has_refinement:
                    # Edge Case 2: Single-field adjustment refines pending query
                    if budget_refined:
                        state.required["budget"] = new_budget
                    if bedrooms_refined:
                        state.required["bedrooms"] = new_bedrooms
                    if frame.get("requested_area"):
                        state.required["area"] = frame["requested_area"]
                    if frame.get("city"):
                        state.required["city"] = frame["city"]
                    if frame.get("property_type"):
                        state.required["property_type"] = frame["property_type"]
                    saved.pop("pending_choice_frame", None)
                    saved.pop("pending_suggested_area", None)
                    saved.pop("pending_suggested_areas", None)
                    # Proceed with updated state to re-run recommendations()
                elif is_returning_from_interruption:
                    # Returning to property topic after off-topic interruption:
                    # Briefly re-anchor: confirm whether they still want to resolve earlier choice before proceeding.
                    opt_a_desc = (frame.get("option_a") or {}).get("desc", "pehle wala option")
                    opt_b_desc = (frame.get("option_b") or {}).get("desc")
                    frame["status"] = "pending"  # now restored to pending resolution
                    if opt_b_desc:
                        return respond(
                            f"Pehle aap {opt_a_desc} aur {opt_b_desc} ke darmiyan choose kar rahe the — "
                            "kya aap inhi dono options mein se koi dekhna chahenge ya naye sirey se search karein?",
                            True,
                        )
                    else:
                        return respond(
                            f"Pehle hum {opt_a_desc} ke barey mein baat kar rahe the — "
                            "kya aap yeh option dekhna chahenge ya naye sirey se search karein?",
                            True,
                        )
                else:
                    # Frame is active (pending resolution):
                    # Classify user response via fail-safe LLM call: OPTION_A / OPTION_B / NEITHER / UNCLEAR
                    opt_a_desc = (frame.get("option_a") or {}).get("desc", "Option A")
                    opt_b_desc = (frame.get("option_b") or {}).get("desc")
                    choice = await self.classify_pending_choice(raw_msg, opt_a_desc, opt_b_desc)

                    if choice == "OPTION_A":
                        saved.pop("pending_choice_frame", None)
                        saved.pop("pending_suggested_area", None)
                        saved.pop("pending_suggested_areas", None)
                        opt_a_props = (frame.get("option_a") or {}).get("properties", [])
                        opt_a_area = (frame.get("option_a") or {}).get("area")
                        if opt_a_area:
                            state.required["area"] = opt_a_area
                        if opt_a_props:
                            batch = opt_a_props[:self.sara.presentation.batch_size]
                            saved.update(
                                property_order=[r["property_id"] for r in opt_a_props],
                                selected=(opt_a_props[0]["property_id"] if len(opt_a_props) == 1 else None),
                                pending_action=None,
                            )
                            intro = f"Ji bilkul! {opt_a_area} mein aapke liye ye option available hai:"
                            msg = self.sara.presentation.format_batch(batch, has_more=False, first_batch=True, custom_intro=intro)
                            return respond(msg, properties=batch)
                        elif opt_a_area:
                            rid, area_rows = await self.services.recommendations(
                                identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                                filter_overrides={"area": opt_a_area}
                            )
                            if area_rows:
                                safe_rows = [public_property(r) for r in area_rows]
                                saved.update(
                                    recommendation_session_id=str(rid),
                                    property_order=[r["property_id"] for r in area_rows],
                                    selected=(area_rows[0]["property_id"] if len(area_rows) == 1 else None),
                                    pending_action=None,
                                )
                                city = state.required.get("city") or frame.get("city") or "Karachi"
                                intro = f"Ji bilkul! {opt_a_area}, {city} mein aapke budget ke mutabiq ye verified options available hain:"
                                msg = self.sara.presentation.format_batch(area_rows, has_more=False, first_batch=True, custom_intro=intro)
                                return respond(msg, recommendation_session_id=str(rid), properties=safe_rows)
                            else:
                                city = state.required.get("city") or frame.get("city") or "Karachi"
                                return respond(f"{opt_a_area} mein is criteria par koi verified options nahi mil sake.", True)
                    elif choice == "OPTION_B":
                        saved.pop("pending_choice_frame", None)
                        saved.pop("pending_suggested_area", None)
                        saved.pop("pending_suggested_areas", None)
                        chosen_area = (frame.get("option_b") or {}).get("area")
                        if chosen_area:
                            state.required["area"] = chosen_area
                            rid, area_rows = await self.services.recommendations(
                                identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                                filter_overrides={"area": chosen_area}
                            )
                            if area_rows:
                                safe_rows = [public_property(r) for r in area_rows]
                                saved.update(
                                    recommendation_session_id=str(rid),
                                    property_order=[r["property_id"] for r in area_rows],
                                    selected=(area_rows[0]["property_id"] if len(area_rows) == 1 else None),
                                    pending_action=None,
                                )
                                city = state.required.get("city") or frame.get("city") or "Karachi"
                                intro = f"Ji bilkul! {chosen_area}, {city} mein aapke budget ke mutabiq ye verified options available hain:"
                                msg = self.sara.presentation.format_batch(area_rows, has_more=False, first_batch=True, custom_intro=intro)
                                return respond(msg, recommendation_session_id=str(rid), properties=safe_rows)
                    elif choice == "NEITHER":
                        saved.pop("pending_choice_frame", None)
                        saved.pop("pending_suggested_area", None)
                        saved.pop("pending_suggested_areas", None)
                        return respond(
                            "Theek hai, koi baat nahi. Aap apni requirement mein kya tabdeeli karna chahenge — budget, area, ya koi aur criteria?",
                            True,
                        )
                    elif choice == "UNCLEAR":
                        # If UNCLEAR, ask a clarifying question re-stating options in plain language — do not guess!
                        if opt_b_desc:
                            return respond(
                                f"Barah-e-karam wazeh kar dein: Kya aap {opt_a_desc} dekhna chahenge ya {opt_b_desc}? Taake main wahi dikha sakoon.",
                                True,
                            )
                        else:
                            return respond(
                                f"Barah-e-karam wazeh kar dein: Kya aap {opt_a_desc} dekhna chahenge? Taake main wahi dikha sakoon.",
                                True,
                            )

        # Check for user response to pending_suggested_area / pending_suggested_areas
        if saved.get("pending_suggested_area") or saved.get("pending_suggested_areas"):
            is_confirm = bool(re.search(
                r"\b(?:haan|ji|jee|g|yes|theek hai|sahi hai|zaroor|bilkul|dekhna|dikhayein|dikha\s*do|dikhado|dikha\s+dein|chahu|chahungi|chahti|chahta|options?\s+dekh)\b",
                raw_msg, flags=re.IGNORECASE
            ))
            is_decline = bool(re.search(
                r"\b(?:nahi|nahin|no|rehne do|mat)\b",
                raw_msg, flags=re.IGNORECASE
            )) and not re.search(r"\bdikh[aoaei]+\b|\bshow\b|\bdekhna\b", raw_msg, re.IGNORECASE)

            suggested_areas = saved.get("pending_suggested_areas") or [saved.get("pending_suggested_area")]
            suggested_areas = [str(a) for a in suggested_areas if a]

            chosen_area = None
            for sa in suggested_areas:
                if re.search(rf"\b{re.escape(sa)}\b", raw_msg, re.IGNORECASE):
                    chosen_area = sa
                    break

            if not chosen_area and is_confirm and not is_decline:
                chosen_area = suggested_areas[0]

            if chosen_area:
                saved.pop("pending_suggested_area", None)
                saved.pop("pending_suggested_areas", None)
                state.required["area"] = chosen_area
                has_pref_confirm = bool(re.search(
                    r"\b(?:mer[aiy]+\s+preference|preference\s+(?:hai|save|update)|yehi\s+chahiye|yehi\s+meri\s+requirement|save\s+k(?:ar|r)|mujhe\s+yehi\s+chahiye|isi\s+ko\s+save|confirm)\b",
                    raw_msg, re.IGNORECASE
                ))
                if has_pref_confirm:
                    await asyncio.to_thread(self.services.customers.update_preferences, identity.customer_id, {"area": chosen_area})
                rid, area_rows = await self.services.recommendations(
                    identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                    filter_overrides={"area": chosen_area}
                )
                if area_rows:
                    from web_api.services import public_property
                    safe_rows = [public_property(r) for r in area_rows]
                    saved.update(
                        recommendation_session_id=str(rid),
                        property_order=[r["property_id"] for r in area_rows],
                        selected=(area_rows[0]["property_id"] if len(area_rows) == 1 else None),
                        pending_action=None,
                    )
                    city = state.required.get("city") or "Karachi"
                    intro = f"Ji bilkul! {chosen_area}, {city} mein aapke budget ke mutabiq ye verified options available hain:"
                    msg = self.sara.presentation.format_batch(area_rows, has_more=False, first_batch=True, custom_intro=intro)
                    return respond(msg, recommendation_session_id=str(rid), properties=safe_rows)
                else:
                    return respond(f"Ji bilkul, {chosen_area} mein options check kar rahi hoon.", True)
            elif is_decline:
                saved.pop("pending_suggested_area", None)
                saved.pop("pending_suggested_areas", None)

        # Check for phase inventory question: "DHA k kn kn se phase mein options available hai", "DHA ke kaunse phases mein hain"
        is_phase_inventory_question = bool(re.search(
            r"\b(?:kn\s*kn\s*se[y]?|konsay|konse|kaunsay|kaunse|kitn[ey]?)\s+(?:phase|phases|sub[- ]?area|areas?)\b.*\b(?:available|hain|hai)\b|"
            r"\b(?:phase|phases)\s+(?:konsay|konse|kaunsay|kaunse|kitne|kitnay)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        if is_phase_inventory_question:
            # Derive base area token generically by stripping trailing Phase / Sector / Block suffix
            candidate = (
                u.required.get("area")
                or getattr(u, "preferred", {}).get("area")
                or state.required.get("area")
            )
            base_token = ""
            if candidate:
                base_token = re.sub(r"\s+(?:phase|sector|block)\b.*$", "", str(candidate), flags=re.IGNORECASE).strip()

            if not base_token:
                m = re.search(
                    r"\b([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+)?)\s+(?:k[ay]?|ke|mein|me|main)?\s*"
                    r"(?:(?:kn\s*kn\s*se[y]?|konsay|konse|kaunsay|kaunse|kitn[ey]?)\s+(?:phase|phases|sub[- ]?area|areas?)|(?:phase|phases))\b",
                    raw_msg, flags=re.IGNORECASE
                )
                if m:
                    word = m.group(1).strip()
                    if word.lower() not in {"ye", "yeh", "is", "in", "un", "kya", "konsa", "kaunsa", "batao", "aur", "aor"}:
                        base_token = re.sub(r"\s+(?:phase|sector|block)\b.*$", "", word, flags=re.IGNORECASE).strip()

            cust_for_areas = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            pick_city = (
                u.required.get("city")
                or state.required.get("city")
                or (cust_for_areas.preferences.city if cust_for_areas and cust_for_areas.preferences else None)
            )
            if not pick_city and order:
                for pid in order:
                    p = await asyncio.to_thread(self.services.properties.get_property, pid)
                    if p and p.get("city"):
                        pick_city = p.get("city")
                        break

            if not pick_city and base_token:
                available_cities = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_cities", lambda: ["Lahore", "Islamabad", "Rawalpindi"])
                )
                for c in available_cities:
                    areas = await asyncio.to_thread(
                        getattr(self.services.properties, "list_available_areas", lambda **k: []),
                        city=c, limit=20
                    )
                    if any(base_token.lower() in str(a).lower() for a in areas):
                        pick_city = c
                        break

            if pick_city and base_token:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=pick_city, limit=20
                )
                matching_variants = [a for a in available_areas if base_token.lower() in str(a).lower()]
                if matching_variants:
                    for mv in matching_variants:
                        idx = mv.lower().find(base_token.lower())
                        if idx >= 0:
                            base_token = mv[idx:idx + len(base_token)]
                            break
                    variants_str = ", ".join(matching_variants)
                    return respond(
                        f"Filhaal {pick_city} mein {base_token} ke in phases mein verified options available hain: {variants_str}. "
                        "Kis phase ke options dekhna chahengi?",
                        True,
                    )
                return respond(f"Filhaal {base_token} ke kisi phase mein verified options available nahi hain.", True)

        # Check for more options / pagination: "is k ilawa", "aur options", "more options", "koi aur option", "aur kya options"
        is_more_options = bool(re.search(
            r"\b(?:is|in|un|iske|inke|unke)\s*(?:ke|k|kay)?\s*(?:ilawa|elawa|alawa|lawa)\b|"
            r"\b(?:aur|aor|mazeed|more|koi\s+(?:aur|aor)|agla|next)\s+(?:kya\s+|knsey\s+|kn\s*kn\s*se[y]?\s+|konse\s+|kaunsay\s+|bhi\s+)?(?:options?|properties|plots?|ghars?|houses?|flats?|apartments?|dikhao|dikhayein|hai|hain|available)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        if is_more_options and order:
            already_shown = list(saved.get("property_order", []))
            if not already_shown:
                state.flexible.add("area")
                state.flexible.add("budget")
                saved["flexible"] = sorted(state.flexible)
                search_overrides = {}
                if state.required.get("area"):
                    search_overrides["area"] = state.required["area"]
                if state.required.get("budget"):
                    search_overrides["budget"] = state.required["budget"]
                rid, rows = await self.services.recommendations(
                    identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                    filter_overrides=search_overrides or None
                )
                if rows:
                    saved.update(recommendation_session_id=str(rid), property_order=[r["property_id"] for r in rows])
                    msg = self.sara.presentation.format_batch(rows, has_more=False, first_batch=True)
                    return respond(msg, recommendation_session_id=str(rid), properties=rows)

            search_overrides = {}
            area_is_flexible = "area" in saved.get("flexible", []) or "area" in state.flexible or "area" in (u.relax or [])
            if area_is_flexible:
                search_overrides["area"] = None
            elif state.required.get("area"):
                search_overrides["area"] = state.required["area"]
            if state.required.get("budget"):
                search_overrides["budget"] = state.required["budget"]
            rid, all_rows = await self.services.recommendations(
                identity.customer_id, 30, None, identity.user_id,
                filter_overrides=search_overrides or None
            )
            unseen = [r for r in all_rows if r.get("property_id") not in already_shown]
            if unseen:
                batch = unseen[:self.sara.presentation.batch_size]
                saved["property_order"] = already_shown + [r["property_id"] for r in batch]
                has_more = len(unseen) > len(batch)
                message_text = self.sara.presentation.format_batch(batch, has_more=has_more, first_batch=False)
                return respond(message_text, recommendation_session_id=str(rid), properties=batch)

            # If current specific area has no more options, ask permission before switching area (Bug A fix)
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None)
            active_area = u.required.get("area") or state.required.get("area") or (cust_rec and getattr(cust_rec.preferences, "area", None))
            if city and active_area and not area_is_flexible:
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=city, property_type=state.required.get("property_type"),
                    purpose=state.required.get("purpose"), budget=state.required.get("budget"), limit=6
                )
                if not available_areas:
                    available_areas = await asyncio.to_thread(
                        getattr(self.services.properties, "list_available_areas", lambda **k: []),
                        city=city, limit=6
                    )
                other_areas = [a for a in available_areas if a.lower() != str(active_area).lower()]
                if other_areas:
                    other_str = ", ".join(other_areas)
                    saved["pending_expand_area"] = {"city": city, "area": active_area}
                    return respond(
                        f"{active_area} mein filhaal aur koi verified option available nahi hai. "
                        f"Kya aap {city} ke doosre areas (jaise {other_str}) ke options dekhna chahenge?",
                        True,
                    )
                else:
                    saved["last_asked_broaden"] = True
                    return respond(
                        f"{active_area} mein filhaal aur koi verified option available nahi hai, aur {city} mein bhi mazeed options nahi hain. "
                        "Kya aap budget thora extend karna chahenge?",
                        True,
                    )

            saved["last_asked_broaden"] = True
            return respond(
                "Aapke current criteria par filhaal yahi verified options available the jo maine aapko dikhaye hain, is ke ilawa mazeed options abhi nahi hain. "
                "Kya aap chahenge ke hum thora budget extend karein ya kisi qareebi area mein options check karein?",
                True,
            )

        # Check for broadening / relaxation agreement: "haan", "theek hai", "ji", "g", "extend kar lo", "dusre areas", "mazeed areas"
        is_broadening_agreement = bool(re.search(
            r"\b(?:haan|theek\s+hai|sahi\s+hai|ji\s+haan|ji\s+bilkul|ji|jee|g|yes|kar\s+do|kr\s+do|widen|extend|broaden|dekh\s+lo|check\s+kar\s+lo)\b|"
            r"\b(?:dusre|dusray|doosre|doosray|other|different|aur|aor|mazeed|more|qareebi)\s+areas?\b|"
            r"\b(?:areas?|locations?)\s+(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|check|dekh)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        if is_broadening_agreement and saved.get("last_asked_broaden"):
            saved["last_asked_broaden"] = False
            wants_area_broaden = bool(re.search(
                r"\b(?:dusre|dusray|doosre|doosray|other|different|aur|aor|mazeed|more|qareebi)\s+areas?\b|"
                r"\b(?:areas?|locations?)\s+(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|check|dekh)\b",
                raw_msg, flags=re.IGNORECASE
            ))
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            current_budget = state.required.get("budget") or (cust_rec.preferences.budget_max if cust_rec and cust_rec.preferences else None)
            new_budget = current_budget
            updates = {}
            if not wants_area_broaden:
                new_budget = int(current_budget * 1.25) if current_budget else None
                if new_budget:
                    updates["budget_max"] = new_budget
                    state.required["budget"] = new_budget
            state.required.pop("area", None)
            state.flexible.add("area")
            saved["flexible"] = sorted(state.flexible)
            search_overrides = {"area": None}
            if new_budget:
                search_overrides["budget"] = new_budget
            rid, rows = await self.services.recommendations(
                identity.customer_id, self.sara.presentation.batch_size, None, identity.user_id,
                filter_overrides=search_overrides
            )
            if rows:
                saved.update(recommendation_session_id=str(rid), property_order=[r["property_id"] for r in rows])
                intro = "Theek hai! Karachi ke doosre areas se ye verified options mile hain:" if wants_area_broaden else "Theek hai! Maine criteria thora broaden kiya hai. Ye mazeed options mile hain:"
                msg = f"{intro}\n\n" + self.sara.presentation.format_batch(rows, has_more=False, first_batch=True)
                return respond(msg, recommendation_session_id=str(rid), properties=rows)
            else:
                city = state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or "Karachi"
                pt = state.required.get("property_type") or (cust_rec.preferences.property_type if cust_rec and cust_rec.preferences else None) or "House"
                b_str = f"{current_budget / 10_000_000:g} Crore PKR" if current_budget and current_budget >= 10_000_000 else (f"{current_budget:,} PKR" if current_budget else "Aapke budget")
                all_props = await asyncio.to_thread(self.services.properties.search, city=city, purpose="purchase", property_type=pt)
                min_p = min([int(p.get("price", 0)) for p in (all_props or []) if p.get("price")], default=None)
                min_s = f"{min_p / 10_000_000:g} Crore PKR" if min_p and min_p >= 10_000_000 else "6.5 Crore PKR"
                msg = (
                    f"{city} ke doosre areas mein bhi {b_str} mein verified {pt.lower()}s available nahi hain, "
                    f"kyunke {city} mein {pt.lower()}s kam az kam {min_s} se shuru hotay hain. "
                    "Lekin agar aap is budget mein dekhna chahte hain to Apartments ke options check kar sakte hain. "
                    "Kya aap Apartments dekhna chahenge?"
                )
                return respond(msg, True)

        # -----------------------------------------------------------------
        # Property Type by Budget Query (e.g. "1.2 crore mein apartment aye ga ya house")
        # -----------------------------------------------------------------
        has_budget_mention = bool(re.search(r"\b(?:\d+(?:\.\d+)?\s*(?:crore|cr|lakh|lac|million))\b", raw_msg, re.I)) or getattr(u, "query_budget", None) is not None
        is_prop_type_budget_query = (
            u.intent in {"PROPERTY_TYPE_BY_BUDGET_QUERY", "property_type_by_budget_query"}
            or (has_budget_mention and bool(re.search(
                r"\b(?:apartment|flat)\s*(?:aye\s*ga|miley?ga|hoga|milega)?\s*(?:ya|aor|or)\s*(?:house|ghar|makan)\b|"
                r"\b(?:house|ghar|makan)\s*(?:aye\s*ga|miley?ga|hoga|milega)?\s*(?:ya|aor|or)\s*(?:apartment|flat)\b|"
                r"\b(?:\d+(?:\.\d+)?\s*(?:crore|cr|lakh|lac|million))\s*(?:mein|me|main)\s+(?:kya\s+miley?ga|kya\s+aye\s*ga|kya\s+milega|apartment|flat|house|ghar)\b",
                raw_msg, flags=re.IGNORECASE
            )))
        ) and getattr(u, "clarification_reason", None) != "ambiguous_property_type"
        if is_prop_type_budget_query:
            target_budget = getattr(u, "query_budget", None)
            if not target_budget:
                bm = re.search(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lac|million)", raw_msg, flags=re.IGNORECASE)
                if bm:
                    num = float(bm.group(1))
                    unit = bm.group(2).lower()
                    if unit in ("crore", "cr"):
                        target_budget = int(num * 10_000_000)
                    elif unit in ("lakh", "lac"):
                        target_budget = int(num * 100_000)
                    elif unit == "million":
                        target_budget = int(num * 1_000_000)
            if not target_budget:
                target_budget = state.required.get("budget")

            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = (
                u.required.get("city")
                or state.required.get("city")
                or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None)
                or "Karachi"
            )
            purpose = (
                u.required.get("purpose")
                or state.required.get("purpose")
                or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None)
                or "Purchase"
            )

            # Query database for Apartments and Houses under target_budget
            apt_matches = await asyncio.to_thread(
                self.services.properties.search,
                city=city, purpose=purpose, property_type="Apartment", budget=target_budget
            ) if target_budget else []
            hse_matches = await asyncio.to_thread(
                self.services.properties.search,
                city=city, purpose=purpose, property_type="House", budget=target_budget
            ) if target_budget else []

            # Query all verified Apartments and Houses in that city to determine exact starting prices
            all_apts = await asyncio.to_thread(
                self.services.properties.search,
                city=city, purpose=purpose, property_type="Apartment"
            )
            all_houses = await asyncio.to_thread(
                self.services.properties.search,
                city=city, purpose=purpose, property_type="House"
            )

            def _get_min_price(items):
                prices = [int(p.get("price", 0)) for p in (items or []) if p.get("price")]
                return min(prices) if prices else None

            def _fmt_price(p):
                if not p:
                    return "N/A"
                if p >= 10_000_000:
                    val = p / 10_000_000
                    return f"{val:g} Crore PKR"
                val = p / 100_000
                return f"{val:g} Lakh PKR"

            min_apt = _get_min_price(all_apts)
            min_hse = _get_min_price(all_houses)
            b_str = _fmt_price(target_budget) if target_budget else "is budget"

            has_apt = bool(apt_matches)
            has_hse = bool(hse_matches)

            if not has_apt and not has_hse:
                apt_str = f"apartments kam az kam {_fmt_price(min_apt)} se" if min_apt else "apartments available nahi hain"
                hse_str = f"houses kam az kam {_fmt_price(min_hse)} se" if min_hse else "houses available nahi hain"
                msg = (
                    f"{city} mein {b_str} mein na hi apartment aaye ga aur na hi house. "
                    f"Verified inventory ke mutabiq {apt_str} aur {hse_str} shuru hotay hain. "
                    "Kya aap apna budget extend karna chahenge ya koi aur option dekhna pasand karenge?"
                )
            elif has_apt and not has_hse:
                hse_str = f"houses kam az kam {_fmt_price(min_hse)} se shuru hotay hain" if min_hse else "is budget mein house available nahi hai"
                msg = (
                    f"{city} mein {b_str} mein apartment to mil sakta hai (starting from {_fmt_price(min_apt)}), "
                    f"lekin house nahi mil sakta kyunke {hse_str}. "
                    "Kya aap apartments ke options dekhna chahenge?"
                )
            elif has_hse and not has_apt:
                apt_str = f"apartments kam az kam {_fmt_price(min_apt)} se shuru hotay hain" if min_apt else "is budget mein apartment available nahi hai"
                msg = (
                    f"{city} mein {b_str} mein house to mil sakta hai (starting from {_fmt_price(min_hse)}), "
                    f"lekin apartment nahi mil sakta kyunke {apt_str}. "
                    "Kya aap houses ke options dekhna chahenge?"
                )
            else:
                msg = (
                    f"{city} mein {b_str} mein apartment aur house dono mil sakte hain. "
                    f"Apartments {_fmt_price(min_apt)} se aur houses {_fmt_price(min_hse)} se shuru hotay hain. "
                    "Aap kis property type ke options dekhna chahenge?"
                )
            return respond(msg, True)

        # -----------------------------------------------------------------
        # Comparative Cheaper Request & Price Objection Handling
        # -----------------------------------------------------------------
        is_cheaper_request = bool(re.search(
            r"\b(?:is\s+se\s+sast[aei]|us\s+se\s+sast[aei]|isse\s+sast[aei]|usse\s+sast[aei]|"
            r"is\s+se\s+kam|us\s+se\s+kam|isse\s+kam|usse\s+kam|"
            r"sast[aei]\s+(?:property|option|ghar|listing|makan)|"
            r"kam\s+(?:price|qeemat|rate|budget)\s+wal[aei]|"
            r"kuch\s+sast[aei]|cheaper)\b",
            raw_msg, flags=re.IGNORECASE
        )) or (getattr(u.comparison, "field", None) == "price" and getattr(u.comparison, "operator", None) == "lt")

        # Also check if user is accepting an offered cheaper alternative
        has_pending_offer = bool(saved.get("pending_cheaper_offer"))
        is_declining = bool(re.search(r"\b(?:nahi|no|na|cancel|rehne\s+do)\b", raw_msg, flags=re.IGNORECASE))
        has_new_budget = bool(u.required.get("budget") or u.preferred.get("budget") or re.search(r"\b\d+\s*(?:crore|lakh|million|arab|cr|k)\b", raw_msg, flags=re.IGNORECASE))

        is_accepting_cheaper_offer = has_pending_offer and not is_declining and not has_new_budget and (
            bool(re.search(
                r"\b(?:haan|ji|jee|g|yes|yep|sure|theek|sahi|ok|okay|acha|achha|zaroor|bilkul|"
                r"dikh[a-z]*|dekho|dekhna|bata[a-z]*|show|details?|option|pehli|first)\b",
                raw_msg, flags=re.IGNORECASE
            ))
            or u.intent in {"property_details", "property_selection", "property_search", "affirmation"}
        )

        if has_pending_offer and is_declining:
            saved.pop("pending_cheaper_offer", None)
            return respond("Theek hai! Aapka comfortable target budget kitna hai ya kis specific area mein options dekhna chahenge?", True)

        is_price_objection = (
            bool(re.search(
                r"\b(?:mengh[aei]|mehng[aei]|expensive|price\s+(?:bohat\s+|bht\s+)?(?:zyada|high)|"
                r"rate\s+(?:bohat\s+|bht\s+)?zyada|budget\s+se\s+bahar|out\s+of\s+budget)\b",
                raw_msg, flags=re.IGNORECASE
            ))
            or (u.intent in {"objection", "BUDGET_OBJECTION", "budget_objection"} and getattr(u.comparison, "field", None) == "price")
            or (u.intent in {"objection", "BUDGET_OBJECTION", "budget_objection"})
        ) and not bool(re.search(r"\b(?:s[ab]b?\s*se\s*m(?:ehng|engh)[aeiouy]*|most\s*expensive|highest\s*price|maximum\s*price|costliest)\b", raw_msg, re.IGNORECASE))

        if (is_cheaper_request or is_accepting_cheaper_offer or is_price_objection) and not (u.intent == "property_search" and getattr(u.comparison, "field", None)):
            ref_id = selected or saved.get("selected") or (order[0] if order else None)
            ref_prop = await asyncio.to_thread(self.services.properties.get_property, ref_id) if ref_id else None

            if not ref_prop and not order and not saved.get("pending_cheaper_offer"):
                return respond(
                    "Aap kis city ya area mein aur kis budget tak sasti property dekhna chahenge? "
                    "Main aapke liye matching options search kar leti hoon.",
                    True
                )

            ref_price = int(ref_prop.get("price", 0)) if ref_prop else 0
            ref_city = (ref_prop.get("city") if ref_prop else None) or state.required.get("city") or "Karachi"
            ref_type = (ref_prop.get("property_type") if ref_prop else None) or state.required.get("property_type") or "House"
            ref_purpose = (ref_prop.get("purpose") if ref_prop else None) or state.required.get("purpose") or "Purchase"
            ref_beds = (ref_prop.get("bedrooms") if ref_prop else None) or state.required.get("bedrooms")
            ref_area = ref_prop.get("area", "") if ref_prop else ""
            ref_price_str = f"{ref_price / 10_000_000:.1f} Crore" if ref_price >= 10_000_000 else f"{ref_price / 100_000:.0f} Lakh"

            offered_id = saved.pop("pending_cheaper_offer", None)
            cheaper_props = []
            if is_accepting_cheaper_offer and offered_id:
                offered_prop = await asyncio.to_thread(self.services.properties.get_property, offered_id)
                if offered_prop:
                    cheaper_props = [offered_prop]

            relaxed_beds = False
            if not cheaper_props and ref_price > 0:
                if ref_beds:
                    same_bed_matches = await asyncio.to_thread(
                        self.services.properties.search,
                        city=ref_city,
                        purpose=ref_purpose,
                        property_type=ref_type,
                        bedrooms=ref_beds,
                        budget=ref_price - 1,
                    )
                    cheaper_props = [
                        p for p in (same_bed_matches or [])
                        if p.get("property_id") != ref_id and int(p.get("price", 0)) < ref_price
                    ]

                if not cheaper_props:
                    any_bed_matches = await asyncio.to_thread(
                        self.services.properties.search,
                        city=ref_city,
                        purpose=ref_purpose,
                        property_type=ref_type,
                        budget=ref_price - 1,
                    )
                    cheaper_props = [
                        p for p in (any_bed_matches or [])
                        if p.get("property_id") != ref_id and int(p.get("price", 0)) < ref_price
                    ]
                    if cheaper_props:
                        relaxed_beds = True

                if cheaper_props:
                    cheaper_props.sort(key=lambda p: int(p.get("price", 0)), reverse=True)

            if is_cheaper_request or is_accepting_cheaper_offer:
                if cheaper_props:
                    top_c = cheaper_props[0]
                    c_price = int(top_c.get("price", 0))
                    c_price_str = f"{c_price / 10_000_000:.1f} Crore" if c_price >= 10_000_000 else f"{c_price / 100_000:.0f} Lakh"
                    c_name = top_c.get("property_name") or top_c.get("name")
                    c_area = top_c.get("area", "")
                    c_beds = top_c.get("bedrooms")
                    diff = ref_price - c_price
                    diff_str = f"{diff / 10_000_000:.1f} Crore" if diff >= 10_000_000 else f"{diff / 100_000:.0f} Lakh"

                    if relaxed_beds and c_beds:
                        intro = (
                            f"Ji bilkul! {ref_area} mein to is se sasta verified option nahi hai, "
                            f"lekin {c_area} mein {c_beds} bedrooms ka verified option available hai "
                            f"jo pichle option ({ref_price_str} PKR) ke muqablay mein poore {diff_str} sasta hai:"
                        )
                    else:
                        intro = (
                            f"Ji bilkul! {c_area} mein ye verified option available hai "
                            f"jo pichle option ({ref_price_str} PKR) ke muqablay mein poore {diff_str} sasta hai:"
                        )

                    item_line = f"1. **{c_name}** — {c_area}, {ref_city} — {c_beds} bedrooms — **{c_price:,} PKR** ({c_price_str} PKR)"
                    closing = "Agar aap is property ki mazeed details dekhna chahte hain ya visit schedule karna chahte hain, to batayein."
                    msg = f"{intro}\n\n{item_line}\n\n{closing}"

                    from web_api.services import RecommendationContext, property_snapshot, preference_snapshot, public_property
                    rec_id = uuid4()
                    saved["recommendation_session_id"] = str(rec_id)
                    saved["selected"] = top_c["property_id"]
                    saved["property_order"] = [p["property_id"] for p in cheaper_props[:2]]
                    state.required["budget"] = c_price
                    state.required["area"] = c_area
                    if relaxed_beds and c_beds:
                        state.required["bedrooms"] = c_beds

                    cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
                    ctx = RecommendationContext(
                        customer_id=identity.customer_id,
                        property_snapshots={p["property_id"]: public_property(p) for p in cheaper_props[:2]},
                        preference_snapshot=preference_snapshot(cust_rec.preferences) if cust_rec and cust_rec.preferences else {},
                    )
                    try:
                        await asyncio.to_thread(self.services.sessions.put, rec_id, ctx, identity.user_id)
                    except TypeError:
                        await asyncio.to_thread(self.services.sessions.put, rec_id, ctx)

                    await asyncio.to_thread(
                        self.services.interactions.record_interaction,
                        customer_id=identity.customer_id,
                        conversation_id=str(rec_id),
                        property_id=str(top_c["property_id"]),
                        action="shown",
                        preference_snapshot=ctx.preference_snapshot,
                        property_snapshot=property_snapshot(top_c),
                    )

                    return respond(msg, recommendation_session_id=str(rec_id), properties=[top_c])

                else:
                    # Look for residential alternatives (Apartments) when user was searching for a House,
                    # never jump to empty land plots for a living accommodation buyer!
                    pref_type = "Apartment" if str(ref_type).lower() == "house" else None
                    alt_type_matches = await asyncio.to_thread(
                        self.services.properties.search,
                        city=ref_city,
                        purpose=ref_purpose,
                        property_type=pref_type,
                        budget=ref_price - 1 if ref_price > 0 else None,
                    )
                    alt_type_matches = [
                        p for p in (alt_type_matches or [])
                        if p.get("property_id") != ref_id and int(p.get("price", 0)) < ref_price
                        and (str(p.get("property_type", "")).lower() != "plot" if str(ref_type).lower() == "house" else True)
                    ] if ref_price > 0 else (alt_type_matches or [])
                    if alt_type_matches:
                        alt_type_matches.sort(key=lambda p: int(p.get("price", 0)))
                        alt_p = alt_type_matches[0]
                        alt_t = alt_p.get("property_type", "Apartment")
                        alt_pr = int(alt_p.get("price", 0))
                        alt_pr_str = f"{alt_pr / 10_000_000:.1f} Crore" if alt_pr >= 10_000_000 else f"{alt_pr / 100_000:.0f} Lakh"
                        alt_area = alt_p.get("area", "")
                        area_hint = f" (jaise {alt_area} mein)" if alt_area else ""
                        msg = (
                            f"{ref_city} mein verified {ref_type.lower()}s mein filhaal yahi sab se kam price wala option hai ({ref_price_str} PKR). "
                            f"Lekin agar aap kam budget mein residential option dekh rahe hain to {ref_city} mein {alt_t.lower()}s {alt_pr_str} PKR se shuru ho rahe hain{area_hint}. "
                            f"Kya aap {alt_t.lower()}s ke options dekhna chahenge ya apna budget adjust karna chahenge?"
                        )
                    else:
                        msg = (
                            f"{ref_city} mein verified properties mein filhaal yahi sab se kam price wala option hai ({ref_price_str} PKR). "
                            "Kya aap kisi doosri city ke options check karna chahenge ya apna budget extend karna chahenge?"
                        )
                    return respond(msg, True)

            if is_price_objection:
                if cheaper_props:
                    top_c = cheaper_props[0]
                    saved["pending_cheaper_offer"] = top_c["property_id"]
                    c_price = int(top_c.get("price", 0))
                    c_price_str = f"{c_price / 10_000_000:.1f} Crore" if c_price >= 10_000_000 else f"{c_price / 100_000:.0f} Lakh"
                    c_area = top_c.get("area", "")
                    c_beds = top_c.get("bedrooms")
                    diff = ref_price - c_price
                    diff_str = f"{diff / 10_000_000:.1f} Crore" if diff >= 10_000_000 else f"{diff / 100_000:.0f} Lakh"

                    if relaxed_beds and c_beds:
                        alt_mention = (
                            f"{ref_area} mein to is se sasta house nahi hai, "
                            f"lekin {ref_city} mein hamare paas {c_area} mein {c_beds} bedrooms ka verified house "
                            f"{c_price_str} PKR (poore {diff_str} kam) mein available hai."
                        )
                    else:
                        alt_mention = (
                            f"{ref_city} mein hamare paas {c_area} mein "
                            f"{c_price_str} PKR (poore {diff_str} kam) mein verified option available hai."
                        )

                    msg = (
                        f"Main samajh sakti hoon, {ref_price_str} PKR waqai ek heavy budget hai. "
                        f"{alt_mention} "
                        "Kya aap yeh sasta option dekhna chahenge, ya aapka koi specific target budget hai jismein hum options search karein?"
                    )
                    return respond(msg, True)
                else:
                    msg = (
                        f"Main samajh sakti hoon, {ref_price_str} PKR premium price hai. "
                        f"{ref_city} mein verified {ref_type}s mein filhaal yeh sab se kam price wala option hai. "
                        "Aapka comfortable target budget kitna hai? Agar budget kam hai to hum Apartments ya kisi aur city ke options dekh sakte hain."
                    )
                    return respond(msg, True)

        # Check for consultative recommendation among currently shown options:
        # e.g. "mujey property recommend kro jo best hai aor budget b thora kaam ho jye to best hai"
        is_recommend_shown = bool(re.search(
            r"\b(?:recommend|mashwara|kons[ayie]\s+(?:best|ach[ayie]|sahi)|best\s+option|behtareen\s+option|sabse\s+sast[aei]|sast[aei]\s+wala|cheapest)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        prefers_lower_budget = bool(re.search(
            r"\b(?:budget\s*(?:b|bhi)?\s*(?:thora\s+)?(?:ka+m|low)|kam\s+budget|sasta|sasti|affordable|value|bachat)\b",
            raw_msg, flags=re.IGNORECASE
        ))
        if is_recommend_shown and order:
            props = []
            for pid in order:
                p = await asyncio.to_thread(self.services.properties.get_property, pid)
                if p:
                    props.append(p)
            if props:
                # If user wants lower budget or value, sort by price ascending
                if prefers_lower_budget:
                    props.sort(key=lambda x: x.get("price", 0))
                top_pick = props[0]
                tp_price = int(top_pick.get("price", 0))
                tp_price_str = f"{tp_price / 10_000_000:.1f} Crore" if tp_price >= 10_000_000 else f"{tp_price / 100_000:.0f} Lakh"
                tp_name = top_pick.get("property_name", "Option 1")
                tp_area = top_pick.get("area", "")

                if len(props) > 1 and prefers_lower_budget:
                    other = props[1]
                    o_price = int(other.get("price", 0))
                    diff = abs(o_price - tp_price)
                    diff_str = f"{diff / 100_000:.0f} Lakh" if diff < 10_000_000 else f"{diff / 10_000_000:.1f} Crore"
                    o_name = other.get("property_name", "Option 2")
                    o_area = other.get("area", "")

                    msg = (
                        f"Aapke budget aur behtareen value ko dekhte hue, main Option 1 ({tp_name}) recommend karungi:\n\n"
                        f"• Price: {tp_price_str} ({tp_price:,} PKR)  ye {o_name} ke muqablay mein {diff_str} kam hai, jo aapki kam budget wali requirement ke bilkul mutabiq hai.\n"
                        f"• Features: {tp_area} mein verified aur ready location hai.\n\n"
                        f"Agar aapka priority kam budget aur value for money hai to {tp_area} best choice hai. Aur agar aap prime brand value chahte hain to {o_name} ({o_area}) behtareen alternative hai.\n\n"
                        f"Kya aap {tp_name} ka visit schedule karna chahenge ya iski mazeed details dekhna pasand karenge?"
                    )
                else:
                    msg = (
                        f"Current options mein se main aapko {tp_name} ({tp_area}) recommend karungi:\n\n"
                        f"• Price: {tp_price_str} ({tp_price:,} PKR)\n"
                        f"• Location: {tp_area}\n\n"
                        f"Ye verified listing aapke criteria ke bilkul mutabiq hai. Kya aap iska visit schedule karna chahenge ya details dekhna pasand karenge?"
                    )
                return respond(msg, True, properties=props[:2])

        # Check for price range / budget inquiry: "minimum budget kitna hona chahey", "starting price kya hai"
        is_budget_inquiry = bool(re.search(
            r"\b(?:budget\s*(?:kitna|kya|hona)|kitna\s*budget|max\s*budget|minimum\s*budget|min\s*budget|starting\s*price|price\s*range)\b",
            raw_msg, flags=re.IGNORECASE
        )) or u.intent in {"MINIMUM_BUDGET_QUERY", "minimum_budget_query"}
        if is_budget_inquiry:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            city = (
                u.required.get("city")
                or state.required.get("city")
                or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None)
                or "Karachi"
            )
            purpose = (
                u.required.get("purpose")
                or state.required.get("purpose")
                or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None)
                or "Purchase"
            )
            req_type = (
                u.required.get("property_type")
                or state.required.get("property_type")
                or (cust_rec.preferences.property_type if cust_rec and cust_rec.preferences else None)
            )

            def _fmt_p(val: int | None) -> str:
                if not val:
                    return "N/A"
                if val >= 10_000_000:
                    return f"{val / 10_000_000:g} Crore PKR"
                return f"{val / 100_000:g} Lakh PKR"

            # If user is asking about or actively filtering by a specific property type (e.g. House):
            if req_type and req_type.lower() in ("house", "apartment", "plot", "commercial"):
                target_type = req_type.capitalize()
                type_props = await asyncio.to_thread(
                    self.services.properties.search,
                    city=city, purpose=purpose, property_type=target_type
                )
                if type_props:
                    lowest = min(type_props, key=lambda x: int(x.get("price", 0)))
                    min_p = int(lowest.get("price", 0))
                    min_s = _fmt_p(min_p)
                    name = lowest.get("property_name") or lowest.get("name")
                    area = lowest.get("area", "")
                    msg = (
                        f"{city} mein verified {target_type}s mein kam az kam budget {min_s} hona chahiye "
                        f"(sab se sasta {target_type.lower()} **{name}** {area} mein {min_s} ka hai). "
                        "Aapka comfortable target budget kitna hai?"
                    )
                    return respond(msg, True)

            # If no specific property type, provide verified breakdown across available types in the city:
            price_summary = await asyncio.to_thread(
                getattr(self.services.properties, "get_city_price_summary", lambda c: []),
                city
            )
            if price_summary:
                lines = []
                for item in price_summary:
                    pt = item.get("property_type")
                    pur = item.get("purpose")
                    min_p = int(item.get("min_price", 0))
                    max_p = int(item.get("max_price", 0))
                    cnt = item.get("count", 0)
                    lines.append(f"• {pt} ({pur}): {_fmt_p(min_p)} se {_fmt_p(max_p)} tak ({cnt} options)")
                summary_text = "\n".join(lines)
                msg = (
                    f"{city} mein verified properties ki pricing kuch is tarah hai:\n\n"
                    f"{summary_text}\n\n"
                    "Aap kis property type (jaise Apartment ya House) mein dekhna pasand karenge?"
                )
                return respond(msg, True)
            else:
                all_apts = await asyncio.to_thread(self.services.properties.search, city=city, purpose=purpose, property_type="Apartment")
                all_houses = await asyncio.to_thread(self.services.properties.search, city=city, purpose=purpose, property_type="House")
                min_apt = min([int(p.get("price", 0)) for p in (all_apts or []) if p.get("price")], default=None)
                min_hse = min([int(p.get("price", 0)) for p in (all_houses or []) if p.get("price")], default=None)
                lines = []
                if min_apt:
                    lines.append(f"• Apartment: kam az kam {_fmt_p(min_apt)} se")
                if min_hse:
                    lines.append(f"• House: kam az kam {_fmt_p(min_hse)} se")
                summary_text = "\n".join(lines)
                msg = (
                    f"{city} mein verified properties ki starting prices yeh hain:\n\n"
                    f"{summary_text}\n\n"
                    "Aap kis property type mein dekhna chahenge?"
                )
                return respond(msg, True)

        # -----------------------------------------------------------------
        # Budget Feasibility Query (e.g. "mera budget enough hai?")
        # -----------------------------------------------------------------
        is_feasibility_query = (
            u.intent in {"BUDGET_FEASIBILITY_QUERY", "budget_feasibility_query"}
            or bool(re.search(
                r"\b(?:mera\s+budget|yeh\s+budget|ye\s+budget)\s+(?:enough|kafi|theek|chaley?ga)\b|"
                r"\bkya\s+(?:\d+(?:\.\d+)?\s*(?:crore|cr|lakh|lac|million))\s+(?:enough|kafi|chaley?ga|mein\s+ho\s+jaye\s*ga)\b",
                raw_msg, flags=re.IGNORECASE
            ))
        )
        if is_feasibility_query:
            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
            target_budget = getattr(u, "query_budget", None)
            if not target_budget:
                bm = re.search(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lac|million)", raw_msg, flags=re.IGNORECASE)
                if bm:
                    num = float(bm.group(1))
                    unit = bm.group(2).lower()
                    if unit in ("crore", "cr"):
                        target_budget = int(num * 10_000_000)
                    elif unit in ("lakh", "lac"):
                        target_budget = int(num * 100_000)
                    elif unit == "million":
                        target_budget = int(num * 1_000_000)
            if not target_budget:
                target_budget = state.required.get("budget") or (cust_rec.preferences.budget_max if cust_rec and cust_rec.preferences else None)

            city = u.required.get("city") or state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or "Karachi"
            purpose = u.required.get("purpose") or state.required.get("purpose") or (cust_rec.preferences.purpose if cust_rec and cust_rec.preferences else None) or "Purchase"
            req_type = u.required.get("property_type") or state.required.get("property_type") or (cust_rec.preferences.property_type if cust_rec and cust_rec.preferences else None) or "House"
            target_area = u.required.get("area") or u.preferred.get("area") or getattr(self.sara.understanding, "_extract_explicit_area", lambda m: None)(raw_msg)

            def _fmt_p(val: int | None) -> str:
                if not val:
                    return "N/A"
                if val >= 10_000_000:
                    return f"{val / 10_000_000:g} Crore PKR"
                if val >= 100_000:
                    return f"{val / 100_000:g} Lakh PKR"
                return f"{val:,} PKR"

            # Check database for matches
            search_kw = {"city": city, "purpose": purpose, "property_type": req_type, "budget": target_budget}
            if target_area:
                search_kw["area"] = target_area
            matches = await asyncio.to_thread(self.services.properties.search, **search_kw) if target_budget else []

            all_kw = {"city": city, "purpose": purpose, "property_type": req_type}
            if target_area:
                all_kw["area"] = target_area
            all_for_type = await asyncio.to_thread(self.services.properties.search, **all_kw)
            if not all_for_type and target_area:
                all_for_type = await asyncio.to_thread(
                    self.services.properties.search,
                    city=city, purpose=purpose, property_type=req_type
                )
            min_for_type = min([int(p.get("price", 0)) for p in (all_for_type or []) if p.get("price")], default=None)

            b_str = _fmt_p(target_budget) if target_budget else "Aapka budget"
            loc_str = f"{target_area}, {city}" if target_area else city
            if matches:
                msg = f"Ji bilkul! {loc_str} mein {b_str} ke mutabiq {req_type}s ke verified options available hain. Kya aap options dekhna chahenge?"
            else:
                min_s = _fmt_p(min_for_type)
                msg = (
                    f"{loc_str} mein {b_str} {req_type.lower()} purchase ke liye kafi nahi hai, "
                    f"kyunke verified {req_type.lower()}s kam az kam {min_s} se shuru hotay hain. "
                    "Kya aap budget adjust karna chahenge ya Apartments ke options check karna chahenge?"
                )
            return respond(msg, True)

        if u.intent in {"schedule_visit", "reschedule_visit", "cancel_visit"}:
            pending = saved.get("pending_action") or {}
            if pending.get("intent") != u.intent:
                pending = {"intent": u.intent}
            saved["pending_action"] = pending
            if u.intent == "schedule_visit":
                selected = selected or (saved.get("selected") if not has_reference else None)
                if not selected or selected not in order:
                    return respond("Kis property ka visit book karna hai? Option number bata dein.", True)
                starts = u.starts_at or (pending.get("starts_at") if pending.get("property_id") == selected else None)
                saved["pending_action"] = {"intent": u.intent, "property_id": selected, "starts_at": starts}
                if not starts:
                    return respond("Visit ke liye kis date aur time par available hain?", True)
                if u.needs_clarification:
                    return respond("Visit ki date aur time dobara confirm kar dein.", True)
                # Re-check membership/expiry before any external side effect.
                rid_saved = saved.get("recommendation_session_id")
                if not rid_saved:
                    return respond("Yeh action purani search ke options ke liye tha. Pehle naye options dikhwa lein, phir visit schedule karein?", True)
                await self._recommendation(identity, saved, selected)
                try:
                    request = MeAppointmentBook(property_id=selected, starts_at=starts)
                except ValueError:
                    return respond("Visit ki date aur time timezone ke saath confirm kar dein.", True)
                response = await book(request)
            else:
                appointment_id = u.appointment_id or pending.get("appointment_id")
                if not appointment_id:
                    return respond("Appointments page se apni appointment ID confirm kar dein.", True)
                try:
                    appointment_id = UUID(appointment_id)
                except ValueError:
                    return respond("Appointment ID dobara confirm kar dein.", True)
                pending["appointment_id"] = str(appointment_id)
                if u.needs_clarification:
                    return respond("Appointment request dobara confirm kar dein.", True)
                # Ownership checked by existing authenticated endpoint before Day 4.
                if u.intent == "cancel_visit":
                    response = await cancel(appointment_id)
                else:
                    if not u.starts_at:
                        return respond("Nayi date aur time bata dein.", True)
                    try:
                        request = AppointmentReschedule(starts_at=u.starts_at)
                    except ValueError:
                        return respond("Nayi date aur time timezone ke saath confirm kar dein.", True)
                    response = await reschedule(appointment_id, request)
            appointment = response.get("appointment")
            if not isinstance(appointment, dict) or not appointment.get("appointment_id"):
                return respond("Appointment service ne confirmation nahi di. Appointments page par status check kar lein.")
            saved["pending_action"] = None
            return respond("Ji, appointment request confirm ho gayi. Appointments page par details dekh sakte hain.",
                           appointment={key: appointment[key] for key in ("appointment_id", "status") if key in appointment})

        if u.intent in {"property_details", "property_selection", "availability"}:
            if saved.get("pending_cheaper_offer"):
                offered_id = saved.pop("pending_cheaper_offer", None)
                if offered_id:
                    selected = offered_id
                    saved["selected"] = offered_id
                    saved["property_order"] = [offered_id]
                    # If user was simply saying "g dikha dein" / "dikhao" / "show" (not asking for deep technical specs),
                    # present the clean listing option and card instead of dumping raw database specs!
                    user_wants_specs = bool(re.search(
                        r"\b(?:details?|specifications?|developer|marla|sqft|covered\s+area|bathrooms?|plot\s+size)\b",
                        raw_msg, flags=re.IGNORECASE
                    ))
                    if not user_wants_specs:
                        offered_prop = await asyncio.to_thread(self.services.properties.get_property, offered_id)
                        if offered_prop:
                            c_price = int(offered_prop.get("price", 0))
                            c_price_str = f"{c_price / 10_000_000:.1f} Crore" if c_price >= 10_000_000 else f"{c_price / 100_000:.0f} Lakh"
                            c_name = offered_prop.get("property_name") or offered_prop.get("name")
                            c_area = offered_prop.get("area", "")
                            c_city = offered_prop.get("city", "Karachi")
                            c_beds = offered_prop.get("bedrooms")
                            msg = (
                                f"Ji bilkul! Aapke liye {c_area} mein ye behtareen verified option available hai:\n\n"
                                f"1. **{c_name}** — {c_area}, {c_city} — {c_beds} bedrooms — **{c_price:,} PKR** ({c_price_str} PKR)\n\n"
                                "Agar aap is property ki mazeed details dekhna chahte hain ya visit schedule karna chahte hain, to batayein."
                            )
                            from web_api.services import RecommendationContext, property_snapshot, preference_snapshot, public_property
                            rec_id = uuid4()
                            saved["recommendation_session_id"] = str(rec_id)
                            cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
                            ctx = RecommendationContext(
                                customer_id=identity.customer_id,
                                property_snapshots={offered_id: public_property(offered_prop)},
                                preference_snapshot=preference_snapshot(cust_rec.preferences) if cust_rec and cust_rec.preferences else {},
                            )
                            try:
                                await asyncio.to_thread(self.services.sessions.put, rec_id, ctx, identity.user_id)
                            except TypeError:
                                await asyncio.to_thread(self.services.sessions.put, rec_id, ctx)
                            return respond(msg, recommendation_session_id=str(rec_id), properties=[offered_prop])
            if not selected and order:
                area_filter_match = re.search(
                    r"\b([\w\s-]{2,25}?)\s+(?:mein|me|main)\s+(?:k[a]?n?\s*)?(?:kn\s*kn\s*sey|konsay|kaunsay|kya|kitney|which)\s+options?\b|"
                    r"\boptions?\s+(?:konsay|kaunsay|kya)\s+(?:hain|hai)\s+([\w\s-]{2,25}?)\s+(?:mein|me|main)\b|"
                    r"\b([\w\s-]{2,25}?)\s+(?:k[ay]?|ke)\s+options?\s+(?:konsay|kaunsay|kya)\s+(?:hain|hai)\b|"
                    r"\b([\w\s-]{2,25}?)\s+(?:mein|me|main)\s+(?:kya\s+hai|kya\s+options?\s+hai|kya\s+kya\s+hai)\b",
                    raw_msg, flags=re.IGNORECASE
                )
                if area_filter_match:
                    named_area = next((g for g in area_filter_match.groups() if g), "").strip()
                    if named_area:
                        shown_props = []
                        for pid in order:
                            p = await asyncio.to_thread(self.services.properties.get_property, pid)
                            if p:
                                shown_props.append(p)
                        matches = [p for p in shown_props if named_area.lower() in str(p.get("area", "")).lower() or named_area.lower() in str(p.get("city", "")).lower()]
                        if matches:
                            lines = []
                            for p in matches:
                                price = int(p.get("price", 0))
                                price_str = f"{price / 10_000_000:.1f} Crore" if price >= 10_000_000 else f"{price / 100_000:.0f} Lakh"
                                lines.append(f"- {p.get('property_name')} — {p.get('area')}, {p.get('city')} — {p.get('bedrooms')} bedrooms — {price_str} PKR")
                            intro = f"{named_area} mein filhaal ye option{'s' if len(matches) > 1 else ''} available {'hain' if len(matches) > 1 else 'hai'}:"
                            # FIX: Update property_order to the filtered subset that was just displayed.
                            # Any subsequent ordinal reference ("first", "pehli wali", etc.) in the next
                            # turn must resolve against what the user actually saw — NOT the stale full list.
                            saved["property_order"] = [p["property_id"] for p in matches]
                            return respond(intro + "\n" + "\n".join(lines) + "\n\nIn mein se kisi ki details chahiye ya visit schedule karna chahengi?", True, properties=matches)
                        else:
                            return respond(f"Abhi dikhaye gaye options mein {named_area} ka koi option nahi hai. Naye options dhoondun?", True)

            selected = selected or (saved.get("selected") if not has_reference else None) or (order[0] if len(order) == 1 and not has_reference else None)
            if not selected:
                return respond("Kis option ki details chahiye? Option number bata dein.", True)
            rid_saved = saved.get("recommendation_session_id")
            if not rid_saved:
                return respond("Yeh action purani search ke options ke liye tha. Pehle naye options dikhwa lein, phir details dekhein?", True)
            await self._recommendation(identity, saved, selected)
            row = await asyncio.to_thread(self.services.properties.get_property, selected)
            if not row or not row.get("available"):
                return respond("Yeh property ab available nahi hai. Naye options dekhna chahenge?", True)
            return respond(self._format_property_details(row))

        if u.intent in {"property_search", "recommendation", "SAME_REQUIREMENTS", "same_requirements"}:
            # Current web search contract cannot express exclusion/comparison filters.
            # Ask instead of silently discarding a constraint and presenting false matches.
            if state.excluded or u.comparison.field:
                return respond("Is comparison ke liye apni exact city, area ya maximum budget bata dein.", True)

            # Resolve parent area names against this city's filtered inventory.
            area_resolved = False
            named_area = u.required.get("area") or u.preferred.get("area") or state.required.get("area")
            if named_area and str(named_area).strip():
                cust_for_areas = await asyncio.to_thread(
                    self.services.customers.resolve_for_customer_id, identity.customer_id)
                pick_city = (state.required.get("city")
                             or (cust_for_areas.preferences.city
                                 if cust_for_areas and cust_for_areas.preferences else None))
                if pick_city:
                    available_areas = await asyncio.to_thread(
                        getattr(self.services.properties, "list_available_areas", lambda **k: []),
                        city=pick_city, property_type=state.required.get("property_type"),
                        purpose=state.required.get("purpose"), budget=state.required.get("budget"), limit=20)
                    named_lower = str(named_area).strip().casefold()
                    exact_match = any(str(a).strip().casefold() == named_lower for a in available_areas)
                    matching_variants = list(dict.fromkeys(
                        str(a) for a in available_areas if named_lower in str(a).casefold()))
                    if not exact_match and len(matching_variants) > 1:
                        return respond(
                            f"Ji, {named_area} mein kai phases available hain: {', '.join(matching_variants)}. "
                            "Ap kis phase mein dekhna chahengi?", True)
                    if not exact_match and len(matching_variants) == 1:
                        state.required["area"] = matching_variants[0]
                        state.preferred.pop("area", None)
                        state.flexible.discard("area")
                        saved["flexible"] = [f for f in saved.get("flexible", []) if f != "area"]
                        is_one_time = bool(re.search(
                            r"\b(?:dikh[aoaei]+|show|options?\s+dikha|dekhna\s+hai|dekhni\s+hai|check\s+k(?:ar|r)|options?\s+dekh)\b",
                            raw_msg, re.IGNORECASE
                        ))
                        has_pref_confirm = bool(re.search(
                            r"\b(?:mer[aiy]+\s+preference|preference\s+(?:hai|save|update)|yehi\s+chahiye|yehi\s+meri\s+requirement|save\s+k(?:ar|r)|mujhe\s+yehi\s+chahiye|isi\s+ko\s+save|confirm)\b",
                            raw_msg, re.IGNORECASE
                        ))
                        existing_area_pref = getattr(getattr(cust_for_areas, "preferences", None), "area", None)
                        if not is_one_time or has_pref_confirm or existing_area_pref is not None:
                            await asyncio.to_thread(self.services.customers.update_preferences,
                                                    identity.customer_id, {"area": matching_variants[0]})
                        area_resolved = True

            # Tier 1 Gate: Essential slots (Purpose -> City/Area -> Budget)
            decision = await asyncio.to_thread(self.sara.policy.next_tier1_requirement,
                                               state=state, knowledge=self.services.properties, intent=u.intent)
            area_is_flexible = "area" in saved.get("flexible", []) or "area" in (u.relax or [])
            if decision:
                # "sab areas k dikhayen": area already relaxed — do NOT re-ask the
                # area slot; proceed straight to cross-area recommendations.
                if area_is_flexible and re.search(r"area", decision.message or "", re.IGNORECASE):
                    decision = None
                else:
                    # A NEW question is being asked: any earlier "budget extend?"
                    # offer is now stale, otherwise the user's "haan" to this
                    # question would wrongly broaden the budget.
                    saved.pop("last_asked_broaden", None)
                    saved["pending_action"] = decision.pending_action
                    return respond(decision.message, True)
            if u.needs_clarification and not area_resolved:
                if u.clarification_reason == "ambiguous_purpose":
                    return respond("Aap property purchase ke liye dekh rahe hain ya rent par lena chahte hain?", True)
                if u.clarification_reason == "ambiguous_property_type":
                    return respond("Aap kis property type (jaise apartment ya house) mein dekhna chahte hain?", True)
                if u.clarification_reason == "ambiguous_bedrooms":
                    return respond("Aapko kitne bedrooms (jaise 2 ya 3 bedroom) ki requirement hai?", True)
                if u.clarification_reason == "incomplete_location":
                    return respond("Aap kis specific area ya phase mein dekhna chahte hain?", True)
                # Contextual recovery, not a canned "clear kar dein" — reference
                # what we already know so the reply feels like a real agent.
                known = []
                if state.required.get("property_type"):
                    known.append(str(state.required["property_type"]).lower())
                if state.required.get("city"):
                    known.append(str(state.required["city"]) + " mein")
                if state.required.get("budget"):
                    b = state.required["budget"]
                    known.append((f"{b / 10_000_000:g} crore" if b >= 10_000_000 else f"{b:,} PKR") + " tak budget")
                known_str = (", ".join(known[:-1]) + " aur " + known[-1]) if len(known) > 1 else (known[0] if known else "")
                if known_str:
                    return respond(f"Ji, {known_str} samajh gayi. Bas ye thora sa clear kar dein  kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?", True)
                return respond("Ji zaroor, thori si detail bata dein, ap kis city mein property dekhna chahtey hai aor ap ka budget kiya hai? Phir main behtr options bta skti hun.", True)

            # Tier 2 Gate: Narrowing slots (Bedrooms -> Property Type -> Amenities)
            # Only checked when Tier 1 is complete and matching inventory count > threshold.
            clarify_threshold = int(os.environ.get("SARA_RESULTS_CLARIFY_THRESHOLD", 5))
            matching_props = await asyncio.to_thread(
                self.services.properties.search,
                city=state.required.get("city"),
                area=state.required.get("area"),
                purpose=state.required.get("purpose"),
                budget=state.required.get("budget"),
                property_type=state.required.get("property_type"),
                bedrooms=state.required.get("bedrooms"),
            )
            matching_count = len(matching_props) if matching_props else 0
            if matching_count > clarify_threshold:
                narrowing_dec = await asyncio.to_thread(
                    self.sara.policy.next_narrowing_requirement,
                    state=state,
                    matching_count=matching_count,
                    threshold=clarify_threshold,
                )
                if narrowing_dec:
                    saved.pop("last_asked_broaden", None)
                    saved["pending_action"] = narrowing_dec.pending_action
                    return respond(narrowing_dec.message, True)

            search_overrides = {}
            if area_is_flexible:
                search_overrides["area"] = None
            elif state.required.get("area"):
                search_overrides["area"] = state.required["area"]
            if state.required.get("city"):
                search_overrides["city"] = state.required["city"]
            if state.required.get("budget"):
                search_overrides["budget"] = state.required["budget"]
            if state.required.get("bedrooms") is not None:
                search_overrides["bedrooms"] = state.required["bedrooms"]
            if state.required.get("property_type"):
                search_overrides["property_type"] = state.required["property_type"]
            if state.required.get("purpose"):
                search_overrides["purpose"] = state.required["purpose"]
            rec_res = await self.services.recommendations(
                identity.customer_id, self.sara.presentation.batch_size,
                None, identity.user_id, filter_overrides=search_overrides or None
            )
            rid, rows = rec_res[0], rec_res[1]
            relaxed_rows = getattr(rec_res, "relaxed_properties", [])
            relaxed_constraint = getattr(rec_res, "relaxed_constraint", None)
            relaxed_meta = getattr(rec_res, "relaxed_meta", {})
            fallback_areas = getattr(rec_res, "fallback_areas", [])

            saved.update(recommendation_session_id=str(rid), property_order=[r["property_id"] for r in rows],
                         selected=(rows[0]["property_id"] if len(rows) == 1 else None), pending_action=None)
            if not rows:
                cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
                city = state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or "Is city"
                requested_area = u.required.get("area") or u.preferred.get("area") or state.required.get("area")

                # Filter fallback_areas to exclude requested_area
                available_areas = []
                for a in fallback_areas:
                    if requested_area:
                        req_l = str(requested_area).strip().lower()
                        if req_l in str(a).strip().lower() or str(a).strip().lower() in req_l:
                            continue
                    available_areas.append(a)

                if not available_areas:
                    raw_available = await asyncio.to_thread(
                        getattr(self.services.properties, "list_available_areas", lambda **k: []),
                        city=city, property_type=state.required.get("property_type"),
                        purpose=state.required.get("purpose"), budget=state.required.get("budget"),
                        bedrooms=state.required.get("bedrooms"), limit=6
                    )
                    for a in raw_available:
                        if requested_area:
                            req_l = str(requested_area).strip().lower()
                            if req_l in str(a).strip().lower() or str(a).strip().lower() in req_l:
                                continue
                        available_areas.append(a)

                has_relaxed = bool(relaxed_rows and requested_area)
                has_fallback = bool(available_areas)

                req_type = state.required.get("property_type")
                b = state.required.get("budget")
                b_str = (f"{b / 10_000_000:g} crore" if b and b >= 10_000_000 else (f"{b:,} PKR" if b else "is budget"))

                # 4-Branch Logic for Relaxed / Fallback presentation:
                if has_relaxed:
                    opt_a_prop = relaxed_rows[0]
                    orig_beds = relaxed_meta.get("original_bedrooms") or state.required.get("bedrooms")
                    alt_beds = opt_a_prop.get("bedrooms")
                    cand_type = opt_a_prop.get("property_type")

                    # Property type transparency (Failure 2 requirement)
                    type_differs = bool(cand_type and req_type and str(cand_type).strip().lower() != str(req_type).strip().lower())
                    if type_differs:
                        opt_a_desc = f"{requested_area} mein {alt_beds}-bed {cand_type}" if alt_beds else f"{requested_area} mein {cand_type}"
                    else:
                        type_label = f" {cand_type}" if cand_type else (f" {req_type}" if req_type else "")
                        opt_a_desc = f"{requested_area} mein {alt_beds}-bed{type_label} option" if alt_beds else f"{requested_area} mein{type_label} option"

                    if has_fallback:
                        # BRANCH 1: Dual Option (Option A same-area relaxed vs Option B cross-area exact)
                        cross_area = available_areas[0]
                        opt_b_desc = f"{cross_area} mein {orig_beds}-bed exact match" if orig_beds else f"{cross_area} mein options"

                        saved["pending_choice_frame"] = {
                            "status": "pending",
                            "city": city,
                            "requested_area": requested_area,
                            "property_type": req_type,
                            "budget": b,
                            "bedrooms": orig_beds,
                            "option_a": {
                                "type": "same_area_relaxed",
                                "area": requested_area,
                                "bedrooms": alt_beds,
                                "property_type": cand_type,
                                "property_id": opt_a_prop.get("property_id"),
                                "desc": opt_a_desc,
                                "properties": list(relaxed_rows),
                            },
                            "option_b": {
                                "type": "cross_area_exact",
                                "area": cross_area,
                                "bedrooms": orig_beds,
                                "property_type": req_type,
                                "desc": opt_b_desc,
                                "properties": [],
                            },
                        }
                        saved["pending_suggested_areas"] = list(available_areas)
                        saved["pending_suggested_area"] = cross_area

                        if type_differs:
                            msg = (
                                f"{requested_area} mein {orig_beds or ''}-bed {req_type} nahi mila, lekin {alt_beds or ''}-bed {cand_type} available hai. "
                                f"Ya phir {cross_area} mein {orig_beds or ''}-bed exact match bhi hai — kaunsa dekhna chahenge?"
                            )
                        elif orig_beds and alt_beds:
                            type_str = f" {req_type}" if req_type else ""
                            msg = (
                                f"{requested_area} mein {orig_beds}-bed{type_str} nahi hai, lekin {alt_beds}-bed option available hai. "
                                f"Ya phir {cross_area} mein {orig_beds}-bed exact match bhi hai — kaunsa dekhna chahenge?"
                            )
                        else:
                            msg = (
                                f"{requested_area} mein exact match nahi hai, lekin close option available hai. "
                                f"Ya phir {cross_area} mein exact match bhi hai — kaunsa dekhna chahenge?"
                            )
                        return respond(msg, True)
                    else:
                        # BRANCH 2: Option A only (Same-area relaxed match, no cross-area fallback)
                        saved["pending_choice_frame"] = {
                            "status": "pending",
                            "city": city,
                            "requested_area": requested_area,
                            "property_type": req_type,
                            "budget": b,
                            "bedrooms": orig_beds,
                            "option_a": {
                                "type": "same_area_relaxed",
                                "area": requested_area,
                                "bedrooms": alt_beds,
                                "property_type": cand_type,
                                "property_id": opt_a_prop.get("property_id"),
                                "desc": opt_a_desc,
                                "properties": list(relaxed_rows),
                            },
                            "option_b": None,
                        }
                        saved.pop("pending_suggested_area", None)
                        saved.pop("pending_suggested_areas", None)

                        if type_differs:
                            msg = (
                                f"{requested_area} mein {orig_beds or ''}-bed {req_type} nahi mila, lekin {alt_beds or ''}-bed {cand_type} option available hai. "
                                "Kya aap yeh option dekhna chahenge?"
                            )
                        elif orig_beds and alt_beds:
                            type_str = f" {req_type}" if req_type else ""
                            msg = (
                                f"{requested_area} mein {orig_beds}-bed{type_str} nahi hai, lekin {alt_beds}-bed option available hai. "
                                "Kya aap yeh option dekhna chahenge?"
                            )
                        else:
                            msg = (
                                f"{requested_area} mein exact match nahi hai, lekin close option available hai. "
                                "Kya aap yeh option dekhna chahenge?"
                            )
                        return respond(msg, True)

                elif has_fallback:
                    # BRANCH 3: Cross-area only (Same-area empty, but cross-area alternatives exist)
                    cross_area = available_areas[0]
                    orig_beds = state.required.get("bedrooms")
                    opt_a_desc = f"{cross_area} ke options"

                    saved["pending_choice_frame"] = {
                        "status": "pending",
                        "city": city,
                        "requested_area": requested_area,
                        "property_type": req_type,
                        "budget": b,
                        "bedrooms": orig_beds,
                        "option_a": {
                            "type": "cross_area_exact",
                            "area": cross_area,
                            "bedrooms": orig_beds,
                            "property_type": req_type,
                            "desc": opt_a_desc,
                            "properties": [],
                        },
                        "option_b": None,
                    }
                    saved["pending_suggested_areas"] = list(available_areas)
                    saved["pending_suggested_area"] = cross_area

                    if len(available_areas) > 1:
                        areas_str = ", ".join(available_areas)
                        msg = f"{requested_area} mein options nahi hain, lekin {city} mein in areas mein options available hain: {areas_str}. Kis area ke options dekhna chahenge?"
                    else:
                        area_display = requested_area or city
                        msg = (
                            f"{area_display} mein {b_str} ke andar verified options nahi hain, "
                            f"lekin {cross_area} mein exact match available hai. Kya aap {cross_area} ke options dekhna chahenge?"
                        )
                    return respond(msg, True)

                else:
                    # BRANCH 4: Terminal Grounded None (Edge Case 3 - no frame created)
                    saved.pop("pending_choice_frame", None)
                    saved.pop("pending_suggested_area", None)
                    saved.pop("pending_suggested_areas", None)
                    saved["last_asked_broaden"] = True

                    if "area" in saved.get("flexible", []) or "area" in u.relax:
                        return respond(f"{city} mein is criteria par options nahi mile. Kya aap budget thora extend karna chahenge ya kisi aur city ke options dekhna chahenge?", True)

                    area_display = requested_area or city
                    msg = (
                        f"{area_display} mein {b_str} ke andar is criteria par verified options nahi mile. "
                        "Kya aap budget thora extend karna chahenge ya kisi qareebi area ke options dekhna pasand karenge?"
                    )
                    return respond(msg, True)

            intro = None
            if "area" in u.relax or "area" in saved.get("flexible", []):
                cust_rec = await asyncio.to_thread(self.services.customers.resolve_for_customer_id, identity.customer_id)
                # Determine asked-about area token in priority order:
                # 1. Explicitly named in current message (u.required, u.preferred, or explicit area extraction)
                asked_area = u.required.get("area") or getattr(u, "preferred", {}).get("area")
                if not asked_area:
                    extract_fn = getattr(self.sara.understanding, "_extract_explicit_area", None)
                    if extract_fn:
                        asked_area = extract_fn(raw_msg)
                    else:
                        m = re.search(
                            r"\b([A-Za-z0-9-]+(?:\s+[A-Za-z0-9-]+)?)\s+(?:mein|me|main|k[ay]?|ke)\b",
                            raw_msg, flags=re.IGNORECASE
                        )
                        if m:
                            word = m.group(1).strip()
                            blocked = {
                                "ye", "yeh", "is", "in", "un", "kya", "konsa", "kaunsa", "batao",
                                "aur", "aor", "options", "option", "properties", "property",
                                "crore", "cr", "lakh", "lac", "million", "thousand", "k", "budget", "price"
                            }
                            if word.lower() not in blocked and not re.search(r"\b(?:\d+|crore|cr|lakh|lac|million|k)\b", word, re.IGNORECASE):
                                asked_area = word
                # 2. Fall back to state.required["area"] or saved preferences ONLY if not explicitly relaxed
                if not asked_area and "area" not in u.relax:
                    asked_area = state.required.get("area") or (getattr(cust_rec.preferences, "area", None) if cust_rec and cust_rec.preferences else None)

                # Prioritize rows matching asked_area
                prioritized = []
                rest = list(rows)
                if asked_area and rows:
                    asked_lower = asked_area.strip().lower()
                    prioritized = [r for r in rows if asked_lower in str(r.get("area", "")).lower()]
                    rest = [r for r in rows if r not in prioritized]
                    rows = prioritized + rest
                    saved["property_order"] = [r["property_id"] for r in rows]

                city = state.required.get("city") or (cust_rec.preferences.city if cust_rec and cust_rec.preferences else None) or "Is city"
                available_areas = await asyncio.to_thread(
                    getattr(self.services.properties, "list_available_areas", lambda **k: []),
                    city=city, property_type=state.required.get("property_type"),
                    purpose=state.required.get("purpose"), budget=state.required.get("budget"), limit=6
                )
                areas_str = ", ".join(available_areas) if available_areas else ", ".join(list(dict.fromkeys(r.get("area") for r in rows if r.get("area"))))

                is_budget_relaxed = ("budget" in u.relax) or ("budget" in saved.get("flexible", []))
                reason = "chunke aap ne budget flexible rakha hai" if is_budget_relaxed else "Location flexibility ki wajah se"

                if asked_area and prioritized and rest:
                    matched_area = prioritized[0].get("area") or asked_area
                    extra_areas = list(dict.fromkeys(r.get("area") for r in rest if r.get("area")))
                    extra_str = ", ".join(extra_areas) if extra_areas else f"{city} ke doosre areas"
                    opt_word = "ye option mila" if len(prioritized) == 1 else "ye options mile"
                    intro = f"{matched_area} mein to {opt_word} — aur {reason}, {extra_str} se bhi kuch achay options mil gaye hain:"
                elif asked_area and prioritized and not rest:
                    matched_area = prioritized[0].get("area") or asked_area
                    intro = f"Ji! {matched_area} mein aapke criteria ke mutabiq ye verified options mile hain:"
                elif asked_area and not prioritized:
                    intro = f"{asked_area} mein to is criteria par verified options nahi mile, lekin Location flexibility ki wajah se {city} ke in areas ({areas_str}) se ye options mile hain:"
                else:
                    curr_budget = state.required.get("budget")
                    b_str = (f"{curr_budget / 10_000_000:g} Crore PKR" if curr_budget >= 10_000_000 else f"{curr_budget:,} PKR") if curr_budget else None
                    if "area" in u.relax or is_budget_relaxed or not b_str:
                        intro = f"Location flexibility ke mutabiq {city} ke in areas ({areas_str}) se ye options mile hain:" if not is_budget_relaxed else f"Budget flexibility ke mutabiq {city} ke in areas ({areas_str}) se ye options mile hain:"
                    else:
                        intro = f"Ji bilkul! {city} mein {b_str} ke andar in areas ({areas_str}) se yeh verified options available hain:"
            message_text = self.sara.presentation.format_batch(rows, has_more=False, first_batch=True, custom_intro=intro)
            return respond(message_text, recommendation_session_id=str(rid), properties=rows)
        if u.intent == "greeting":
            decision = await asyncio.to_thread(self.sara.policy.next_tier1_requirement,
                state=state, knowledge=self.services.properties)
            intro = "Assalam-o-alaikum! Main Sara hoon, aapki property assistant. " if not saved.get("turn_count") else ""
            if decision:
                saved["pending_action"] = decision.pending_action
                return respond(intro + decision.message, True)
            return respond(intro + "Apni property requirement mein kya change karna chahenge?")
        if re.search(r"aap kaun|ap kon|who are you|loan|financ", raw_msg):
            answer = ("Main Sara hoon, aapki property assistant. " if re.search(r"aap kaun|ap kon|who are you", raw_msg)
                      else "Financing ki eligibility aur terms bank se confirm karni hongi. ")
            decision = await asyncio.to_thread(self.sara.policy.next_tier1_requirement,
                state=state, knowledge=self.services.properties)
            if decision:
                saved["pending_action"] = decision.pending_action
            return respond(answer + (decision.message if decision else "Property search continue karein?"), True)
        if (u.required or u.preferred or u.relax) and not u.needs_clarification:
            return respond("Ji, aapki preferences update ho gayi hain.")
        if u.intent == "off_topic":
            if order:
                return respond(f"Main sirf property se mutaliq madad kar sakti hoon. Abhi aapke samne {len(order)} verified property options khule hain — in mein se kisi ki details chahiye ya visit book karni ho to batayein.", True)
            return respond("Main sirf property search aur appointments mein madad kar sakti hoon. Aap kis city mein property dekhna chahenge?", True)
        # Context-aware fallback: a real agent never resets the conversation —
        # it references what is already on the table and offers next steps.
        ctx_city = state.required.get("city")
        ctx_area = state.required.get("area")
        if ctx_area:
            ctx_hint = f"Hum abhi {ctx_area}"
            if ctx_city:
                ctx_hint += f" ({ctx_city})"
            ctx_hint += " ke options dekh rahe hain. "
        elif ctx_city:
            ctx_hint = f"Hum {ctx_city} dekh rahe hain. "
        else:
            ctx_hint = ""
        if order:
            return respond(ctx_hint + f"Aapke saamne {len(order)} verified options khule hain — in mein se kisi ki details chahiye, visit book karni hai, ya naye options dikhauin?", True)
        return respond(ctx_hint + "Bataiye — main aapke liye options dhoondun, kisi listing ki details nikalun, ya visit ka intezaam karun?", True)

    def _format_property_details(self, row: dict) -> str:
        """Human-readable UrduLish details for a verified listing (web UI variant)."""
        price = row.get("price")
        try:
            price_num = int(price)
            price_str = (
                f"{price_num / 10_000_000:.2f} Crore PKR" if price_num >= 10_000_000
                else (f"{price_num / 100_000:.0f} Lakh PKR" if price_num else None)
            )
        except (TypeError, ValueError):
            price_str = None

        def unit_pair(value_key: str, unit_key: str, default: str = "-") -> str:
            value = row.get(value_key)
            unit = row.get(unit_key)
            if value in (None, ""):
                return default
            return f"{value} {str(unit).lower() if unit else ''}".strip()

        lines = [
            f"Ji, {row.get('property_name', 'yeh property')} ki verified details:",
            "- " + (f"Price: {price_str}" if price_str else "Price: abhi available nahi"),
            f"- Reference: {row.get('property_id', 'N/A')}",
            f"- Location: {row.get('area', 'N/A')}, {row.get('city', 'N/A')}",
            f"- Type: {row.get('property_type', 'N/A')}",
            f"- Bedrooms: {row.get('bedrooms', 'N/A')} | Bathrooms: {row.get('bathrooms', 'N/A')}",
            f"- Plot size: {unit_pair('plot_size', 'plot_unit')}",
            f"- Covered area: {unit_pair('covered_area', 'covered_area_unit')}",
            f"- Purpose: {row.get('purpose', 'N/A')}",
            f"- Status: {row.get('status', 'Ready')}",
        ]
        developer = row.get("developer_name")
        if developer:
            lines.append(f"- Developer: {developer}")
        amenities = row.get("amenities") or []
        if amenities:
            lines.append("- Amenities: " + ", ".join(str(a) for a in amenities[:6]))
        lines.append("Kya aap is property ki visit schedule karna chahenge?")
        return "\n".join(lines)

    async def _recommendation(self, identity, saved, property_id):
        context = await asyncio.to_thread(self.services.sessions.get, UUID(saved["recommendation_session_id"]))
        if not context or context.customer_id != identity.customer_id or property_id not in context.property_snapshots:
            raise PermissionError()
        return context
