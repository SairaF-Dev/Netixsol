"""Unit tests for the rule-based review analyzer and the benchmark's integrity."""

from __future__ import annotations

import pytest

from shopkaro.reviews import benchmark as rb
from shopkaro.reviews import lexicon_analyzer as lx


def test_benchmark_sets_are_separate_and_balanced() -> None:
    dev = {it["text"] for it in rb.SENTIMENT_DEV}
    hold = {it["text"] for it in rb.SENTIMENT_HOLDOUT}
    assert len(rb.SENTIMENT_DEV) == 60 and len(rb.SENTIMENT_HOLDOUT) == 30
    assert not dev & hold
    assert not {it["text"] for it in rb.SPAM_DEV} & {it["text"] for it in rb.SPAM_HOLDOUT}
    for items in (rb.SENTIMENT_DEV, rb.SENTIMENT_HOLDOUT):
        langs = [it["lang"] for it in items]
        assert langs.count("English") == langs.count("Roman_Urdu") == langs.count("Urdu")
        for it in items:
            assert it["sentiment"] in rb.SENTIMENTS
            assert set(it["aspects"]) <= set(rb.ASPECTS)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Not worth the money at all.", "Negative"),  # negation inside a phrase
        ("Bura nahi hai", "Positive"),  # Roman Urdu negation after the word
        ("Theek thaak hai, itna khas nahi.", "Neutral"),
        ("Suit to khoobsurat hai magar 2 hafte baad mila.", "Neutral"),  # mixed: quality + / delivery -
        ("وقت پر پہنچا اور پیکنگ صاف ستھری تھی۔", "Positive"),  # "وقت پر" must not split the clause
    ],
)
def test_sentiment_rules(text: str, expected: str) -> None:
    assert lx.analyze_sentiment(text)["sentiment"] == expected


def test_aspects_follow_clauses() -> None:
    a = lx.analyze_aspects("Delivery to jaldi hui par kameez tang hai.")
    assert a["delivery"] == 1 and a["size_fit"] == -1
    # "do din chala" is about the product working for two days, not about delivery
    b = lx.analyze_aspects("Do din chala phir band ho gaya, bakwas.")
    assert b["delivery"] == 0 and b["quality"] == -1


@pytest.mark.parametrize(
    ("text", "spam"),
    [
        ("Earn Rs 5000 daily from home, WhatsApp 0321-1234567", True),
        ("Nice product nice product nice product nice product", True),
        ("Rider called from a 0300 number before arriving, very polite.", False),  # phone number, but genuine
        ("Fake leather, peeling after a month. Very disappointed.", False),  # the word "fake", but genuine
        ("BOHOT ZABARDAST!!! Ammi ko bohot pasand aaya", False),  # shouting, but genuine
    ],
)
def test_spam_rules(text: str, spam: bool) -> None:
    assert lx.classify_spam(text)["is_fake_spam"] is spam
