from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Iterable


class EdgeCasePolicy:
    """Generic conversational edge-case helpers.

    This module contains only language/schema normalization. It never
    contains property inventory, city/area lists, prices, developers,
    availability, or any other business fact.
    """

    _TOKEN_REPAIRS = {
        # Roman-Urdu request spelling noise.
        "chahiey": "chahiye",
        "chahiy": "chahiye",
        "chahye": "chahiye",
        "chahey": "chahiye",
        "chaye": "chahiye",
        "chahiyeh": "chahiye",
        # Transaction spelling noise.
        "purhcase": "purchase",
        "puchase": "purchase",
        "purchse": "purchase",
        "purchas": "purchase",
        "rnt": "rent",
        # Money unit spelling noise.
        "corore": "crore",
        "carore": "crore",
        "cror": "crore",
    }

    def repair_tokens(self, text: str) -> str:
        """Repair known language typos while preserving punctuation/numbers."""
        if not isinstance(text, str):
            return ""

        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            repaired = self._TOKEN_REPAIRS.get(token.casefold())
            return repaired if repaired is not None else token

        return re.sub(r"\b[a-zA-Z]+\b", replace, text)

    def normalize_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        value = self.repair_tokens(text).casefold()
        value = re.sub(r"[^a-z0-9\s-]+", " ", value)
        return " ".join(value.split())

    def normalize_location_choice(self, text: str) -> str:
        """Normalize a location choice without knowing any locations."""
        value = self.normalize_text(text).replace("-", " ")
        # phase6 -> phase 6, f10 -> f 10
        value = re.sub(r"([a-z])(?=\d)", r"\1 ", value)
        value = re.sub(r"(?<=\d)([a-z])", r" \1", value)
        return " ".join(value.split())

    def match_displayed_option(
        self,
        text: str,
        options: Iterable[str],
    ) -> str | None:
        """Exact normalized match against options Sara actually displayed."""
        target = self.normalize_location_choice(text)
        if not target:
            return None

        for option in options:
            if (
                isinstance(option, str)
                and self.normalize_location_choice(option) == target
            ):
                return option

        return None

    def fuzzy_match_verified_option(
        self,
        text: str,
        options: Iterable[str],
        *,
        minimum_score: float = 0.78,
        minimum_margin: float = 0.08,
    ) -> str | None:
        """Safely fuzzy-match only against verified/displayed choices.

        Auto-correction is accepted only when one candidate is both:
        - sufficiently similar, and
        - clearly better than the second-best candidate.

        This prevents ambiguous inputs such as "DHA" from silently choosing
        a particular phase.
        """
        target = self.normalize_location_choice(text)
        if not target:
            return None

        # Do not interpret obvious non-location numeric/financial answers
        # as fuzzy location names.
        if re.fullmatch(r"\d+(?:\.\d+)?\s*(?:crore|lakh|lac|k)?", target):
            return None

        scored: list[tuple[float, str]] = []

        for option in options:
            if not isinstance(option, str) or not option.strip():
                continue

            normalized = self.normalize_location_choice(option)
            score = SequenceMatcher(None, target, normalized).ratio()

            # Token overlap protects against unrelated short strings.
            target_tokens = set(target.split())
            option_tokens = set(normalized.split())
            if target_tokens and option_tokens:
                overlap = len(target_tokens & option_tokens) / max(
                    1,
                    min(len(target_tokens), len(option_tokens)),
                )
                score = (score * 0.8) + (overlap * 0.2)

            scored.append((score, option))

        if not scored:
            return None

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_option = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0

        if best_score < minimum_score:
            return None

        if len(scored) > 1 and (best_score - second_score) < minimum_margin:
            return None

        return best_option

    def strict_choice_index(self, text: str) -> int | None:
        """Parse a list selection only when the utterance is clearly a choice.

        Embedded digits in `DHA phase6`, `F-10`, `3 crore`, or
        `3 bedroom` are deliberately rejected.
        """
        value = self.normalize_text(text)
        if not value:
            return None

        patterns = (
            r"^(\d{1,2})$",
            r"^(?:option|number|no)\s*(\d{1,2})$",
            r"^(\d{1,2})\s*(?:wala|wali|one)$",
            r"^(\d{1,2})(?:st|nd|rd|th)$",
        )

        for pattern in patterns:
            match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
            if match:
                number = int(match.group(1))
                return number - 1 if number >= 1 else None

        ordinals = {
            0: ("first", "pehla", "pehli", "pahla", "pahli", "first wali", "first wala"),
            1: ("second", "dusra", "dusri", "doosra", "doosri", "second wali", "second wala"),
            2: ("third", "teesra", "teesri", "third wali", "third wala"),
            3: ("fourth", "chautha", "chauthi", "fourth wali", "fourth wala"),
            4: ("fifth", "panchwa", "panchwi", "fifth wali", "fifth wala"),
        }

        for index, phrases in ordinals.items():
            if value in phrases:
                return index

        return None

    def looks_like_generic_property_request(self, text: str) -> bool:
        value = self.normalize_text(text)
        if not value:
            return False

        request_words = {
            "chahiye",
            "dekhni",
            "dekhna",
            "dekhnay",
            "dikhao",
            "dikhaye",
            "dikhayein",
            "search",
            "find",
        }

        tokens = set(value.split())
        return "property" in tokens and bool(tokens & request_words)
