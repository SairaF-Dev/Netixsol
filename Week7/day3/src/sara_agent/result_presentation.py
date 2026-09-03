from __future__ import annotations

import os
from typing import Any

from .formatting import property_summary


class ResultPresentationPolicy:
    """
    Progressive disclosure for real-world property conversations.

    Business values are never stored here. This policy controls only
    how many VERIFIED results Sara presents at one time.

    Defaults:
    - chat / CLI: 5 properties per batch
    - voice: 3 properties per batch
    - area/city choice preview: 5 options

    All values can be changed with environment variables.
    """

    def __init__(
        self,
        mode: str | None = None,
    ):
        requested_mode = (
            mode
            or os.getenv(
                "SARA_RESPONSE_MODE",
                "chat",
            )
        )

        normalized = str(
            requested_mode
        ).strip().casefold()

        self.mode = (
            "voice"
            if normalized == "voice"
            else "chat"
        )

        default_batch = (
            3
            if self.mode == "voice"
            else 5
        )

        self.batch_size = self._env_int(
            "SARA_RESULT_BATCH_SIZE",
            default_batch,
            minimum=1,
            maximum=5,
        )

        self.choice_preview_size = self._env_int(
            "SARA_CHOICE_PREVIEW_SIZE",
            5,
            minimum=3,
            maximum=8,
        )

    def set_mode(
        self,
        mode: str,
    ) -> None:
        normalized = str(
            mode
        ).strip().casefold()

        self.mode = (
            "voice"
            if normalized == "voice"
            else "chat"
        )

        # Respect an explicit environment override. Otherwise adapt
        # automatically when the channel changes.
        if "SARA_RESULT_BATCH_SIZE" not in os.environ:
            self.batch_size = (
                3
                if self.mode == "voice"
                else 5
            )

    def format_batch(
        self,
        batch: list[dict[str, Any]],
        *,
        has_more: bool,
        first_batch: bool,
    ) -> str:
        if not batch:
            return (
                "Is search ke current loaded verified options khatam "
                "ho gaye hain. Aap criteria refine ya change kar sakti hain."
            )

        if first_batch:
            if self.mode == "voice":
                intro = (
                    "Ji. Aapke criteria ke matching verified options "
                    "mein se pehle kuch ye hain:"
                )
            else:
                intro = (
                    "Ji. Aapke current criteria ke matching verified "
                    "options mein se ye relevant options hain:"
                )
        else:
            intro = "Ji, next verified options ye hain:"

        lines = [intro]

        for index, row in enumerate(
            batch,
            start=1,
        ):
            lines.append(
                property_summary(
                    row,
                    index,
                )
            )

        if has_more:
            if self.mode == "voice":
                lines.append(
                    "Aur options bhi hain. 'Aur options' kahen to "
                    "main next few bata dungi."
                )
            else:
                lines.append(
                    "Aur matching verified options bhi hain. "
                    "'Aur options' kahen to next batch dikha dungi."
                )
        else:
            lines.append(
                "Ye current matching verified options ka last loaded batch hai."
            )

        lines.append(
            "In mein se kisi option ki details, comparison ya "
            "aur filtering chahiye?"
        )

        return "\n".join(lines)

    def preview_choices(
        self,
        values: list[str],
    ) -> tuple[list[str], bool]:
        """
        Return a compact preview and whether additional verified choices
        exist beyond the preview.
        """

        preview = list(
            values[: self.choice_preview_size]
        )

        return (
            preview,
            len(values) > len(preview),
        )

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
            value = int(raw)
        except (TypeError, ValueError):
            return default

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )
