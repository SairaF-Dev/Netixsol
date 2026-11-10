"""
Runner script for Day 4 — Tasks 4 & 5: Multilingual Review Intelligence,
6-Aspect ABSA, Unsupervised Topic Discovery, Fake/Spam Review Detection,
and Seller/Management Actionable Insights.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from shopkaro.reviews.intelligence import ReviewIntelligencePipeline


def _ascii_safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def main() -> None:
    print("=" * 80)
    print("SHOPKARO DAY 4 - TASKS 4 & 5: MULTILINGUAL REVIEW INTELLIGENCE PIPELINE")
    print("=" * 80)

    pipeline = ReviewIntelligencePipeline()
    results = pipeline.run_full_pipeline(persist_to_duckdb=True, save_artifacts=True)

    sent = results["sentiment_evaluation"]
    print("\n[Task 4A] Sentiment on the hand-written benchmark (never-seen reviews):")
    for set_name, systems in sent["benchmark"].items():
        for system, m in systems.items():
            if isinstance(m, dict):
                print(f"  {set_name:<11} {system:<36} accuracy={m['accuracy']:.3f}  macro-F1={m['macro_f1']:.3f}")
        print(f"  {set_name:<11} rule analyzer vs majority: exact McNemar p = {systems['rule_vs_majority_mcnemar_p']}")
    print(
        f"  Held-out (headline): accuracy {sent['overall_accuracy']:.4f} | macro-F1 {sent['overall_macro_f1']:.4f}; "
        f"agreement with synthetic corpus labels {sent['corpus_agreement_with_generator_labels']:.3f}"
    )
    for lm in sent["per_language_metrics"]:
        print(
            f"  - {lm['language']:<12} (n={lm['test_samples']:<4}): "
            f"Accuracy={lm['accuracy']:.4f}, Macro-F1={lm['macro_f1']:.4f}"
        )

    print("\n  Contrastive Mixed-Sentiment Probe Examples:")
    for pr in sent["mixed_sentiment_probes"][:3]:
        print(
            f"  * [{pr['language']}] {_ascii_safe(pr['text'][:68])} -> "
            f"Pred={pr['predicted_sentiment']} (ContrastiveMixed={pr['is_contrastive_mixed']})"
        )

    absa = results["absa_evaluation"]
    print("\n[Task 4B] 6-Aspect Sentiment Analysis (ABSA), benchmark:")
    for set_name, systems in absa["benchmark"].items():
        for system, m in systems.items():
            print(
                f"  {set_name:<11} {system:<30} cell-acc={m['cell_accuracy']:.3f}  macro-F1={m['mean_aspect_macro_f1']:.3f}  "
                f"detect P/R={m['detection_precision']:.2f}/{m['detection_recall']:.2f}"
            )
    print(
        f"  Mean Aspect Accuracy: {absa['mean_aspect_accuracy']:.4f} | "
        f"Mean Aspect Macro-F1: {absa['mean_aspect_macro_f1']:.4f}"
    )
    for am in absa["per_aspect_metrics"]:
        print(
            f"  - {am['aspect']:<12}: Acc={am['accuracy']:.4f}, Macro-F1={am['macro_f1']:.4f} "
            f"(Pos={am['positive_rate_pct']}%, Neu={am['neutral_rate_pct']}%, Neg={am['negative_rate_pct']}%)"
        )

    print("\n  Clause-Aware ABSA Contrast Demos:")
    for dm in absa["contrast_absa_demos"]:
        print(f"  * Text: {_ascii_safe(dm['review_text'])}")
        print(f"    Aspects: {json.dumps(dm['aspects'])}")

    topics = results["topic_discovery"]
    print(f"\n[Task 4C] Unsupervised c-TF-IDF Topic Discovery ({topics['n_topics']} Topics):")
    for t in topics["topics"]:
        print(
            f"  - Topic #{t['topic_id']} [{_ascii_safe(t['topic_name'])}]: "
            f"n={t['review_count']} ({t['share_pct']}%), AvgRating={t['avg_rating']}*, "
            f"Lang={t['dominant_language']}, Keywords=[{_ascii_safe(t['top_c_tfidf_keywords'])}]"
        )

    spam = results["spam_detection"]
    print("\n[Task 5A] Fake / Spam Review Detection:")
    print(
        f"  Flagged Spam: {spam['flagged_spam_count']} / {spam['total_reviews']} "
        f"({spam['flagged_spam_pct']}%)"
    )
    for set_name, systems in spam["benchmark"].items():
        for system, m in systems.items():
            print(f"  {set_name:<11} {system:<26} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    print(
        f"  Corpus vs generator spam labels: precision {spam['corpus_precision_vs_generator_labels']:.3f}, "
        f"recall {spam['corpus_recall_vs_generator_labels']:.3f}"
    )
    print(f"  Flagged by Reason: {json.dumps(spam['flagged_by_reason'])}")

    biz = results["business_insights"]
    print("\n[Task 5B] Seller & Management Actionable Insights:")
    print(
        f"  Products Analyzed: {biz['products_analyzed']} | "
        f"Sellers Evaluated: {biz['sellers_evaluated']} | "
        f"Unfairly Penalized by 3PL Courier: {biz['unfairly_penalized_products_count']}"
    )
    print(f"  Seller Tier Distribution: {json.dumps(biz['seller_tier_distribution'])}")
    print("  Top Unfairly Penalized Product Gems (High Quality, High 3PL Delivery Delay):")
    for ex in biz["unfairly_penalized_top_examples"]:
        print(
            f"  * SKU #{ex['product_id']} ({_ascii_safe(ex['brand'])} - {_ascii_safe(ex['title'][:45])}): "
            f"Rating={ex['avg_rating']}*, QualityPos={ex['quality_pos_pct']}%, "
            f"DeliveryNeg={ex['delivery_neg_pct']}% -> {ex['recommended_action']}"
        )

    print("\nArtifacts saved:")
    print("  - reports/day4_review_intelligence_metrics.csv")
    print("  - reports/day4_product_review_intelligence.csv")
    print("  - reports/day4_seller_scorecards.csv")
    print("  - reports/figures/13_review_intelligence_and_absa.png")
    print("=" * 80)


if __name__ == "__main__":
    main()

