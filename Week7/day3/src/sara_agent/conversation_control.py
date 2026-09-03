from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class ControlDecision:
    action: str
    message: str | None = None
    clear_memory: bool = False
    pending_action: dict[str, Any] | None = None


class ConversationControlPolicy:
    """
    Deterministic non-business conversation controls.

    This policy never creates a property fact. It handles only:
    - repeat
    - reset / forget previous requirements
    - human escalation
    - safe refusal to invent/override verified facts
    - natural closing
    """

    def detect(
        self,
        text: str,
        *,
        last_assistant_message: str | None = None,
    ) -> ControlDecision | None:
        normalized = self._normalize(text)

        if not normalized:
            return None

        if self._matches_any(
            normalized,
            (
                r"\brepeat\b",
                r"\bdobara\b",
                r"\bphir se\b",
                r"\bagain\b",
                r"\brepeat kar",
            ),
        ):
            return ControlDecision(
                action="repeat",
                message=(
                    last_assistant_message
                    or "Abhi repeat karne ke liye previous Sara response available nahi hai."
                ),
            )

        if self._matches_any(
            normalized,
            (
                r"\bforget (?:the )?previous\b",
                r"\bforget previous requirements\b",
                r"\bprevious requirements bhool",
                r"\bsab reset\b",
                r"\breset search\b",
                r"\bstart over\b",
                r"\bnayi search\b",
                r"\bnew search\b",
            ),
        ):
            return ControlDecision(
                action="reset",
                clear_memory=True,
                message=(
                    "Theek hai. Previous property requirements clear kar di hain. "
                    "Nayi requirement batayein."
                ),
            )

        if self._matches_any(
            normalized,
            (
                r"\bhuman agent\b",
                r"\breal agent\b",
                r"\bsales agent\b",
                r"\brepresentative\b",
                r"\binsaan se baat\b",
                r"\bagent se baat\b",
                r"\bhuman se baat\b",
                r"\bperson se baat\b",
            ),
        ):
            return ControlDecision(
                action="human_handoff",
                pending_action={
                    "type": "human_handoff",
                },
                message=(
                    "Ji. Main human-agent handoff request note kar rahi hoon. "
                    "Actual routing/CRM handoff configured business workflow ke through hoga; "
                    "main fake transfer confirmation nahi dungi."
                ),
            )

        if self._matches_any(
            normalized,
            (
                r"\bignore (?:your|all) rules\b",
                r"\bmake up (?:a )?property\b",
                r"\binvent (?:a )?price\b",
                r"\bguess (?:the )?price\b",
                r"\bsay .* available\b",
                r"\btell me .* available\b",
                r"\bguaranteed roi\b",
                r"\bguarantee (?:the )?return\b",
                r"\bdatabase check mat\b",
                r"\bwithout database\b",
            ),
        ):
            return ControlDecision(
                action="grounding_safety",
                message=(
                    "Main verified property facts ko override, invent ya guess nahi karungi. "
                    "Price, availability, amenities, developer, nearby data aur returns ke liye "
                    "sirf verified sources use hongi; unavailable information ko unavailable hi bataungi."
                ),
            )

        if self._matches_any(
            normalized,
            (
                r"\bbye\b",
                r"\bgoodbye\b",
                r"\bkhuda hafiz\b",
                r"\ballah hafiz\b",
                r"\bthanks\b",
                r"\bthank you\b",
                r"\bshukriya\b",
                r"\bnot interested\b",
                r"\binterested nahi\b",
                r"\bsoch kar bata",
                r"\bthink about it\b",
                r"\bfamily se discuss\b",
            ),
        ):
            return ControlDecision(
                action="close",
                message=(
                    "Theek hai. Jab bhi property options, verified details, comparison "
                    "ya visit workflow mein help chahiye ho, Sara assist kar sakti hai."
                ),
            )

        return None

    def _normalize(
        self,
        text: str,
    ) -> str:
        return " ".join(
            str(text).casefold().split()
        )

    def _matches_any(
        self,
        text: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        )
