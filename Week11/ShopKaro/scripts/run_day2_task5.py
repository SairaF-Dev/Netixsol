"""
Runner script for Day 2 — Task 5: Business Re-Ranking Layer, Association Rules & Roman Urdu Explanations.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import time

from shopkaro.recommendations.reranking import run_day2_task5_business_reranking


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 2 — Task 5: Business Re-Ranking Layer, Association Rules & Roman Urdu Explanations..."
    )

    summary, assoc_engine, _, demo_recs = run_day2_task5_business_reranking(
        k=10,
        eval_users_sample=300,
    )
    elapsed = time.perf_counter() - t0

    print(f"\n=== Day 2 Task 5: Business Re-Ranking Impact Summary ({elapsed:.2f}s) ===")
    print(json.dumps(asdict(summary), indent=2))

    print(
        "\n=== Sample Business Re-Ranked Top-5 Recommendations (Pre-Eid Mode + Roman Urdu Explanations) ==="
    )
    for rec in demo_recs[:5]:
        print(
            f"  #{rec['rank']} {rec['product_id']} | {rec['brand']} | {rec['title'][:52]} | "
            f"PKR {rec['price_pkr']:,.0f} | Margin={rec['margin_pct']}% | Sale={rec['on_sale']}"
        )
        print(f"     Roman Urdu: \"{rec['explanation_roman_urdu']}\"")

    # Show Frequently Bought Together for a Smartphone (SK-00013) and a Lawn Suit (SK-00001)
    for hero_pid in ["SK-00013", "SK-00001"]:
        fbt = assoc_engine.get_frequently_bought_together(hero_pid, k=4)
        hero_title = assoc_engine.item_metadata.get(hero_pid, {}).get("title", hero_pid)
        print(f"\n=== 'Frequently Bought Together' Rules for {hero_pid}: {hero_title[:60]} ===")
        for idx, r in enumerate(fbt, start=1):
            print(
                f"  #{idx} => {r['consequent_id']} ({r['consequent_brand']} | {r['consequent_category']}) "
                f"| PKR {r['consequent_price_pkr']:,.0f} | Conf={r['confidence']:.2f}, Lift={r['lift']:.2f} "
                f"[{r['rule_source']}]"
            )
            print(f"     Roman Urdu: \"{r['explanation_roman_urdu']}\"")


if __name__ == "__main__":
    main()

