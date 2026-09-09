from __future__ import annotations

import json
import logging
import os
import re
import time
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv

from .models import ComparisonRequest, UserUnderstanding
from .edge_case_policy import EdgeCasePolicy


logger = logging.getLogger(__name__)


INTENTS = {
    "property_search",
    "property_details",
    "property_selection",
    "recommendation",
    "availability",
    "faq",
    "objection",
    "schedule_visit",
    "reschedule_visit",
    "cancel_visit",
    "greeting",
    "reset",
    "off_topic",
    "unknown",
    # Real-estate conversation & inquiry intents
    "same_requirements",
    "change_preference",
    "budget_objection",
    "minimum_budget_query",
    "budget_feasibility_query",
    "property_type_by_budget_query",
    "cheapest_property_query",
    "book_visit",
    "SAME_REQUIREMENTS",
    "CHANGE_PREFERENCE",
    "BUDGET_OBJECTION",
    "MINIMUM_BUDGET_QUERY",
    "BUDGET_FEASIBILITY_QUERY",
    "PROPERTY_TYPE_BY_BUDGET_QUERY",
    "CHEAPEST_PROPERTY_QUERY",
    "MOST_EXPENSIVE_PROPERTY_QUERY",
    "AREAS_QUERY",
    "CITIES_QUERY",
    "LIST_AVAILABLE_OPTIONS_QUERY",
    "PROPERTY_SEARCH",
    "PROPERTY_DETAILS",
    "BOOK_VISIT",
}

FIELDS = {
    "budget",
    "city",
    "area",
    "bedrooms",
    "property_type",
    "purpose",
    "amenities",
    "investment_goal",
    "developer",
}

REFERENCES = {
    None,
    "selected_property",
    "first_result",
    "second_result",
    "third_result",
    "last_result",
}

COMP_FIELDS = {
    None,
    "price",
    "bedrooms",
    "bathrooms",
    "plot_size",
    "covered_area",
}

COMP_OPS = {
    None,
    "lt",
    "gt",
    "lte",
    "gte",
    "eq",
}

INTERACTION_ACTIONS = {
    None,
    "liked",
    "rejected",
    "shortlisted",
}


# These are schema vocabulary aliases, not business/property data.
PROPERTY_TYPE_ALIASES = {
    "flat": "Apartment",
    "flats": "Apartment",
    "apartment": "Apartment",
    "apartments": "Apartment",

    "house": "House",
    "houses": "House",
    "home": "House",
    "homes": "House",
    "villa": "House",
    "villas": "House",
    "ghar": "House",
    "ghars": "House",
    "makan": "House",
    "makaan": "House",

    "office": "Office",
    "office space": "Office",

    "shop": "Shop",
    "shops": "Shop",
    "retail shop": "Shop",

    "plot": "Plot",
    "plots": "Plot",
    "residential plot": "Plot",
    "commercial plot": "Plot",
}

PURPOSE_ALIASES = {
    "rent": "Rental",
    "rental": "Rental",
    "kiraya": "Rental",
    "kiraye": "Rental",
    "rent pe": "Rental",
    "rent par": "Rental",

    "purchase": "Purchase",
    "purchasing": "Purchase",
    "buy": "Purchase",
    "buying": "Purchase",
    "khareedna": "Purchase",
    "kharidna": "Purchase",
    "sale": "Purchase",
}

CITY_ALIASES = {
    "islamabad": "Islamabad",
    "isb": "Islamabad",
    "lahore": "Lahore",
    "lahor": "Lahore",
    "lahoor": "Lahore",
    "lahroe": "Lahore",
    "karachi": "Karachi",
    "khi": "Karachi",
    "rawalpindi": "Rawalpindi",
    "pindi": "Rawalpindi",
    "rwp": "Rawalpindi",
    "peshawar": "Peshawar",
    "pesh": "Peshawar",
    "multan": "Multan",
    "faisalabad": "Faisalabad",
    "fsd": "Faisalabad",
    "quetta": "Quetta",
}


class UnderstandingError(RuntimeError):
    pass


class UserUnderstandingService:
    def __init__(
        self,
        client=None,
        model: str | None = None,
        deterministic_first: bool = True,
    ):
        load_dotenv()
        self.deterministic_first = deterministic_first
        self.edge = EdgeCasePolicy()

        self.model = (
            model
            or os.getenv("OPENROUTER_MODEL")
            or os.getenv(
                "SARA_LLM_MODEL",
                "openai/gpt-4o-mini",
            )
        )

        self.max_tokens = self._env_int(
            "SARA_NLU_MAX_TOKENS",
            600,
            minimum=300,
            maximum=1200,
        )
        if not deterministic_first:
            # Full structured turns include location, references and workflow
            # slots; a voice-sized completion budget can truncate their JSON.
            self.max_tokens = max(self.max_tokens, 700)

        self.timeout_seconds = self._env_float(
            "SARA_LLM_TIMEOUT_SECONDS",
            20.0,
            minimum=5.0,
            maximum=120.0,
        )

        self.max_retries = self._env_int(
            "SARA_LLM_MAX_RETRIES",
            1,
            minimum=0,
            maximum=3,
        )

        # Safety net against pathologically long input (voice transcripts
        # gone wrong, copy-pasted documents, abuse). Regex-heavy parsing
        # and LLM token costs both scale with message length, so we cap it
        # rather than trusting every caller to validate first.
        self.max_message_length = self._env_int(
            "SARA_MAX_MESSAGE_LENGTH",
            2000,
            minimum=50,
            maximum=10_000,
        )

        if client is not None:
            self.client = client
            return

        key = os.getenv("OPENROUTER_API_KEY")

        if not key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured"
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Install dependencies with: "
                "pip install -r requirements.txt"
            ) from exc

        # NOTE: `max_retries` here already makes the OpenAI SDK retry
        # transient errors (rate limits, timeouts, 5xx) internally with
        # its own backoff. We intentionally do NOT re-implement a second
        # retry loop for the same failure classes in `_call_llm` below —
        # doing so previously caused duplicate, uncoordinated retries
        # (e.g. client retries 429 while our own loop also slept and
        # retried), which just multiplied latency without adding safety.
        self.client = OpenAI(
            api_key=key,
            base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ),
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )

    def understand(self, message, context=None):
        from .preference_edit import edit_cues
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be non-empty")
        context = context if isinstance(context, dict) else {}
        action, fields = edit_cues(message)
        semantic_message = message
        # In replacement clauses the left side is the OLD value, not a filter.
        semantic_message = re.sub(r"\b[\w-]+\s+ki\s+jagah\s+", "", semantic_message, flags=re.I)
        pending = context.get("preference_fields", [])
        if len(pending) == 1 and not fields and action is None:
            semantic_message = f"{pending[0].replace('_', ' ')} {semantic_message}"
        # Field-only change commands need no search extraction or model call.
        residue = re.sub(r"\b(?:preferences?|change|kar(?:na|ni|ne|o)?|kr(?:na|ni|ne|o)?|hai|hain|badal\w*|tabdeel\w*|city|budget|location|area|purpose|property|type|bedrooms?|rooms?)\b", "", message, flags=re.I)
        if action in {"cancel", "continue"} or (action == "edit" and not residue.strip(" .!?")):
            result = UserUnderstanding(intent="property_search" if action == "continue" else "unknown")
        else:
            result = self._understand(semantic_message, context)
        result.preference_action = result.preference_action or action
        result.preference_fields = list(dict.fromkeys(result.preference_fields + fields))
        result.raw_message = message.strip()[: self.max_message_length]
        return result

    def _understand(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> UserUnderstanding:
        if not isinstance(message, str):
            raise ValueError("message must be non-empty")

        raw_message = message.strip()
        if not raw_message:
            raise ValueError("message must be non-empty")

        if len(raw_message) > self.max_message_length:
            logger.warning(
                "understand(): message length %s exceeds max %s; truncating.",
                len(raw_message),
                self.max_message_length,
            )
            raw_message = raw_message[: self.max_message_length]

        # Defensive normalization: callers (voice pipeline, API layer,
        # tests) should pass a dict, but we never want a malformed
        # context object to crash NLU — treat anything else as empty.
        if not isinstance(context, dict):
            context = {}

        # Repair only generic language/schema typos. Business/location
        # values are never rewritten here.
        semantic_message = self.edge.repair_tokens(raw_message)
        semantic_message = re.sub(
            r"\bpropert\b",
            "property",
            semantic_message,
            flags=re.IGNORECASE,
        )

        deterministic = self._deterministic_understanding(
            message=semantic_message,
            context=context,
        )

        if deterministic is not None and self.deterministic_first:
            # Deterministic rich-turn parsing may return before the normal
            # post-LLM repair pipeline. Still apply explicit location and relaxation
            # language such as "Islamabad" / "area flexible hai".
            deterministic = self._repair_location_understanding(
                result=deterministic,
                raw_message=semantic_message,
                context=context,
            )
            deterministic = self._repair_relaxation_understanding(
                result=deterministic,
                raw_message=semantic_message,
            )
            deterministic.raw_message = raw_message
            return deterministic

        has_unsupported_script = bool(
            re.search(
                r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\u0900-\u097F\u4e00-\u9fff\u0400-\u04FF]",
                raw_message,
            )
        )
        has_latin_or_digits = bool(
            re.search(r"[a-zA-Z0-9\u0660-\u0669\u06F0-\u06F9]", raw_message)
        )
        if has_unsupported_script and not has_latin_or_digits:
            raise UnderstandingError("unsupported_script")

        payload = {
            "context": self._json_safe(context),
            "current_message": semantic_message,
        }

        try:
            parsed = self._call_llm(payload)

        except Exception as exc:
            logger.warning(
                "LLM understanding failed (%s: %s); falling back to "
                "deterministic parsing.",
                type(exc).__name__,
                exc,
            )

            if not self.deterministic_first:
                raise UnderstandingError("semantic understanding failed") from exc

            fallback = self._deterministic_understanding(
                message=semantic_message,
                context=context,
            )

            if fallback is not None:
                fallback = self._repair_relaxation_understanding(
                    result=fallback,
                    raw_message=semantic_message,
                )
                fallback.raw_message = raw_message
                return fallback

            # Provider-safe schema fallback:
            # preserve only explicit schema facts from the CURRENT message.
            # City/area are still verified later by chatbot.py / Day2Adapter.
            schema_fallback = UserUnderstanding(
                intent="unknown",
                raw_message=raw_message,
            )

            schema_fallback = self._repair_location_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
                context=context,
            )

            schema_fallback = self._repair_explicit_schema_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
            )

            schema_fallback = self._repair_relaxation_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
            )

            schema_fallback = self._repair_budget_understanding(
                result=schema_fallback,
                raw_message=semantic_message,
                context=context,
            )

            if (
                schema_fallback.required
                or schema_fallback.preferred
                or schema_fallback.excluded
                or schema_fallback.relax
            ):
                if schema_fallback.intent == "unknown":
                    schema_fallback.intent = "property_search"

                schema_fallback.raw_message = raw_message
                logger.info(
                    "Recovered a schema-only fallback understanding after "
                    "LLM failure (intent=%s).",
                    schema_fallback.intent,
                )
                return schema_fallback

            raise UnderstandingError(
                "semantic understanding failed"
            ) from exc

        result = self._validate(parsed, raw_message)

        # Deterministic schema repair protects explicit current-turn values
        # when the LLM omits a clear property type/bedroom/purpose.
        result = self._repair_explicit_schema_understanding(
            result=result,
            raw_message=semantic_message,
        )

        # Location repair remains based on the user's original message;
        # actual city/area validation is later grounded by Day2Adapter.
        result = self._repair_location_understanding(
            result=result,
            raw_message=raw_message,
            context=context,
        )

        result = self._repair_correction_understanding(
            result=result,
            raw_message=semantic_message,
            context=context,
        )

        result = self._repair_relaxation_understanding(
            result=result,
            raw_message=semantic_message,
        )

        result = self._repair_exact_constraint_comparison(
            result=result,
            raw_message=semantic_message,
        )

        result = self._repair_budget_understanding(
            result=result,
            raw_message=semantic_message,
            context=context,
        )

        result.raw_message = raw_message
        return result

    def _call_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Call the LLM and return its parsed JSON response.

        Includes response_format={"type": "json_object"} to force structured output,
        transient empty-choice retries with backoff and raw response logging, and
        JSON parse retries with brief delay and corrective prompt.
        """
        last_parse_err: Exception | None = None
        user_content = json.dumps(payload, ensure_ascii=False)

        for attempt in range(2):
            messages = [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": user_content},
            ]

            if attempt > 0:
                time.sleep(0.5)
                messages.append({
                    "role": "user",
                    "content": "IMPORTANT: Output ONLY a valid JSON object matching the required schema. No introductory text or markdown prose.",
                })

            response = None
            choices = None

            # Sub-retry loop specifically for transient empty choices / provider blips
            for choice_attempt in range(3):
                call_kwargs: dict[str, Any] = {
                    "model": self.model,
                    "temperature": 0,
                    "max_tokens": self.max_tokens,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                }

                try:
                    response = self.client.chat.completions.create(**call_kwargs)
                except Exception as api_err:
                    # Fallback if provider/model explicitly rejects response_format parameter
                    if "response_format" in call_kwargs and ("response_format" in str(api_err).lower() or "unsupported" in str(api_err).lower()):
                        call_kwargs.pop("response_format", None)
                        response = self.client.chat.completions.create(**call_kwargs)
                    else:
                        raise api_err

                choices = getattr(response, "choices", None)
                if choices:
                    break

                logger.warning(
                    "Provider returned no message choices (choice_attempt %s/3). Raw response object: %r",
                    choice_attempt + 1,
                    response,
                )
                time.sleep(1.0 * (choice_attempt + 1))

            if not choices:
                last_parse_err = ValueError(f"Provider returned no message choices after retries. Raw response: {response!r}")
                logger.warning(
                    "Provider returned no message choices after retries (attempt %s/2). Raw response: %r",
                    attempt + 1,
                    response,
                )
                continue

            content = choices[0].message.content or ""
            finish_reason = getattr(choices[0], "finish_reason", None)
            if finish_reason and finish_reason not in ("stop", "length"):
                logger.warning("LLM choice finish_reason is %r | Raw response: %r", finish_reason, response)

            try:
                return self._parse_json(content)
            except (ValueError, json.JSONDecodeError) as parse_err:
                last_parse_err = parse_err
                logger.warning(
                    "Malformed JSON from LLM (attempt %s/2): %s | Raw content: %r",
                    attempt + 1,
                    parse_err,
                    content,
                )

        raise last_parse_err or ValueError("LLM returned unparsable content")

    def _deterministic_understanding(
        self,
        message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding | None:
        """
        Handle small, schema-level utterances without calling the LLM.

        This is intentionally conservative. It only handles simple
        transaction-purpose follow-ups/corrections such as:

            rent k liye
            rent k liyee
            kiraye ke liye
            purchase k liye
            buy ke liye
            buying ke liye

        Business/property facts are never inferred here.
        """

        if not isinstance(message, str):
            return None

        raw = message.strip()

        if not raw:
            return None

        text = raw.casefold()

        # Normalize common Roman-Urdu spelling noise and punctuation, preserving decimal numbers (e.g. 1.2 or 6.5).
        text = re.sub(r"(?<!\d)\.|\.(?!\d)|[^a-z0-9\s\.]", " ", text)

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            return None

        # Pure greeting detection
        if re.fullmatch(
            r"(?:hi+|hello|helo|hallo|hey+|yo|salam|salaam|as+alam\s*(?:o|u)?\s*alaikum|as+alamu?alaikum|aoa|a\s*o\s*a|good\s+(?:morning|evening|afternoon))",
            text,
            flags=re.IGNORECASE,
        ):
            return UserUnderstanding(
                intent="greeting",
                raw_message=raw,
            )

        # Area relaxation: "g dusrey areas dikha dein", "mazeed areas dikhao", "dusre areas", etc.
        is_area_relax = bool(re.search(
            r"\b(?:dusre|dusray|dusrey|doosre|doosray|doosrey|other|different|aur|aor|mazeed|more|qareebi)\s+areas?\b|"
            r"\b(?:areas?|locations?)\s+(?:k[ayei]?\s+)?(?:options?\s+)?(?:dikha|dikhao|dikhayein|dikha\s*do|dikhado|check|dekh|dekhna)\b|"
            r"\b(?:kisi\s+(?:aur|aor|dusre|doosre|dusrey|doosrey)\s+area)\b|"
            r"\bkoi\s+bhi\s+(?:area|location)\b|"
            r"\b(?:area|location)\s+(?:flexible|koi\s+bhi|matter\s+nahi)\b",
            text, flags=re.IGNORECASE,
        ))
        if is_area_relax:
            city = self._extract_explicit_city(text)
            req = {"city": city} if city else {}
            return UserUnderstanding(
                intent="property_search",
                required=req,
                relax=["area"],
                raw_message=raw,
            )

        if re.fullmatch(r"(?:budget (?:flexible(?: hai)?|koi masla nahi|ka masla nahi)|no budget limit|budget koi masla nahi hai)", text):
            return UserUnderstanding(intent="property_search", relax=["budget"])
        if re.fullmatch(r"(?:sab|all|saray|saare) (?:suggest kiye hue )?areas?(?: ke)?(?: options)?(?: dikha do| dikhao| dikhayein)?", text):
            return UserUnderstanding(intent="property_search", relax=["area"])

        # Keep this fast-path limited to short conversational follow-ups.
        tokens = text.split()

        if text in {"flexible", "flexible hai", "area flexible", "area flexible hai", "koi bhi area", "area ka issue nahi"}:
            return UserUnderstanding(
                intent="property_search",
                relax=["area"],
                raw_message=raw,
            )

        # Generalized list available options queries (Cities / Areas)
        explicit_area = self._extract_explicit_area(raw)
        has_specific_area = explicit_area is not None

        interrogatives = (
            r"(?:k[ao]ns[aei]|knse?y?|"
            r"k[ao]n\s+k[ao]n\s+s[aei]|kn\s+kn\s+se?y?|"
            r"kin\s+kin|"
            r"which|what|"
            r"kitn[aei]|"
            r"list\s+(?:of\s+)?)"
        )
        city_nouns = r"(?:cities|city|shehar|shahron)"
        area_nouns = r"(?:areas?|locations?|il[ao]q[aei]|jagh[aei]|phases?|sectors?)"

        is_city_list = False
        is_area_list = False

        if not has_specific_area:
            explicit_city = self._extract_explicit_city(raw)
            if not explicit_city:
                is_city_list = bool(re.search(
                    rf"\b{interrogatives}\s+{city_nouns}\b|"
                    rf"\b{city_nouns}\s+(?:mein\s+)?(?:{interrogatives}\s+)?(?:options?\s+)?available\b|"
                    rf"\b{city_nouns}\s+(?:batao|batayein|bata\s+dein)\b|"
                    rf"\bwhich\s+cities\s+do\s+you\s+operate\b",
                    text, flags=re.IGNORECASE
                ))
            
            is_area_list = bool(re.search(
                rf"\b{interrogatives}\s+{area_nouns}\b|"
                rf"\b{area_nouns}\s+(?:k[ayei]?\s+)?(?:options?\s+)?available\b|"
                rf"\b{area_nouns}\s+(?:batao|batayein|bata\s+dein)\b|"
                rf"\boptions?\s+kya\s+hai[n]?\b|\bkya\s+options?\s+hai[n]?\b",
                text, flags=re.IGNORECASE
            ))
            has_interrogative = bool(re.search(
                rf"\b{interrogatives}\b|\bkya\s+hai[n]?\b|\bhai[n]?\s+kya\b|\bbata[aoaei]+\b|\bavailable\b",
                text, flags=re.IGNORECASE
            ))
            if is_area_list and not has_interrogative:
                is_area_list = False

        if is_city_list:
            purp = self._extract_explicit_purpose(text)
            req = {"purpose": purp} if purp else {}
            return UserUnderstanding(
                intent="CITIES_QUERY",
                required=req,
                raw_message=raw,
            )

        if is_area_list:
            city = self._extract_explicit_city(text)
            p_types = self._extract_property_types(text)
            purp = self._extract_explicit_purpose(text)
            req = {}
            if city:
                req["city"] = city
            if p_types:
                req["property_type"] = p_types[0]
            if purp:
                req["purpose"] = purp
            return UserUnderstanding(
                intent="AREAS_QUERY",
                required=req,
                raw_message=raw,
            )

        # Area suggestion requests: "area suggest kro", "koi area recommend kro", "konsa area acha hai", "ap suggest kro", "g suggest krey"
        suggest_area_pattern = (
            r"\b(?:suggest|recommend|batao|bata dein|batayein|konsa|knsa|acha|ache)\s+(?:area|sector|location)\b|"
            r"\b(?:area|sector|location)\s+(?:suggest|recommend|batao|bata dein|batayein)\b|"
            r"\b(?:ap\s+(?:hi\s+)?)?(?:suggest|recommend)\s*(?:kro|karein|krey|krti|karti|krdo|kardo)?\b|"
            r"\b(?:g|ji|jee|haan|yes)\s+(?:bhi\s+)?(?:suggest|recommend)\b|"
            r"\bap\s+batao\b|\bpata\s+nahi\s+konsa\s+area\b"
        )
        if re.search(suggest_area_pattern, text, flags=re.IGNORECASE):
            city = self._extract_explicit_city(text)
            req = {"city": city} if city else {}
            return UserUnderstanding(
                intent="property_search",
                required=req,
                relax=["area"],
                raw_message=raw,
            )

        # Same requirements check: "wahi requirements hai meri", "wahi requirements hain", "same requirements", "requiremenys wahi hai"
        same_req_pattern = (
            r"\b(?:wahi|same)\s+(?:requirements?|requiremenys?|preference|preferences|specs?|criteria)\b|"
            r"\b(?:requirements?|requiremenys?|preference|preferences)\s+(?:wahi|same)\b|"
            r"^\s*(?:wahi\s+chahiye|wahi\s+hai[n]?|same\s+hai[n]?|pichli\s+wali|pichli\s+dafa\s+wali)\s*$"
        )
        if re.search(same_req_pattern, text, flags=re.IGNORECASE):
            return UserUnderstanding(
                intent="SAME_REQUIREMENTS",
                raw_message=raw,
            )

        # Most expensive property query: "sab se mehngi property konsi hai", "sb se menghi property knsi hai karachi mein", "most expensive house"
        is_expensive_query = bool(re.search(
            r"\b(?:s[ab]b?\s*se\s*m(?:ehng|engh)[aeiouy]*|most\s*expensive|highest\s*price|maximum\s*price|costliest|sab\s*se\s*costly|sab\s*se\s*zyada\s*(?:budget|price|qeemat)\s*wal[aei])\b|"
            r"\b(?:m(?:ehng|engh)[aeiouy]*|expensive|costly)\s+(?:house|ghar|apartment|flat|plot|property|option)\s*(?:hai|kons[aei]|knsi|batao)\b",
            text, flags=re.IGNORECASE,
        )) and not bool(re.search(r"\b(?:bohat|bht|too|ye|yeh)\s+m(?:ehng|engh)[aeiouy]*\b", text, re.IGNORECASE))
        if is_expensive_query:
            city = self._extract_explicit_city(text)
            area = self._extract_explicit_area(text)
            p_types = self._extract_property_types(text)
            req = {}
            if city:
                req["city"] = city
            if area:
                req["area"] = area
            if p_types:
                req["property_type"] = p_types[0]
            return UserUnderstanding(
                intent="MOST_EXPENSIVE_PROPERTY_QUERY",
                query_property_types=p_types,
                required=req,
                raw_message=raw,
            )

        # Budget objection: "ye property bohat mehngi hai", "bohat mehnga hai", "ye bht mehngi hai"
        is_price_objection = bool(re.search(
            r"\b(?:mengh[aei]|mehng[aei]|expensive|bohat\s+mehng[aei]|bht\s+mehng[aei]|"
            r"out\s+of\s+budget|budget\s+se\s+(?:bohat\s+|bht\s+)?(?:bahar|zyada)|"
            r"price\s+(?:bohat\s+|bht\s+)?(?:zyada|high)|rate\s+(?:bohat\s+|bht\s+)?zyada)\b",
            text, flags=re.IGNORECASE,
        ))
        if is_price_objection:
            return UserUnderstanding(
                intent="BUDGET_OBJECTION",
                raw_message=raw,
            )

        # Cheapest property query: "sab se sasta house konsa hai", "cheapest property konsi hai"
        is_cheapest_query = bool(re.search(
            r"\b(?:sab\s*se\s*sast[aei]\s+(?:house|ghar|apartment|flat|plot|property|option)|"
            r"cheapest\s+(?:house|property|apartment|option)|"
            r"sab\s*se\s*kam\s*price\s*wal[aei]\s+(?:house|ghar|property|apartment))\b|"
            r"\b(?:sab\s*se\s*sast[aei]|cheapest)\s*(?:hai|kons[aei]|knsi|batao)\b",
            text, flags=re.IGNORECASE,
        ))
        if is_cheapest_query:
            city = self._extract_explicit_city(text)
            area = self._extract_explicit_area(text)
            p_types = self._extract_property_types(text)
            req = {}
            if city:
                req["city"] = city
            if area:
                req["area"] = area
            if p_types:
                req["property_type"] = p_types[0]
            return UserUnderstanding(
                intent="CHEAPEST_PROPERTY_QUERY",
                query_property_types=p_types,
                required=req,
                raw_message=raw,
            )

        # Minimum budget query: "minimum budget kitna hona chahey", "minimum budget kitna hai", "starting price kya hai"
        is_min_budget_query = bool(re.search(
            r"\b(?:minimum\s*budget|min\s*budget|kam\s*(?:az\s*kam|se\s*kam)\s*budget|"
            r"starting\s*price|starting\s*budget|sab\s*se\s*kam\s*(?:price|budget|rate))\s*(?:kitna|kya|hona|chahiye|chahey)?\b|"
            r"\b(?:kitna|kya)\s*(?:minimum|min|kam\s*se\s*kam)\s*budget\b|"
            r"\bminimum\s*budget\s*kitna\b|"
            r"\bbudget\s*(?:kitna|kya)\s*hona\s*(?:chahiye|chahey)\b|"
            r"\bstarting\s*price\b",
            text, flags=re.IGNORECASE,
        ))
        if is_min_budget_query:
            p_types = self._extract_property_types(text)
            return UserUnderstanding(
                intent="MINIMUM_BUDGET_QUERY",
                query_property_types=p_types,
                required={"property_type": p_types[0]} if len(p_types) == 1 else {},
                raw_message=raw,
            )

        # Property type by budget query: "1.2 crore mein apartment aye ga ya house", "1.2 crore mein kya milega"
        is_type_by_budget = bool(re.search(
            r"\b(?:\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b|\b\d+\b)\s+mein\s+(?:kya\s+milega|apartment\s+aye\s*ga\s+ya\s+house|house\s+aye\s*ga\s+ya\s+apartment|kya\s+aa\s+sakta\s+hai|kuch\s+milega|kya\s+options?\s+hai[n]?|options?\s+hai[n]?|kya\s+hai)\b|"
            r"\bis\s+budget\s+mein\s+(?:apartment\s+milega\s+ya\s+house|house\s+milega\s+ya\s+apartment|kya\s+milega|kya\s+aa\s+sakta\s+hai|kya\s+options?\s+hai[n]?)\b|"
            r"\bapartment\s+sasta\s+hai\s+ya\s+house\b|"
            r"\bmera\s+budget\s+kis\s+property\s+type\s+ke\s+liye\s+enough\s+hai\b|"
            r"\b(?:\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b)\s+mein\s+.*\b(?:aye\s*ga|milega|aa\s*sakta|hoga)\b",
            text, flags=re.IGNORECASE,
        )) or (
            ("?" in raw or re.search(r"\b(?:aye\s*ga|milega|hoga)\b", text, re.IGNORECASE))
            and re.search(r"\b(?:apartment|house|flat|ghar)\b", text, re.IGNORECASE)
            and re.search(r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b", text, re.IGNORECASE)
        )
        if is_type_by_budget:
            q_budget = self._extract_budget_amount(text)
            p_types = self._extract_property_types(text)
            return UserUnderstanding(
                intent="PROPERTY_TYPE_BY_BUDGET_QUERY",
                query_budget=q_budget,
                query_property_types=p_types,
                raw_message=raw,
            )

        # Budget feasibility query: "mera budget enough hai?", "kya 1.2 crore kafi hai?", "kiya dha phase 6 mein meray budget k according options available hai"
        is_budget_feasibility = bool(re.search(
            r"\b(?:mera\s+budget\s+enough\s+hai|kya\s+mera\s+budget\s+kafi\s+hai|kya\s+(?:\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k))\s+enough\s+hai|budget\s+kafi\s+hoga)\b|"
            r"\b(?:kiya|kya)?\s*.*?\b(?:meray|mere|apka|mera)?\s*budget\s*(?:k|ke)?\s*(?:according|mutabiq|hisaab)\s*(?:options?|properties?)\s*(?:available|hai[n]?)\b|"
            r"\b(?:budget\s*(?:ke|k)?\s*(?:according|mutabiq|hisaab))\b",
            text, flags=re.IGNORECASE,
        ))
        if is_budget_feasibility:
            q_budget = self._extract_budget_amount(text)
            explicit_area = self._extract_explicit_area(raw)
            req = {"area": explicit_area} if explicit_area else {}
            return UserUnderstanding(
                intent="BUDGET_FEASIBILITY_QUERY",
                query_budget=q_budget,
                required=req,
                raw_message=raw,
            )

        # Change preference: explicit command like "mera budget 1.2 crore kar do", "ab mera budget 1.2 crore hai"
        is_pref_update = bool(re.search(
            r"\b(?:mera\s+budget|budget)\s*(?:ab\s+)?(?:\d+.*?)\s*(?:kar\s+do|kr\s+do|kardein|rakho|set\s+karo)\b|"
            r"\b(?:ab\s+)?(?:mera\s+budget|budget)\s+(?:\d+.*?)\s*(?:hai|krna\s+hai)\b|"
            r"\b(?:\d+.*?)\s*tak\s+(?:options?|properties?)\s+(?:dikhao|dikhayein|dikhado)\b",
            text, flags=re.IGNORECASE,
        ))
        if is_pref_update:
            b_amt = self._extract_budget_amount(text)
            req = {"budget": b_amt} if b_amt else {}
            return UserUnderstanding(
                intent="CHANGE_PREFERENCE",
                required=req,
                raw_message=raw,
            )

        # Confirmation queries: "haan", "theek hai", "g dekhna chahu gi", "wahi chahiye", "haan dikha do"
        confirmation_pattern = (
            r"^\s*(?:"
            r"haan|theek\s+hai|sahi\s+hai|ji\s+haan|ji\s+bilkul|ji|jee|g|yes|"
            r"g\s+zaroor|ji\s+zaroor|zaroor|"
            r"(?:g|ji|jee|haan)?\s*(?:dekhna\s+(?:chahu|chahungi|chahu\s*gi|chahti\s+hoon|chahta\s+hoon|hai)|dikhayein|dikha\s*do|dikhado|dikha\s+dein)|"
            r"wahi|wahi\s+chahiye|wahi\s+requirement|wahi\s+requirements?\s*(?:hai[n]?)?|"
            r"haan\s+wahi|haan\s+wahi\s+chahiye|haan\s+dikha\s*do|haan\s+dikhao|haan\s+dikhayein|"
            r"haan\s+doosre\s+areas|haan\s+doosre\s+areas\s+bhi\s+dikha\s*do"
            r")\s*$"
        )
        if re.search(confirmation_pattern, text, flags=re.IGNORECASE):
            return UserUnderstanding(
                intent="property_search",
                raw_message=raw,
            )

        # Decline queries: "nahi", "nahi sirf b-17 hi chahiye", "nahi rehndo"
        if re.search(r"^\s*(?:nahi|nahin|no)\b", text, flags=re.IGNORECASE):
            explicit_area = self._extract_explicit_area(raw)
            req = {"area": explicit_area} if explicit_area else {}
            return UserUnderstanding(
                intent="property_search",
                required=req,
                raw_message=raw,
            )

        # More options / pagination queries: "is k ilawa", "in k ilawa", "aur options", "koi aur option", "aur kya options"
        more_options_pattern = (
            r"\b(?:is|in|un|iske|inke|unke)\s*(?:ke|k|kay)?\s*(?:ilawa|elawa|alawa|lawa)\b|"
            r"\b(?:aur|aor|mazeed|more|koi\s+(?:aur|aor)|agla|next|knsey|konse|kaunsay|kn\s*kn\s*se[y]?)\s+(?:kya\s+|knsey\s+|konse\s+|kaunsay\s+|kn\s*kn\s*se[y]?\s+|bhi\s+)?(?:options?|properties|plots?|ghars?|houses?|flats?|apartments?|dikhao|dikhayein|hai|hain|available)\b"
        )
        if re.search(more_options_pattern, text, flags=re.IGNORECASE):
            explicit_area = self._extract_explicit_area(raw)
            explicit_city = self._extract_explicit_city(raw)
            req = {}
            if explicit_area:
                req["area"] = explicit_area
            if explicit_city:
                req["city"] = explicit_city
            relax = ["budget"]
            if not explicit_area:
                relax.append("area")
            return UserUnderstanding(
                intent="property_search",
                required=req,
                relax=relax,
                raw_message=raw,
            )

        # Recommendation / cheapest among options: "property recommend kro", "konsa best hai", "inme se sabse sasta wala kaunsa hai"
        recommend_pattern = r"\b(?:recommend|mashwara|kons[ayie]\s+(?:best|ach[ayie]|sahi|sast[ayie]|kam)|best\s+option|behtareen\s+option|sabse\s+sast[ayie]|sabse\s+kam|cheapest|lowest\s+price)\b"
        if re.search(recommend_pattern, text, flags=re.IGNORECASE):
            return UserUnderstanding(
                intent="recommendation",
                raw_message=raw,
            )

        # Budget inquiry: "max budget kitna hona chahey", "kitna budget chahiye"
        budget_inquiry_pattern = r"\b(?:budget\s*(?:kitna|kya|hona)|kitna\s*budget|max\s*budget|minimum\s*budget|min\s*budget|starting\s*price|price\s*range)\b"
        if re.search(budget_inquiry_pattern, text, flags=re.IGNORECASE):
            return UserUnderstanding(
                intent="MINIMUM_BUDGET_QUERY",
                raw_message=raw,
            )

        # Explicit area selection: "mujhey DHA Phase 8 mrein dekhna hai", "DHA Phase 8 mein", "DHA Phase 8 chahiye"
        explicit_area = self._extract_explicit_area(raw)
        has_contradiction = bool(re.search(
            r"\b(?:lakin|lekin|magar|kyun|kyu|pehle|pahle|phir\s+bhi)\b",
            text, re.IGNORECASE
        ))
        all_found_areas = re.findall(
            r"\b(?:DHA\s+Phase\s*[-#]?\s*[A-Za-z0-9]+|Sector\s*[-#]?\s*[A-Za-z0-9]+|Block\s*[-#]?\s*[A-Za-z0-9]+)\b",
            raw, re.IGNORECASE
        )
        has_multiple_areas = len(set(a.lower() for a in all_found_areas)) > 1
        if (
            explicit_area
            and not has_contradiction
            and not has_multiple_areas
            and not re.search(r"\b(?:kitna|kya|enough|kafi|starting|sasta|cheap)\b", text, re.IGNORECASE)
        ):
            area_intent_cues = bool(re.search(
                r"\b(?:dekhna|dekhni|dikhao|dikhayein|dikhado|dikha|chahiye|mein|me|main|mrein|options?)\b",
                text, re.IGNORECASE
            )) or len(text.split()) <= 4
            if area_intent_cues:
                req = {"area": explicit_area}
                p_types = self._extract_property_types(text)
                if len(p_types) == 1:
                    req["property_type"] = p_types[0]
                purp = self._extract_explicit_purpose(text)
                if purp:
                    req["purpose"] = purp
                return UserUnderstanding(
                    intent="property_search",
                    required=req,
                    raw_message=raw,
                )

        # --------------------------------------------------------------
        # Generic/simple property-search intent
        # --------------------------------------------------------------

        explicit_purpose = self._extract_explicit_purpose(
            text
        )

        investment_request = bool(
            re.search(
                r"\b(?:"
                r"investment\s+(?:ke|k|kay)\s+liye|"
                r"investment\s+option|"
                r"investment\s+property|"
                r"invest\s+(?:karna|krna|karni|krni)|"
                r"invest\s+(?:ke|k|kay)\s+liye|"
                r"purpose\s+investment"
                r")\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        # In this real-estate agent, an explicit request for an investment
        # property is a recommendation/search for an asset to purchase.
        # This is semantic intent normalization, not a property/business fact.
        if investment_request and explicit_purpose is None:
            explicit_purpose = "Purchase"

        deterministic_intent = (
            "recommendation"
            if investment_request
            else "property_search"
        )

        if self.edge.looks_like_generic_property_request(raw):
            # Use this fast-path only for a genuinely simple property request.
            # Rich turns must continue to semantic NLU so city, area, budget,
            # bedrooms and other explicit current-turn constraints survive.
            has_money = bool(
                re.search(
                    r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    r"\b(?:budget|max|maximum|under|upto|up to|tak)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            has_location_shape = bool(
                re.search(
                    r"\b(?:phase|sector|block)\s*[a-z0-9-]+\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(r"\b(?:mein|me|main)\b", text)
            )
            has_schema_constraint = bool(
                re.search(
                    r"\b(?:bed|beds|bedroom|bedrooms|bhk|flat|apartment|house|home|villa|plot|office|shop)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )

            if not (has_money or has_location_shape or has_schema_constraint):
                required: dict[str, Any] = {}

                if explicit_purpose:
                    required["purpose"] = explicit_purpose

                return UserUnderstanding(
                    intent=deterministic_intent,
                    required=required,
                    raw_message=raw,
                )

        # A simple explicit property-type request should also work without
        # an LLM, e.g. "apartment chahiye". Keep this conservative so
        # complex multi-constraint turns still go through semantic NLU.
        simple_types = []
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text):
                if canonical not in simple_types:
                    simple_types.append(canonical)

        request_cue = bool(
            re.search(
                r"\b(?:chahiye|dekhni|dekhna|dekh\s+rahi|dekh\s+raha|dikhao|show|find|search)\b",
                text,
            )
        )

        complex_markers = (
            "gym", "parking", "security", "pool", "amenity",
            "developer", "school", "hospital", "installment",
        )

        rich_type_turn = bool(
            explicit_purpose
            or re.search(
                r"\b(?:budget|max|maximum|under|upto|up to|tak)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b(?:phase|sector|block|mein|me)\b",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b\d{1,2}\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if (
            len(simple_types) == 1
            and request_cue
            and not rich_type_turn
            and not any(marker in text for marker in complex_markers)
            and not re.search(r"\b(?:ya|or|either)\b", text)
        ):
            return UserUnderstanding(
                intent=deterministic_intent,
                required={"property_type": simple_types[0]},
                raw_message=raw,
            )

        # --------------------------------------------------------------
        # Deterministic budget understanding
        # --------------------------------------------------------------
        budget_value = self._extract_budget_amount(
            text
        )

        if budget_value is not None:
            rich_budget_turn = bool(
                explicit_purpose
                or simple_types
                or re.search(
                    r"\b(?:phase|sector|block|mein|me)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    r"\b\d{1,2}\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                or (
                    request_cue
                    and len(tokens) >= 5
                )
            )

            # For clear multi-field search turns, preserve the explicit
            # schema facts deterministically. City/area are intentionally
            # NOT guessed here; chatbot.py verifies them against Day 2 data.
            # This keeps ordinary structured requests working even when the
            # external semantic LLM is slow/unavailable.
            if rich_budget_turn:
                soft_markers = (
                    "around",
                    "approx",
                    "approximately",
                    "roughly",
                    "takreeban",
                    "taqreeban",
                    "qareeban",
                    "kareeban",
                    "flexible",
                    "thora upar neeche",
                    "thoda upar neeche",
                    "preferred",
                    "preference",
                )

                is_soft = any(
                    marker in text
                    for marker in soft_markers
                )

                required: dict[str, Any] = {}
                preferred: dict[str, Any] = {}

                if is_soft:
                    preferred["budget"] = budget_value
                else:
                    required["budget"] = budget_value

                if explicit_purpose:
                    required["purpose"] = explicit_purpose

                if len(simple_types) == 1:
                    required["property_type"] = simple_types[0]

                bedroom_values = {
                    int(value)
                    for value in re.findall(
                        r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                        text,
                        flags=re.IGNORECASE,
                    )
                    if int(value) > 0
                }

                if len(bedroom_values) == 1:
                    required["bedrooms"] = next(iter(bedroom_values))

                detected_amenities = []
                amenity_patterns = {
                    "Swimming Pool": r"\b(?:swimming\s*pool|pool)\b",
                    "Servant Quarter": r"\b(?:servant\s*quarter|servant\s*room)\b",
                    "Gym": r"\b(?:gym|fitness\s*center)\b",
                    "Backup Generator": r"\b(?:generator|power\s*backup)\b",
                    "Lift": r"\b(?:lift|elevator)\b",
                    "Parking": r"\b(?:parking|garage)\b",
                    "Security": r"\b(?:security|cctv|guard)\b",
                    "Lawn": r"\b(?:lawn|garden)\b",
                    "Balcony": r"\b(?:balcony|terrace)\b",
                }
                for amenity_name, pattern in amenity_patterns.items():
                    if re.search(pattern, text, flags=re.IGNORECASE):
                        detected_amenities.append(amenity_name)
                if detected_amenities:
                    preferred["amenities"] = detected_amenities

                # If a clear purpose was not present, preserve the budget but
                # let ConversationPolicy ask purpose instead of guessing.
                return UserUnderstanding(
                    intent=deterministic_intent,
                    required=required,
                    preferred=preferred,
                    raw_message=raw,
                )

            soft_markers = (
                "around",
                "approx",
                "approximately",
                "roughly",
                "takreeban",
                "taqreeban",
                "qareeban",
                "kareeban",
                "flexible",
                "thora upar neeche",
                "thoda upar neeche",
                "preferred",
                "preference",
            )

            is_soft = any(
                marker in text
                for marker in soft_markers
            )

            required: dict[str, Any] = {}
            preferred: dict[str, Any] = {}

            if is_soft:
                preferred["budget"] = budget_value
            else:
                required["budget"] = budget_value

            context_required = (
                context.get("required")
                if isinstance(context, dict)
                else {}
            ) or {}

            context_preferred = (
                context.get("preferred")
                if isinstance(context, dict)
                else {}
            ) or {}

            purpose_known = bool(
                context_required.get("purpose")
                or context_preferred.get("purpose")
            )

            return UserUnderstanding(
                intent=deterministic_intent,
                required=required,
                preferred=preferred,
                excluded={},
                relax=[],
                reference_type=None,
                selected_index=None,
                comparison=ComparisonRequest(
                    None,
                    None,
                    None,
                    None,
                ),
                needs_clarification=not purpose_known,
                clarification_reason=(
                    None
                    if purpose_known
                    else "missing_purpose_for_budget"
                ),
                raw_message=raw,
            )

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )

        purpose: str | None = None

        if any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in rental_patterns
        ):
            purpose = "Rental"

        if any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in purchase_patterns
        ):
            # If both purpose families somehow occur, leave it to the
            # semantic layer instead of guessing.
            if purpose is not None:
                return None

            purpose = "Purchase"

        if purpose is None:
            return None

        # Reject obviously complex requests that merely mention rent/buy
        # alongside other new search fields. Those still belong to the LLM.
        complex_field_markers = (
            "bedroom",
            "bedrooms",
            "budget",
            "crore",
            "lakh",
            "city",
            "area",
            "sector",
            "phase",
            "block",
            "apartment",
            "flat",
            "house",
            "plot",
            "office",
            "shop",
            "developer",
            "amenity",
            "gym",
            "parking",
            # A purpose plus a location relation is no longer a purpose-only
            # follow-up. Let semantic NLU preserve the current-turn location.
            " mein ",
            " me ",
        )

        has_location_relation = bool(
            re.search(
                r"\b(?:mein|me)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if (
            has_location_relation
            or any(
                marker in text
                for marker in complex_field_markers
            )
        ):
            # Preserve the explicit purpose deterministically; verified
            # location repair later adds only Day 2-confirmed city/area.
            required = {"purpose": purpose}

            if len(simple_types) == 1:
                required["property_type"] = simple_types[0]

            bedroom_values = {
                int(value)
                for value in re.findall(
                    r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                    text,
                    flags=re.IGNORECASE,
                )
                if int(value) > 0
            }

            if len(bedroom_values) == 1:
                required["bedrooms"] = next(iter(bedroom_values))

            return UserUnderstanding(
                intent=deterministic_intent,
                required=required,
                raw_message=raw,
            )

        return UserUnderstanding(
            intent=deterministic_intent,
            required={
                "purpose": purpose,
            },
            preferred={},
            excluded={},
            relax=[],
            reference_type=None,
            selected_index=None,
            comparison=ComparisonRequest(
                None,
                None,
                None,
                None,
            ),
            needs_clarification=False,
            clarification_reason=None,
            raw_message=raw,
        )

    def _repair_explicit_schema_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """Repair explicit schema values without inventing business facts.

        This layer may recognize canonical property types, exact bedroom
        counts and transaction purpose. It never recognizes a specific
        city/area/property/developer from a hard-coded list.
        """
        normalized = " ".join(raw_message.casefold().split())

        # ---- Property type -------------------------------------------------
        # We track BOTH the alias text that actually matched and its
        # canonical form. The negation check below needs the original
        # alias (e.g. "flat"), not the canonical "Apartment" — building
        # that alias back out via a nested regex-inside-regex (as an
        # earlier version of this function did) was fragile and easy to
        # get wrong. Capturing it up front is simpler and correct.
        detected_matches: list[tuple[str, str]] = []
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if re.search(
                rf"\b{re.escape(alias)}\b",
                normalized,
                flags=re.IGNORECASE,
            ):
                detected_matches.append((alias, canonical))

        detected_types: list[str] = []
        for _alias, canonical in detected_matches:
            if canonical not in detected_types:
                detected_types.append(canonical)

        if len(detected_types) > 1:
            # "apartment ya house" is a choice, not permission to guess.
            if re.search(r"\b(?:ya|or|either)\b", normalized):
                result.required.pop("property_type", None)
                result.preferred.pop("property_type", None)
                result.needs_clarification = True
                result.clarification_reason = "ambiguous_property_type"

        elif len(detected_types) == 1:
            property_type = detected_types[0]

            matched_alias = next(
                (
                    alias
                    for alias, canonical in detected_matches
                    if canonical == property_type
                ),
                property_type.casefold(),
            )

            # Do not turn explicit negation into a positive filter.
            negative = bool(
                re.search(
                    rf"\b(?:no|not)\s+{re.escape(matched_alias)}\b|\b{re.escape(matched_alias)}\b\s+(?:nahi|nai|nahin|not|nai lena)\b",
                    normalized,
                    flags=re.IGNORECASE,
                )
            )

            if negative:
                result.required.pop("property_type", None)
                result.preferred.pop("property_type", None)
                if "property_type" not in result.excluded:
                    result.excluded["property_type"] = [property_type]
                elif property_type not in result.excluded["property_type"]:
                    result.excluded["property_type"].append(property_type)
            elif (
                "property_type" not in result.required
                and "property_type" not in result.preferred
                and property_type not in result.excluded.get("property_type", [])
            ):
                result.required["property_type"] = property_type

        # ---- Bedrooms -----------------------------------------------------
        bedroom_values = {
            int(value)
            for value in re.findall(
                r"\b(\d{1,2})\s*(?:bed|beds|bedroom|bedrooms|bhk)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            if int(value) > 0
        }

        if len(bedroom_values) > 1:
            result.required.pop("bedrooms", None)
            result.preferred.pop("bedrooms", None)
            result.needs_clarification = True
            result.clarification_reason = "ambiguous_bedrooms"
        elif len(bedroom_values) == 1 and "bedrooms" not in result.required:
            result.required["bedrooms"] = next(iter(bedroom_values))

        # ---- Purpose ------------------------------------------------------
        rental = bool(
            re.search(r"\b(?:rent|rental|kiraya|kiraye)\b", normalized)
        )
        rental_negated = bool(
            re.search(r"\b(?:rent|rental|kiraya|kiraye)\s*(?:par|pe)?\s*(?:nahi|nahin|nai|not)\b|\b(?:no|not)\s+(?:rent|rental)\b", normalized)
        )
        purchase = bool(
            re.search(r"\b(?:purchase|purchasing|buy|buying|khareedna|kharidna|investment|invest)\b", normalized)
        )
        purchase_negated = bool(
            re.search(r"\b(?:purchase|purchasing|buy|buying|khareedna|kharidna)\s*(?:nahi|nahin|nai|not)\b|\b(?:no|not)\s+(?:purchase|buy)\b", normalized)
        )

        if rental_negated:
            result.required.pop("purpose", None)
            result.preferred.pop("purpose", None)
            if "purpose" not in result.excluded:
                result.excluded["purpose"] = ["Rental"]
            elif "Rental" not in result.excluded["purpose"]:
                result.excluded["purpose"].append("Rental")

        if purchase_negated:
            result.required.pop("purpose", None)
            result.preferred.pop("purpose", None)
            if "purpose" not in result.excluded:
                result.excluded["purpose"] = ["Purchase"]
            elif "Purchase" not in result.excluded["purpose"]:
                result.excluded["purpose"].append("Purchase")

        if rental and purchase and not (rental_negated or purchase_negated):
            result.required.pop("purpose", None)
            result.preferred.pop("purpose", None)
            result.needs_clarification = True
            result.clarification_reason = "ambiguous_purpose"
        elif rental and not rental_negated and "Rental" not in result.excluded.get("purpose", []) and "purpose" not in result.required:
            result.required["purpose"] = "Rental"
        elif purchase and not purchase_negated and "Purchase" not in result.excluded.get("purpose", []) and "purpose" not in result.required:
            result.required["purpose"] = "Purchase"
        elif (
            not rental
            and not purchase
            and result.required.get("property_type") == "Plot"
            and "purpose" not in result.required
            and "Purchase" not in result.excluded.get("purpose", [])
        ):
            # In Pakistani real estate, plots are exclusively for purchase/investment
            result.required["purpose"] = "Purchase"

        # ---- Budget -------------------------------------------------------
        if "budget" not in result.required and "budget" not in result.preferred:
            extracted_budget = self._extract_budget_amount(normalized)
            if extracted_budget is not None:
                if self._looks_like_soft_preference(normalized) or re.search(r"\b(?:around|approx|approximately|takreeban|taqreeban)\b", normalized, flags=re.IGNORECASE):
                    result.preferred["budget"] = extracted_budget
                else:
                    result.required["budget"] = extracted_budget

        # ---- Amenities ----------------------------------------------------
        detected_amenities = []
        excluded_amenities = []
        amenity_patterns = {
            "Swimming Pool": r"\b(?:swimming\s*pool|pool)\b",
            "Servant Quarter": r"\b(?:servant\s*quarter|servant\s*room)\b",
            "Gym": r"\b(?:gym|fitness\s*center)\b",
            "Backup Generator": r"\b(?:generator|power\s*backup)\b",
            "Lift": r"\b(?:lift|elevator)\b",
            "Parking": r"\b(?:parking|garage)\b",
            "Security": r"\b(?:security|cctv|guard)\b",
            "Lawn": r"\b(?:lawn|garden)\b",
            "Balcony": r"\b(?:balcony|terrace)\b",
        }
        for amenity_name, pattern in amenity_patterns.items():
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                is_negated = bool(re.search(rf"\b(?:no|not|baghair|bagair|without)\s+.*{pattern}\b|{pattern}\s+.*(?:nahi|nahin|nai|not|baghair|bagair)\b|{pattern}\s+(?:nahi|nahin|nai|not|ke\s+baghair)\b", normalized, flags=re.IGNORECASE))
                if is_negated:
                    excluded_amenities.append(amenity_name)
                elif amenity_name not in result.excluded.get("amenities", []):
                    detected_amenities.append(amenity_name)

        if excluded_amenities:
            if "amenities" not in result.excluded:
                result.excluded["amenities"] = excluded_amenities
            else:
                for a in excluded_amenities:
                    if a not in result.excluded["amenities"]:
                        result.excluded["amenities"].append(a)
            if "amenities" in result.preferred:
                result.preferred["amenities"] = [a for a in result.preferred["amenities"] if a not in excluded_amenities]
            if "amenities" in result.required:
                result.required["amenities"] = [a for a in result.required["amenities"] if a not in excluded_amenities]

        if detected_amenities and "amenities" not in result.required and "amenities" not in result.preferred:
            result.preferred["amenities"] = detected_amenities

        if (
            result.intent == "unknown"
            and (
                result.required
                or result.preferred
                or result.excluded
            )
        ):
            result.intent = "property_search"

        return result

    def _extract_budget_amount(
        self,
        text: str,
    ) -> int | None:
        """
        Parse common PKR budget expressions deterministically.

        Supported examples:
            3 crore
            5 corore   (common typing noise)
            2.5 crore
            1.5 lakh / lac
            150k
            budget 150000

        Money-unit spelling normalization is language handling only;
        it does not introduce any property/business fact.
        """

        if not isinstance(text, str):
            return None

        normalized = " ".join(
            text.casefold()
            .replace(",", "")
            .split()
        )

        if not normalized:
            return None

        has_budget_word = bool(
            re.search(
                r"\b(?:budget|max|maximum|under|upto|up\s+to|tak)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

        # Check for range: e.g. "50-60 million", "3 to 4 crore", "50 - 60 lakh"
        range_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(?:-|to|se|tak)\s*(\d+(?:\.\d+)?)\s*(crore|corore|carore|cror|cr|lakh|lac|million|mil|m|k)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        raw_result = None
        if range_match:
            unit = range_match.group(3).lower()
            val = float(range_match.group(2))
            if unit in ("crore", "corore", "carore", "cror", "cr"):
                raw_result = int(val * 10_000_000)
            elif unit in ("lakh", "lac"):
                raw_result = int(val * 100_000)
            elif unit in ("million", "mil", "m"):
                raw_result = int(val * 1_000_000)
            elif unit == "k":
                raw_result = int(val * 1_000)

        if raw_result is None:
            crore_match = re.search(
                r"\b(\d+(?:\.\d+)?)\s*(?:crore|corore|carore|cror|cr)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            if crore_match:
                raw_result = int(
                    float(crore_match.group(1))
                    * 10_000_000
                )

        if raw_result is None:
            million_match = re.search(
                r"\b(\d+(?:\.\d+)?)\s*(?:million|mil|m)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            if million_match:
                raw_result = int(
                    float(million_match.group(1))
                    * 1_000_000
                )

        if raw_result is None:
            lakh_match = re.search(
                r"\b(\d+(?:\.\d+)?)\s*(?:lakh|lac)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            if lakh_match:
                raw_result = int(
                    float(lakh_match.group(1))
                    * 100_000
                )

        if raw_result is None:
            # Match "k" as thousands, e.g. "50k", "150k".
            # In Roman Urdu, "k" is commonly the preposition "ke" (e.g. "phase 8 k options", "meray budget k according").
            for k_m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*k\b", normalized, flags=re.IGNORECASE):
                start, end = k_m.span()
                full_str = k_m.group(0).lower()
                prefix = normalized[:start].strip().split()
                suffix = normalized[end:].strip().split()
                last_before = prefix[-1].lower() if prefix else ""
                first_after = suffix[0].lower() if suffix else ""
                if last_before in {"phase", "sector", "block", "street", "gali", "floor", "bed", "bedroom", "room"}:
                    continue
                if " " in full_str:
                    if first_after in {"options", "option", "mutabiq", "hisaab", "according", "liye", "baad", "se", "mein", "me", "main", "pe", "par", "wali", "wala", "walay", "wale", "dekhna", "dikha", "dikhayein", "dikhado"}:
                        continue
                    if not has_budget_word:
                        continue
                val = float(k_m.group(1))
                if val >= 10 or has_budget_word:
                    raw_result = int(val * 1_000)
                    break

        if raw_result is None and has_budget_word:
            number_match = re.search(
                r"\b(\d{4,})\b",
                normalized,
            )

            if number_match:
                raw_result = int(
                    number_match.group(1)
                )

        if raw_result is not None and raw_result > 0:
            return raw_result

        return None

    def _extract_property_types(self, text: str) -> list[str]:
        """Extract canonical property types (Apartment, House, Plot, etc.) mentioned in text."""
        if not isinstance(text, str):
            return []
        types = []
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE):
                if canonical not in types:
                    types.append(canonical)
        return types

    def _env_int(
        self,
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        raw = os.getenv(
            name
        )

        if raw is None:
            return default

        try:
            value = int(
                raw
            )
        except (
            TypeError,
            ValueError,
        ):
            logger.warning(
                "Invalid int env value for %s=%r; using default %s.",
                name, raw, default,
            )
            return default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    def _env_float(
        self,
        name: str,
        default: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:
        raw = os.getenv(
            name
        )

        if raw is None:
            return default

        try:
            value = float(
                raw
            )
        except (
            TypeError,
            ValueError,
        ):
            logger.warning(
                "Invalid float env value for %s=%r; using default %s.",
                name, raw, default,
            )
            return default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    def _extract_explicit_purpose(
        self,
        text: str,
    ) -> str | None:

        normalized = text.casefold()

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )
        if any(
            re.search(pattern, normalized)
            for pattern in rental_patterns
        ):
            return "Rental"

        if any(
            re.search(pattern, normalized)
            for pattern in purchase_patterns
        ):
            return "Purchase"

        return None

    def _system_prompt(self) -> str:
        return """
You are the semantic NLU layer for Sara, a Pakistani real-estate
sales assistant.

Return ONLY valid JSON.
Do NOT answer the user.
Do NOT invent property or business facts.

Schema:

{
  "intent": "unknown",
  "preference_action": null,
  "preference_fields": [],
  "required": {},
  "preferred": {},
  "excluded": {},
  "relax": [],
  "reference_type": null,
  "selected_index": null,
    "interaction_action": null,
    "interaction_property_id": null,
  "appointment_id": null,
  "starts_at": null,
  "comparison": {
    "field": null,
    "operator": null,
    "reference": null,
    "value": null
  },
  "needs_clarification": false,
  "clarification_reason": null
}

Allowed intents:

For changing saved preferences set preference_action to "edit" and
preference_fields to the requested fields (city, area, budget, property_type,
purpose, bedrooms, amenities). Use "continue" to keep them, "cancel" to cancel
an edit. Recognize UrduLish paraphrases as well as English. Field-only edit
requests have no required values. Never copy old values from context into
required. context.preference_state and context.preference_fields identify an
active edit and the values being requested; interpret short replies accordingly.
In replacements such as "Karachi ki jagah Lahore", extract only the NEW value.

For appointment requests extract appointment_id only when explicitly supplied.
Extract starts_at as an ISO 8601 date/time with timezone only when the user
supplies an unambiguous date and time. Use context.current_date and
context.timezone for relative dates. Never invent a missing time or date.
If context.pending_action is a visit workflow, a date/time answer continues
that workflow's intent. Never treat identity/contact data as preferences.

