from __future__ import annotations

import os
import re


class VoiceResponseFormatter:
    """Make verified Sara replies concise for spoken TTS output only."""

    _NUMBERED_LINE = re.compile(r"(?m)^\s*(\d+)\.\s+(.+?)\s*$")

    def __init__(self) -> None:
        self.max_chars = self._env_int(
            "SARA_VOICE_MAX_CHARS", 480, minimum=180, maximum=1200
        )
        self.max_property_options = self._env_int(
            "SARA_VOICE_PROPERTY_OPTIONS", 2, minimum=1, maximum=3
        )
        self.max_area_options = self._env_int(
            "SARA_VOICE_AREA_OPTIONS", 3, minimum=1, maximum=5
        )

    def format(self, response: str) -> str:
        if not isinstance(response, str):
            return ""
        text = response.strip()
        if not text:
            return ""

        numbered = self._NUMBERED_LINE.findall(text)
        if numbered:
            return self._format_numbered_response(text, numbered)

        if len(text) <= self.max_chars:
            return self._voice_cleanup(text)

        return self._sentence_limit(text)

    def _format_numbered_response(
        self,
        text: str,
        numbered: list[tuple[str, str]],
    ) -> str:
        first_match = self._NUMBERED_LINE.search(text)
        preamble = text[: first_match.start()].strip() if first_match else ""

        is_property_list = any(
            self._looks_like_property_line(item)
            for _, item in numbered
        )
        limit = (
            self.max_property_options
            if is_property_list
            else self.max_area_options
        )
        chosen = numbered[:limit]

        if is_property_list:
            intro = self._compact_property_intro(preamble)
            parts = [intro] if intro else ["Ji bilkul."]
            for index, (_, item) in enumerate(chosen, start=1):
                parts.append(
                    f"Option {index}: {self._clean_property_line(item)}"
                )

            if len(numbered) > limit:
                parts.append(
                    "Aur matching options screen par available hain."
                )
            else:
                parts.append(
                    "In mein se kisi ki details chahiye to bata dein."
                )
            return self._sentence_limit(" ".join(parts))

        intro = self._compact_area_intro(preamble)
        labels = [self._clean_choice_line(item) for _, item in chosen]
        ending = (
            "Aur areas bhi screen par available hain."
            if len(numbered) > limit
            else "Aap kis area ko prefer karti hain?"
        )
        return self._sentence_limit(
            f"{intro} {', '.join(labels)}. {ending}".strip()
        )

    @staticmethod
    def _looks_like_property_line(item: str) -> bool:
        lower = item.casefold()
        return (
            "pkr" in lower
            or "bedroom" in lower
            or "purchase" in lower
            or "rent" in lower
        )

    def _compact_property_intro(self, preamble: str) -> str:
        lower = preamble.casefold()
        if "matching verified options" in lower:
            return "Ji bilkul. Matching verified options mein se:"
        if "verified options" in lower:
            return "Ji bilkul. Verified options mein se:"
        return self._voice_cleanup(preamble)

    @staticmethod
    def _compact_area_intro(preamble: str) -> str:
        match = re.search(
            r"\b(Lahore|Islamabad|Karachi)\b",
            preamble,
            flags=re.IGNORECASE,
        )
        if match:
            return f"Ji. {match.group(1)} mein kuch verified areas hain:"
        return "Ji. Kuch verified areas hain:"

    @staticmethod
    def _clean_property_line(item: str) -> str:
        text = " ".join(item.split())
        text = re.sub(
            r"\s+—\s+0\s+bedrooms?\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.rstrip(" .")

    @staticmethod
    def _clean_choice_line(item: str) -> str:
        return " ".join(item.split()).rstrip(" .")

    def _sentence_limit(self, text: str) -> str:
        cleaned = self._voice_cleanup(text)
        if len(cleaned) <= self.max_chars:
            return cleaned

        candidate = cleaned[: self.max_chars + 1]
        boundary = max(
            candidate.rfind(". "),
            candidate.rfind("? "),
            candidate.rfind("! "),
        )
        if boundary >= int(self.max_chars * 0.55):
            return candidate[: boundary + 1].strip()

        candidate = candidate[: self.max_chars]
        if " " in candidate:
            candidate = candidate.rsplit(" ", 1)[0]
        return candidate.rstrip(" ,;:-") + "."

    @staticmethod
    def _voice_cleanup(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()

    @staticmethod
    def _env_int(
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError:
            value = default
        return max(minimum, min(maximum, value))


_default_formatter = VoiceResponseFormatter()


def format_voice_response(response: str) -> str:
    return _default_formatter.format(response)
