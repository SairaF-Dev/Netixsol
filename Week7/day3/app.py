from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from sara_agent.runtime import SaraRuntime


def configure_logging() -> None:
    level_name = os.getenv(
        "SARA_LOG_LEVEL",
        "WARNING",
    ).upper()

    logging.basicConfig(
        level=getattr(
            logging,
            level_name,
            logging.WARNING,
        ),
        format="%(levelname)s %(name)s: %(message)s",
    )


def main():
    configure_logging()

    try:
        runtime = SaraRuntime()
        bot = runtime.new_bot(
            response_mode="chat"
        )
    except Exception as exc:
        print(
            "Sara startup configuration error: "
            f"{exc.__class__.__name__}: {exc}"
        )
        print(
            "Check .env values for DAY2_ROOT, DATABASE_URL, "
            "OPENROUTER_API_KEY and optional RAG settings."
        )
        return

    print(
        "Sara: Assalam-o-Alaikum! Main Sara hoon. "
        "Ji batayein, aap kis tarah ki property dekh rahi hain?"
    )
    print(
        "      Exit: quit | Memory clear: reset"
    )

    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSara: Allah Hafiz!")
            break

        if text.casefold() in {
            "quit",
            "exit",
        }:
            print("Sara: Allah Hafiz!")
            break

        if not text:
            continue

        print(
            "\nSara:",
            bot.handle_message(text),
        )


if __name__ == "__main__":
    main()