property_search
property_details
property_selection
recommendation
availability
faq
objection
schedule_visit
reschedule_visit
cancel_visit
greeting
reset
off_topic
unknown
same_requirements
change_preference
budget_objection
minimum_budget_query
budget_feasibility_query
property_type_by_budget_query
cheapest_property_query
book_visit

When user asks a question about what is available in a budget (e.g. "1.2 crore mein apartment aye ga ya house?", "1.2 crore mein kya milega?"):
- Use intent "property_type_by_budget_query" or "budget_feasibility_query".
- Do NOT extract the budget into "required"! A question is NOT a confirmed preference update.
- Only extract "budget" into "required" when user explicitly commands an update (e.g. "mera budget 1.2 crore kar do", "ab mera budget 1.2 crore hai", "1.2 crore tak options dikhao").

Use off_topic when the user's request is clearly outside real estate,
property discovery, property visits, or the supported customer workflow.
Examples include weather, sports, politics, recipes, coding help, jokes,
general trivia, and requests to perform unrelated tasks. Do not use
off_topic for a vague or incomplete property question; use unknown and
request clarification instead.

Allowed filter fields:

budget
city
area
bedrooms
property_type
purpose
amenities
investment_goal
developer


IMPORTANT MEMORY RULE

Extract ONLY changes expressed in the CURRENT message.

Do not copy old city, area, budget, bedrooms or other filters from
conversation context into required/preferred/excluded.

Application memory will merge current-turn changes with previous state.


CONSTRAINT STRENGTH

Use "required" when the user expresses a hard requirement.

Examples:

"Mujhe Lahore mein flat chahiye"

required:
{
  "city": "Lahore",
  "property_type": "Apartment"
}

"Sirf DHA mein"

required:
{
  "area": "DHA"
}

"Maximum 150k"

required:
{
  "budget": 150000
}


Use "preferred" for soft preferences.

Examples:

"DHA preferred hai"

preferred:
{
  "area": "DHA"
}

"Gym ho to acha hai"

preferred:
{
  "amenities": ["Gym"]
}

"Budget around 3 crore hai"

preferred:
{
  "budget": 30000000
}

"Mera budget 3 crore hai"

required:
{
  "budget": 30000000
}

A plain stated budget is normally a HARD maximum budget unless the user
uses soft wording such as around, approximately, takreeban, flexible,
or preferred.


Use "excluded" for things the user does not want.

Examples:

"Bahria nahi chahiye"

excluded:
{
  "area": ["Bahria"]
}

"DHA aur Bahria ke ilawa"

excluded:
{
  "area": ["DHA", "Bahria"]
}

"Apartment nahi chahiye"

