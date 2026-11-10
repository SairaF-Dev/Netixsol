"""
Runner script for Day 4 — Tasks 2 & 3: Personalized Search Re-Ranking & Tool-Calling UrduLish Shopping Assistant.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import time

from shopkaro.assistant.shopping_agent import (
    run_day4_task2_task3_personalizer_and_assistant,
)


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 4 — Tasks 2 & 3: Personalized Search Re-Ranking & Tool-Calling UrduLish Assistant..."
    )

    pers_summary, turns, assistant = run_day4_task2_task3_personalizer_and_assistant()
    elapsed = time.perf_counter() - t0

    print(f"\n=== Task 2: Personalized Search Re-Ranking Summary ({elapsed:.2f}s) ===")
    print(json.dumps(asdict(pers_summary), indent=2))

    # Show Luxury vs Budget top-3 for "eid lawn suit"
    lux_res, _ = assistant.tools.personalizer.search_personalized(
        "eid lawn suit", user_id="PERSONA_LUXURY_VIP", k=3
    )
    bud_res, _ = assistant.tools.personalizer.search_personalized(
        "eid lawn suit", user_id="PERSONA_BUDGET_HUNTER", k=3
    )
    print("\n--- Query: \"eid lawn suit\" -> Luxury VIP Persona Top-3 ---")
    for r in lux_res:
        print(
            f"  #{r['rank']} {r['product_id']} | {r['brand']} | {r['title'][:48]} | "
            f"PKR {r['price_pkr']:,.0f} | Score={r['score']}"
        )
    print("\n--- Query: \"eid lawn suit\" -> Budget Bargain Hunter Persona Top-3 ---")
    for r in bud_res:
        print(
            f"  #{r['rank']} {r['product_id']} | {r['brand']} | {r['title'][:48]} | "
            f"PKR {r['price_pkr']:,.0f} | Sale={r['on_sale']} | Score={r['score']}"
        )

    print("\n=== Task 3: 6-Turn Multi-Tool UrduLish Shopping Assistant Walkthrough ===")
    for t in turns:
        print(f"\n[Turn {t.turn_index}] User: \"{t.user_message}\"")
        print(
            f"  -> Intent: {t.detected_intent} | Tools Invoked: {t.invoked_tools} | "
            f"Zero-Hallucination Check: {t.hallucination_audit.passed_zero_hallucination_check}"
        )
        print(f"  -> Assistant Reply:\n{t.assistant_reply_urdulish}")


if __name__ == "__main__":
    main()

