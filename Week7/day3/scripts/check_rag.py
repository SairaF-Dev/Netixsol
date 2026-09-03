from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        ROOT
        / "src"
    ),
)
load_dotenv(
    ROOT
    / ".env"
)

from sara_agent.rag_bridge import (
    build_default_rag_bridge,
)


def main():
    bridge = (
        build_default_rag_bridge()
    )

    print(
        "RAG STATUS"
    )
    print(
        bridge.status()
    )

    question = (
        "Are investment returns guaranteed?"
    )

    print(
        "\nQUESTION"
    )
    print(
        question
    )

    try:
        answer = bridge.answer(
            question
        )
    except Exception as exc:
        print(
            "\nRAG ERROR"
        )
        print(
            f"{exc.__class__.__name__}: {exc}"
        )
        return

    print(
        "\nANSWER"
    )
    print(
        answer
        or "NO GROUNDED ANSWER"
    )

    print(
        "\nUPDATED STATUS"
    )
    print(
        bridge.status()
    )


if __name__ == "__main__":
    main()