excluded:
{
  "property_type": ["Apartment"]
}


Use "relax" when an OLD constraint should be removed entirely.

Examples:

"Area flexible hai"

relax:
["area"]

"Sector koi bhi ho"
"Chahey sector koi b ho"
"Location koi bhi chalegi"

relax:
["area"]

IMPORTANT:
Do NOT extract fake areas such as "sector koi", "area koi", or
"location flexible". These phrases mean the old area constraint is
being relaxed.

"Budget ka issue nahi"

relax:
["budget"]

"Bedrooms koi bhi chalein ge"

relax:
["bedrooms"]


PROPERTY TYPE NORMALIZATION

Normalize ordinary Pakistani real-estate wording into these canonical
property types:

flat / flats / apartment / apartments
-> Apartment

house / home / villa
-> House

office / office space
-> Office

shop / retail shop
-> Shop

plot
-> Plot

If the user explicitly asks for a property type, normally treat it as
required unless they clearly say it is optional/preferred.

Examples:

"Mujhe flat chahiye"

required:
{
  "property_type": "Apartment"
}

"Apartment preferred hai"

preferred:
{
  "property_type": "Apartment"
}

"House nahi chahiye"

excluded:
{
  "property_type": ["House"]
}


PURPOSE NORMALIZATION

rent / rental / kiraya / kiraye pe
-> Rental

buy / purchase / purchasing / khareedna / investment property request
-> Purchase


MONEY NORMALIZATION

Normalize clear PKR expressions.

150k
-> 150000

1.5 lakh
-> 150000

3 crore
-> 30000000

2.5 crore
-> 25000000


LOCATION RULES

Do NOT hard-code actual place names.

Extract whatever city, area, phase, sector, society or location the
user actually mentions.

Examples:

"DHA mein sirf"

required:
{
  "area": "DHA"
}

"DHA Phase 6"

required:
{
  "area": "DHA Phase 6"
}

"Lahore"

required:
{
  "city": "Lahore"
}


INCOMPLETE LOCATION RULE

Do not guess a missing phase, sector, block or identifier.

If the user appears to give an incomplete location such as:

"DHA Phase only"
"Sector mein dikhao"
"Block wala"

and the missing identifier is necessary to understand the intended
location, set:

"needs_clarification": true

and use:

"clarification_reason": "incomplete_location"


REFERENCE RULES

first / pehli
-> selected_index 0

second / dusri
-> selected_index 1

third / teesri
-> selected_index 2

When selecting a numbered result:
intent = property_selection

FEEDBACK RULES

For explicit customer feedback about a shown property, set exactly one:

"interaction_action": "liked" | "rejected" | "shortlisted"

"Mujhe second wali pasand hai" -> interaction_action liked, selected_index 1.
"First wali reject kar dein" -> interaction_action rejected, selected_index 0.
"Third property shortlist kar do" -> interaction_action shortlisted, selected_index 2.
These are feedback actions, not requests for property details or new searches.
context.last_results is the latest PRESENTED list in display order. An entry's
property_id is sufficient to resolve its ordinal; no additional property facts
are needed to resolve a numbered choice. Do not ask for clarification for an
explicit ordinal within this list. An unselected "this one" with several
results remains ambiguous.

Use selected_index for "first", "second", or "third" shown results. Use
interaction_property_id only when the customer explicitly names a property ID
that is present in the current shown-result context. If the property cannot be
resolved reliably, leave the interaction fields null and request clarification.

"iski details"
"uski details"
"this property's details"

If a selected property is clearly available in context:
intent = property_details
reference_type = selected_property

If reference cannot be resolved reliably:
needs_clarification = true
clarification_reason = "ambiguous_reference"


COMPARISON RULES

cheaper / sasti
-> field price, operator lt

more expensive / mehngi
-> field price, operator gt

more bedrooms
-> bedrooms gt

fewer bedrooms
-> bedrooms lt

An exact bedroom request is NOT a comparison.

"3 bedrooms wala dikhao"
-> required {"bedrooms": 3}
-> comparison must be null

"3 bedrooms dikhao chahey sector koi bhi ho"
-> required {"bedrooms": 3}
-> relax ["area"]
-> comparison must be null

larger plot
-> plot_size gt

smaller plot
-> plot_size lt

larger covered area
-> covered_area gt

smaller covered area
-> covered_area lt

comparison.value should normally be null because the verified comparison
value must come from database-backed conversation memory.


OTHER INTENTS

Question about whether selected property is available:
-> availability

Book / schedule / arrange property visit:
-> schedule_visit

Move / change an existing visit:
-> reschedule_visit

Cancel visit:
-> cancel_visit

Investment property / investment option search:
-> recommendation

Price concern, trust concern, location concern, investment-risk/return concern,
builder/developer concern or maintenance concern:
-> objection

General process, company information, brochure or FAQ question:
-> faq


SAFETY RULE

Never invent:

price
availability
ROI
future appreciation
developer reputation
amenities
payment plans
school distance
hospital distance
appointment confirmation
agent information

