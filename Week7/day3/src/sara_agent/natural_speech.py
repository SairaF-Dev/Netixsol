from __future__ import annotations

import hashlib
import os
import re


class NaturalSpeechPolicy:
    """
    Adds restrained Pakistani conversational markers without changing facts.

    This layer is DELIVERY-ONLY:
    - no property facts are added
    - no prices/availability/locations are changed
    - only acknowledgement/filler/hesitation style is added

    Supported events:
        normal
        ack
        thinking
        clarification
        no_result
        success
        interruption
        light_laughter
    """

    ACKS = (
        "Ji bilkul.",
        "Acha.",
        "Theek hai.",
        "Hmm, samajh gayi.",
    )

    THINKING = (
        "Ek second...",
        "Hmm...",
        "Acha, ek second...",
    )

    CLARIFICATION = (
        "Acha...",
        "Ji, thora clear kar dein.",
        "Hmm, samajh gayi...",
    )

    NO_RESULT = (
        "Hmm...",
        "Acha...",
    )

    SUCCESS = (
        "Ji bilkul.",
        "Acha,",
    )

    LIGHT_LAUGHTER = (
        "Haha...",
        "Hehe...",
    )

    INTERRUPTION = (
        "Ji, boliye — main sun rahi hoon.",
        "Ji bilkul, boliye.",
    )

    SERIOUS_MARKERS = (
        "mehngi",
        "mehnga",
        "price",
        "trust",
        "risk",
        "safe",
        "investment",
        "builder",
        "developer",
        "maintenance",
        "problem",
        "issue",
        "complaint",
    )

    JOKE_MARKERS = (
        "haha",
        "hehe",
        "lol",
        "mazak",
        "joke",
        "funny",
    )

    _PREFIX_RE = re.compile(
        r"^(?:"
        r"ji\b|"
        r"acha\b|"
        r"theek\b|"
        r"hmm\b|"
        r"ek second\b|"
        r"haha\b|"
        r"hehe\b"
        r")",
        flags=re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.enabled = self._env_bool(
            "SARA_NATURAL_SPEECH_ENABLED",
            True,
        )
        self.laughter_enabled = self._env_bool(
            "SARA_NATURAL_SPEECH_LAUGHTER",
            True,
        )
        self.deterministic_variation = self._env_bool(
            "SARA_NATURAL_SPEECH_VARIATION",
            True,
        )

    def decorate(
        self,
        text: str,
        event: str = "normal",
        *,
        user_text: str = "",
    ) -> str:
        """
        Decorate response for spoken delivery.

        Same input + same event gives the same phrase when deterministic
        variation is enabled, which keeps tests reproducible.
        """

        if not isinstance(text, str):
            return ""

        cleaned = self._clean(text)

        if not cleaned or not self.enabled:
            return cleaned

        event = (event or "normal").strip().casefold()

        if event == "normal":
            return cleaned

        if event == "interruption":
            return self.interruption_ack()

        # Avoid duplicate fillers.
        if self._PREFIX_RE.match(cleaned):
            return cleaned

        if event == "ack":
            prefix = self._choose(
                self.ACKS,
                key=f"ack|{cleaned}",
            )
            return f"{prefix} {cleaned}"

        if event == "thinking":
            prefix = self._choose(
                self.THINKING,
                key=f"thinking|{cleaned}",
            )
            return f"{prefix} {cleaned}"

        if event == "clarification":
            prefix = self._choose(
                self.CLARIFICATION,
                key=f"clarification|{cleaned}",
            )
            return f"{prefix} {cleaned}"

        if event == "no_result":
            prefix = self._choose(
                self.NO_RESULT,
                key=f"no_result|{cleaned}",
            )
            return f"{prefix} {cleaned}"

        if event == "success":
            prefix = self._choose(
                self.SUCCESS,
                key=f"success|{cleaned}",
            )
            return f"{prefix} {cleaned}"

        if event == "light_laughter":
            return self._decorate_laughter(
                cleaned,
                user_text=user_text,
            )

        # Unknown event: fail safely and preserve original facts.
        return cleaned

    def auto_decorate(
        self,
        text: str,
        *,
        user_text: str = "",
    ) -> str:
        """
        Infer a safe delivery event from Sara's already-generated response.

        This is useful in the voice pipeline when caller does not explicitly
        supply an event.
        """

        cleaned = self._clean(text)

        if not cleaned or not self.enabled:
            return cleaned

        lower = cleaned.casefold()

        if (
            "reliably samajh nahi saki" in lower
            or "thora differently" in lower
            or "thora aur clear" in lower
            or "ambiguous" in lower
        ):
            event = "clarification"

        elif (
            "verified match nahi mila" in lower
            or "current exact criteria" in lower
            or "current budget ke saath" in lower
            or "available area nahi mila" in lower
        ):
            event = "no_result"

        elif (
            "matching verified options" in lower
            or "verified options mein se" in lower
            or "verified areas" in lower
        ):
            event = "success"

        elif (
            "maximum purchase budget" in lower
            or "maximum rent budget" in lower
            or "kis city mein" in lower
            or "kis area" in lower
            or (
                "rent ke liye" in lower
                and "purchase ke liye" in lower
            )
        ):
            event = "ack"

        else:
            event = "normal"

        result = self.decorate(
            cleaned,
            event=event,
            user_text=user_text,
        )

        # Laughter is a second, rare contextual layer.
        if self._should_laugh(user_text):
            result = self.decorate(
                result,
                event="light_laughter",
                user_text=user_text,
            )

        return result

    def interruption_ack(self) -> str:
        return self._choose(
            self.INTERRUPTION,
            key="interruption",
        )

    def thinking_ack(self) -> str:
        """Useful when a slow tool/RAG call begins."""
        return self._choose(
            self.THINKING,
            key="thinking_ack",
        )

    def _decorate_laughter(
        self,
        text: str,
        *,
        user_text: str,
    ) -> str:
        if not self.laughter_enabled:
            return text

        if not self._should_laugh(user_text):
            return text

        if self._PREFIX_RE.match(text):
            return text

        prefix = self._choose(
            self.LIGHT_LAUGHTER,
            key=f"laugh|{user_text}|{text}",
        )
        return f"{prefix} {text}"

    def _should_laugh(self, user_text: str) -> bool:
        value = (user_text or "").casefold()

        if not value:
            return False

        if any(
            marker in value
            for marker in self.SERIOUS_MARKERS
        ):
            return False

        return any(
            marker in value
            for marker in self.JOKE_MARKERS
        )

    def _choose(
        self,
        options: tuple[str, ...],
        *,
        key: str,
    ) -> str:
        if not options:
            return ""

        if not self.deterministic_variation:
            return options[0]

        digest = hashlib.sha256(
            key.encode("utf-8")
        ).digest()

        index = int.from_bytes(
            digest[:4],
            "big",
        ) % len(options)

        return options[index]

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _env_bool(
        name: str,
        default: bool,
    ) -> bool:
        value = os.getenv(name)

        if value is None:
            return default

        return value.strip().casefold() not in {
            "0",
            "false",
            "no",
            "off",
        }


_default_policy = NaturalSpeechPolicy()


def naturalize_speech(
    text: str,
    *,
    event: str = "normal",
    user_text: str = "",
) -> str:
    return _default_policy.decorate(
        text,
        event=event,
        user_text=user_text,
    )


def auto_naturalize_speech(
    text: str,
    *,
    user_text: str = "",
) -> str:
    return _default_policy.auto_decorate(
        text,
        user_text=user_text,
    )
