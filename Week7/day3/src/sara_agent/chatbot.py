from __future__ import annotations

import copy
import logging
import os
import re
import threading

from typing import Any

from .memory import ConversationState
from .query_planner import QueryPlanner
from .conversation_policy import ConversationPolicy
from .result_presentation import ResultPresentationPolicy
from .conversation_control import ConversationControlPolicy
from .comparison_policy import VerifiedComparisonPolicy
from .edge_case_policy import EdgeCasePolicy
from .rag_bridge import RagBridge
from .formatting import (
    format_results,
    format_details,
    property_summary,
)
from .natural_speech import NaturalSpeechPolicy
from .objections import ObjectionHandler
from .understanding import (
    UserUnderstandingService,
    UnderstandingError,
)
logger = logging.getLogger(__name__)

from .models import (
    ComparisonRequest,
    UserUnderstanding,
)


class SaraChatbot:
    def __init__(
        self,
        knowledge_adapter,
        understanding_service=None,
        response_mode: str | None = None,
        rag_bridge=None,
    ):
        self.knowledge = knowledge_adapter
        self.memory = ConversationState()
        self.understanding = (
            understanding_service
            or UserUnderstandingService()
        )
        self.planner = QueryPlanner()
        self.presentation = ResultPresentationPolicy(
            response_mode
        )
        self.conversation_policy = ConversationPolicy(
            self.presentation
        )
        self.control_policy = ConversationControlPolicy()
        self.comparison_policy = VerifiedComparisonPolicy()
        self.edge = EdgeCasePolicy()
        self.rag = rag_bridge or RagBridge()
        self.speech = NaturalSpeechPolicy()
        self.objections = ObjectionHandler()
        self._turn_lock = threading.RLock()

    def handle_message(
        self,
        text: str,
    ) -> str:
        # A single REST/voice session can receive concurrent requests.
        # Serialize state mutations so one turn cannot partially overwrite
        # another turn's memory/selection.
        with self._turn_lock:
            return self._handle_message_unlocked(
                text
            )

    def _handle_message_unlocked(
        self,
        text: str,
    ) -> str:
        if not isinstance(text, str) or not text.strip():
            return "Ji, apni property requirement batayein."

        text = text.strip()
        self.memory.add_message("user", text)

        control = self.control_policy.detect(
            text,
            last_assistant_message=self._last_assistant_message(),
        )

        if control is not None:
            if control.clear_memory:
                self.memory.clear()

            if control.pending_action is not None:
                self.memory.pending_action = (
                    control.pending_action
                )

            return self._remember(
                control.message
                or "Ji."
            )

        pair_comparison = (
            self._try_verified_pair_comparison(
                text
            )
        )

        if pair_comparison is not None:
            return self._remember(
                pair_comparison
            )

        better_question = (
            self._try_better_without_basis(
                text
            )
        )

        if better_question is not None:
            return self._remember(
                better_question
            )

        greeting_response = self._try_social_greeting(
            text
        )

        if greeting_response is not None:
            return self._remember(
                greeting_response
            )

        # Pure acknowledgements are conversation control, not amenities or
        # business requirements. This prevents turns such as "okay" /
        # "thik hai" from becoming amenities=["thik"].
        acknowledgement = self._try_acknowledgement(
            text
        )

        if acknowledgement is not None:
            return self._remember(
                acknowledgement
            )

        # Budget guidance is a QUESTION about verified market options, not a
        # new budget value. Example:
        #   "max budget kitna hona chahey Lahore mein property buy krney k liye"
        #
        # Handle it before pending-budget collection / semantic NLU so Sara
        # does not simply repeat the previous no-result fallback.
        if self._looks_like_budget_guidance_request(
            text
        ):
            return self._remember(
                self._budget_guidance_response(
                    text
                )
            )

        # Real-world progressive disclosure:
        # "aur options" after displayed results means NEXT batch, not a
        # repeated LLM search or an accidental change of constraints.
        next_batch_response = (
            self._try_next_result_batch(
                text
            )
        )

        if next_batch_response is not None:
            return self._remember(
                next_batch_response
            )

        # Relative price language such as "us se sasti koi option?" needs a
        # real reference property. If none is selected yet, do not send this
        # vague pronoun to semantic NLU and end up in "unknown".
        relative_price_question = (
            self._relative_price_reference_clarification(
                text
            )
        )

        if relative_price_question is not None:
            return self._remember(
                relative_price_question
            )

        # Deterministic handling for very common Pakistani real-estate
        # requirement phrases. This protects both TEXT and VOICE paths from
        # semantic-NLU misses such as:
        #   "mujey zameen kharidni hai"
        #   "mujey ghar chahey"
        #   "mujey plot chahey"
        pending_understanding = (
            self._deterministic_basic_requirement_understanding(
                text
            )
        )

        # Generic "jagah chahiye" is intentionally NOT guessed as Plot/House.
        if pending_understanding is None:
            generic_property_question = (
                self._generic_property_type_clarification(
                    text
                )
            )

            if generic_property_question is not None:
                return self._remember(
                    generic_property_question
                )

        # Investment "better city" needs an explicit comparison basis unless
        # verified investment metrics are available; never invent ROI.
        if pending_understanding is None:
            investment_basis_question = (
                self._investment_city_basis_clarification(
                    text
                )
            )

            if investment_basis_question is not None:
                return self._remember(
                    investment_basis_question
                )

        # Natural memory follow-up:
        #   "Us se sasti koi option?"
        # If a property is already selected, preserve the pronoun reference
        # deterministically and let QueryPlanner retrieve the selected
        # property's VERIFIED price from memory/database-backed state.
        if pending_understanding is None:
            pending_understanding = (
                self._deterministic_relative_price_understanding(
                    text
                )
            )

        # Verified location phrases such as "DHA mein kya options hain?"
        # are structural search requirements, not amenities.
        if pending_understanding is None:
            pending_understanding = (
                self._deterministic_verified_location_search_understanding(
                    text
                )
            )

        # A direct city correction must override the currently pending slot.
        # Example:
        #   "Islamabad nahi, mujhe Karachi mein options dikhao."
        # City names are never hard-coded here; they come from verified Day 2
        # location data.
        if pending_understanding is None:
            pending_understanding = (
                self._deterministic_city_correction_understanding(
                    text
                )
            )

        # Otherwise resolve the answer to Sara's most recent requirement.
        # Short replies such as "flexible" get their meaning from pending_action.
        if pending_understanding is None:
            pending_understanding = (
                self._pending_requirement_understanding(
                    text
                )
            )

        if pending_understanding is None:
            pending_understanding = (
                self._deterministic_search_followup_understanding(
                    text
                )
            )

        # The current verified nearby dataset contains schools/hospitals,
        # not generic nearby-office/place discovery. Answer this limitation
        # explicitly instead of routing it to unknown or treating "office" as
        # an amenity.
        if (
            pending_understanding is None
            and self._asks_unsupported_nearby_office(
                text
            )
        ):
            return self._remember(
                "Nearby offices ka verified distance dataset current knowledge "
                "base mein configured nahi hai. Main office proximity guess "
                "nahi karungi."
            )

        # Only try selected-property facts if this turn was not already
        # resolved as an answer to Sara's pending requirement.
        if pending_understanding is None:
            verified_fact_response = (
                self._try_verified_property_fact_request(
                    text
                )
            )

            if verified_fact_response is not None:
                return self._remember(
                    verified_fact_response
                )

        # Structural area/sector discovery should not depend on the LLM.
        # Examples:
        #   "area knsey hai"
        #   "kon se areas hain"
        #   "Karachi mein konse areas available hain"
        #
        # Resolve any city/area mentioned in the CURRENT turn directly from
        # verified Day-2 location data. If none is mentioned, the response
        # safely falls back to the city already committed in memory.
        if (
            pending_understanding is None
            and self._is_location_options_request(
                text
            )
        ):
            resolver = getattr(
                self.knowledge,
                "resolve_locations",
                None,
            )
            resolved_for_options = {}

            if callable(resolver):
                try:
                    candidate = resolver(
                        text,
                        city_hint=self.memory.required.get(
                            "city"
                        ),
                    )
                except Exception:
                    candidate = {}

                if isinstance(candidate, dict):
                    resolved_for_options = candidate

            return self._remember(
                self._location_options_response(
                    resolved_for_options
                )
            )

        trusted_location_fields = set()

        if pending_understanding is not None:
            trusted_location_fields = {
                field_name
                for field_name in ("city", "area")
                if field_name in pending_understanding.required
            }

        try:
            if pending_understanding is not None:
                u = pending_understanding
            else:
                u = self.understanding.understand(
                    text,
                    self._context(),
                )
        except UnderstandingError:
            # Location-only follow-ups should not fail just because the
            # external LLM/provider failed. Resolve them against VERIFIED
            # Day 2 location data before giving up.
            u = self._verified_location_fallback(
                text
            )

            if u is None:
                return self._remember(
                    "Sorry, main is request ko reliably samajh nahi saki. "
                    "Thora differently bata dein."
                )

        # Repair location classification against VERIFIED Day 2 data.
        # This protects the conversation from LLM mistakes such as:
        #   "Islamabad mein dikhao"
        # -> intent=unknown, relax=["city"], incomplete_location=True
        resolved_locations = self._repair_with_verified_locations(
            u,
            text,
            trusted_fields=trusted_location_fields,
        )

        # Mixed search + amenity turns should become database filters,
        # not selected-property fact questions.
        self._repair_search_amenity_constraint(
            u,
            text,
            resolved_locations,
        )

        # Location discovery is structured retrieval, not a generic FAQ.
        # Example:
        #   "Islamabad mein kon kon se sector available hain?"
        if self._is_location_options_request(text):
            return self._remember(
                self._location_options_response(
                    resolved_locations
                )
            )

        if u.intent == "reset":
            self.memory.clear()
            return self._remember(
                "Theek hai. Search aur conversation memory clear "
                "ho gayi hai. Nayi requirement batayein."
            )

        if u.intent == "greeting":
            return self._remember(
                "Wa-Alaikum-Assalam! Ji batayein, "
                "aap kis tarah ki property dekh rahi hain?"
            )

        # Fail closed before planning, retrieval, or workflow execution.
        # Off-topic turns must never trigger property/RAG/business tools or
        # mutate the customer's saved property requirements.
        if u.intent == "off_topic":
            return self._remember(
                "Main sirf real estate aur property-related assistance "
                "mein help kar sakti hoon. Property search, verified "
                "details ya visit booking ke bare mein batayein."
            )

        # "Kiya relax karna hai?", "what should I change?", etc.
        # This is a conversation-control question, not a property fact.
        # Answer it from committed memory instead of forcing the LLM
        # to invent a new business intent.
        if (
            u.intent == "unknown"
            and self._is_relaxation_help_request(text)
        ):
            return self._remember(
                self._relaxation_help()
            )

        plan = self.planner.build_plan(
            u,
            self.memory,
        )

        self._debug_turn(
            understanding=u,
            plan=plan,
        )

        if plan.needs_clarification:
            return self._remember(
                self._clarify(
                    plan.clarification_reason
                )
            )

        # ----------------------------------------------------------
        # Human real-estate requirement collection.
        # This decides only WHAT to ask next. All cities/areas shown
        # come from verified Day 2 data.
        # ----------------------------------------------------------
        requirement_decision = (
            self.conversation_policy.next_requirement(
                intent=u.intent,
                state=self.memory,
                knowledge=self.knowledge,
            )
        )

        if requirement_decision is not None:
            self.memory.pending_action = (
                requirement_decision.pending_action
            )

            return self._remember(
                requirement_decision.message
            )

        # Search is now sufficiently scoped.
        if (
            u.intent
            in {
                "property_search",
                "recommendation",
            }
        ):
            self.memory.pending_action = None

        if u.intent == "property_selection":
            p = self.memory.selected_property

            if p:
                return self._remember(
                    "Ji, ye option select ho gaya:\n"
                    + property_summary(p)
                    + "\nIski details, comparison ya visit ke "
                    "bare mein pooch sakti hain."
                )

            return self._remember(
                "Kaunsa option select karna hai?"
            )

        if u.intent == "property_details":
            if self.memory.selected_property:
                property_row = self._refresh_verified_property(
                    self.memory.selected_property
                )

                return self._remember(
                    format_details(
                        property_row
                    )
                )

            # General project/brochure descriptions are semantic knowledge
            # and may be answered by the verified Day 2 RAG layer. Exact
            # structured questions are rejected by Day 2 query_policy and
            # therefore still fail closed here.
            try:
                rag_answer = self.rag.answer(
                    text
                )
            except Exception:
                logger.exception(
                    "Verified RAG property-description retrieval failed"
                )
                rag_answer = None

            if rag_answer:
                return self._remember(
                    rag_answer
                )

            return self._remember(
                "Exact property facts ke liye pehle property select kar dein. "
                "Agar ye project overview/brochure question hai aur verified "
                "RAG context available hoga to main usi se answer dungi."
            )

        if u.intent == "availability":
            p = self.memory.selected_property

            if not p:
                return self._remember(
                    "Availability check ke liye property select kar dein."
                )

            p = self._refresh_verified_property(
                p
            )

            available = p.get(
                "available"
            )

            if available is None:
                return self._remember(
                    "Is property ki verified availability current data "
                    "mein available nahi hai."
                )

            return self._remember(
                "Latest verified PostgreSQL record ke mutabiq ye property "
                + (
                    "available hai."
                    if available
                    else "available nahi hai."
                )
            )

        if u.intent == "objection":
            selected = self.memory.selected_property

            if selected:
                selected = self._refresh_verified_property(
                    selected
                )

            return self._remember(
                self.objections.respond(
                    text,
                    selected,
                )
            )

        if u.intent in {
            "schedule_visit",
            "reschedule_visit",
            "cancel_visit",
        }:
            return self._remember(
                self._workflow_handoff(
                    u.intent
                )
            )

        if u.intent == "faq":
            try:
                answer = self.rag.answer(text)
            except Exception:
                logger.exception("Verified RAG/FAQ retrieval failed")
                answer = None

            if answer:
                return self._remember(answer)

            return self._remember(
                "Is sawal ka verified FAQ/RAG answer current runtime mein "
                "available nahi hai. Main guess karke jawab nahi dungi."
            )

        if u.intent in {
            "property_search",
            "recommendation",
        }:
            if (
                not plan.required
                and not plan.preferred
                and not plan.excluded
                and not plan.comparison_field
            ):
                return self._remember(
                    "City, budget, bedrooms, area ya property type "
                    "mein se jo pata ho bata dein; baqi flexible reh "
                    "sakta hai."
                )

            try:
                results = self.knowledge.execute_plan(
                    plan,
                    recommendation=(
                        u.intent == "recommendation"
                    ),
                )
            except Exception:
                logger.exception("Verified property retrieval failed")
                return self._remember(
                    "Verified property retrieval mein issue aaya hai; "
                    "main guess karke property nahi bataungi."
                )

            self.memory.last_intent = u.intent

            if not results:
                self.memory.store_result_pool(
                    [],
                    self.presentation.batch_size,
                )
                return self._remember(
                    self._no_results(plan)
                )

            batch = self.memory.store_result_pool(
                results,
                self.presentation.batch_size,
            )

            return self._remember(
                self.presentation.format_batch(
                    batch,
                    has_more=(
                        self.memory.has_more_results()
                    ),
                    first_batch=True,
                )
            )

        return self._remember(
            "Main real-estate related property search, verified details, "
            "comparison, objections aur visit-workflow requests mein help kar sakti hoon. "
            "Agar sawal property-related hai to thora specific bata dein."
        )

    def _debug_turn(
        self,
        *,
        understanding: UserUnderstanding,
        plan,
    ) -> None:
        """Emit structured turn state only when explicitly enabled."""
        if os.getenv("SARA_DEBUG", "").strip().casefold() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return

        logger.info(
            "understanding=%r memory=%r plan=%r",
            understanding,
            {
                "required": self.memory.required,
                "preferred": self.memory.preferred,
                "excluded": self.memory.excluded,
                "selected_property": self.memory.selected_property,
            },
            plan,
        )

    def _last_assistant_message(
        self,
    ) -> str | None:
        for item in reversed(
            self.memory.history
        ):
            if (
                item.get("role") == "assistant"
                and item.get("content")
            ):
                return item["content"]

        return None

    def _try_verified_pair_comparison(
        self,
        text: str,
    ) -> str | None:
        results = self.memory.last_results

        pair = self.comparison_policy.parse_pair(
            text,
            len(results),
        )

        if pair is None:
            return None

        left_index, right_index = pair

        return self.comparison_policy.format_comparison(
            results[left_index],
            results[right_index],
            left_label=f"Option {left_index + 1}",
            right_label=f"Option {right_index + 1}",
        )

    def _is_relative_cheaper_request(
        self,
        text: str,
    ) -> bool:
        if not isinstance(text, str):
            return False

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not normalized:
            return False

        return bool(
            re.search(
                r"\b(?:"
                r"us\s+se\s+sast[ai]|"
                r"is\s+se\s+sast[ai]|"
                r"usse\s+sast[ai]|"
                r"isse\s+sast[ai]|"
                r"cheaper|"
                r"less\s+expensive|"
                r"kam\s+price|"
                r"kam\s+qeemat|"
                r"sasti\s+(?:koi\s+)?option|"
                r"sasta\s+(?:koi\s+)?option"
                r")\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _relative_price_reference_clarification(
        self,
        text: str,
    ) -> str | None:
        """Clarify 'us se sasti' only when no property is selected."""

        if not self._is_relative_cheaper_request(
            text
        ):
            return None

        if self.memory.selected_property:
            return None

        pending = self.memory.pending_action

        if isinstance(
            pending,
            dict,
        ):
            if (
                pending.get("type")
                == "collect_requirement"
            ):
                field = pending.get(
                    "field"
                )

                if field == "city":
                    return (
                        "Ji. Cheaper comparison se pehle city bata dein. "
                        "Budget aur baqi saved requirements memory mein rahengi; "
                        "city confirm hone ke baad main verified options dikha "
                        "kar kisi selected option se sasti property compare karungi."
                    )

                if field == "purpose":
                    return (
                        "Ji. Cheaper comparison se pehle rent ya purchase "
                        "confirm kar dein. Uske baad verified options mein se "
                        "reference property select karke sasti option compare "
                        "kar sakti hoon."
                    )

        if self.memory.last_results:
            return (
                "Ji. 'Us se sasti' ke liye pehle reference property select "
                "kar dein—jaise 'option 1'. Phir main uski verified price ke "
                "against cheaper options search karungi."
            )

        return (
            "Abhi compare karne ke liye koi reference property select nahi "
            "hui. Pehle search complete karke koi option select kar dein; "
            "phir 'us se sasti' naturally work karega."
        )

    def _deterministic_relative_price_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Preserve selected-property reference for cheaper follow-ups."""

        if not self._is_relative_cheaper_request(
            text
        ):
            return None

        if not self.memory.selected_property:
            return None

        return UserUnderstanding(
            intent="property_search",
            comparison=ComparisonRequest(
                "price",
                "lt",
                "selected_property",
                None,
            ),
            raw_message=text,
        )

    @staticmethod
    def _normalized_location_label(
        value: str,
    ) -> str:
        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            value.casefold(),
        )
        return " ".join(
            normalized.split()
        )

    def _verified_area_family_from_text(
        self,
        text: str,
        areas: list[str],
    ) -> str | None:
        """Resolve generic verified area families such as DHA or Gulberg.

        The family name is derived from VERIFIED area labels; no business
        location is hard-coded here.
        """

        if not areas:
            return None

        normalized = self._normalized_location_label(
            text
        )

        tokens = normalized.split()

        stopwords = {
            "mein",
            "me",
            "main",
            "kya",
            "kiya",
            "kia",
            "option",
            "options",
            "property",
            "properties",
            "dikhao",
            "dikhaye",
            "dikhayein",
            "show",
            "available",
            "hain",
            "hai",
            "hy",
            "he",
            "mujhe",
            "mujey",
            "mujhey",
            "koi",
            "kon",
            "kaun",
            "se",
            "si",
            "ke",
            "ki",
            "ka",
            "rent",
            "rental",
            "purchase",
            "buy",
            "flat",
            "apartment",
            "house",
            "plot",
        }

        content_tokens = [
            token
            for token in tokens
            if token not in stopwords
        ]

        if not content_tokens:
            return None

        generic_only = {
            "phase",
            "sector",
            "block",
            "area",
            "location",
        }

        normalized_areas = [
            (
                area,
                self._normalized_location_label(
                    area
                ),
            )
            for area in areas
            if isinstance(area, str)
            and area.strip()
        ]

        # Prefer the longest phrase explicitly spoken by the user.
        max_width = min(
            3,
            len(content_tokens),
        )

        for width in range(
            max_width,
            0,
            -1,
        ):
            for start in range(
                0,
                len(content_tokens) - width + 1,
            ):
                phrase_tokens = content_tokens[
                    start:start + width
                ]
                phrase = " ".join(
                    phrase_tokens
                )

                if (
                    phrase in generic_only
                    or len(phrase) < 2
                ):
                    continue

                matches = [
                    (
                        area,
                        area_norm,
                    )
                    for area, area_norm
                    in normalized_areas
                    if (
                        area_norm == phrase
                        or area_norm.startswith(
                            phrase + " "
                        )
                    )
                ]

                if not matches:
                    continue

                # Exact canonical verified area.
                for area, area_norm in matches:
                    if area_norm == phrase:
                        return area

                # Generic family prefix derived from the first verified match.
                first_area = matches[0][0]
                original_parts = re.split(
                    r"\s+",
                    first_area.strip(),
                )

                if len(original_parts) >= width:
                    return " ".join(
                        original_parts[:width]
                    )

        return None

    def _deterministic_verified_location_search_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Treat verified location search turns as locations, never amenities.

        Example:
            "DHA mein kya options hain?"
        """

        if not isinstance(text, str):
            return None

        normalized = self._normalized_location_label(
            text
        )

        search_markers = (
            "option",
            "options",
            "dikhao",
            "dikhaye",
            "dikhayein",
            "show",
            "available",
            "property",
            "properties",
            "dekhna",
            "dekhni",
            "chahiye",
            "chahye",
            "chahey",
        )

        if not any(
            marker in normalized
            for marker in search_markers
        ):
            return None

        resolver = getattr(
            self.knowledge,
            "resolve_locations",
            None,
        )

        resolved = {}

        if callable(resolver):
            try:
                candidate = resolver(
                    text,
                    city_hint=self.memory.required.get(
                        "city"
                    ),
                )
            except Exception:
                candidate = {}

            if isinstance(candidate, dict):
                resolved = candidate

        required = {}

        if resolved.get("city"):
            required["city"] = resolved["city"]

        if resolved.get("area"):
            required["area"] = resolved["area"]

        if required:
            return UserUnderstanding(
                intent="property_search",
                required=required,
                raw_message=text,
            )

        # If resolver reports several concrete phases/sectors, infer only the
        # family prefix the user explicitly said (e.g. DHA), never a phase.
        raw_candidates = resolved.get(
            "_area_candidates",
            [],
        )

        candidate_labels: list[str] = []

        if isinstance(raw_candidates, list):
            for item in raw_candidates:
                if isinstance(item, str):
                    candidate_labels.append(item)
                elif isinstance(item, dict):
                    for key in (
                        "area",
                        "name",
                        "label",
                        "value",
                    ):
                        value = item.get(key)
                        if isinstance(value, str) and value.strip():
                            candidate_labels.append(value)
                            break

        family = self._verified_area_family_from_text(
            text,
            candidate_labels,
        )

        # Fallback: derive family against the complete VERIFIED Day-2 catalog.
        if family is None:
            list_cities = getattr(
                self.knowledge,
                "list_cities",
                None,
            )
            list_areas = getattr(
                self.knowledge,
                "list_areas",
                None,
            )

            catalog_areas: list[str] = []

            if callable(list_cities) and callable(list_areas):
                try:
                    cities = list_cities(
                        filters={}
                    )
                except Exception:
                    cities = []

                for city in cities or []:
                    try:
                        city_areas = list_areas(
                            city,
                            filters={},
                        )
                    except Exception:
                        city_areas = []

                    for area in city_areas or []:
                        if (
                            isinstance(area, str)
                            and area not in catalog_areas
                        ):
                            catalog_areas.append(area)

            family = self._verified_area_family_from_text(
                text,
                catalog_areas,
            )

        if family is None:
            return None

        return UserUnderstanding(
            intent="property_search",
            required={
                "area": family,
            },
            raw_message=text,
        )

    def _try_better_without_basis(
        self,
        text: str,
    ) -> str | None:
        if not self.comparison_policy.asks_better_without_basis(
            text,
            len(self.memory.last_results),
        ):
            return None

        return (
            "Aap 'better/best' kis basis par decide karna chahti hain—"
            "price, location, bedrooms, size ya amenities? "
            "Main winner apni taraf se assume nahi karungi."
        )

    def set_response_mode(
        self,
        mode: str,
    ) -> None:
        """
        VoicePipeline can switch Sara to shorter voice-friendly batches
        without changing any search/business logic.
        """

        self.presentation.set_mode(
            mode
        )

    def _try_next_result_batch(
        self,
        text: str,
    ) -> str | None:
        if not self.memory.result_pool:
            return None

        if not self._is_next_batch_request(
            text
        ):
            return None

        batch = self.memory.next_result_batch(
            self.presentation.batch_size
        )

        return self.presentation.format_batch(
            batch,
            has_more=(
                self.memory.has_more_results()
            ),
            first_batch=False,
        )

    def _is_next_batch_request(
        self,
        text: str,
    ) -> bool:
        """
        Conservative pagination command.

        Only generic continuation phrases are captured here. A message
        containing a city/area/budget/etc. continues through normal
        understanding because it may be a refinement instead.
        """

        normalized = " ".join(
            text.casefold().split()
        )

        phrases = {
            "aur options",
            "aor options",
            "or options",
            "more options",
            "next options",
            "next",
            "aur dikhao",
            "aor dikhao",
            "or dikhao",
            "mazeed",
            "mazeed dikhao",
            "aur properties",
            "aor properties",
            "more properties",
            "next properties",
        }

        return normalized in phrases

    def _asks_unsupported_nearby_office(
        self,
        text: str,
    ) -> bool:
        if not isinstance(text, str):
            return False

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        return bool(
            re.search(
                r"\b(?:office|offices)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            and re.search(
                r"\b(?:nearby|near|qareeb|qarib|pass|paas|distance|fasla|faslay|fasley)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _try_verified_property_fact_request(
        self,
        text: str,
    ) -> str | None:
        """
        Handle deterministic questions about the currently selected
        property's verified Day 2 facts.

        Supported:
            nearby schools
            nearby hospitals
            verification status

        Returns None when the turn is not one of these fact requests.
        """

        if not isinstance(text, str):
            return None

        normalized = " ".join(
            text.casefold().split()
        )

        if not normalized:
            return None

        # Only bypass fact routing for an EXPLICIT search/show command.
        # A plain reference such as:
        #   "is property ka developer kon hai?"
        # must remain a fact request even though it contains "property".
        explicit_search_action = self._contains_any_phrase(
            normalized,
            (
                "dikhao",
                "dikha",
                "dikhayein",
                "dikhaein",
                "show",
                "suggest",
                "recommend",
                "search",
                "find",
                "dekhna hai",
                "dekh rahi",
                "dekh raha",
                "chahiye",
                "chahye",
            ),
        )

        if (
            explicit_search_action
            and self._looks_like_search_with_constraints(
                normalized
            )
        ):
            return None

        school_request = self._contains_any_phrase(
            normalized,
            (
                "school",
                "schools",
                "school nearby",
                "schools nearby",
                "nearby school",
                "nearby schools",
            ),
        )

        hospital_request = self._contains_any_phrase(
            normalized,
            (
                "hospital",
                "hospitals",
                "hospital nearby",
                "hospitals nearby",
                "nearby hospital",
                "nearby hospitals",
                "medical centre",
                "medical center",
            ),
        )

        verification_request = self._contains_any_phrase(
            normalized,
            (
                "verified",
                "verify",
                "verification",
                "kiya ye verified",
                "kya ye verified",
                "kia ye verified",
                "verified hai",
                "data verified",
                "price verified",
            ),
        )

        payment_plan_request = self._contains_any_phrase(
            normalized,
            (
                "payment plan",
                "payment plans",
                "installment",
                "installments",
                "instalment",
                "instalments",
                "down payment",
            ),
        )

        developer_request = (
            self._contains_any_phrase(
                normalized,
                (
                    "developer",
                    "builder",
                ),
            )
            and not self._contains_any_phrase(
                normalized,
                (
                    "trust",
                    "trustworthy",
                    "reputation",
                    "reliable",
                    "acha developer",
                    "good developer",
                ),
            )
        )

        assigned_agent_request = self._contains_any_phrase(
            normalized,
            (
                "assigned agent",
                "property agent",
                "agent assigned",
                "contact agent",
                "sales contact",
                "agent ka naam",
                "agent name",
                "agent kon",
                "agent kaun",
                "agent kya naam",
            ),
        )

        property_type_request = bool(
            self._contains_any_phrase(
                normalized,
                (
                    "property type",
                    "kis type",
                    "what type",
                    "apartment hai",
                    "flat hai",
                    "house hai",
                    "plot hai",
                    "office hai",
                    "shop hai",
                    "apartment ya",
                    "flat ya",
                    "house ya",
                    "plot ya",
                    "office ya",
                    "shop ya",
                ),
            )
            and self._contains_any_phrase(
                normalized,
                (
                    "property",
                    "ye ",
                    "is ",
                    "selected",
                    "option",
                ),
            )
        )

        status_request = self._contains_any_phrase(
            normalized,
            (
                "property status",
                "status kya",
                "status kia",
                "status kiya",
                "construction status",
                "under construction",
                "ready hai",
                "ready ya",
                "possession status",
            ),
        )

        amenity_request = self._parse_amenity_fact_request(
            normalized
        )

        # A pure verified city/area continuation such as "aor Karachi"
        # is a location refinement, not an amenity query.
        if (
            amenity_request is not None
            and self._message_resolves_to_verified_location(
                text
            )
            and self._looks_like_pure_location_continuation(
                text
            )
        ):
            amenity_request = None

        if not (
            school_request
            or hospital_request
            or verification_request
            or payment_plan_request
            or developer_request
            or assigned_agent_request
            or property_type_request
            or status_request
            or amenity_request is not None
        ):
            return None

        property_row = self._current_property_for_facts()

        # If there is no single selected property, nearby-school/hospital
        # wording can be interpreted as a verified refinement of the
        # CURRENT result set rather than forcing an unnecessary selection.
        if not property_row:
            if school_request:
                return self._filter_current_results_by_nearby(
                    kind="schools"
                )

            if hospital_request:
                return self._filter_current_results_by_nearby(
                    kind="hospitals"
                )

            if verification_request:
                return self._verification_for_current_results()

            if amenity_request is not None:
                return self._amenity_response_for_current_results(
                    amenity_request
                )

            if (
                payment_plan_request
                or developer_request
                or assigned_agent_request
                or property_type_request
                or status_request
            ):
                return (
                    "Is exact fact ko verified tareeqe se check karne ke "
                    "liye pehle ek property select kar dein."
                )

            return (
                "Is fact ko verified tareeqe se check karne ke liye "
                "pehle ek property select kar dein."
            )

        property_id = property_row.get(
            "property_id"
        )

        property_name = (
            property_row.get("property_name")
            or "selected property"
        )

        if not property_id:
            return (
                "Selected property ka verified property ID available "
                "nahi hai, isliye main guess nahi karungi."
            )

        if school_request:
            return self._nearby_fact_response(
                property_id=property_id,
                property_name=property_name,
                kind="schools",
            )

        if hospital_request:
            return self._nearby_fact_response(
                property_id=property_id,
                property_name=property_name,
                kind="hospitals",
            )

        if property_type_request:
            property_type = property_row.get(
                "property_type"
            )

            if property_type:
                return (
                    f"Ji. {property_name} ka verified property type "
                    f"{property_type} hai."
                )

            return (
                f"{property_name} ka property type current verified "
                "record mein available nahi hai. Main guess nahi karungi."
            )

        if status_request:
            status = property_row.get(
                "status"
            )

            if status:
                return (
                    f"Ji. {property_name} ka verified property status "
                    f"{status} hai."
                )

            return (
                f"{property_name} ka construction/readiness status "
                "current verified record mein available nahi hai. "
                "Main guess nahi karungi."
            )

        if amenity_request is not None:
            return self._amenity_response_for_property(
                property_row=property_row,
                request=amenity_request,
            )

        if payment_plan_request:
            return self._payment_plan_response(
                property_id=property_id,
                property_name=property_name,
            )

        if developer_request:
            return self._developer_fact_response(
                property_id=property_id,
                property_name=property_name,
            )

        if assigned_agent_request:
            return self._assigned_agent_response(
                property_id=property_id,
                property_name=property_name,
            )

        return self._verification_response(
            property_id=property_id,
            property_name=property_name,
        )

    def _looks_like_location_exclusion(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        markers = (
            " k ilawa",
            " ke ilawa",
            " kay ilawa",
            " se ilawa",
            "except ",
            "excluding ",
            "exclude ",
            "nahi chahiye",
            "nahi chahye",
        )

        return any(
            marker in normalized
            for marker in markers
        )

    def _looks_like_broader_location_search(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        markers = (
            "aur option",
            "aor option",
            "or option",
            "more option",
            "other option",
            "dusre option",
            "doosre option",
            "mazeed option",
            "aur properties",
            "aor properties",
            "more properties",
            "other properties",
        )

        return any(
            marker in normalized
            for marker in markers
        )

    def _message_has_explicit_money(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        return bool(
            re.search(
                r"\b(?:budget|max|maximum|under|upto|up to|tak)\b",
                normalized,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b\d+(?:\.\d+)?\s*(?:crore|corore|carore|cror|cr|lakh|lac|k)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    def _looks_like_search_with_constraints(
        self,
        normalized: str,
    ) -> bool:
        search_markers = (
            "dikhao",
            "dikha",
            "dikhayein",
            "dikhaein",
            "show",
            "options",
            "option",
            "suggest",
            "recommend",
            "properties",
            "property",
            "jaha",
            "jahan",
            "with ",
            "wali",
            "wala",
        )

        return any(
            marker in normalized
            for marker in search_markers
        )

    def _looks_like_pure_location_continuation(
        self,
        text: str,
    ) -> bool:
        """
        True for short turns such as:
            "aor Karachi"
            "Lahore mein"
            "F 10"
        but not for:
            "Islamabad mein security wali options dikhao"
        """

        normalized = " ".join(
            text.casefold().split()
        )

        if self._looks_like_search_with_constraints(
            normalized
        ):
            # Plain "Karachi mein dikhao" is still a location search and
            # should not be swallowed by amenity parsing.
            facility_cues = (
                "jaha",
                "jahan",
                "with ",
                "wali",
                "wala",
                "gym",
                "security",
                "parking",
                "pool",
                "amenity",
                "amenities",
                "facility",
                "facilities",
            )

            return not any(
                cue in normalized
                for cue in facility_cues
            )

        return True

    def _repair_search_amenity_constraint(
        self,
        understanding,
        text: str,
        resolved_locations: dict[str, str],
    ) -> None:
        """
        Convert mixed search requests into a verified amenities filter.

        Example:
            "Islamabad mein wo options dikhao jaha security b ho"

        becomes:
            city=Islamabad
            amenities=["security"]

        The actual match is later performed against verified property
        amenities by Day 2 retrieval.
        """

        normalized = " ".join(
            text.casefold().split()
        )

        if not self._looks_like_search_with_constraints(
            normalized
        ):
            return

        # Do not treat ordinary property-search wording as an amenity name.
        # Example: "Mujhe property dekhni hai" previously became the fake
        # amenity "mujhe dekhni" because generic words were stripped later.
        # This repair is only for structurally explicit amenity constraints;
        # ordinary preferences can still be handled by semantic NLU.
        amenity_structure_cues = (
            "jaha",
            "jahan",
            "where ",
            "with ",
            "wali",
            "wala",
            "ke sath",
            "ke saath",
            "amenity",
            "amenities",
            "facility",
            "facilities",
        )

        if not any(
            cue in normalized
            for cue in amenity_structure_cues
        ):
            return

        candidate_text = normalized

        # Remove verified location values so they cannot be mistaken for
        # amenity names.
        for value in (
            resolved_locations.get("city"),
            resolved_locations.get("area"),
        ):
            if not value:
                continue

            normalized_value = re.sub(
                r"[^a-z0-9]+",
                " ",
                str(value).casefold(),
            )
            normalized_value = " ".join(
                normalized_value.split()
            )

            if normalized_value:
                candidate_text = candidate_text.replace(
                    normalized_value,
                    " ",
                )

        request = self._parse_amenity_fact_request(
            candidate_text
        )

        if (
            not request
            or request.get("mode") != "check"
            or not request.get("query")
        ):
            return

        amenity = request["query"]

        understanding.required["amenities"] = [
            amenity
        ]
        understanding.preferred.pop(
            "amenities",
            None,
        )
        understanding.excluded.pop(
            "amenities",
            None,
        )

        understanding.intent = (
            "property_search"
        )
        understanding.needs_clarification = False

        if understanding.clarification_reason in {
            "incomplete_location",
            "ambiguous_reference",
        }:
            understanding.clarification_reason = None

    def _message_resolves_to_verified_location(
        self,
        text: str,
    ) -> bool:
        """
        Return True when the current turn contains a verified city/area
        according to Day 2 location data.

        This prevents generic facility parsing from swallowing turns like:
            "aor Karachi"
            "Lahore mein"
            "F 10 mein"
        """

        resolver = getattr(
            self.knowledge,
            "resolve_locations",
            None,
        )

        if not callable(resolver):
            return False

        try:
            resolved = resolver(
                text,
                city_hint=self.memory.required.get(
                    "city"
                ),
            )
        except Exception:
            return False

        if not isinstance(
            resolved,
            dict,
        ):
            return False

        return bool(
            resolved.get("city")
            or resolved.get("area")
            or resolved.get("_area_candidates")
        )

    def _parse_amenity_fact_request(
        self,
        normalized: str,
    ) -> dict[str, str | None] | None:
        """
        Parse generic amenity/facility follow-ups.

        Modes:
            list       -> list verified amenities
            check      -> amenity is listed
            not_listed -> amenity is not listed in verified record

        "not listed" is intentionally different from proving that a
        facility definitely does not exist.
        """

        if not isinstance(normalized, str):
            return None

        text = " ".join(
            normalized.casefold().split()
        )

        if not text:
            return None

        # Money/budget answers must never be interpreted as amenity names.
        # Example: "3 crore hai" previously became amenities=["3 crore"]
        # because generic amenity parsing noticed the word "hai".
        if self._message_has_explicit_money(text):
            return None

        # A verified city/area (including an ambiguous verified location
        # family such as DHA across multiple phases) must never be stored as
        # an amenity.
        if self._message_resolves_to_verified_location(text):
            return None

        negative_request = bool(
            re.search(
                r"\b(?:nahi|nai|nahin|without|no)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        explicit_amenity_words = (
            "amenity",
            "amenities",
            "facility",
            "facilities",
        )

        list_markers = (
            "konsi",
            "kon si",
            "knsi",
            "kaunsi",
            "which",
            "what amenities",
            "list",
        )

        if any(
            word in text
            for word in explicit_amenity_words
        ):
            if (
                any(
                    marker in text
                    for marker in list_markers
                )
                or text.strip()
                in {
                    "amenity",
                    "amenities",
                    "facility",
                    "facilities",
                }
            ):
                return {
                    "mode": "list",
                    "query": None,
                }

        conversational_markers = (
            "aor ",
            "aur ",
            "bhi ",
            "b ho",
            "hai",
            "hy",
            "kya",
            "kiya",
            "kia",
            "available",
            "nearby",
            "kis ",
        )

        if not any(
            marker in text
            for marker in conversational_markers
        ):
            return None

        reserved_topics = (
            "price",
            "budget",
            "bedroom",
            "bathroom",
            "developer",
            "agent",
            "school",
            "hospital",
            "verified",
            "verification",
            "availability",
            "rent",
            "rental",
            "purchase",
            "city",
            "area",
            "sector",
            "phase",
            "block",
            "details",
            "detail",
            "comparison",
            "compare",
            "visit",
            "booking",
            "payment plan",
            "payment plans",
            "installment",
            "installments",
            "instalment",
            "instalments",
            "down payment",
            "roi",
            "return",
            "returns",
            "maintenance",
            "property type",
            "apartment",
            "flat",
            "house",
            "plot",
            "office",
            "shop",
            "status",
            "construction",
            "ready",
            "possession",
            "zameen",
            "land",
            "ghar",
            "makan",
            "bungalow",
            "bangla",
            "kothi",
            "villa",
            "dukan",
            "portion",
            "kharid",
            "khareed",
            "kharidni",
            "khareedni",
            "kharidna",
            "khareedna",
            "okay",
            "theek",
            "thik",
            "alright",
        )

        if any(
            topic in text
            for topic in reserved_topics
        ):
            return None

        candidate = text

        candidate = re.sub(
            r"^\s*(?:aor|aur)\s+",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        # Multi-word scaffolding first.
        candidate = re.sub(
            r"\b(?:"
            r"kis\s+mein|kis\s+me|kis\s+main|"
            r"kon\s+si|kaun\s+si|knsi|konsi|"
            r"which\s+one|which\s+property"
            r")\b",
            " ",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = re.sub(
            r"\b(?:"
            r"wo|woh|jo|jaha|jahan|"
            r"option|options|property|properties|"
            r"dikhao|dikha|dikhayein|dikhaein|show|"
            r"mein|me|main|with|"
            r"bhi|b|ho|hai|hain|hy|he|"
            r"kya|kiya|kia|"
            r"nahi|nai|nahin|without|no|"
            r"miley\s+gi|milay\s+gi|mile\s+gi|"
            r"miley\s+ga|milay\s+ga|mile\s+ga|"
            r"milegi|milega|milti|milta|miltay|milte|"
            r"available|nearby|please|pls|"
            r"provide|provides|provided|"
            r"karte|karta|karti|"
            r"amenity|amenities|facility|facilities"
            r")\b",
            " ",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = re.sub(
            r"\s+",
            " ",
            candidate,
        ).strip(" ?!.,-")

        if not candidate:
            if any(
                word in text
                for word in explicit_amenity_words
            ):
                return {
                    "mode": "list",
                    "query": None,
                }

            return None

        words = candidate.split()

        if len(words) > 4:
            return None

        leftover_question_words = {
            "kis",
            "mein",
            "me",
            "main",
            "kon",
            "kaun",
            "which",
            "wala",
            "wali",
            "is",
            "it",
            "this",
            "that",
            "ye",
            "woh",
            "wo",
        }

        if any(
            word in leftover_question_words
            for word in words
        ):
            return None

        return {
            "mode": (
                "not_listed"
                if negative_request
                else "check"
            ),
            "query": candidate,
        }

    def _amenity_response_for_property(
        self,
        property_row: dict[str, Any],
        request: dict[str, str | None],
    ) -> str:
        property_name = (
            property_row.get("property_name")
            or "Selected property"
        )

        amenities = self._verified_amenities_for_property(
            property_row
        )

        mode = request.get("mode")
        query = request.get("query")

        if mode == "list":
            if not amenities:
                return (
                    f"{property_name} ke current verified property record "
                    "mein amenities list available nahi hai."
                )

            return (
                f"Ji. {property_name} ki verified amenities hain: "
                + ", ".join(amenities)
                + "."
            )

        if not query:
            return None

        matches = [
            amenity
            for amenity in amenities
            if self._amenity_matches(
                query,
                amenity,
            )
        ]

        if mode == "not_listed":
            if matches:
                return (
                    f"{property_name} ke verified amenities record mein "
                    + ", ".join(matches)
                    + " listed hai. Isliye current verified record ke "
                      f"mutabiq ye '{query}' not-listed option nahi hai."
                )

            return (
                f"{property_name} ke current verified amenities record mein "
                f"'{query}' listed nahi hai. Note: 'not listed' ka matlab "
                "ye nahi ke facility definitely maujood nahi; main absence "
                "guess nahi karungi."
            )

        if matches:
            return (
                f"Ji. {property_name} ke verified amenities record mein "
                + ", ".join(matches)
                + " listed hai."
            )

        return (
            f"{property_name} ke current verified amenities record mein "
            f"'{query}' listed nahi hai. Main isay nearby ya available "
            "hone ka guess nahi karungi."
        )

    def _amenity_response_for_current_results(
        self,
        request: dict[str, str | None],
    ) -> str:
        results = list(
            self.memory.last_results
        )

        mode = request.get("mode")
        query = request.get("query")

        if not results:
            if (
                mode in {
                    "check",
                    "not_listed",
                }
                and query
            ):
                if mode == "not_listed":
                    return (
                        "Pehle matching properties search kar lein; phir main "
                        f"current verified options mein '{query}' not-listed "
                        "records compare kar sakti hoon."
                    )

                self.memory.apply(
                    required={
                        "amenities": [
                            query
                        ]
                    }
                )

                return self._missing_scope_for_amenity(
                    query
                )

            return (
                "Ji, amenities check kar sakti hoon. "
                "Pehle property search scope bata dein."
            )

        if mode == "list":
            lines = []

            for index, row in enumerate(
                results[:5],
                start=1,
            ):
                name = (
                    row.get("property_name")
                    or f"Option {index}"
                )

                amenities = self._verified_amenities_for_property(
                    row
                )

                amenity_text = (
                    ", ".join(amenities)
                    if amenities
                    else "verified amenities list unavailable"
                )

                lines.append(
                    f"{index}. {name} — {amenity_text}"
                )

            return (
                "Current verified options ki amenities:\n"
                + "\n".join(lines)
            )

        if not query:
            return None

        if mode == "not_listed":
            matched = []

            for row in results:
                amenities = self._verified_amenities_for_property(
                    row
                )

                if not any(
                    self._amenity_matches(
                        query,
                        amenity,
                    )
                    for amenity in amenities
                ):
                    matched.append(
                        row
                    )

            if not matched:
                return (
                    f"Current displayed verified results mein '{query}' "
                    "sab ke amenities record mein listed hai. "
                    f"'{query}' not-listed option nahi mila."
                )

            self.memory.store_results(
                matched
            )

            return (
                f"Current verified results mein '{query}' amenities record "
                f"mein listed na hone wali {len(matched)} properties hain:\n"
                + self._compact_result_lines(
                    matched
                )
                + "\nNote: not-listed ka matlab facility definitely absent "
                  "hona prove nahi karta."
            )

        matched = []

        for row in results:
            amenities = self._verified_amenities_for_property(
                row
            )

            if any(
                self._amenity_matches(
                    query,
                    amenity,
                )
                for amenity in amenities
            ):
                matched.append(
                    row
                )

        if not matched:
            return (
                f"Current verified results mein '{query}' kisi property "
                "ke amenities record mein listed nahi mila. Main guess "
                "nahi karungi."
            )

        self.memory.store_results(
            matched
        )

        return (
            f"Ji. '{query}' verified amenity wali "
            f"{len(matched)} properties mili hain:\n"
            + self._compact_result_lines(
                matched
            )
            + "\nKis option ki details chahiye?"
        )

    def _missing_scope_for_amenity(
        self,
        amenity: str,
    ) -> str:
        """
        Fresh amenity-first requests are valid search requirements.

        Save the amenity, then ask only the next useful question.
        The central ConversationPolicy will continue with area, purpose
        and budget on later turns.
        """

        display_amenity = (
            amenity.strip().title()
            if isinstance(amenity, str)
            else str(amenity)
        )

        if not self.memory.required.get("city"):
            return (
                f"Ji, {display_amenity} wali property dekhte hain. "
                "Aap kis city mein dekhna chahti hain?"
            )

        if (
            not self.memory.required.get("area")
            and "area" not in self.memory.flexible
        ):
            return (
                f"Ji, {display_amenity} requirement save hai. "
                "Ab area select kar lete hain."
            )

        if not self.memory.required.get("purpose"):
            return (
                f"Ji, {display_amenity} requirement save hai. "
                "Aap rent ke liye dekh rahi hain ya purchase ke liye?"
            )

        return (
            f"Ji, {display_amenity} requirement save kar li hai. "
            "Apni location ya budget bata dein."
        )

    def _verified_amenities_for_property(
        self,
        property_row: dict[str, Any],
    ) -> list[str]:
        raw = None
        property_id = property_row.get(
            "property_id"
        )

        amenity_getter = getattr(
            self.knowledge,
            "get_property_amenities",
            None,
        )

        if property_id and callable(
            amenity_getter
        ):
            try:
                rows = amenity_getter(
                    property_id
                )
            except Exception:
                logger.exception(
                    "Verified amenity refresh failed"
                )
                rows = []

            if rows:
                raw = [
                    row.get(
                        "amenity"
                    )
                    for row in rows
                    if isinstance(
                        row,
                        dict,
                    )
                    and row.get(
                        "amenity"
                    )
                ]

        # Backward-compatible fallback for lightweight test adapters.
        if raw is None:
            raw = property_row.get(
                "amenities"
            )

        if raw is None:
            return []

        if isinstance(raw, str):
            values = [
                part.strip()
                for part in raw.split(",")
            ]
        elif isinstance(
            raw,
            (list, tuple, set),
        ):
            values = [
                str(item).strip()
                for item in raw
            ]
        else:
            return []

        output = []
        seen = set()

        for value in values:
            if not value:
                continue

            key = self._normalize_amenity_text(
                value
            )

            if key in seen:
                continue

            seen.add(key)
            output.append(value)

        return output

    def _amenity_matches(
        self,
        requested: str,
        verified_amenity: str,
    ) -> bool:
        requested_tokens = self._amenity_tokens(
            requested
        )

        actual_tokens = self._amenity_tokens(
            verified_amenity
        )

        if (
            not requested_tokens
            or not actual_tokens
        ):
            return False

        return requested_tokens.issubset(
            actual_tokens
        )

    def _amenity_tokens(
        self,
        value: str,
    ) -> set[str]:
        normalized = self._normalize_amenity_text(
            value
        )

        tokens = set()

        for token in normalized.split():
            # Small singularization for conversational plurals:
            # "parks" -> "park", "gyms" -> "gym".
            if (
                len(token) > 3
                and token.endswith("s")
                and not token.endswith("ss")
            ):
                token = token[:-1]

            if token:
                tokens.add(token)

        return tokens

    def _normalize_amenity_text(
        self,
        value: Any,
    ) -> str:
        text = str(
            value
        ).casefold()

        text = re.sub(
            r"[^a-z0-9]+",
            " ",
            text,
        )

        return " ".join(
            text.split()
        )

    def _compact_result_lines(
        self,
        results: list[dict[str, Any]],
    ) -> str:
        """
        Render result rows without format_results()'s conversational intro,
        so nested responses do not say "Ji" twice.
        """

        lines = []

        for index, row in enumerate(
            results[:5],
            start=1,
        ):
            name = (
                row.get("property_name")
                or "Unnamed property"
            )

            area = row.get("area")
            city = row.get("city")
            bedrooms = row.get("bedrooms")
            purpose = row.get("purpose")
            price = row.get("price")
            currency = (
                row.get("currency")
                or "PKR"
            )

            parts = [name]

            location = ", ".join(
                str(value)
                for value in (
                    area,
                    city,
                )
                if value
            )

            if location:
                parts.append(location)

            if (
                isinstance(bedrooms, (int, float))
                and not isinstance(bedrooms, bool)
                and bedrooms > 0
            ):
                parts.append(
                    f"{int(bedrooms)} bedrooms"
                )

            if purpose:
                parts.append(
                    str(purpose)
                )

            if price is not None:
                try:
                    price_text = (
                        f"{float(price):,.0f} {currency}"
                    )
                except Exception:
                    price_text = (
                        f"{price} {currency}"
                    )

                parts.append(
                    price_text
                )

            lines.append(
                f"{index}. "
                + " — ".join(parts)
            )

        return "\n".join(lines)

    def _filter_current_results_by_nearby(
        self,
        kind: str,
    ) -> str:
        """
        Filter the current verified result set to properties that have an
        explicit linked nearby-school/hospital record in Day 2 data.
        """

        results = list(
            self.memory.last_results
        )

        if not results:
            if not self.memory.required.get(
                "area"
            ):
                return (
                    "Abhi verified areas list hui hai, property results load "
                    "nahi hue. Pehle area select kar dein; phir budget bata dein "
                    "ya budget flexible keh dein. Uske baad main property-linked "
                    "nearby school/hospital data aur recorded distance check "
                    "kar sakti hoon."
                )

            if (
                not self.memory.required.get(
                    "budget"
                )
                and "budget" not in self.memory.flexible
            ):
                return (
                    "Area select ho gaya hai. Ab budget bata dein ya budget "
                    "flexible keh dein; phir main matching verified properties "
                    "ke nearby school/hospital records aur distance check karungi."
                )

            return (
                "Abhi matching property results load nahi hue. Search complete "
                "hone ke baad main verified nearby school/hospital data ke basis "
                "par options filter kar sakti hoon."
            )

        if kind == "schools":
            getter = getattr(
                self.knowledge,
                "get_nearby_schools",
                None,
            )
            label = "nearby school"
        else:
            getter = getattr(
                self.knowledge,
                "get_nearby_hospitals",
                None,
            )
            label = "nearby hospital"

        if not callable(getter):
            return (
                f"Verified {label} lookup abhi configured nahi hai."
            )

        matched: list[dict[str, Any]] = []

        for property_row in results:
            property_id = property_row.get(
                "property_id"
            )

            if not property_id:
                continue

            try:
                linked = getter(
                    property_id
                )
            except Exception:
                linked = []

            if linked:
                matched.append(
                    property_row
                )

        if not matched:
            return (
                f"Current verified results mein kisi property ke saath "
                f"explicit property-linked {label} record nahi mila. "
                "Main distance guess nahi karungi."
            )

        # This is now the user's active result set.
        self.memory.store_results(
            matched
        )

        return (
            f"Ji. Current results mein {len(matched)} verified "
            f"{label} wali properties mili hain:\n"
            + self._compact_result_lines(matched)
            + "\nKis option ki details chahiye?"
        )

    def _verification_for_current_results(
        self,
    ) -> str:
        """
        Summarize verification for the current result set when the user
        says things like "kya ye verified hai?" after multiple options.
        """

        results = list(
            self.memory.last_results
        )

        if not results:
            return (
                "Abhi verify karne ke liye current property results nahi hain."
            )

        getter = getattr(
            self.knowledge,
            "get_verification_info",
            None,
        )

        if not callable(getter):
            return (
                "Verification lookup abhi configured nahi hai."
            )

        lines = []

        for index, property_row in enumerate(
            results[:5],
            start=1,
        ):
            property_id = property_row.get(
                "property_id"
            )
            property_name = (
                property_row.get(
                    "property_name"
                )
                or f"Option {index}"
            )

            if not property_id:
                lines.append(
                    f"{index}. {property_name} — property ID missing"
                )
                continue

            try:
                info = getter(
                    property_id
                )
            except Exception:
                info = None

            if not info:
                lines.append(
                    f"{index}. {property_name} — verification record unavailable"
                )
                continue

            status = info.get(
                "verification_status"
            )

            verified_on = info.get(
                "verified_on"
            )

            if status:
                text = (
                    f"{index}. {property_name} — "
                    f"price status: {status}"
                )
            else:
                text = (
                    f"{index}. {property_name} — "
                    "explicit price verification status unavailable"
                )

            if verified_on:
                text += (
                    f" ({verified_on})"
                )

            lines.append(text)

        extra = (
            len(results) - 5
        )

        if extra > 0:
            lines.append(
                f"Aur {extra} current results bhi hain."
            )

        return (
            "Ji. Current displayed options ke verified Day 2 records:\n"
            + "\n".join(lines)
        )

    def _current_property_for_facts(
        self,
    ) -> dict[str, Any] | None:
        """
        Use only an explicit/currently safe property reference and refresh
        exact mutable facts from PostgreSQL before presenting them.
        """

        if self.memory.selected_property:
            return self._refresh_verified_property(
                self.memory.selected_property
            )

        if len(self.memory.last_results) == 1:
            return self._refresh_verified_property(
                self.memory.last_results[0]
            )

        return None

    def _refresh_verified_property(
        self,
        property_row: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            property_row,
            dict,
        ):
            return property_row

        property_id = property_row.get(
            "property_id"
        )

        getter = getattr(
            self.knowledge,
            "get_property",
            None,
        )

        if not property_id or not callable(
            getter
        ):
            return property_row

        try:
            refreshed = getter(
                property_id
            )
        except Exception:
            logger.exception(
                "Exact verified property refresh failed"
            )
            return property_row

        if not isinstance(
            refreshed,
            dict,
        ):
            return property_row

        # Exact lookup may not include every joined child collection
        # (e.g. amenities), so merge it over the richer search row.
        merged = {
            **property_row,
            **refreshed,
        }

        if (
            self.memory.selected_property
            and self.memory.selected_property.get(
                "property_id"
            ) == property_id
        ):
            self.memory.selected_property = merged

        return merged

    def _nearby_fact_response(
        self,
        property_id: str,
        property_name: str,
        kind: str,
    ) -> str:
        if kind == "schools":
            getter = getattr(
                self.knowledge,
                "get_nearby_schools",
                None,
            )
            singular = "school"
            plural = "schools"

        else:
            getter = getattr(
                self.knowledge,
                "get_nearby_hospitals",
                None,
            )
            singular = "hospital"
            plural = "hospitals"

        if not callable(getter):
            return (
                f"{plural.capitalize()} ka verified lookup "
                "abhi configured nahi hai."
            )

        try:
            rows = getter(
                property_id
            )
        except Exception:
            return (
                f"{property_name} ke nearby {plural} ka verified "
                "data retrieve karne mein issue aaya; main guess "
                "nahi karungi."
            )

        if not rows:
            return (
                f"{property_name} ke liye current verified data mein "
                f"koi property-linked nearby {singular} record "
                "available nahi hai."
            )

        lines = []

        for index, row in enumerate(
            rows,
            start=1,
        ):
            name = row.get("name")
            distance = row.get(
                "distance_km"
            )

            if distance is not None:
                lines.append(
                    f"{index}. {name} — {distance} km"
                )
            else:
                lines.append(
                    f"{index}. {name}"
                )

        return (
            f"Ji. {property_name} ke liye verified nearby "
            f"{plural} record mein:\n"
            + "\n".join(lines)
        )

    def _payment_plan_response(
        self,
        property_id: str,
        property_name: str,
    ) -> str:
        getter = getattr(
            self.knowledge,
            "get_payment_plans",
            None,
        )

        if not callable(getter):
            return (
                "Payment-plan ka structured lookup abhi configured nahi hai."
            )

        try:
            rows = list(
                getter(
                    property_id
                )
                or []
            )
        except Exception:
            logger.exception(
                "Verified payment-plan lookup failed"
            )
            return (
                f"{property_name} ka verified payment-plan data retrieve "
                "karne mein issue aaya; main plan guess nahi karungi."
            )

        if not rows:
            return (
                f"{property_name} ke current structured record mein "
                "payment plan listed nahi hai."
            )

        lines = []

        for index, row in enumerate(
            rows,
            start=1,
        ):
            name = row.get(
                "plan_name"
            ) or "Payment plan"

            summary = row.get(
                "summary"
            )
            status = row.get(
                "status"
            )

            detail = str(
                name
            )

            if summary:
                detail += (
                    f" — {summary}"
                )

            if status:
                detail += (
                    f" [{status}]"
                )

            lines.append(
                f"{index}. {detail}"
            )

        return (
            f"Ji. {property_name} ke verified structured payment plans:\n"
            + "\n".join(
                lines
            )
        )

    def _developer_fact_response(
        self,
        property_id: str,
        property_name: str,
    ) -> str:
        getter = getattr(
            self.knowledge,
            "get_developer",
            None,
        )

        if not callable(getter):
            return (
                "Developer ka structured lookup abhi configured nahi hai."
            )

        try:
            row = getter(
                property_id
            )
        except Exception:
            logger.exception(
                "Verified developer lookup failed"
            )
            return (
                f"{property_name} ka developer record retrieve karne "
                "mein issue aaya; main developer guess nahi karungi."
            )

        if not isinstance(
            row,
            dict,
        ) or not row.get(
            "developer_name"
        ):
            return (
                f"{property_name} ke current structured record mein "
                "developer detail available nahi hai."
            )

        return (
            f"Ji. {property_name} ke verified record mein developer "
            f"{row['developer_name']} listed hai. "
            "Main reputation/trustworthiness ka unsupported claim nahi karungi."
        )

    def _assigned_agent_response(
        self,
        property_id: str,
        property_name: str,
    ) -> str:
        getter = getattr(
            self.knowledge,
            "get_agents_for_property",
            None,
        )

        if not callable(getter):
            return (
                "Assigned-agent ka structured lookup abhi configured nahi hai."
            )

        try:
            rows = list(
                getter(
                    property_id
                )
                or []
            )
        except Exception:
            logger.exception(
                "Verified assigned-agent lookup failed"
            )
            return (
                f"{property_name} ke assigned agents retrieve karne "
                "mein issue aaya; main contact guess nahi karungi."
            )

        if not rows:
            return (
                f"{property_name} ke liye current structured data mein "
                "koi active assigned-agent record available nahi hai."
            )

        lines = []

        for index, row in enumerate(
            rows,
            start=1,
        ):
            name = (
                row.get(
                    "agent_name"
                )
                or row.get(
                    "name"
                )
                or "Agent"
            )
            phone = row.get(
                "phone"
            )
            email = row.get(
                "email"
            )

            parts = [
                str(
                    name
                )
            ]

            if phone:
                parts.append(
                    str(
                        phone
                    )
                )

            if email:
                parts.append(
                    str(
                        email
                    )
                )

            lines.append(
                f"{index}. "
                + " — ".join(
                    parts
                )
            )

        return (
            f"Ji. {property_name} ke verified assigned contacts:\n"
            + "\n".join(
                lines
            )
        )

    def _verification_response(
        self,
        property_id: str,
        property_name: str,
    ) -> str:
        getter = getattr(
            self.knowledge,
            "get_verification_info",
            None,
        )

        if not callable(getter):
            return (
                "Verification lookup abhi configured nahi hai."
            )

        try:
            info = getter(
                property_id
            )
        except Exception:
            return (
                "Verification record retrieve karne mein issue aaya; "
                "main verification status guess nahi karungi."
            )

        if not info:
            return (
                f"{property_name} ka verified exact-property record "
                "current data mein nahi mila."
            )

        verification_status = info.get(
            "verification_status"
        )
        verified_on = info.get(
            "verified_on"
        )
        available = info.get(
            "available"
        )

        if verification_status:
            verification_text = (
                f"price verification status "
                f"`{verification_status}` hai"
            )
        else:
            verification_text = (
                "explicit price verification status "
                "record mein available nahi hai"
            )

        if verified_on:
            verification_text += (
                f", verified on {verified_on}"
            )

        if available is True:
            availability_text = (
                " Database record mein property available hai."
            )
        elif available is False:
            availability_text = (
                " Database record mein property available nahi hai."
            )
        else:
            availability_text = ""

        return (
            f"Ji. {property_name} ka {verification_text}."
            + availability_text
            + " Main price/availability ko Day 2 PostgreSQL "
              "record se read kar rahi hoon, guess nahi kar rahi."
        )

    def _contains_any_phrase(
        self,
        text: str,
        phrases: tuple[str, ...],
    ) -> bool:
        return any(
            phrase in text
            for phrase in phrases
        )

    def _looks_like_budget_guidance_request(
        self,
        text: str,
    ) -> bool:
        """Detect 'what budget should I keep?' style questions."""

        if not isinstance(text, str):
            return False

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not normalized:
            return False

        if not re.search(
            r"\b(?:budget|price|range)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return False

        question_markers = (
            "kitna",
            "kitni",
            "kitney",
            "kitne",
            "how much",
            "what budget",
            "budget range",
            "hona chahey",
            "hona chahiye",
            "rakhun",
            "rakhoon",
            "rakhna chahey",
            "rakhna chahiye",
            "minimum budget",
            "min budget",
            "max budget",
            "maximum budget",
        )

        if not any(
            marker in normalized
            for marker in question_markers
        ):
            return False

        # If the user is clearly stating a new money amount, let the ordinary
        # budget-update flow handle it instead of treating it as guidance.
        explicit_amount = re.search(
            r"\b\d+(?:\.\d+)?\s*"
            r"(?:crore|corore|carore|cror|cr|lakh|lac|k)\b",
            normalized,
            flags=re.IGNORECASE,
        )

        return explicit_amount is None

    def _budget_guidance_response(
        self,
        text: str,
    ) -> str:
        """Answer budget guidance from verified structured results only.

        Important:
        - Real conversation memory is NOT mutated.
        - Current-turn scope overrides old memory for this guidance query.
          Example:
              memory: Plot + Karachi + Rental
              user: "Karachi mein rent par flat ke liye budget kitna ho?"
              probe: Apartment + Karachi + Rental
        - Only the budget constraint is removed before retrieval.
        """

        temp_memory = copy.deepcopy(
            self.memory
        )

        # Budget guidance asks what budget would work, so the OLD budget must
        # not cap the temporary verified retrieval.
        temp_memory.apply(
            relax=[
                "budget",
            ]
        )

        # ----------------------------------------------------------
        # 1. Current-turn property type / purpose override old memory
        # ----------------------------------------------------------
        current_scope = (
            self._deterministic_basic_requirement_understanding(
                text
            )
        )

        if (
            current_scope is not None
            and not current_scope.needs_clarification
        ):
            # Never let this helper accidentally re-introduce a budget.
            current_required = dict(
                current_scope.required
            )
            current_required.pop(
                "budget",
                None,
            )

            current_preferred = dict(
                current_scope.preferred
            )
            current_preferred.pop(
                "budget",
                None,
            )

            temp_memory.apply(
                required=current_required,
                preferred=current_preferred,
                excluded=current_scope.excluded,
                relax=[
                    field_name
                    for field_name
                    in current_scope.relax
                    if field_name != "budget"
                ],
            )

        # ----------------------------------------------------------
        # 2. Current-turn VERIFIED location overrides old location
        # ----------------------------------------------------------
        resolver = getattr(
            self.knowledge,
            "resolve_locations",
            None,
        )

        if callable(resolver):
            try:
                resolved = resolver(
                    text,
                    city_hint=temp_memory.required.get(
                        "city"
                    ),
                )
            except Exception:
                resolved = {}

            if isinstance(
                resolved,
                dict,
            ):
                verified_location_required = {}

                resolved_city = resolved.get(
                    "city"
                )
                resolved_area = resolved.get(
                    "area"
                )

                if resolved_city:
                    verified_location_required[
                        "city"
                    ] = resolved_city

                if resolved_area:
                    verified_location_required[
                        "area"
                    ] = resolved_area

                if verified_location_required:
                    temp_memory.apply(
                        required=verified_location_required
                    )

        city = temp_memory.required.get(
            "city"
        )
        purpose = temp_memory.required.get(
            "purpose"
        )
        property_type = temp_memory.required.get(
            "property_type"
        )
        area = temp_memory.required.get(
            "area"
        )

        if not city:
            return (
                "Budget guidance ke liye pehle city bata dein. "
                "Main verified property prices ke basis par range bataungi."
            )

        # ----------------------------------------------------------
        # 3. Retrieve verified options with budget removed
        # ----------------------------------------------------------
        probe_understanding = UserUnderstanding(
            intent="property_search",
            raw_message=text,
        )

        try:
            probe_plan = self.planner.build_plan(
                probe_understanding,
                temp_memory,
            )

            results = self.knowledge.execute_plan(
                probe_plan,
                recommendation=False,
            )
        except Exception:
            logger.exception(
                "Verified budget-guidance retrieval failed"
            )
            return (
                "Verified budget range retrieve karne mein issue aaya hai. "
                "Main budget amount guess nahi karungi."
            )

        scope_parts = [
            str(city),
        ]

        if isinstance(
            purpose,
            str,
        ) and purpose.strip():
            scope_parts.append(
                purpose
            )

        if isinstance(
            property_type,
            str,
        ) and property_type.strip():
            scope_parts.append(
                property_type
            )

        if isinstance(
            area,
            str,
        ) and area.strip():
            scope_parts.append(
                area
            )

        scope = " / ".join(
            scope_parts
        )

        if not results:
            return (
                f"Current verified {scope} criteria mein budget constraint "
                "remove karne par bhi koi matching option nahi mila. "
                "Property type, area ya purpose mein se koi condition "
                "change karni hogi."
            )

        # ----------------------------------------------------------
        # 4. Calculate verified price range
        # ----------------------------------------------------------
        priced_rows: list[
            tuple[int, dict[str, Any]]
        ] = []

        for row in results:
            if not isinstance(
                row,
                dict,
            ):
                continue

            raw_price = row.get(
                "price"
            )

            try:
                price = int(
                    float(raw_price)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if price > 0:
                priced_rows.append(
                    (
                        price,
                        row,
                    )
                )

        if not priced_rows:
            return (
                f"Current verified {scope} options mil gaye hain, lekin "
                "usable verified price current result mein available nahi "
                "hai. Main budget amount guess nahi karungi."
            )

        priced_rows.sort(
            key=lambda item: item[0]
        )

        lowest_price, lowest_row = (
            priced_rows[0]
        )
        highest_price = (
            priced_rows[-1][0]
        )

        current_budget = self.memory.required.get(
            "budget"
        )

        property_name = (
            lowest_row.get(
                "property_name"
            )
            or lowest_row.get(
                "name"
            )
            or "lowest verified option"
        )

        lowest_area = lowest_row.get(
            "area"
        )

        location_text = (
            f" — {lowest_area}"
            if lowest_area
            else ""
        )

        is_rental = (
            isinstance(
                purpose,
                str,
            )
            and purpose.casefold()
            == "rental"
        )

        if is_rental:
            price_label = (
                "lowest verified monthly rent"
            )
            range_label = (
                "monthly rent range"
            )
        else:
            price_label = (
                "lowest verified purchase price"
            )
            range_label = (
                "verified price range"
            )

        if (
            isinstance(
                current_budget,
                (int, float),
            )
            and current_budget > 0
            and current_budget < lowest_price
        ):
            gap = int(
                lowest_price
                - current_budget
            )

            intro = (
                f"Aapka current budget {int(current_budget):,} PKR hai. "
                f"Current verified {scope} options mein {price_label} "
                f"{lowest_price:,} PKR hai, yani kam az kam "
                f"{gap:,} PKR aur budget chahiye."
            )
        else:
            intro = (
                f"Current verified {scope} options mein {price_label} "
                f"{lowest_price:,} PKR hai."
            )

        if highest_price > lowest_price:
            range_text = (
                f" Retrieved options ka {range_label} "
                f"{lowest_price:,} se {highest_price:,} PKR tak hai."
            )
        else:
            range_text = ""

        return (
            intro
            + range_text
            + f" Lowest verified option: {property_name}{location_text}. "
              "Agar aap chahein to main isi workable budget ke around "
              "options filter kar sakti hoon."
        )

    def _try_acknowledgement(
        self,
        text: str,
    ) -> str | None:
        """Handle pure acknowledgements without mutating search state."""

        if not isinstance(text, str):
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if normalized not in {
            "ok",
            "okay",
            "theek",
            "theek hai",
            "thik",
            "thik hai",
            "acha",
            "acha theek",
            "acha theek hai",
            "alright",
            "hmm okay",
            "hmm theek",
        }:
            return None

        pending = self.memory.pending_action

        if isinstance(pending, dict):
            pending_type = pending.get(
                "type"
            )
            field = pending.get(
                "field"
            )

            if (
                pending_type == "choose_verified_area"
                or (
                    pending_type == "collect_requirement"
                    and field == "area"
                )
            ):
                return (
                    "Ji. In mein se area name ya option number "
                    "bata dein."
                )

            if (
                pending_type == "collect_requirement"
                and field == "budget"
            ):
                return (
                    "Ji. Apna maximum budget bata dein, ya agar "
                    "budget flexible hai to 'budget flexible hai' keh dein."
                )

            if (
                pending_type == "collect_requirement"
                and field == "city"
            ):
                return (
                    "Ji. Kis city mein property dekhni hai?"
                )

        return "Ji."

    def _try_social_greeting(
        self,
        text: str,
    ) -> str | None:
        """Handle greetings naturally without forcing a scripted first question."""

        normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold())
        normalized = " ".join(normalized.split())

        patterns = (
            r"w\s*asalam",
            r"walaikum\s*assalam",
            r"wa\s*alaikum\s*assalam",
            r"assalam\s*o?\s*alaikum",
            r"salam",
            r"hello",
            r"hi",
            r"hey",
        )

        if not any(re.fullmatch(p, normalized, flags=re.IGNORECASE) for p in patterns):
            return None

        islamic_greeting = bool(
            re.fullmatch(
                r"(?:w\s*)?asalam|walaikum\s*assalam|wa\s*alaikum\s*assalam|"
                r"assalam\s*o?\s*alaikum|salam",
                normalized,
                flags=re.IGNORECASE,
            )
        )
        prefix = "Wa-Alaikum-Assalam!" if islamic_greeting else "Hello!"

        if not self.memory.required and not self.memory.preferred:
            return prefix + " Ji batayein, aap kis tarah ki property dekh rahi hain?"

        return (
            prefix
            + " Ji, batayein. Property requirement mein kya dekhna "
              "ya change karna chahti hain?"
        )

    def _deterministic_search_followup_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """
        Structural search follow-up that contains no business fact.

        Example:
            "wo area batao jahan gym bhi ho"

        The amenity becomes a filter. Actual matching areas are still
        fetched dynamically from verified Day 2 data.
        """

        amenity = self._extract_area_amenity_requirement(
            text
        )

        if not amenity:
            return None

        return UserUnderstanding(
            intent="property_search",
            required={
                "amenities": [
                    amenity
                ],
            },
            raw_message=text,
        )

    def _extract_area_amenity_requirement(
        self,
        text: str,
    ) -> str | None:
        normalized = " ".join(
            text.casefold().split()
        )

        if not re.search(
            r"\bareas?\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        if not re.search(
            r"\b(?:jaha|jahan|where|batao|btaye|bataye|batayein|dikhao|show)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        candidate = re.sub(
            r"\b(?:"
            r"wo|woh|areas?|"
            r"jaha|jahan|where|"
            r"batao|btaye|bataye|batayein|"
            r"dikhao|show|"
            r"jis|jin|mein|me|main|"
            r"bhi|b|ho|hai|hain|hy|he|"
            r"kya|kiya|kia|"
            r"available|please|pls"
            r")\b",
            " ",
            normalized,
            flags=re.IGNORECASE,
        )

        candidate = re.sub(
            r"\s+",
            " ",
            candidate,
        ).strip(" ?!.,-")

        if not candidate:
            return None

        if len(
            candidate.split()
        ) > 4:
            return None

        return candidate

    def _deterministic_basic_requirement_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Parse simple property-type/purpose requests without an LLM.

        This is language normalization only. It never creates property facts,
        locations, prices or availability.

        Examples:
            "mujey zameen kharidni hai" -> Plot + Purchase
            "mujey ghar chahey" -> House
            "mujey flat chahiye" -> Apartment
            "mujey office k liye jagah dikhao" -> Office
        """

        if not isinstance(text, str) or not text.strip():
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not normalized:
            return None

        # Only treat these aliases as requirements when the turn actually
        # sounds like a search/desire statement. This avoids swallowing fact
        # questions such as "ye property apartment hai ya house hai?".
        desire_markers = (
            "mujhe",
            "mujey",
            "mujhey",
            "chahiye",
            "chahye",
            "chahey",
            "chaheye",
            "dikhao",
            "dikhaye",
            "dikhayein",
            "show",
            "dekhna",
            "dekhni",
            "kharid",
            "khareed",
            "buy",
            "rent",
            "kiraya",
            "kiraye",
            "options",
            "option",
        )

        if not any(
            marker in normalized
            for marker in desire_markers
        ):
            return None

        property_alias_groups = (
            (
                "Plot",
                (
                    "plot",
                    "zameen",
                    "land",
                ),
            ),
            (
                "House",
                (
                    "ghar",
                    "house",
                    "makan",
                    "bungalow",
                    "bangla",
                    "kothi",
                    "villa",
                ),
            ),
            (
                "Apartment",
                (
                    "flat",
                    "apartment",
                    "portion",
                ),
            ),
            (
                "Office",
                (
                    "office",
                    "office space",
                ),
            ),
            (
                "Shop",
                (
                    "shop",
                    "dukan",
                    "retail shop",
                ),
            ),
        )

        matched_types: list[str] = []

        for canonical, aliases in property_alias_groups:
            if any(
                re.search(
                    rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
                    normalized,
                    flags=re.IGNORECASE,
                )
                for alias in aliases
            ):
                matched_types.append(
                    canonical
                )

        # Multiple types in a desire/search turn are genuinely ambiguous.
        if len(matched_types) > 1:
            return UserUnderstanding(
                intent="property_search",
                needs_clarification=True,
                clarification_reason="ambiguous_property_type",
                raw_message=text,
            )

        required = {}

        if matched_types:
            required["property_type"] = matched_types[0]

        purchase_markers = (
            "purchase",
            "buy",
            "kharid",
            "khareed",
            "kharidni",
            "khareedni",
            "kharidna",
            "khareedna",
        )
        rental_markers = (
            "rent",
            "rental",
            "kiraya",
            "kiraye",
        )

        has_purchase = any(
            marker in normalized
            for marker in purchase_markers
        )
        has_rental = any(
            marker in normalized
            for marker in rental_markers
        )

        if has_purchase and has_rental:
            return None

        if has_purchase:
            required["purpose"] = "Purchase"
        elif has_rental:
            required["purpose"] = "Rental"

        # "investment ke liye property options" is a valid search goal even
        # without a concrete property type.
        investment_request = bool(
            re.search(
                r"\binvest(?:ment|ing)?\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

        if not required and not investment_request:
            return None

        return UserUnderstanding(
            intent=(
                "recommendation"
                if investment_request
                else "property_search"
            ),
            required=required,
            raw_message=text,
        )

    def _generic_property_type_clarification(
        self,
        text: str,
    ) -> str | None:
        """Clarify generic 'jagah' without guessing a property type."""

        if not isinstance(text, str):
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not re.search(
            r"\b(?:jagah|place|space)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        if not re.search(
            r"\b(?:mujhe|mujey|mujhey|chahiye|chahye|chahey|dikhao|show|dekhna)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        # If a concrete property type is also present, the deterministic
        # requirement parser already handles it.
        concrete_types = (
            "plot",
            "zameen",
            "ghar",
            "house",
            "makan",
            "flat",
            "apartment",
            "office",
            "shop",
            "dukan",
        )

        if any(
            re.search(
                rf"\b{re.escape(value)}\b",
                normalized,
                flags=re.IGNORECASE,
            )
            for value in concrete_types
        ):
            return None

        return (
            "Ji. Aap apartment, house, plot, office ya shop mein se "
            "kis type ki property dekhna chahti hain?"
        )

    def _investment_city_basis_clarification(
        self,
        text: str,
    ) -> str | None:
        """Clarify 'best/better city for investment' without inventing ROI."""

        if not isinstance(text, str):
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not re.search(
            r"\binvest(?:ment|ing)?\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        if not re.search(
            r"\b(?:better|best|behtar|achi|acha|suitable)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        if not re.search(
            r"\b(?:city|shehar|shahar|kahan|kis)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return None

        return (
            "Investment ke liye 'better city' decide karne ke liye basis "
            "chahiye—entry price, rental potential, location/amenities ya "
            "payment plan. Main ROI ya future return guess nahi karungi. "
            "Aap kis basis par compare karna chahti hain?"
        )

    def _deterministic_city_correction_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Resolve explicit city corrections against VERIFIED city names.

        Examples:
            "Lahore nahi, Karachi mein dikhao"
            "Lahore k bajaye Karachi mein dikhao"
            "sorry Lahore nahi, Karchi mein dekhni thi"
            "Actually Islamabad"

        City names are never hard-coded. Candidate cities come from Day 2.
        A conservative fuzzy match is allowed only inside an explicit
        correction fragment, so STT typos such as "Karchi" can recover to a
        single verified city without guessing normal turns.
        """

        if not isinstance(text, str) or not text.strip():
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            text.casefold(),
        )
        normalized = " ".join(
            normalized.split()
        )

        if not normalized:
            return None

        correction_pattern = re.compile(
            r"\b(?:"
            r"nahi|nahin|nai|"
            r"actually|instead|rather|"
            r"i\s+mean|mera\s+matlab|matlab|"
            r"ke\s+bajaye|k\s+bajaye|bajaye|"
            r"poochna\s+tha|kehna\s+tha"
            r")\b",
            flags=re.IGNORECASE,
        )

        correction_matches = list(
            correction_pattern.finditer(
                normalized
            )
        )

        # "sorry" alone is not enough, but it is useful when the turn also
        # contains a negative/replacement construction.
        if not correction_matches:
            return None

        lister = getattr(
            self.knowledge,
            "list_cities",
            None,
        )

        if not callable(lister):
            return None

        filters = dict(
            self.memory.required
        )
        filters.pop(
            "city",
            None,
        )
        filters.pop(
            "area",
            None,
        )

        verified_cities: list[str] = []

        # First gather cities valid under current non-location filters.
        try:
            filtered = lister(
                filters=filters
            )
        except Exception:
            filtered = []

        # Then union with the full verified city catalog. A user may correct
        # to a city that currently has no match under the old filters.
        try:
            all_cities = lister(
                filters={}
            )
        except Exception:
            all_cities = []

        seen_city_keys = set()

        for city in list(filtered or []) + list(all_cities or []):
            if not isinstance(city, str) or not city.strip():
                continue

            key = re.sub(
                r"[^a-z0-9]+",
                " ",
                city.casefold(),
            )
            key = " ".join(
                key.split()
            )

            if key and key not in seen_city_keys:
                seen_city_keys.add(key)
                verified_cities.append(
                    city
                )

        if not verified_cities:
            return None

        # Try fragments after correction markers from newest to oldest.
        # This avoids losing the city when the sentence itself ends with a
        # discourse phrase such as "... property poochna tha".
        target_fragments = [
            normalized[
                match.end():
            ].strip()
            for match in reversed(
                correction_matches
            )
            if normalized[
                match.end():
            ].strip()
        ]

        if not target_fragments:
            return None

        def _norm_city(value: str) -> str:
            result = re.sub(
                r"[^a-z0-9]+",
                " ",
                value.casefold(),
            )
            return " ".join(
                result.split()
            )

        corrected_city = None

        for target_fragment in target_fragments:
            # Exact verified city mentioned in this correction fragment.
            exact_mentions: list[
                tuple[int, str]
            ] = []

            for city in verified_cities:
                city_norm = _norm_city(
                    city
                )

                if not city_norm:
                    continue

                for match in re.finditer(
                    rf"(?<![a-z0-9]){re.escape(city_norm)}(?![a-z0-9])",
                    target_fragment,
                    flags=re.IGNORECASE,
                ):
                    exact_mentions.append(
                        (
                            match.start(),
                            city,
                        )
                    )

            if exact_mentions:
                exact_mentions.sort(
                    key=lambda item: item[0]
                )
                corrected_city = (
                    exact_mentions[-1][1]
                )
                break

            # Conservative typo recovery only inside explicit correction text.
            stopwords = {
                "mein",
                "me",
                "main",
                "property",
                "dikhao",
                "dikhaye",
                "dekhni",
                "dekhna",
                "thi",
                "tha",
                "mujhe",
                "mujey",
                "mujhey",
                "options",
                "option",
                "please",
                "pls",
                "poochna",
                "kehna",
            }

            tokens = [
                token
                for token in target_fragment.split()
                if token not in stopwords
                and len(token) >= 3
            ]

            candidates: list[
                tuple[float, str, str]
            ] = []

            for width in (1, 2, 3):
                for index in range(
                    0,
                    len(tokens) - width + 1,
                ):
                    fragment = " ".join(
                        tokens[
                            index:index + width
                        ]
                    )

                    for city in verified_cities:
                        city_norm = _norm_city(
                            city
                        )
                        score = SequenceMatcher(
                            None,
                            fragment,
                            city_norm,
                        ).ratio()

                        candidates.append(
                            (
                                score,
                                city,
                                fragment,
                            )
                        )

            candidates.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            if candidates:
                best_score, best_city, _ = (
                    candidates[0]
                )
                second_score = (
                    candidates[1][0]
                    if len(candidates) > 1
                    else 0.0
                )

                if (
                    best_score >= 0.82
                    and best_score - second_score
                    >= 0.05
                ):
                    corrected_city = (
                        best_city
                    )
                    break

        if corrected_city is None:
            return None

        current_city = self.memory.required.get(
            "city"
        )

        if (
            isinstance(current_city, str)
            and current_city.strip().casefold()
            == corrected_city.strip().casefold()
        ):
            return None

        return UserUnderstanding(
            intent="property_search",
            required={
                "city": corrected_city,
            },
            raw_message=text,
        )

    def _pending_requirement_understanding(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Resolve short answers using the question Sara just asked.

        Location choices are matched only against verified choices/catalog
        values. Fuzzy correction requires a clear single winner.
        """
        pending = self.memory.pending_action

        if not isinstance(pending, dict):
            return None

        pending_type = pending.get("type")
        field = pending.get("field")

        # Strong correction language overrides the currently pending slot.
        # Example:
        #   pending budget relaxation
        #   user: "actually Gulberg better rahega, budget same 3 crore rakho"
        #
        # Resolve the NEW area against the verified location catalog, not
        # against availability filtered by the current budget/bedrooms/etc.
        correction_fragment = self._area_correction_fragment(text)

        if correction_fragment:
            resolver = getattr(
                self.knowledge,
                "resolve_locations",
                None,
            )

            if callable(resolver):
                try:
                    resolved = resolver(
                        correction_fragment,
                        city_hint=self.memory.required.get("city"),
                    )
                except Exception:
                    logger.exception(
                        "Verified correction location resolution failed"
                    )
                    resolved = {}

                if isinstance(resolved, dict):
                    area_candidates = resolved.get(
                        "_area_candidates",
                        [],
                    )

                    if area_candidates:
                        return UserUnderstanding(
                            intent="property_search",
                            needs_clarification=True,
                            clarification_reason="ambiguous_location_fragment",
                            raw_message=text,
                        )

                    corrected_area = resolved.get("area")

                    if corrected_area:
                        return UserUnderstanding(
                            intent="property_search",
                            required={"area": corrected_area},
                            raw_message=text,
                        )

        if (
            pending_type == "collect_requirement"
            and field == "budget"
        ):
            if self._looks_like_budget_flexible(text):
                return UserUnderstanding(
                    intent="property_search",
                    relax=["budget"],
                    raw_message=text,
                )

            amount = self._parse_contextual_budget(
                self.edge.repair_tokens(text)
            )

            if amount is not None:
                return UserUnderstanding(
                    intent="property_search",
                    required={"budget": amount},
                    raw_message=text,
                )

            return None

        if (
            pending_type == "collect_requirement"
            and field == "area"
        ):
            # When Sara explicitly asked for an area (including a fallback
            # prompt when verified choices could not be listed), a short
            # "flexible" reply safely means relax/skip the area slot.
            if self._looks_like_area_flexible(text):
                return UserUnderstanding(
                    intent="property_search",
                    relax=["area"],
                    raw_message=text,
                )

            # Non-flexible replies continue through normal verified
            # location understanding rather than being guessed here.
            return None

        if (
            pending_type == "collect_requirement"
            and field == "city"
        ):
            options = pending.get("options", [])
            if not isinstance(options, list):
                options = []

            matched = (
                self.edge.match_displayed_option(text, options)
                or self.edge.fuzzy_match_verified_option(text, options)
            )

            if matched is None:
                lister = getattr(self.knowledge, "list_cities", None)
                if callable(lister):
                    filters = dict(self.memory.required)
                    filters.pop("city", None)
                    filters.pop("area", None)

                    try:
                        all_cities = lister(filters=filters)
                    except Exception:
                        logger.exception("Verified city list lookup failed")
                        all_cities = []

                    matched = (
                        self.edge.match_displayed_option(text, all_cities)
                        or self.edge.fuzzy_match_verified_option(text, all_cities)
                    )

            if matched is not None:
                return UserUnderstanding(
                    intent="property_search",
                    required={"city": matched},
                    raw_message=text,
                )

            return None

        if pending_type != "choose_verified_area":
            return None

        # Correction turns must prefer the NEW value after discourse markers.
        # Example:
        #   "Pehle DHA Phase 6 ... actually Gulberg better rahega"
        # should resolve Gulberg, not the older DHA Phase 6 mention.
        correction_fragment = self._area_correction_fragment(text)

        if correction_fragment:
            options = pending.get("options", [])
            if not isinstance(options, list):
                options = []

            corrected_match = (
                self.edge.match_displayed_option(
                    correction_fragment,
                    options,
                )
                or self.edge.fuzzy_match_verified_option(
                    correction_fragment,
                    options,
                )
            )

            if corrected_match is None:
                lister = getattr(self.knowledge, "list_areas", None)
                city = self.memory.required.get("city")

                if callable(lister) and isinstance(city, str) and city.strip():
                    filters = dict(self.memory.required)
                    filters.pop("area", None)

                    try:
                        all_areas = lister(
                            city,
                            filters=filters,
                        )
                    except Exception:
                        logger.exception(
                            "Verified corrected-area lookup failed"
                        )
                        all_areas = []

                    corrected_match = (
                        self.edge.match_displayed_option(
                            correction_fragment,
                            all_areas,
                        )
                        or self.edge.fuzzy_match_verified_option(
                            correction_fragment,
                            all_areas,
                        )
                    )

            if corrected_match is not None:
                return UserUnderstanding(
                    intent="property_search",
                    required={"area": corrected_match},
                    raw_message=text,
                )

            # If the corrected fragment did not safely match a verified area,
            # do not fall back to matching an older area mentioned earlier
            # in the same sentence. Let semantic/verified location repair
            # handle the turn instead.
            return None

        amenity = self._extract_area_amenity_requirement(text)
        if amenity:
            return UserUnderstanding(
                intent="property_search",
                required={"amenities": [amenity]},
                raw_message=text,
            )

        if self._looks_like_area_flexible(text):
            return UserUnderstanding(
                intent="property_search",
                relax=["area"],
                raw_message=text,
            )

        options = pending.get("options", [])
        if not isinstance(options, list):
            options = []

        # 1. Exact normalized name, e.g. "DHA phase6".
        matched = self.edge.match_displayed_option(
            text,
            options,
        )

        # 2. Safe typo recovery, e.g. "Bagria Town" -> a verified option.
        if matched is None:
            matched = self.edge.fuzzy_match_verified_option(
                text,
                options,
            )

        # 3. If the user named an area outside the short preview, compare
        #    against the full VERIFIED area list for the active filters.
        if matched is None:
            lister = getattr(self.knowledge, "list_areas", None)
            city = self.memory.required.get("city")

            if callable(lister) and isinstance(city, str) and city.strip():
                filters = dict(self.memory.required)
                filters.pop("area", None)

                try:
                    all_areas = lister(
                        city,
                        filters=filters,
                    )
                except Exception:
                    logger.exception("Verified area list lookup failed")
                    all_areas = []

                matched = self.edge.match_displayed_option(
                    text,
                    all_areas,
                ) or self.edge.fuzzy_match_verified_option(
                    text,
                    all_areas,
                )

        if matched is not None:
            return UserUnderstanding(
                intent="property_search",
                required={"area": matched},
                raw_message=text,
            )

        # Only pure/explicit list choices may be interpreted numerically.
        index = self.edge.strict_choice_index(text)

        if index is None:
            return None

        if not (0 <= index < len(options)):
            return UserUnderstanding(
                intent="property_search",
                needs_clarification=True,
                clarification_reason="selected_area_not_available",
                raw_message=text,
            )

        return UserUnderstanding(
            intent="property_search",
            required={"area": options[index]},
            raw_message=text,
        )

    def _area_correction_fragment(
        self,
        text: str,
    ) -> str | None:
        """Return only the NEW area phrase from a correction-style turn."""

        if not isinstance(text, str):
            return None

        normalized = " ".join(text.strip().split())
        if not normalized:
            return None

        # Prefer the text after the LAST strong correction marker.
        matches = list(
            re.finditer(
                r"\b(?:actually|instead|rather|i\s+mean|mera\s+matlab|matlab)\b",
                normalized,
                flags=re.IGNORECASE,
            )
        )

        if not matches:
            return None

        fragment = normalized[matches[-1].end():].strip(" ,.-")
        if not fragment:
            return None

        # Keep the location phrase and drop trailing conversational clauses.
        fragment = re.split(
            r"\b(?:"
            r"better|behtar|preferred|prefer|"
            r"budget|price|same|"
            r"rakho|rakhna|rahega|rahegi|"
            r"chahiye|chahey|chahye|"
            r"please|pls"
            r")\b",
            fragment,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        fragment = re.sub(
            r"\b(?:mein|me|main)\b\s*$",
            "",
            fragment,
            flags=re.IGNORECASE,
        )

        fragment = " ".join(fragment.split()).strip(" ,.-")
        return fragment or None

    def _parse_contextual_budget(
        self,
        text: str,
    ) -> int | None:
        """Parse a budget answer while Sara is explicitly waiting for budget.

        Accepts natural short answers such as:
            2 crore
            2 crore hai
            mera budget 2 crore hai
            budget 1.5 lakh hai
            150k
            PKR 500000

        Because this method is used only for the pending budget slot, it can
        safely extract one clear money expression from conversational wording.
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

        # Prefer explicit units because they are unambiguous.
        match = re.search(
            r"(?:rs\.?\s*|pkr\s*)?"
            r"(\d+(?:\.\d+)?)"
            r"\s*(crore|corore|carore|cror|cr|lakh|lac|k)"
            r"(?:\s*(?:rs\.?|pkr))?",
            normalized,
            flags=re.IGNORECASE,
        )

        # A plain numeric amount is also safe in this pending-budget context.
        if match is None:
            match = re.search(
                r"(?:rs\.?\s*|pkr\s*)?"
                r"(\d{4,})"
                r"(?:\s*(?:rs\.?|pkr))?",
                normalized,
                flags=re.IGNORECASE,
            )

        if match is None:
            return None

        number = float(
            match.group(1)
        )

        unit = (
            match.group(2)
            if match.lastindex
            and match.lastindex >= 2
            else None
        )

        multiplier = 1

        if unit in {
            "crore",
            "corore",
            "carore",
            "cror",
            "cr",
        }:
            multiplier = 10_000_000

        elif unit in {
            "lakh",
            "lac",
        }:
            multiplier = 100_000

        elif unit == "k":
            multiplier = 1_000

        amount = int(
            number * multiplier
        )

        return (
            amount
            if amount > 0
            else None
        )

    def _looks_like_budget_flexible(
        self,
        text: str,
    ) -> bool:
        """
        Detect conversational budget relaxation.

        Called only when Sara is explicitly waiting for the budget slot.
        Extra conversational words or STT noise should not make a clear
        "budget flexible" answer fail.
        """

        if not isinstance(text, str):
            return False

        normalized = " ".join(
            text.casefold().split()
        )

        if not normalized:
            return False

        if re.search(
            r"\b(?:flexible|open budget|no limit|any budget)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

        if re.search(
            r"\b(?:koi|kuch)\s+(?:bhi|b)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

        no_issue_patterns = (
            r"\bbudget\b.*\b(?:issue|masla|problem)\b.*\b(?:nahi|nahin|nai|no)\b",
            r"\b(?:issue|masla|problem)\b.*\b(?:nahi|nahin|nai|no)\b.*\bbudget\b",
            r"\b(?:koi\s+)?(?:issue|masla|problem)\s+(?:nahi|nahin|nai)\b",
            r"\bbudget\s+ka\s+(?:issue|masla|problem)\s+(?:nahi|nahin|nai)\b",
            r"\bbudget\s+(?:constraint|limit)\s+(?:nahi|nahin|nai)\b",
        )

        return any(
            re.search(
                candidate_pattern,
                normalized,
                flags=re.IGNORECASE,
            )
            for candidate_pattern in no_issue_patterns
        )

    def _looks_like_area_flexible(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        markers = {
            "flexible",
            "g flexible",
            "ji flexible",
            "flexible hai",
            "flexible hy",
            "koi bhi",
            "koi b",
            "any",
            "koi bhi area",
            "area koi bhi",
            "area flexible",
            "area flexible hai",
            "area flexible hy",
            "flexible area",
            "flexible area hai",
            "koi bhi chalega",
            "koi bhi chalegi",
            "koi b chaley ga",
            "any area",
        }

        return normalized in markers

    def _extract_choice_index(
        self,
        text: str,
    ) -> int | None:
        """Backward-compatible wrapper around strict list-choice parsing."""
        return self.edge.strict_choice_index(text)

    def _verified_location_fallback(
        self,
        text: str,
    ) -> UserUnderstanding | None:
        """Build a safe fallback from VERIFIED Day 2 location data."""
        resolver = getattr(
            self.knowledge,
            "resolve_locations",
            None,
        )

        if not callable(resolver):
            return None

        try:
            resolved = resolver(
                text,
                city_hint=self.memory.required.get("city"),
            )
        except Exception:
            logger.exception("Verified location fallback failed")
            return None

        if not isinstance(resolved, dict):
            return None

        area_candidates = resolved.get("_area_candidates", [])
        if area_candidates:
            return UserUnderstanding(
                intent="property_search",
                needs_clarification=True,
                clarification_reason="ambiguous_location_fragment",
                raw_message=text,
            )

        required = {}

        if resolved.get("city"):
            required["city"] = resolved["city"]

        if resolved.get("area"):
            required["area"] = resolved["area"]

        if not required:
            return None

        return UserUnderstanding(
            intent="property_search",
            required=required,
            comparison=ComparisonRequest(None, None, None, None),
            raw_message=text,
        )

    def _repair_with_verified_locations(
        self,
        understanding,
        text: str,
        *,
        trusted_fields: set[str] | None = None,
    ) -> dict[str, str]:
        """
        Repair city/area extraction using Day 2 verified location values.

        No business locations are hard-coded in this method.
        """

        trusted_fields = trusted_fields or set()

        resolver = getattr(
            self.knowledge,
            "resolve_locations",
            None,
        )

        if not callable(resolver):
            return {}

        try:
            resolved = resolver(
                text,
                city_hint=self.memory.required.get(
                    "city"
                ),
            )
        except Exception:
            # Location repair is defensive. A resolver failure should
            # not break the whole chatbot turn.
            return {}

        if not isinstance(
            resolved,
            dict,
        ):
            return {}

        current_fields = set()

        city = resolved.get("city")
        area = resolved.get("area")

        # Preserve what semantic NLU claimed before verified Day 2 repair.
        # Current-turn location values must never become authoritative
        # solely because the LLM emitted them.
        nlu_city = (
            understanding.required.get("city")
            or understanding.preferred.get("city")
        )
        nlu_area = (
            understanding.required.get("area")
            or understanding.preferred.get("area")
        )

        # Pending numbered/name choices come directly from VERIFIED
        # options Sara displayed; trust their canonical location value.
        if (
            not city
            and nlu_city
            and "city" in trusted_fields
        ):
            city = nlu_city

        if (
            not area
            and nlu_area
            and "area" in trusted_fields
        ):
            area = nlu_area

        # A semantic value may still be valid when the raw user spelling
        # contains a typo. Accept it only if (a) the current message likely
        # mentions it and (b) Day 2's verified catalog confirms it.
        if (
            not city
            and nlu_city
            and self._location_value_mentioned(nlu_city, text)
        ):
            city = self._canonical_verified_location_value(
                field="city",
                value=nlu_city,
                city_hint=None,
            )

        if (
            not area
            and nlu_area
            and self._location_value_mentioned(nlu_area, text)
        ):
            area = self._canonical_verified_location_value(
                field="area",
                value=nlu_area,
                city_hint=(
                    city
                    or self.memory.required.get("city")
                    or nlu_city
                ),
            )

        if city:
            understanding.required["city"] = city
            understanding.preferred.pop(
                "city",
                None,
            )
            understanding.excluded.pop(
                "city",
                None,
            )
            current_fields.add("city")

        if area:
            understanding.required["area"] = area
            understanding.preferred.pop(
                "area",
                None,
            )
            understanding.excluded.pop(
                "area",
                None,
            )
            current_fields.add("area")

        # If semantic NLU emitted a location but Day 2 could not verify
        # it from the CURRENT message, do not commit the raw LLM value.
        unverified_fields = []

        if nlu_city and not city:
            understanding.required.pop("city", None)
            understanding.preferred.pop("city", None)
            if self._location_value_mentioned(nlu_city, text):
                unverified_fields.append("city")

        if nlu_area and not area:
            understanding.required.pop("area", None)
            understanding.preferred.pop("area", None)
            if self._location_value_mentioned(nlu_area, text):
                unverified_fields.append("area")

        if unverified_fields:
            understanding.needs_clarification = True
            understanding.clarification_reason = "unverified_location"
            understanding.intent = "property_search"

        if current_fields:
            understanding.relax = [
                field_name
                for field_name
                in understanding.relax
                if field_name
                not in current_fields
            ]

        # ----------------------------------------------------------
        # Verified location exclusion
        # ----------------------------------------------------------
        # Examples:
        #   "E-11 k ilawa"
        #   "DHA Phase 6 ke ilawa"
        #   "except Bahria Town"
        #
        # The excluded place itself comes from the VERIFIED Day 2
        # location resolver, not from a hard-coded location list.
        if (
            area
            and self._looks_like_location_exclusion(
                text
            )
        ):
            understanding.required.pop(
                "area",
                None,
            )
            understanding.preferred.pop(
                "area",
                None,
            )

            understanding.excluded["area"] = [
                area
            ]

            understanding.relax = [
                field_name
                for field_name
                in understanding.relax
                if field_name != "area"
            ]

            # "E-11 ke ilawa" means the user accepts other areas.
            # Keep the exclusion, but do not immediately ask them to
            # choose another exact area.
            understanding.relax.append(
                "area"
            )

            # Prevent identifiers such as E-11/F-10/B-17 from being
            # hallucinated as numeric budgets on exclusion turns.
            if not self._message_has_explicit_money(
                text
            ):
                understanding.required.pop(
                    "budget",
                    None,
                )
                understanding.preferred.pop(
                    "budget",
                    None,
                )

            understanding.intent = (
                "property_search"
            )
            understanding.selected_index = None
            understanding.reference_type = None
            understanding.needs_clarification = False
            understanding.clarification_reason = None

        # ----------------------------------------------------------
        # Broadening within a city
        # ----------------------------------------------------------
        # If the user says "Islamabad mein aur options dikhao" while an
        # old area such as E-11 is active, the intent is to broaden back
        # to the city level. Since the city itself may be unchanged, the
        # memory layer cannot infer this automatically.
        if (
            city
            and not area
            and self._looks_like_broader_location_search(
                text
            )
        ):
            understanding.required.pop(
                "area",
                None,
            )
            understanding.preferred.pop(
                "area",
                None,
            )
            understanding.excluded.pop(
                "area",
                None,
            )

            if "area" not in understanding.relax:
                understanding.relax.append(
                    "area"
                )

            understanding.intent = (
                "property_search"
            )
            understanding.needs_clarification = False

            if understanding.clarification_reason in {
                "incomplete_location",
                "ambiguous_location_fragment",
            }:
                understanding.clarification_reason = None

        # A verified current-turn location should win over accidental
        # result-selection classification.
        #
        # Example:
        #   "B-17"
        # may be misread by the LLM as "result 17/second result".
        # If B-17 is a VERIFIED area and the user did not explicitly say
        # "option 2", "second", etc., it is a location refinement.
        if (
            current_fields
            and understanding.intent == "property_selection"
            and not self._looks_like_explicit_result_selection(
                text
            )
        ):
            understanding.intent = "property_search"
            understanding.selected_index = None
            understanding.reference_type = None

        # If a verified location was recovered and the message is plainly
        # asking to show/search options, repair an unknown/FAQ intent.
        if (
            current_fields
            and understanding.intent
            in {
                "unknown",
                "faq",
            }
            and self._looks_like_property_search_request(
                text
            )
            and not self._is_location_options_request(
                text
            )
        ):
            understanding.intent = (
                "property_search"
            )

        # "Islamabad mein dikhao" is complete. But a turn such as
        # "Islamabad sector mein dikhao" still lacks the sector ID.
        if (
            understanding.needs_clarification
            and understanding.clarification_reason
            == "incomplete_location"
            and current_fields
            and not self._has_unresolved_sub_location(
                text
            )
        ):
            understanding.needs_clarification = False
            understanding.clarification_reason = None

        return {
            key: value
            for key, value in {
                "city": city,
                "area": area,
            }.items()
            if value
        }

    def _location_value_mentioned(
        self,
        value,
        text: str,
    ) -> bool:
        """Whether a semantic location plausibly came from this turn.

        This is not verification. It only prevents old context copied by the
        LLM from being treated as a current-turn change.
        """
        if not isinstance(value, str) or not value.strip():
            return False

        from difflib import SequenceMatcher

        wanted = self.edge.normalize_location_choice(value)
        current = self.edge.normalize_location_choice(text)

        if not wanted or not current:
            return False

        if wanted in current:
            return True

        wanted_tokens = wanted.split()
        current_tokens = current.split()

        widths = {
            max(1, len(wanted_tokens) - 1),
            len(wanted_tokens),
            len(wanted_tokens) + 1,
        }

        best = 0.0

        for width in widths:
            if width > len(current_tokens):
                continue

            for start in range(
                0,
                len(current_tokens) - width + 1,
            ):
                phrase = " ".join(
                    current_tokens[start:start + width]
                )
                best = max(
                    best,
                    SequenceMatcher(
                        None,
                        wanted,
                        phrase,
                    ).ratio(),
                )

        return best >= 0.78

    def _canonical_verified_location_value(
        self,
        *,
        field: str,
        value,
        city_hint: str | None,
    ) -> str | None:
        """Return the canonical verified catalog value, or None."""
        if not isinstance(value, str) or not value.strip():
            return None

        target = self.edge.normalize_location_choice(value)

        if field == "city":
            lister = getattr(self.knowledge, "list_cities", None)

            if not callable(lister):
                return None

            try:
                values = lister(filters={})
            except Exception:
                logger.exception("Verified city validation failed")
                return None

        elif field == "area":
            lister = getattr(self.knowledge, "list_areas", None)

            if (
                not callable(lister)
                or not isinstance(city_hint, str)
                or not city_hint.strip()
            ):
                return None

            try:
                values = lister(
                    city_hint,
                    filters={},
                )
            except Exception:
                logger.exception("Verified area validation failed")
                return None

        else:
            return None

        for candidate in values or []:
            if (
                isinstance(candidate, str)
                and self.edge.normalize_location_choice(candidate)
                == target
            ):
                return candidate

        # The semantic layer may have normalized a typo to the canonical
        # spelling; safe fuzzy matching is still limited to verified values.
        return self.edge.fuzzy_match_verified_option(
            value,
            values or [],
        )

    def _looks_like_explicit_result_selection(
        self,
        text: str,
    ) -> bool:
        """
        Detect explicit references to a result/option.

        Pure location tokens such as "B-17" or "F-11" must not be treated
        as result numbers just because they contain digits.
        """

        import re

        normalized = " ".join(
            text.casefold().split()
        ).strip()

        if not normalized:
            return False

        # Plain integer such as "2" is a result selection.
        if re.fullmatch(
            r"\d+",
            normalized,
        ):
            return True

        ordinal_words = (
            "first",
            "second",
            "third",
            "last",
            "pehli",
            "pehla",
            "dusri",
            "doosri",
            "dusra",
            "doosra",
            "teesri",
            "teesra",
            "akhri",
            "aakhri",
        )

        if any(
            word in normalized
            for word in ordinal_words
        ):
            return True

        # Explicit option/result wording.
        if re.search(
            r"\b(option|result|property)\s*#?\s*\d+\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

        return False

    def _looks_like_property_search_request(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        markers = (
            "dikhao",
            "dikha",
            "dikhayein",
            "show",
            "options",
            "option",
            "suggest",
            "recommend",
            "chahiye",
            "chahye",
            "dekhna",
            "dekhni",
        )

        return any(
            marker in normalized
            for marker in markers
        )

    def _has_unresolved_sub_location(
        self,
        text: str,
    ) -> bool:
        """
        Return True for genuinely incomplete expressions such as:
            "sector mein dikhao"
            "phase mein"
            "block wala"

        A concrete identifier such as "sector F-11" is complete.
        """

        import re

        normalized = " ".join(
            text.casefold().split()
        )

        for keyword in (
            "phase",
            "sector",
            "block",
        ):
            if keyword not in normalized:
                continue

            pattern = (
                rf"\\b{keyword}\\s*"
                rf"(?:[-#]?\\s*)"
                rf"(?:\\d+[a-z]?|[a-z]\\s*[-/]?\\s*\\d+|[a-z])\\b"
            )

            if not re.search(
                pattern,
                normalized,
                flags=re.IGNORECASE,
            ):
                return True

        return False

    def _is_location_options_request(
        self,
        text: str,
    ) -> bool:
        """
        Detect questions asking which areas/sectors/locations are present.

        This is a structural conversational command only. Actual location
        names still come from PostgreSQL.
        """

        normalized = " ".join(
            text.casefold().split()
        )

        location_words = (
            "sector",
            "sectors",
            "area",
            "areas",
            "location",
            "locations",
            "phase",
            "phases",
        )

        discovery_markers = (
            "available",
            "kon kon",
            "kn kn",
            "kaun kaun",
            "which",
            "konsay",
            "konse",
            "kon se",
            "konsey",
            "knse",
            "knsey",
            "kaun se",
            "kaunse",
            "konsi",
            "kaunsi",
            "kya kya",
            "list",
        )

        return (
            any(
                word in normalized
                for word in location_words
            )
            and any(
                marker in normalized
                for marker in discovery_markers
            )
        )

    def _location_options_response(
        self,
        resolved_locations: dict[str, str],
    ) -> str:
        """
        Return verified area/location options from Day 2 structured data.
        """

        city = (
            resolved_locations.get("city")
            or self.memory.required.get(
                "city"
            )
        )

        if not city:
            return (
                "Ji, kis city ke available areas ya sectors "
                "dekhne hain?"
            )

        # The user is exploring the city as a whole, so old area scope
        # should not restrict this turn.
        self.memory.apply(
            required={
                "city": city,
            },
            relax=[
                "area",
            ],
        )

        lister = getattr(
            self.knowledge,
            "list_areas",
            None,
        )

        if not callable(lister):
            return (
                "Verified location listing abhi configured nahi hai."
            )

        # Preserve relevant current hard constraints such as Apartment,
        # Rental, bedrooms, budget, etc., but never carry an old area.
        filters = dict(
            self.memory.required
        )
        filters.pop(
            "area",
            None,
        )

        try:
            areas = lister(
                city,
                filters=filters,
            )
        except Exception:
            return (
                "Verified location data retrieve karne mein issue aaya "
                "hai; main sector names guess nahi karungi."
            )

        self.memory.last_intent = (
            "location_options"
        )

        if not areas:
            return (
                f"{city} mein current filters ke liye koi verified "
                "available area/sector nahi mila."
            )

        lines = [
            f"{index}. {area}"
            for index, area
            in enumerate(
                areas,
                start=1,
            )
        ]

        self.memory.pending_action = {
            "type": "choose_verified_area",
            "field": "area",
            "options": list(areas),
        }

        return (
            f"{city} mein current verified data ke mutabiq "
            "ye areas/sectors available hain:\n"
            + "\n".join(lines)
            + "\nAap in mein se koi area select kar sakti hain."
        )

    def _context(self) -> dict[str, Any]:
        return {
            "required": self.memory.required,
            "preferred": self.memory.preferred,
            "excluded": self.memory.excluded,
            "flexible": sorted(self.memory.flexible),
            "selected_property": self.memory.selected_property,
            "last_results": self.memory.last_results[
                : self.presentation.batch_size
            ],
            "has_more_results": self.memory.has_more_results(),
            "last_intent": self.memory.last_intent,
            "pending_action": self.memory.pending_action,
        }

    def _remember(
        self,
        text: str,
    ) -> str:
        self.memory.add_message(
            "assistant",
            text,
        )
        return text

    def _clarify(
        self,
        reason: str | None,
    ) -> str:
        return {
            "selected_result_not_available":
                "Ye option current results mein nahi hai. "
                "Valid option number batayein.",

            "selected_area_not_available":
                "Ye area option current verified list mein nahi hai. "
                "Valid area number ya area name bata dein.",

            "missing_comparison_reference":
                "Kis property ke saath comparison karna hai?",

            "missing_verified_comparison_value":
                "Comparison ke liye required verified value "
                "available nahi hai.",

            "incomplete_location":
                "Ji, location thori incomplete hai. Phase, sector "
                "ya block identifier bata dein, ya keh dein ke "
                "area flexible hai.",

            "ambiguous_reference":
                "Aap kis property ki baat kar rahi hain? "
                "Option number ya property name bata dein.",

            "missing_purpose_for_budget":
                "Aap ye budget rent ke liye bata rahi hain ya purchase "
                "ke liye? Dono ki pricing basis different hoti hai, "
                "isliye main guess nahi karungi.",

            "ambiguous_property_type":
                "Aap apartment, house, plot ya kisi ek specific property "
                "type ko prefer karti hain? Main choice guess nahi karungi.",

            "ambiguous_bedrooms":
                "Exact bedrooms kitne chahiye? Aap ne multiple bedroom "
                "counts mention kiye hain.",

            "ambiguous_purpose":
                "Aap rent ke liye dekh rahi hain ya purchase ke liye? "
                "Main dono mein se guess nahi karungi.",

            "ambiguous_location_fragment":
                "Is phase/sector/block ke multiple verified locations "
                "match ho rahe hain. Society ya complete area name "
                "bata dein.",

            "unverified_location":
                "Ye location current verified property data mein confirm "
                "nahi ho saki. Available city/area ka naam bata dein, "
                "ya main verified options dikha sakti hoon.",
        }.get(
            reason,
            "Requirement thori ambiguous hai. Thora aur clear kar dein.",
        )

    def _no_results(
        self,
        plan,
    ) -> str:
        if (
            plan.comparison_field == "price"
            and plan.comparison_operator == "lt"
            and plan.comparison_value is not None
        ):
            return (
                f"Current criteria mein "
                f"{plan.comparison_value:,.0f} PKR se cheaper "
                "verified option nahi mila."
            )

        recovery = self._grounded_no_result_recovery(
            plan
        )

        if recovery:
            return recovery

        active = self._active_constraint_labels()

        if active:
            return (
                "Current criteria ke exact combination mein verified "
                "property nahi mili. Current filters hain: "
                + ", ".join(active)
                + ". Aap area, budget ya kisi preference ko relax/change "
                  "kar sakti hain; main sirf verified matches dikhaungi."
            )

        return (
            "Current criteria ke andar koi verified property nahi mili. "
            "Aap requirement change ya relax kar sakti hain."
        )

    def _grounded_no_result_recovery(
        self,
        plan,
    ) -> str | None:
        """
        Suggest a useful next step only when Day 2 verified data proves
        that relaxing a specific constraint opens matching areas.

        No alternative area/property is invented by the LLM.
        """

        required = dict(
            plan.required
        )

        city = required.get(
            "city"
        )

        if not isinstance(
            city,
            str,
        ) or not city.strip():
            return None

        lister = getattr(
            self.knowledge,
            "list_areas",
            None,
        )

        if not callable(lister):
            return None

        current_area = required.get(
            "area"
        )

        # ----------------------------------------------------------
        # Probe 1: relax only area.
        # All other current hard constraints remain unchanged.
        # ----------------------------------------------------------
        without_area = dict(
            required
        )
        without_area.pop(
            "area",
            None,
        )

        try:
            areas_without_area = lister(
                city,
                filters=without_area,
            )
        except Exception:
            areas_without_area = []

        if current_area:
            alternatives = [
                area
                for area in areas_without_area
                if self._normalize_compare_text(area)
                != self._normalize_compare_text(
                    current_area
                )
            ]

            if alternatives:
                preview, has_more = (
                    self.presentation.preview_choices(
                        alternatives
                    )
                )

                extra = (
                    " Aur areas bhi hain."
                    if has_more
                    else ""
                )

                self.memory.pending_action = {
                    "type": "collect_requirement",
                    "field": "area",
                    "options": alternatives,
                }

                return (
                    f"{current_area}, {city} mein current exact criteria "
                    "ka verified match nahi mila. Lekin same baqi criteria "
                    "ke saath verified options in areas mein available hain: "
                    + ", ".join(preview)
                    + "."
                    + extra
                    + " Agar area flexible hai to main in mein options dikha sakti hoon."
                )

        # ----------------------------------------------------------
        # Probe 2: remove budget as well. If this opens areas while the
        # previous probe did not, budget is a grounded blocker city-wide
        # for the remaining constraints.
        # ----------------------------------------------------------
        if "budget" in required:
            without_budget = dict(
                without_area
            )
            without_budget.pop(
                "budget",
                None,
            )

            try:
                areas_without_budget = lister(
                    city,
                    filters=without_budget,
                )
            except Exception:
                areas_without_budget = []

            if (
                not areas_without_area
                and areas_without_budget
            ):
                preview, has_more = (
                    self.presentation.preview_choices(
                        areas_without_budget
                    )
                )

                extra = (
                    " Aur areas bhi hain."
                    if has_more
                    else ""
                )

                self.memory.pending_action = {
                    "type": "collect_requirement",
                    "field": "budget",
                    "options": [],
                }

                return (
                    "Current budget ke saath is combination ka verified "
                    "match nahi mila. Budget ko relax karne par matching "
                    "verified options in areas mein available hain: "
                    + ", ".join(preview)
                    + "."
                    + extra
                    + " Agar budget flexible hai to bata dein."
                )

        # ----------------------------------------------------------
        # Probe 3: remove amenities. This proves that a requested
        # amenity is the blocking constraint city-wide.
        # ----------------------------------------------------------
        if required.get(
            "amenities"
        ):
            without_amenities = dict(
                without_area
            )
            without_amenities.pop(
                "amenities",
                None,
            )

            try:
                areas_without_amenities = lister(
                    city,
                    filters=without_amenities,
                )
            except Exception:
                areas_without_amenities = []

            if (
                not areas_without_area
                and areas_without_amenities
            ):
                preview, has_more = (
                    self.presentation.preview_choices(
                        areas_without_amenities
                    )
                )

                extra = (
                    " Aur areas bhi hain."
                    if has_more
                    else ""
                )

                return (
                    "Requested amenity ke saath current exact combination "
                    "ka verified match nahi mila. Amenity ko relax karne par "
                    "verified options in areas mein available hain: "
                    + ", ".join(preview)
                    + "."
                    + extra
                    + " Main amenity ko guess ya assume nahi karungi."
                )

        return None

    def _normalize_compare_text(
        self,
        value,
    ) -> str:
        return " ".join(
            str(value)
            .casefold()
            .replace("-", " ")
            .split()
        )


    def _is_relaxation_help_request(
        self,
        text: str,
    ) -> bool:
        normalized = " ".join(
            text.casefold().split()
        )

        markers = (
            "kya relax",
            "kiya relax",
            "kia relax",
            "what should i relax",
            "what can i relax",
            "kya change",
            "kiya change",
            "kia change",
            "kis cheez ko relax",
            "konsa filter relax",
            "kaunsa filter relax",
        )

        return any(
            marker in normalized
            for marker in markers
        )

    def _relaxation_help(self) -> str:
        """
        Explain only CURRENT user-provided constraints.
        No property/business fact is invented here.
        """

        required = self.memory.required

        if not required:
            return (
                "Abhi koi hard search constraint active nahi hai. "
                "City, budget, area, bedrooms ya property type "
                "specify kar sakti hain."
            )

        # Prefer relaxing the most specific constraints before broader
        # intent-defining constraints.
        priority = (
            "area",
            "budget",
            "bedrooms",
            "amenities",
            "property_type",
            "purpose",
            "developer",
            "city",
        )

        field_labels = {
            "area": "area",
            "budget": "budget",
            "bedrooms": "bedrooms",
            "amenities": "amenities",
            "property_type": "property type",
            "purpose": "purpose",
            "developer": "developer",
            "city": "city",
            "investment_goal": "investment goal",
        }

        first_candidate = next(
            (
                field_name
                for field_name in priority
                if field_name in required
            ),
            None,
        )

        active = self._active_constraint_labels()

        if first_candidate:
            label = field_labels.get(
                first_candidate,
                first_candidate,
            )

            return (
                "Abhi aapke hard filters hain: "
                + ", ".join(active)
                + f". Sab se pehle {label} relax/change karna "
                "reasonable hoga. Agar aap chahein to keh dein "
                f"'{label} flexible hai'."
            )

        return (
            "Abhi aapke hard filters hain: "
            + ", ".join(active)
            + ". In mein se koi constraint relax ya change kar sakti hain."
        )

    def _active_constraint_labels(
        self,
    ) -> list[str]:
        labels = {
            "city": "city",
            "area": "area",
            "budget": "budget",
            "bedrooms": "bedrooms",
            "property_type": "property type",
            "purpose": "purpose",
            "amenities": "amenities",
            "investment_goal": "investment goal",
            "developer": "developer",
        }

        output = []

        for key, value in self.memory.required.items():
            label = labels.get(key, key)

            if isinstance(value, list):
                value_text = ", ".join(
                    str(item)
                    for item in value
                )
            else:
                value_text = str(value)

            output.append(
                f"{label}={value_text}"
            )

        return output

    def _workflow_handoff(
        self,
        intent: str,
    ) -> str:
        p = self.memory.selected_property

        if (
            not p
            and intent != "cancel_visit"
        ):
            return (
                "Visit workflow se pehle property select kar dein."
            )

        self.memory.pending_action = {
            "type": intent,
            "property": p,
        }

        action = {
            "schedule_visit": "booking",
            "reschedule_visit": "rescheduling",
            "cancel_visit": "cancellation",
        }[intent]

        return (
            f"{action.capitalize()} request samajh gayi. "
            "Day 4 Calendar/Email workflow actual availability "
            "verify karke hi final confirmation dega."
        )


RealEstateChatbot = SaraChatbot