This layer only understands and structures what the user said.
"""

    def _parse_json(
        self,
        content: str,
    ) -> dict[str, Any]:

        text = content.strip()

        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )

            text = re.sub(
                r"\s*```$",
                "",
                text,
            )

        try:
            value = json.loads(text)
        except (ValueError, json.JSONDecodeError):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                cleaned_text = match.group(0)
                cleaned_text = re.sub(r",\s*([\}\]])", r"\1", cleaned_text)
                cleaned_text = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', cleaned_text)
                cleaned_text = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', cleaned_text)
                try:
                    value = json.loads(cleaned_text)
                except (ValueError, json.JSONDecodeError):
                    try:
                        import ast
                        value = ast.literal_eval(cleaned_text)
                    except Exception:
                        raise
            else:
                raise

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "expected JSON object"
            )

        return value

    def _validate(
        self,
        p: dict[str, Any],
        raw: str,
    ) -> UserUnderstanding:

        intent = (
            p.get("intent")
            if p.get("intent") in INTENTS
            else "unknown"
        )

        required = self._clean_filter_map(
            p.get("required")
        )

        preferred = self._clean_filter_map(
            p.get("preferred")
        )

        excluded = self._clean_excluded_map(
            p.get("excluded")
        )

        relax = p.get(
            "relax",
            [],
        )

        if not isinstance(
            relax,
            list,
        ):
            relax = []

        relax = [
            field_name
            for field_name in relax
            if field_name in FIELDS
        ]

        ref = p.get(
            "reference_type"
        )

        if ref not in REFERENCES:
            ref = None

        idx = p.get(
            "selected_index"
        )

        if (
            isinstance(idx, bool)
            or not isinstance(idx, int)
        ):
            idx = None

        interaction_action = p.get("interaction_action")
        if interaction_action not in INTERACTION_ACTIONS:
            interaction_action = None

        interaction_property_id = p.get("interaction_property_id")
        if not isinstance(interaction_property_id, str) or not interaction_property_id.strip():
            interaction_property_id = None
        elif len(interaction_property_id.strip()) > 50:
            interaction_property_id = None
        else:
            interaction_property_id = interaction_property_id.strip()

        comparison_raw = p.get(
            "comparison",
            {},
        )

        if not isinstance(
            comparison_raw,
            dict,
        ):
            comparison_raw = {}

        comparison_field = (
            comparison_raw.get("field")
            if comparison_raw.get("field")
            in COMP_FIELDS
            else None
        )

        comparison_operator = (
            comparison_raw.get("operator")
            if comparison_raw.get("operator")
            in COMP_OPS
            else None
        )

        comparison_reference = (
            comparison_raw.get("reference")
            if comparison_raw.get("reference")
            in REFERENCES
            else None
        )

        comparison_value = (
            comparison_raw.get("value")
        )

        if (
            isinstance(
                comparison_value,
                bool,
            )
            or not isinstance(
                comparison_value,
                (int, float),
            )
        ):
            comparison_value = None

        if (
            not comparison_field
            or not comparison_operator
        ):
            comparison_field = None
            comparison_operator = None
            comparison_reference = None
            comparison_value = None

        clarification_reason = (
            p.get(
                "clarification_reason"
            )
        )

        if not isinstance(
            clarification_reason,
            str,
        ):
            clarification_reason = None

        needs_clarification = bool(
            p.get(
                "needs_clarification",
                False,
            )
        )

        # Guard against false-positive incomplete-location decisions.
        # Example: "DHA Phase 5" already contains a concrete phase number.
        # This is generic schema validation; no business/place names are hard-coded.
        if (
            needs_clarification
            and clarification_reason == "incomplete_location"
        ):
            area_value = (
                required.get("area")
                or preferred.get("area")
            )

            if self._has_location_identifier(area_value):
                needs_clarification = False
                clarification_reason = None

        return UserUnderstanding(
            intent=intent,
            preference_action=p.get("preference_action") if p.get("preference_action") in {"edit", "continue", "cancel"} else None,
            preference_fields=[f for f in p.get("preference_fields", []) if f in FIELDS] if isinstance(p.get("preference_fields"), list) else [],
            required=required,
            preferred=preferred,
            excluded=excluded,
            relax=relax,
            reference_type=ref,
            selected_index=idx,
            interaction_action=interaction_action,
            interaction_property_id=interaction_property_id,
            comparison=ComparisonRequest(
                comparison_field,
                comparison_operator,
                comparison_reference,
                comparison_value,
            ),
            needs_clarification=needs_clarification,
            clarification_reason=clarification_reason,
            raw_message=raw,
            appointment_id=p.get("appointment_id") if isinstance(p.get("appointment_id"), str) and len(p["appointment_id"]) <= 36 else None,
            starts_at=p.get("starts_at") if isinstance(p.get("starts_at"), str) and len(p["starts_at"]) <= 64 else None,
        )

    def _clean_filter_map(
        self,
        raw_map: Any,
    ) -> dict[str, Any]:

        if not isinstance(
            raw_map,
            dict,
        ):
            return {}

        cleaned: dict[str, Any] = {}

        for key, value in raw_map.items():

            if key not in FIELDS:
                continue

            if value in (
                None,
                "",
                [],
            ):
                continue

            value = self._normalize_filter_value(
                key,
                value,
            )

            if value not in (
                None,
                "",
                [],
            ):
                cleaned[key] = value

        return cleaned

    def _clean_excluded_map(
        self,
        raw_map: Any,
    ) -> dict[str, list[Any]]:

        if not isinstance(
            raw_map,
            dict,
        ):
            return {}

        cleaned: dict[
            str,
            list[Any],
        ] = {}

        for key, value in raw_map.items():

            if key not in FIELDS:
                continue

            values = (
                value
                if isinstance(
                    value,
                    list,
                )
                else [value]
            )

            normalized_values = []

            for item in values:

                if item in (
                    None,
                    "",
                ):
                    continue

                item = (
                    self._normalize_filter_value(
                        key,
                        item,
                    )
                )

                if item not in (
                    None,
                    "",
                ):
                    normalized_values.append(
                        item
                    )

            if normalized_values:
                cleaned[key] = (
                    normalized_values
                )

        return cleaned

    def _normalize_filter_value(
        self,
        field_name: str,
        value: Any,
    ) -> Any:

        if field_name == "property_type":
            return self._normalize_property_type(
                value
            )

        if field_name == "purpose":
            return self._normalize_purpose(
                value
            )

        if field_name == "budget":
            if isinstance(value, (int, float)):
                return int(value) if value > 0 else None
            return None

        if field_name == "bedrooms":
            if isinstance(
                value,
                bool,
            ):
                return value

            if isinstance(
                value,
                (int, float),
            ):
                return int(value)

        return value

    def _normalize_property_type(
        self,
        value: Any,
    ) -> Any:

        if not isinstance(
            value,
            str,
        ):
            return value

        cleaned = (
            value
            .strip()
            .casefold()
        )

        return PROPERTY_TYPE_ALIASES.get(
            cleaned,
            value.strip(),
        )

    def _normalize_purpose(
        self,
        value: Any,
    ) -> Any:

        if not isinstance(
            value,
            str,
        ):
            return value

        cleaned = (
            value
            .strip()
            .casefold()
        )

        return PURPOSE_ALIASES.get(
            cleaned,
            value.strip(),
        )

    def _has_location_identifier(
        self,
        area: Any,
    ) -> bool:
        """
        Return True when an area expression already contains a concrete
        phase, sector, or block identifier.

        Examples considered complete:
        - "DHA Phase 5"
        - "Phase 6"
        - "Sector F-11"
        - "Block C"

        No actual society/city/developer names are hard-coded here.
        """

        if not isinstance(area, str):
            return False

        text = area.strip()

        if not text:
            return False

        patterns = (
            r"\bphase\s*[-#]?\s*[a-z0-9]+\b",
            r"\bsector\s*[-#]?\s*[a-z0-9]+(?:[-/][a-z0-9]+)?\b",
            r"\bblock\s*[-#]?\s*[a-z0-9]+\b",
        )

        return any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        )

    def _repair_correction_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding:
        """
        Repair short conversational corrections such as:

            "Bahria mein sorry"
            "Gulberg sorry"
            "actually Phase 5"
            "nahi, Sector F-11"

        This does not hard-code business locations. It only detects
        correction language and reuses the location phrase spoken by
        the user in the CURRENT turn.
        """

        if not isinstance(raw_message, str):
            return result

        if not self._looks_like_correction(raw_message):
            return result

        # Purpose corrections must be handled before generic area
        # corrections. Otherwise "purchase k liye" can be mistaken for
        # an area phrase.
        corrected_purpose = self._extract_corrected_purpose(
            raw_message
        )

        if corrected_purpose:
            result.required["purpose"] = corrected_purpose
            result.preferred.pop("purpose", None)
            result.excluded.pop("purpose", None)

            result.relax = [
                field_name
                for field_name in result.relax
                if field_name != "purpose"
            ]

            # Remove any bogus area hallucinated from this purpose-only
            # correction turn.
            bogus_area = result.required.get("area")
            if self._looks_like_purpose_phrase(bogus_area):
                result.required.pop("area", None)

            bogus_area = result.preferred.get("area")
            if self._looks_like_purpose_phrase(bogus_area):
                result.preferred.pop("area", None)

            if "area" in result.excluded:
                result.excluded["area"] = [
                    value
                    for value in result.excluded["area"]
                    if not self._looks_like_purpose_phrase(value)
                ]

                if not result.excluded["area"]:
                    result.excluded.pop("area", None)

            result.intent = "property_search"
            result.needs_clarification = False

            if result.clarification_reason in {
                "missing_purpose_for_budget",
                "incomplete_location",
            }:
                result.clarification_reason = None

            return result

        corrected_area = self._extract_correction_area(raw_message)

        if not corrected_area:
            return result

        if corrected_area in result.excluded.get("area", []):
            return result

        # A correction means "replace my previous area with this one".
        result.required["area"] = corrected_area
        result.preferred.pop("area", None)

        # Do not interpret the corrected location as an exclusion.
        if "area" in result.excluded:
            corrected_norm = self._normalize_text(corrected_area)

            kept_area_exclusions = []

            for value in result.excluded["area"]:
                value_norm = self._normalize_text(value)

                same_location = (
                    value_norm == corrected_norm
                    or (
                        value_norm
                        and corrected_norm
                        and (
                            value_norm in corrected_norm
                            or corrected_norm in value_norm
                        )
                    )
                )

                if not same_location:
                    kept_area_exclusions.append(value)

            if kept_area_exclusions:
                result.excluded["area"] = kept_area_exclusions
            else:
                result.excluded.pop("area", None)

        # A correction to area is not a relaxation of the area field.
        result.relax = [
            field_name
            for field_name in result.relax
            if field_name != "area"
        ]

        # If the LLM failed to classify the short correction, treat it
        # as a property search.
        if result.intent == "unknown":
            result.intent = "property_search"

        # A successfully recovered correction is not ambiguous.
        if (
            result.clarification_reason == "incomplete_location"
            and self._has_location_identifier(corrected_area)
        ):
            result.needs_clarification = False
            result.clarification_reason = None

        return result

    def _extract_corrected_purpose(
        self,
        message: str,
    ) -> str | None:
        """Extract Rental/Purchase correction from the current turn."""

        if not isinstance(message, str):
            return None

        text = " ".join(
            message.strip().casefold().split()
        )

        if not text:
            return None

        rental_patterns = (
            r"\brent\b",
            r"\brental\b",
            r"\bkiraya\b",
            r"\bkiraye\b",
        )

        purchase_patterns = (
            r"\bpurchase\b",
            r"\bpurchasing\b",
            r"\bbuy\b",
            r"\bbuying\b",
            r"\bkhareedna\b",
            r"\bkharidna\b",
            r"\bsale\b",
        )

        rental_negated = bool(
            re.search(r"\b(?:rent|rental|kiraya|kiraye)\s*(?:par|pe)?\s*(?:nahi|nahin|nai|not)\b|\b(?:no|not)\s+(?:rent|rental)\b", text)
        )
        purchase_negated = bool(
            re.search(r"\b(?:purchase|purchasing|buy|buying|khareedna|kharidna)\s*(?:nahi|nahin|nai|not)\b|\b(?:no|not)\s+(?:purchase|buy)\b", text)
        )

        if not rental_negated:
            for pattern in rental_patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return "Rental"

        if not purchase_negated:
            for pattern in purchase_patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return "Purchase"

        return None

    def _looks_like_purpose_phrase(
        self,
        value: Any,
    ) -> bool:
        """Detect bogus area values that are really purpose wording."""

        if not isinstance(value, str):
            return False

        text = value.strip().casefold()
        purpose_words = (
            "rent",
            "rental",
            "kiraya",
            "kiraye",
            "purchase",
            "buy",
            "buying",
            "khareedna",
            "kharidna",
        )
        return any(
            re.search(
                rf"\b{re.escape(word)}\b",
                text,
                flags=re.IGNORECASE,
            )
            for word in purpose_words
        )

    def _looks_like_correction(
        self,
        message: str,
    ) -> bool:
        if not isinstance(message, str):
            return False

        text = message.casefold().strip()

        # "X nahi Y chahiye" (where Y is not a verb like chahiye/lena) is an explicit correction
        if re.search(r"\b[A-Za-z0-9-]+\s+(?:nahi|nahin|nai)\s+(?!chahiye|chahye|lena|karna|krna|dekhna)[A-Za-z0-9-]+", text):
            return True

        # Pure negation (e.g. "DHA nahi chahiye", "rent nahi chahiye", "rental nahi") is an exclusion, not a replacement
        if re.search(r"\b(?:nahi|nahin|nai|not)\s*(?:chahiye|chahye|lena|chahie|ab|please|pls)?\s*$", text):
            # Unless there's an explicit correction marker like "Bahria nahi DHA chahiye"
            if not re.search(r"\b(?:sorry|actually|rather|instead\s+of)\b", text):
                return False

        markers = (
            "sorry",
            "actually",
            "rather",
            "i mean",
            "mera matlab",
            "matlab",
            "nahi,",
            "nahin,",
            "no,",
            "instead of",
        )

        return any(marker in text for marker in markers)

    def _extract_correction_area(
        self,
        message: str,
    ) -> str | None:
        """
        Extract the location phrase from a short correction without
        relying on a hard-coded city/society list.
        """

        if not isinstance(message, str):
            return None

        text = message.strip()
        if not text:
            return None

        # Check "Y instead of X": Y is the target
        instead_match = re.search(r"\b(.+?)\s+instead\s+of\s+(.+)\b", text, flags=re.IGNORECASE)
        if instead_match:
            candidate = self._extract_explicit_area(instead_match.group(1))
            if candidate:
                return candidate

        # Check "X sorry Y" / "X nahi Y" / "X actually Y": Y is the target
        marker_match = re.search(r"\b(?:sorry|actually|rather|i\s+mean|mera\s+matlab|matlab|nahi|nahin|no)\b\s*(?:mein\s+)?(.+)", text, flags=re.IGNORECASE)
        if marker_match:
            candidate = self._extract_explicit_area(marker_match.group(1))
            if candidate:
                return candidate

        # Remove correction discourse markers.
        cleaned = re.sub(
            r"\b("
            r"sorry|actually|rather|"
            r"i\s+mean|mera\s+matlab|matlab|"
            r"no|nahi|nahin"
            r")\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

        # Remove common relation/action words around the location.
        cleaned = re.sub(
            r"\b("
            r"mein|me|main|"
            r"dikhao|dikhayein|dikhaein|show|"
            r"sirf|only|please|pls|"
            r"property|properties|option|options"
            r")\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip(" ,.-")

        # Remove trailing conversational/copula words that are not part
        # of the location itself.
        # Examples:
        #   "bahria tha"  -> "bahria"
        #   "gulberg thi" -> "gulberg"
        #   "phase 5 hai" -> "phase 5"
        cleaned = re.sub(
            r"\s+\b(tha|thi|the|hai|hain|hy|he)\b\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ,.-")

        if not cleaned:
            return None

        # If a concrete phase/sector/block phrase exists, prefer it.
        explicit = self._extract_explicit_area(cleaned)
        if explicit:
            return explicit

        # For short corrections, the remaining current-turn noun phrase
        # is the location candidate. Keep this conservative.
        words = cleaned.split()

        if 1 <= len(words) <= 4:
            return cleaned

        return None

    def _normalize_text(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value).strip().casefold(),
        )

    def _repair_relaxation_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """
        Repair explicit field-relaxation language.

        Examples:
            "area flexible hai"
            "location koi bhi ho"
            "sector koi bhi ho"
            "phase koi b ho"
            "3 bedrooms dikhao chahey sector koi bhi ho"

        These are schema-level language rules only. No city, society,
        phase, or sector names are hard-coded.
        """

        if not isinstance(raw_message, str):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        if not text:
            return result

        area_words = (
            "area",
            "location",
            "sector",
            "phase",
            "block",
        )

        flexible_markers = (
            "flexible",
            "koi bhi",
            "koi b",
            "kuch bhi",
            "any",
            "doesn't matter",
            "does not matter",
            "matter nahi",
            "issue nahi",
            "issue nai",
            "masla nahi",
            "masla nai",
            "problem nahi",
            "problem nai",
            "farq nahi",
            "farak nahi",
            "zaroori nahi",
            "necessary nahi",
        )

        has_flex_marker = any(
            re.search(rf"\b{re.escape(marker)}\b", text)
            for marker in flexible_markers
        )

        budget_relaxed = (
            (any(w in text for w in ("budget", "price", "amount", "paise", "pese")) and has_flex_marker)
            or "no budget limit" in text
            or "budget koi masla nahi" in text
            or "budget flexible" in text
        )

        bedrooms_relaxed = (
            any(w in text for w in ("bedroom", "bedrooms", "bed", "beds", "room", "rooms"))
            and (has_flex_marker or "adjustable" in text)
        )

        type_relaxed = (
            any(w in text for w in ("property type", "property_type", "type"))
            and (has_flex_marker or "any property type" in text or "any type" in text)
        )

        area_relaxed = (
            (any(word in text for word in area_words) and has_flex_marker)
            or bool(re.search(r"\b(?:kon\s*sey|kon\s*se|konsay|konsi|knsey|knsi|which|what)\s+areas?\b", text, flags=re.IGNORECASE))
            or (has_flex_marker and not (budget_relaxed or bedrooms_relaxed or type_relaxed))
        )

        if budget_relaxed:
            result.required.pop("budget", None)
            result.preferred.pop("budget", None)
            if "budget" not in result.relax:
                result.relax.append("budget")
            if result.intent == "unknown":
                result.intent = "property_search"

        if bedrooms_relaxed:
            result.required.pop("bedrooms", None)
            result.preferred.pop("bedrooms", None)
            if "bedrooms" not in result.relax:
                result.relax.append("bedrooms")
            if result.intent == "unknown":
                result.intent = "property_search"

        if type_relaxed:
            result.required.pop("property_type", None)
            result.preferred.pop("property_type", None)
            if "property_type" not in result.relax:
                result.relax.append("property_type")
            if result.intent == "unknown":
                result.intent = "property_search"

        if area_relaxed:
            result.required.pop("area", None)
            result.preferred.pop("area", None)
            if "area" not in result.relax:
                result.relax.append("area")
            if result.clarification_reason == "incomplete_location":
                result.needs_clarification = False
                result.clarification_reason = None
            if result.intent == "unknown":
                result.intent = "property_search"

        return result

    def _repair_exact_constraint_comparison(
        self,
        result: UserUnderstanding,
        raw_message: str,
    ) -> UserUnderstanding:
        """
        Prevent an exact numeric requirement from being hallucinated as
        a relative comparison.

        Example:
            "3 bedrooms wala dikhao"
        means:
            bedrooms == 3

        It does NOT mean:
            bedrooms > selected_property.bedrooms

        A comparison is preserved only when the current message actually
        contains comparative language such as "more", "zyada", "kam",
        "fewer", etc.
        """

        comparison = result.comparison

        if comparison is None:
            return result

        if (
            comparison.field != "bedrooms"
            or "bedrooms" not in result.required
        ):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        comparative_markers = (
            "more bedroom",
            "more bedrooms",
            "extra bedroom",
            "extra bedrooms",
            "zyada bedroom",
            "zyada bedrooms",
            "ziyada bedroom",
            "ziyada bedrooms",
            "zayada bedroom",
            "zayada bedrooms",
            "se zyada",
            "se ziyada",
            "se ziada",
            "fewer bedroom",
            "fewer bedrooms",
            "less bedroom",
            "less bedrooms",
            "kam bedroom",
            "kam bedrooms",
            "se kam",
        )

        has_comparative_language = any(
            marker in text
            for marker in comparative_markers
        )

        if not has_comparative_language:
            result.comparison = ComparisonRequest(
                None,
                None,
                None,
                None,
            )

        return result

    def _repair_budget_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding:
        """
        Make budget semantics deterministic.

        Rules:
        - Plain "mera budget 3 crore hai" -> hard budget ceiling.
        - "around/takreeban 3 crore" -> soft preference.
        - If a budget is supplied but rent vs purchase is still unknown,
          ask for purpose before using that budget across incomparable
          transaction types.
        """

        if not isinstance(raw_message, str):
            return result

        text = " ".join(
            raw_message.casefold().split()
        )

        informational_intents = {
            "PROPERTY_TYPE_BY_BUDGET_QUERY", "property_type_by_budget_query",
            "MINIMUM_BUDGET_QUERY", "minimum_budget_query",
            "BUDGET_FEASIBILITY_QUERY", "budget_feasibility_query",
            "CHEAPEST_PROPERTY_QUERY", "cheapest_property_query",
        }
        if result.intent in informational_intents or result.query_budget is not None:
            if "budget" in result.required:
                if result.query_budget is None:
                    result.query_budget = result.required["budget"]
                result.required.pop("budget", None)
            if "budget" in result.preferred:
                if result.query_budget is None:
                    result.query_budget = result.preferred["budget"]
                result.preferred.pop("budget", None)
            return result

        budget_value = (
            result.required.get("budget")
            if "budget" in result.required
            else result.preferred.get("budget")
        )

        if budget_value is None:
            return result

        soft_markers = (
            "around",
            "approx",
            "approximately",
            "roughly",
            "takreeban",
            "taqreeban",
            "qareeban",
            "kareeban",
            "flexible",
            "thora upar neeche",
            "thoda upar neeche",
            "preferred",
            "preference",
        )

        is_soft = any(
            marker in text
            for marker in soft_markers
        )

        if is_soft:
            result.preferred["budget"] = budget_value
            result.required.pop("budget", None)
        else:
            # A plain stated budget is a maximum search constraint.
            result.required["budget"] = budget_value
            result.preferred.pop("budget", None)

        # Determine whether purpose is already known either in the current
        # turn or in committed conversation context.
        purpose_known = bool(
            result.required.get("purpose")
            or result.preferred.get("purpose")
            or (
                isinstance(context, dict)
                and (
                    (context.get("required") or {}).get("purpose")
                    or (context.get("preferred") or {}).get("purpose")
                )
            )
        )

        if not purpose_known:
            result.needs_clarification = True
            result.clarification_reason = "missing_purpose_for_budget"

        return result

    def _json_safe(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            Decimal,
        ):
            return float(value)

        if hasattr(value, "isoformat"):
            return value.isoformat()

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): self._json_safe(
                    item
                )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                self._json_safe(
                    item
                )
                for item in value
            ]

        if isinstance(value, (int, float, str, bool, type(None))):
            return value

        return str(value)

    def _repair_location_understanding(
        self,
        result: UserUnderstanding,
        raw_message: str,
        context: dict[str, Any],
    ) -> UserUnderstanding:
        """
        Repair obvious LLM inconsistencies for explicit location follow-ups.

        Examples:
            "DHA Phase 6"
            "DHA Phase 5 mein dikhao"
            "Sector F-11 only"
            "Block C mein"

        No actual city/society names are hard-coded.
        """

        for alias, canonical in CITY_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", raw_message, flags=re.IGNORECASE):
                result.required["city"] = canonical
                break

        explicit_area = self._extract_explicit_area(
            raw_message
        )

        if not explicit_area:
            return result

        # Check for explicit area negation: e.g. "DHA nahi chahiye", "no DHA please", "DHA ke ilawa"
        is_negated_area = bool(
            re.search(
                rf"\b(?:no|not)\s+{re.escape(explicit_area)}\b|\b{re.escape(explicit_area)}\s+(?:nahi|nai|nahin|not|ke\s+ilawa|k\s+ilawa)\b|\b(?:nahi|nahin|no)\b.*\b{re.escape(explicit_area)}\s+(?:nahi|nahin|nai)\b",
                raw_message,
                flags=re.IGNORECASE,
            )
        )
        if is_negated_area:
            result.required.pop("area", None)
            result.preferred.pop("area", None)
            if "area" not in result.excluded:
                result.excluded["area"] = [explicit_area]
            elif explicit_area not in result.excluded["area"]:
                result.excluded["area"].append(explicit_area)
            if result.intent == "unknown":
                result.intent = "property_search"
            return result

        if explicit_area in result.excluded.get("area", []):
            result.required.pop("area", None)
            result.preferred.pop("area", None)
            return result

        # A bare explicit location follow-up should be treated as a
        # hard narrowing constraint unless the user explicitly marks
        # it as a preference.
        if not self._looks_like_soft_preference(
            raw_message
        ):
            result.required["area"] = explicit_area
            result.preferred.pop("area", None)

            # Explicit current-turn area and relax-area are contradictory.
            # The explicit area wins.
            result.relax = [
                field_name
                for field_name in result.relax
                if field_name != "area"
            ]

            # A clear location follow-up is a property search even if
            # the LLM accidentally labels the intent as unknown.
            if result.intent == "unknown":
                result.intent = "property_search"

        # If area is phase alone without city or parent society in message or context, it needs clarification
        if explicit_area and re.fullmatch(r"Phase\s*[-#]?\s*[A-Za-z0-9]+", explicit_area, re.IGNORECASE):
            has_city = result.required.get("city") or (context.get("required") or {}).get("city")
            has_parent = (context.get("required") or {}).get("area")
            if not has_city and not has_parent:
                result.needs_clarification = True
                result.clarification_reason = "incomplete_location"
                return result

        # If the raw message contains a concrete identifier,
        # it is not an incomplete location.
        if self._has_location_identifier(
            explicit_area
        ):
            if (
                result.clarification_reason
                == "incomplete_location"
            ):
                result.needs_clarification = False
                result.clarification_reason = None

        return result

    def _extract_explicit_city(
        self,
        message: str,
    ) -> str | None:
        """
        Extract an explicit city name from the message.
        """
        if not isinstance(message, str):
            return None
        for alias, canonical in CITY_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", message, flags=re.IGNORECASE):
                return canonical
        return None

    def _extract_explicit_area(
        self,
        message: str,
    ) -> str | None:
        """
        Extract an explicit phase/sector/block location from the CURRENT
        message without hard-coding society or city names.
        """

        if not isinstance(message, str):
            return None

        text = message.strip()
        if not text:
            return None

        # Remove conversational/action words, not real place names.
        cleaned = re.sub(
            r"\b("
            r"mujhe|mujhey|mujey|mjy|mujy|humain|humein|main|hum|ap|aap|tum|"
            r"mera|meri|meray|mere|kya|kiya|agar|to|bhi|aur|and|or|please|pls|"
            r"dekhna|hai|hain|chahiye|chahta|chahti|chahu|chahungi|batao|batayein|bataiye|dikhao|dikhayein|dikhaein|dikha|show|"
            r"property|properties|option|options|sirf|only|"
            r"ke|k|ki|ka|mein|me|main|mrein|mien|mey|par|pe|se|ko|"
            r"according|mutabiq|hisaab|budget"
            r")\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")

        patterns = (
            # Known major societies + Phase identifier first (avoids greedy match on conversational words)
            r"\b((?:DHA|Bahria(?:\s+Town)?|Askari|Gulberg|State\s+Life)\s+Phase\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Society/name + Phase identifier, e.g. "DHA Phase 5".
            r"\b([A-Za-z][A-Za-z0-9.'-]*(?:\s+[A-Za-z][A-Za-z0-9.'-]*){0,2}"
            r"\s+Phase\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Sector, e.g. "Sector F-11".
            r"\b(Sector\s*[-#]?\s*[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)?)\b",

            # Block, e.g. "Block C".
            r"\b(Block\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Phase alone, e.g. "Phase 5".
            r"\b(Phase\s*[-#]?\s*[A-Za-z0-9]+)\b",

            # Bare society/area names, e.g. "DHA", "Bahria", "Askari", "Gulberg", "B-17".
            r"\b(DHA|Bahria|Bahria Town|Bahria Enclave|Gulberg|Johar Town|Askari|Clifton|Gulshan|B-17|E-11|F-11|G-11|I-8|F-7|F-8|F-10)\b",
        )

        noise_tokens = {
            "mujhe", "mujhey", "mujey", "mjy", "mujy", "humain", "humein", "main", "hum",
            "ap", "aap", "tum", "mera", "meri", "meray", "mere", "kya", "kiya", "agar",
            "to", "bhi", "aur", "and", "or", "please", "pls", "dekhna", "hai", "hain",
            "chahiye", "chahta", "chahti", "chahu", "chahungi", "batao", "batayein", "bataiye",
            "dikhao", "dikhayein", "dikhaein", "dikha", "show", "property", "properties",
            "option", "options", "sirf", "only", "ke", "k", "ki", "ka", "mein", "me",
            "mrein", "mien", "mey", "par", "pe", "se", "ko", "according", "mutabiq", "hisaab", "budget"
        }

        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                tokens = match.group(1).split()
                while tokens and tokens[0].lower() in noise_tokens:
                    tokens.pop(0)
                while tokens and tokens[-1].lower() in noise_tokens:
                    tokens.pop()
                if not tokens:
                    continue
                extracted = " ".join(tokens)
                if extracted.lower().startswith("dha "):
                    extracted = re.sub(r"^dha\s+phase\b", "DHA Phase", extracted, flags=re.IGNORECASE)
                    if not extracted.startswith("DHA "):
                        extracted = "DHA " + extracted[4:]
                return extracted

        return None

    def _looks_like_soft_preference(
        self,
        message: str,
    ) -> bool:
        """
        Return True only when the user explicitly marks the location
        as optional/soft. A plain location such as "DHA Phase 6"
        remains a hard search constraint.
        """

        if not isinstance(message, str):
            return False

        text = message.casefold()
        markers = (
            "prefer",
            "preferred",
            "preference",
            "ho to acha",
            "ho to achha",
            "ideally",
            "agar ho",
            "flexible",
        )
        return any(marker in text for marker in markers)
