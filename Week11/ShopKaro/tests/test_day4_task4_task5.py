"""
Verification tests for Day 4 — Tasks 4 & 5: sentiment, 6-aspect ABSA, topics, spam, seller insights.

Quality is checked on the hand-written benchmark (`shopkaro.reviews.benchmark`), never on the 11-template
synthetic corpus, where any model scores ~100% by memorising the templates.
"""

from __future__ import annotations

import duckdb

from shopkaro.config.settings import settings
from shopkaro.reviews.intelligence import ASPECT_NAMES, ReviewIntelligencePipeline


def test_day4_task4_and_task5_review_intelligence() -> None:
    pipeline = ReviewIntelligencePipeline()
    results = pipeline.run_full_pipeline(persist_to_duckdb=True, save_artifacts=True)

    # 4A sentiment: held-out hand-written reviews
    sent = results["sentiment_evaluation"]
    hold = sent["benchmark"]["holdout_30"]
    assert hold["rule analyzer"]["accuracy"] >= 0.70
    assert hold["rule analyzer"]["accuracy"] > hold["majority (always Positive)"]["accuracy"] + 0.2
    assert hold["rule analyzer"]["macro_f1"] > hold["word count (no clauses / negation)"]["macro_f1"]
    assert hold["rule_vs_majority_mcnemar_p"] < 0.05
    assert {m["language"] for m in sent["per_language_metrics"]} == {"Roman_Urdu", "English", "Urdu"}
    for lm in sent["per_language_metrics"]:
        assert lm["accuracy"] >= 0.6

    mixed = pipeline.sentiment_clf.predict_text("Product bohot acha hai lekin delivery 10 din late aayi")
    assert mixed["is_mixed_sentiment"] is True and mixed["sentiment"] == "Neutral"
    assert len(mixed["clauses"]) == 2

    # 4B aspects: better than predicting "nothing mentioned", and precise when it does flag an aspect
    absa = results["absa_evaluation"]
    ah = absa["benchmark"]["holdout_30"]
    assert ah["rule analyzer"]["cell_accuracy"] > ah["all zero (nothing mentioned)"]["cell_accuracy"]
    assert ah["rule analyzer"]["detection_precision"] >= 0.9
    assert ah["rule analyzer"]["mean_aspect_macro_f1"] > 0.5
    assert [m["aspect"] for m in absa["per_aspect_metrics"]] == ASPECT_NAMES
    aspects = pipeline.absa_analyzer.predict_aspects("Product bohot acha hai lekin delivery 10 din late aayi")
    assert aspects["quality"] == 1 and aspects["delivery"] == -1

    # 4C topics
    topics = results["topic_discovery"]
    assert topics["n_topics"] == 6 and len(topics["topics"]) == 6
    assert sum(t["review_count"] for t in topics["topics"]) == 8000

    # 5A spam: new spam formats and hard genuine reviews
    spam = results["spam_detection"]
    sh = spam["benchmark"]["holdout_10"]
    assert sh["rule detector"]["f1"] >= 0.8
    assert sh["rule detector"]["f1"] > sh["previous regex patterns"]["f1"]
    assert sh["rule detector"]["precision"] == 1.0  # no genuine review flagged
    promo = pipeline.spam_detector.score_review(
        "Cheap discount offer WhatsApp now",
        "Visit www.cheap-deals-pk.biz or WhatsApp 0300-0000000 for 90% off replicas!!",
        rating=5,
    )
    assert promo["is_fake_spam"] is True and promo["spam_reason"] == "promo_link"

    # 5B insights are computed from predictions
    biz = results["business_insights"]
    assert biz["products_analyzed"] >= 400
    assert biz["sellers_evaluated"] >= 50
    assert biz["unfairly_penalized_products_count"] >= 1
    sample_pid = biz["unfairly_penalized_top_examples"][0]["product_id"]
    single = pipeline.get_product_review_intelligence(sample_pid)
    assert single["product_id"] == sample_pid
    assert single["is_unfairly_penalized_by_courier"] is True
    assert "quality" in single["aspect_scores"]

    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    con.close()
    assert {"review_intelligence_summary", "seller_scorecards"} <= tables
    assert (settings.figures_dir / "13_review_intelligence_and_absa.png").exists()
