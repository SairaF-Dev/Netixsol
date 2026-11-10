"""
Day 4 — Tasks 4 & 5: Multilingual Review Intelligence & Actionable Insights.

1. MultilingualSentimentClassifier (4A): Positive / Neutral / Negative for English, Roman Urdu and Urdu, with
   clause-level mixed-sentiment detection ("Product bohot acha hai lekin delivery 10 din late aayi").
2. AspectSentimentAnalyzer (4B): polarity of quality, price, delivery, size_fit, packaging, seller.
3. ReviewTopicDiscoverer (4C): TF-IDF + SVD + KMeans + c-TF-IDF topics (BERTopic-style, without neural
   embeddings) with monthly trends.
4. SpamReviewDetector (5A): promotional / bot spam with a reason.
5. SellerInsightsEngine (5B): separates product quality from courier delays ("unfairly penalised" products),
   product and seller scorecards.

1, 2 and 4 are rule-based (`lexicon_analyzer`) and evaluated on a hand-written benchmark (`benchmark`), because
the synthetic training corpus is 11 templates and trained models only memorised them. Business insights (5B) are
computed from the analyzers' predictions, not from the generator's labels, as they would be on real reviews.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer, TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import Normalizer

from shopkaro.config.settings import settings
from shopkaro.reviews import benchmark as rb
from shopkaro.reviews import lexicon_analyzer as lx
from shopkaro.reviews.insights_report import customer_summaries, save_insight_tables


ASPECT_NAMES: list[str] = list(lx.ASPECTS)

ASPECT_COLUMN_MAP: dict[str, str] = {
    "quality": "aspect_quality",
    "price": "aspect_price",
    "delivery": "aspect_delivery",
    "size_fit": "aspect_size_fit",
    "packaging": "aspect_packaging",
    "seller": "aspect_seller",
}

# Names kept for the dashboard and older callers; the vocabulary lives in lexicon_analyzer.
CONTRAST_SPLIT_PATTERN = lx.CLAUSE_SPLIT
ASPECT_KEYWORDS = lx.ASPECT_KEYWORDS
POSITIVE_WORDS: list[str] = lx.POSITIVE
NEGATIVE_WORDS: list[str] = lx.NEGATIVE


def _count_matches(text: str, phrases: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for phrase in phrases if phrase in text_lower)


def _word_count_sentiment(text: str) -> str:
    """Baseline: count positive vs negative words, no clauses, no negation."""
    p, n = _count_matches(text, POSITIVE_WORDS), _count_matches(text, NEGATIVE_WORDS)
    return "Positive" if p > n else ("Negative" if n > p else "Neutral")


def _review_texts(df: pd.DataFrame) -> pd.Series:
    return df["review_title"].fillna("") + " . " + df["review_text"].fillna("")


def _exact_mcnemar_p(a_correct: list[bool], b_correct: list[bool]) -> float:
    """Two-sided exact McNemar test on paired correct/incorrect outcomes."""
    b_only = sum(1 for a, b in zip(a_correct, b_correct) if b and not a)
    a_only = sum(1 for a, b in zip(a_correct, b_correct) if a and not b)
    n = a_only + b_only
    return 1.0 if n == 0 else float(binomtest(b_only, n, 0.5).pvalue)


@dataclass
class SentimentEvaluationResult:
    """Sentiment results. Headline numbers are on the held-out hand-written benchmark."""

    overall_accuracy: float
    overall_macro_f1: float
    overall_weighted_f1: float
    per_language_metrics: list[dict[str, Any]]
    mixed_sentiment_probes: list[dict[str, Any]]
    benchmark: dict[str, Any]
    corpus_agreement_with_generator_labels: float


class MultilingualSentimentClassifier:
    """
    Task 4A: English / Roman Urdu / Urdu sentiment (Positive / Neutral / Negative) with clause-level mixed
    sentiment ("Product bohot acha hai lekin delivery 10 din late aayi" -> Neutral, quality +, delivery -).

    Rule-based (`lexicon_analyzer`). An earlier TF-IDF + logistic regression model reported 100% accuracy on a
    random split of the 11-template synthetic corpus but scored 50% on new hand-written reviews; see the Day 4
    report. Evaluation now uses `shopkaro.reviews.benchmark` (60 dev + 30 held-out reviews).
    """

    def __init__(self) -> None:
        self._is_fitted = True

    def fit_and_evaluate(self, reviews_df: pd.DataFrame) -> SentimentEvaluationResult:
        systems = {
            "majority (always Positive)": lambda t: "Positive",
            "word count (no clauses / negation)": _word_count_sentiment,
            "rule analyzer": lambda t: lx.analyze_sentiment(t)["sentiment"],
        }
        bench: dict[str, Any] = {}
        for set_name, items in (("dev_60", rb.SENTIMENT_DEV), ("holdout_30", rb.SENTIMENT_HOLDOUT)):
            bench[set_name] = {name: rb.evaluate_sentiment(fn, items) for name, fn in systems.items()}
            ours = [it["sentiment"] == lx.analyze_sentiment(it["text"])["sentiment"] for it in items]
            base = [it["sentiment"] == "Positive" for it in items]
            bench[set_name]["rule_vs_majority_mcnemar_p"] = round(_exact_mcnemar_p(base, ours), 4)

        hold = bench["holdout_30"]["rule analyzer"]
        y_hold = [it["sentiment"] for it in rb.SENTIMENT_HOLDOUT]
        p_hold = [lx.analyze_sentiment(it["text"])["sentiment"] for it in rb.SENTIMENT_HOLDOUT]
        weighted = float(f1_score(y_hold, p_hold, average="weighted", zero_division=0))
        per_lang = [
            {"language": lang, "test_samples": m["n"], "accuracy": m["accuracy"], "macro_f1": m["macro_f1"]}
            for lang, m in hold["per_language"].items()
        ]

        genuine = reviews_df[~reviews_df["is_fake_spam"]]
        texts = _review_texts(genuine)
        pred = texts.map({t: lx.analyze_sentiment(t)["sentiment"] for t in texts.unique()})
        agreement = float((pred.to_numpy() == genuine["sentiment_label"].to_numpy()).mean())

        probes = [
            ("Product bohot acha hai lekin delivery 10 din late aayi", "Roman_Urdu", "Neutral"),
            ("Bohot ghatiya quality ka kurta bheja hai. Dabba phata hua tha aur seller reply nahi karta.", "Roman_Urdu", "Negative"),
            ("The phone quality is genuinely nice for the price, however delivery took over a week.", "English", "Neutral"),
            ("یہ پراڈکٹ بہت شاندار ہے۔ کوالٹی اور پیکنگ دونوں لاجواب ہیں۔", "Urdu", "Positive"),
        ]
        probe_results = []
        for text, lang, expected in probes:
            out = lx.analyze_sentiment(text)
            probe_results.append(
                {
                    "text": text,
                    "language": lang,
                    "expected_sentiment": expected,
                    "predicted_sentiment": out["sentiment"],
                    "is_contrastive_mixed": out["is_mixed_sentiment"],
                    "clause_breakdown": out["clauses"],
                }
            )

        return SentimentEvaluationResult(
            overall_accuracy=hold["accuracy"],
            overall_macro_f1=hold["macro_f1"],
            overall_weighted_f1=round(weighted, 4),
            per_language_metrics=per_lang,
            mixed_sentiment_probes=probe_results,
            benchmark=bench,
            corpus_agreement_with_generator_labels=round(agreement, 4),
        )

    def predict_text(self, text: str) -> dict[str, Any]:
        """Sentiment + clause breakdown for any English / Roman Urdu / Urdu review."""
        return lx.analyze_sentiment(text)


class AspectSentimentAnalyzer:
    """
    Task 4B: polarity {-1, 0, +1} for `quality`, `price`, `delivery`, `size_fit`, `packaging`, `seller`, scored
    clause by clause so "Product acha hai lekin delivery late" gives quality +1, delivery -1. Rule-based
    (`lexicon_analyzer`); evaluated on the hand-written benchmark.
    """

    def __init__(self) -> None:
        self._is_fitted = True

    def extract_clause_aspect_lexicon_scores(self, text: str) -> dict[str, int]:
        return lx.analyze_aspects(text)

    def predict_aspects(self, text: str) -> dict[str, int]:
        return lx.analyze_aspects(text)

    def fit_and_evaluate(self, reviews_df: pd.DataFrame) -> dict[str, Any]:
        systems = {"all zero (nothing mentioned)": lambda t: {}, "rule analyzer": lx.analyze_aspects}
        bench = {
            set_name: {name: rb.evaluate_aspects(fn, items) for name, fn in systems.items()}
            for set_name, items in (("dev_60", rb.SENTIMENT_DEV), ("holdout_30", rb.SENTIMENT_HOLDOUT))
        }

        # Per-aspect accuracy / macro-F1 on the held-out set; polarity shares from predictions on the corpus.
        y = np.array([[it["aspects"].get(a, 0) for a in ASPECT_NAMES] for it in rb.SENTIMENT_HOLDOUT])
        p = np.array([[lx.analyze_aspects(it["text"])[a] for a in ASPECT_NAMES] for it in rb.SENTIMENT_HOLDOUT])
        genuine = reviews_df[~reviews_df["is_fake_spam"]]
        texts = _review_texts(genuine)
        cache = {t: lx.analyze_aspects(t) for t in texts.unique()}
        per_aspect = []
        for j, asp in enumerate(ASPECT_NAMES):
            corpus_pred = np.array([cache[t][asp] for t in texts])
            per_aspect.append(
                {
                    "aspect": asp,
                    "column": ASPECT_COLUMN_MAP[asp],
                    "accuracy": round(float(accuracy_score(y[:, j], p[:, j])), 4),
                    "macro_f1": round(float(f1_score(y[:, j], p[:, j], labels=[-1, 0, 1], average="macro", zero_division=0)), 4),
                    "positive_rate_pct": round(float(np.mean(corpus_pred == 1) * 100.0), 2),
                    "negative_rate_pct": round(float(np.mean(corpus_pred == -1) * 100.0), 2),
                    "neutral_rate_pct": round(float(np.mean(corpus_pred == 0) * 100.0), 2),
                }
            )

        demos = [
            "Product bohot acha hai lekin delivery 10 din late aayi",
            "Kapra aur finishing zabardast hai magar size thora chhota hai aur packing phata hua tha",
            "Quality is excellent and price is affordable, but courier delivery was very slow",
        ]
        return {
            "mean_aspect_accuracy": bench["holdout_30"]["rule analyzer"]["cell_accuracy"],
            "mean_aspect_macro_f1": bench["holdout_30"]["rule analyzer"]["mean_aspect_macro_f1"],
            "per_aspect_metrics": per_aspect,
            "benchmark": bench,
            "contrast_absa_demos": [{"review_text": t, "aspects": lx.analyze_aspects(t)} for t in demos],
        }


# English stop words plus common Roman Urdu function words, so topic keywords show content ("kapra", "delivery",
# "size") rather than "aur / hai / bhi".
ROMAN_URDU_STOP_WORDS = {
    "aur", "hai", "hain", "ha", "bhi", "ka", "ki", "ke", "ko", "se", "ne", "mein", "main", "me", "tha", "thi", "the",
    "ho", "hua", "hui", "hota", "hoti", "bohot", "bohat", "bahut", "ye", "yeh", "wo", "woh", "to", "par", "pe", "kar",
    "kiya", "diya", "gaya", "gayi", "liye", "wala", "wali", "bilkul", "ek", "kuch", "sab", "jo", "na", "nahi",
}
TOPIC_STOP_WORDS = sorted(set(ENGLISH_STOP_WORDS) | ROMAN_URDU_STOP_WORDS)


class ReviewTopicDiscoverer:
    """
    Task 4C: Unsupervised Topic Modeling (BERTopic-inspired pipeline:
    Multilingual TF-IDF + TruncatedSVD Dense Embeddings + KMeans + Class-based TF-IDF / c-TF-IDF).
    Discovers latent customer feedback themes and tracks monthly topic trends.
    """

    def __init__(self, n_topics: int = 6) -> None:
        self.n_topics = n_topics
        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=3000,
            lowercase=True,
            stop_words=TOPIC_STOP_WORDS,
        )
        self.svd = TruncatedSVD(n_components=24, random_state=42)
        self.normalizer = Normalizer(copy=False)
        self.kmeans = KMeans(n_clusters=n_topics, random_state=42, n_init=10)
        self.backend = "tfidf_svd_kmeans"  # becomes "bertopic" when the library is installed

    @staticmethod
    def _infer_topic_label(top_words: list[str], avg_rating: float, spam_share: float) -> str:
        joined = " ".join(top_words).lower()
        if spam_share > 0.40 or "100%" in joined or "whatsapp" in joined or "competitor" in joined:
            return "Promotional & Bot Spam Anomalies"
        if "late" in joined or "week" in joined or "5 din" in joined or "smaller" in joined or "chhota" in joined or "size" in joined:
            return "Late Courier Delivery & Sizing Complaints"
        if "ghatiya" in joined or "damaged" in joined or "phata" in joined or "zaya" in joined or "torn" in joined or "overpriced" in joined or "مختلف" in joined:
            return "Defective Quality & Torn Packaging Complaints"
        if any("\u0600" <= ch <= "\u06FF" for ch in joined):
            return "Urdu Script Quality & Value Reviews"
        if "paisa" in joined or "wasool" in joined or "hisaab" in joined or "taawun" in joined or "kamaal" in joined:
            return "Value for Money (Paisa Wasool) & Seller Praise"
        if "kapra" in joined or "achi hai" in joined or "tasveer" in joined:
            return "Fabric & Stitching Quality Praise (Roman Urdu)"
        if "exceeded" in joined or "arrived" in joined or "fits perfectly" in joined or "time par" in joined:
            return "Fast Delivery & Authentic Product Praise (English)"
        return f"Customer Feedback Cluster (Avg {avg_rating:.1f}★)"

    def _bertopic_clusters(self, texts: list[str]) -> tuple[np.ndarray, dict[int, list[str]]] | None:
        """
        BERTopic (multilingual sentence embeddings -> UMAP -> KMeans(n_topics) -> c-TF-IDF keywords) when the
        library is installed (Python 3.11 env). Only distinct texts are embedded (the corpus repeats templates).
        Returns (cluster per input text, keywords per cluster) or None to use the TF-IDF + SVD fallback.
        """
        try:
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
            from umap import UMAP
        except Exception:
            return None
        uniq = list(dict.fromkeys(texts))
        model_name = settings.search_embedding_model
        encoder = SentenceTransformer(model_name, device="cpu")
        prefix = "passage: " if "e5" in model_name.lower() else ""
        emb = encoder.encode([prefix + t for t in uniq], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        topic_model = BERTopic(
            embedding_model=encoder,
            umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
            hdbscan_model=KMeans(n_clusters=self.n_topics, random_state=42, n_init=10),
            vectorizer_model=CountVectorizer(ngram_range=(1, 2), stop_words=TOPIC_STOP_WORDS, min_df=2),
            calculate_probabilities=False,
        )
        uniq_topics, _ = topic_model.fit_transform(uniq, embeddings=emb)
        topic_of = dict(zip(uniq, uniq_topics))
        clusters = np.array([int(topic_of[t]) for t in texts])
        terms = {int(cid): [w for w, _ in (topic_model.get_topic(cid) or [])] for cid in set(uniq_topics)}
        return clusters, terms

    def discover_topics(self, reviews_df: pd.DataFrame) -> dict[str, Any]:
        """Run unsupervised topic discovery and compute c-TF-IDF keywords + monthly trends."""
        df = reviews_df.copy()
        texts = (
            df["review_title"].fillna("") + " " + df["review_text"].fillna("")
        ).tolist()

        bertopic_terms = self._bertopic_clusters(texts)
        if bertopic_terms is not None:
            clusters, terms_by_cluster = bertopic_terms
            self.backend = "bertopic"
        else:
            X_tfidf = self.tfidf.fit_transform(texts)
            n_comp = min(24, X_tfidf.shape[1] - 1)
            if n_comp != self.svd.n_components:
                self.svd = TruncatedSVD(n_components=max(2, n_comp), random_state=42)
            X_emb = self.normalizer.fit_transform(self.svd.fit_transform(X_tfidf))
            clusters = self.kmeans.fit_predict(X_emb)
            terms_by_cluster = None
            self.backend = "tfidf_svd_kmeans"
        df["topic_id"] = clusters

        # Class-based TF-IDF (c-TF-IDF) per cluster
        count_vec = CountVectorizer(
            ngram_range=(1, 2),
            max_features=2500,
            stop_words=TOPIC_STOP_WORDS,
        )
        cluster_docs = []
        for cid in range(self.n_topics):
            sub_texts = [texts[i] for i in range(len(texts)) if clusters[i] == cid]
            cluster_docs.append(" ".join(sub_texts))

        tf_matrix = count_vec.fit_transform(cluster_docs).toarray().astype(np.float64)
        vocab = np.array(count_vec.get_feature_names_out())

        # c-TF-IDF formula: tf_{t, c} * log(1 + A / tf_t)
        words_per_class = np.maximum(tf_matrix.sum(axis=1, keepdims=True), 1.0)
        tf_norm = tf_matrix / words_per_class
        total_freq_per_word = np.maximum(tf_matrix.sum(axis=0, keepdims=True), 1.0)
        avg_words_per_class = float(np.mean(words_per_class))
        idf = np.log(1.0 + avg_words_per_class / total_freq_per_word)
        c_tfidf = tf_norm * idf

        topic_summaries: list[dict[str, Any]] = []
        topic_id_to_name: dict[int, str] = {}

        for cid in range(self.n_topics):
            sub_df = df[df["topic_id"] == cid]
            if terms_by_cluster is not None:
                top_terms = terms_by_cluster.get(cid, [])[:8]  # BERTopic's own c-TF-IDF keywords
            else:
                top_indices = np.argsort(c_tfidf[cid])[::-1][:8]
                top_terms = [str(vocab[idx]) for idx in top_indices]
            avg_rating = float(sub_df["rating"].mean()) if len(sub_df) else 0.0
            spam_share = float(sub_df["is_fake_spam"].mean()) if len(sub_df) else 0.0
            label = self._infer_topic_label(top_terms, avg_rating, spam_share)
            if label in topic_id_to_name.values():
                label = f"{label} #{cid + 1}"
            topic_id_to_name[cid] = label

            topic_summaries.append(
                {
                    "topic_id": int(cid),
                    "topic_name": label,
                    "review_count": int(len(sub_df)),
                    "share_pct": round(float(len(sub_df) / len(df) * 100.0), 2),
                    "avg_rating": round(avg_rating, 2),
                    "avg_delivery_delay_days": round(float(sub_df["delivery_delay_days"].mean()), 2),
                    "dominant_language": str(sub_df["language"].mode().iloc[0]) if len(sub_df) else "N/A",
                    "top_c_tfidf_keywords": ", ".join(top_terms[:6]),
                }
            )

        df["topic_name"] = df["topic_id"].map(topic_id_to_name)

        # Monthly topic trend table
        df["year_month"] = pd.to_datetime(df["review_date"]).dt.to_period("M").astype(str)
        trend_df = (
            df.groupby(["year_month", "topic_name"], as_index=False)
            .size()
            .rename(columns={"size": "review_count"})
            .sort_values(["year_month", "review_count"], ascending=[True, False])
        )

        return {
            "n_topics": self.n_topics,
            "topics": sorted(topic_summaries, key=lambda x: x["review_count"], reverse=True),
            "monthly_trends_sample": trend_df.tail(18).to_dict("records"),
            "topic_assignments": df[["review_id", "topic_id", "topic_name"]],
        }


class SpamReviewDetector:
    """
    Task 5A: fake / spam review detection with an explainable reason (`promo_link`, `duplicate_bot`,
    `extreme_burst`). Rule-based signals (`lexicon_analyzer.spam_signals`): URLs / @handles, a phone number with a
    contact verb, promo / referral / wholesale offers, competitor promotion, bot phrases and repetitive text.

    An earlier random-forest model scored 1.000 on a split of the corpus, whose spam is three fixed sentences
    repeated; on new spam it caught 1 in 5. Evaluation now uses the hand-written benchmark.
    """

    # Kept for the dashboard's live analyzer.
    URL_PHONE_PATTERN = lx.URL_OR_HANDLE
    BOT_TEMPLATE_PATTERN = lx.BOT_PHRASES
    BURST_ATTACK_PATTERN = lx.BOT_PHRASES

    def __init__(self) -> None:
        self._is_fitted = True

    @staticmethod
    def _regex_baseline(text: str) -> bool:
        """The previous detector's three hand-written patterns, as a baseline."""
        return bool(
            re.search(r"(?:http[s]?://|www\.|\.biz|\.com|whatsapp|03\d{2}[-\s]?\d{7}|replicas|90%\s*off)", text, re.I)
            or re.search(r"(?:100%\s*a\+\+\+|must\s*buy\s*best\s*seller|5\s*stars!{2,})", text, re.I)
            or re.search(r"(?:fake\s+fake\s+fake|competitor\s+store\s+is\s+better|do\s+not\s+buy)", text, re.I)
        )

    def predict_corpus(self, reviews_df: pd.DataFrame) -> pd.DataFrame:
        texts = _review_texts(reviews_df)
        cache = {t: lx.classify_spam(t) for t in texts.unique()}
        return pd.DataFrame(
            {
                "is_fake_spam": [cache[t]["is_fake_spam"] for t in texts],
                "spam_reason": [cache[t]["spam_reason"] for t in texts],
            },
            index=reviews_df.index,
        )

    def fit_and_evaluate(self, reviews_df: pd.DataFrame) -> dict[str, Any]:
        systems = {
            "previous regex patterns": lambda t, r: self._regex_baseline(t),
            "rule detector": lambda t, r: lx.classify_spam(t)["is_fake_spam"],
        }
        bench = {
            set_name: {name: rb.evaluate_spam(fn, items) for name, fn in systems.items()}
            for set_name, items in (("dev_16", rb.SPAM_DEV), ("holdout_10", rb.SPAM_HOLDOUT))
        }
        hold = bench["holdout_10"]["rule detector"]

        pred = self.predict_corpus(reviews_df)
        y_corpus = reviews_df["is_fake_spam"].astype(bool).to_numpy()
        p_corpus = pred["is_fake_spam"].to_numpy()
        return {
            "total_reviews": int(len(reviews_df)),
            "flagged_spam_count": int(p_corpus.sum()),
            "flagged_spam_pct": round(float(p_corpus.mean() * 100.0), 2),
            "test_precision": hold["precision"],
            "test_recall": hold["recall"],
            "test_f1": hold["f1"],
            "benchmark": bench,
            "corpus_precision_vs_generator_labels": round(float(precision_score(y_corpus, p_corpus, zero_division=0)), 4),
            "corpus_recall_vs_generator_labels": round(float(recall_score(y_corpus, p_corpus, zero_division=0)), 4),
            "flagged_by_reason": {str(k): int(v) for k, v in pred.loc[pred["is_fake_spam"], "spam_reason"].value_counts().items()},
        }

    def score_review(self, review_title: str, review_text: str, rating: int = 5) -> dict[str, Any]:
        out = lx.classify_spam(f"{review_title} . {review_text}")
        return {
            "is_fake_spam": out["is_fake_spam"],
            "spam_reason": out["spam_reason"],
            "signals": out["signals"],
        }


class SellerInsightsEngine:
    """
    Task 5B: Seller & Management Actionable Insights Generator.
    - Separates Intrinsic Product Quality from 3PL Courier Delivery penalties.
    - Identifies "Unfairly Penalized Gems" (products/sellers whose star rating is
      dragged down by slow 3PL couriers despite high product quality praise).
    - Persists `review_intelligence_summary` and `seller_scorecards` into DuckDB.
    """

    def generate_insights(
        self,
        reviews_df: pd.DataFrame,
        catalogue_df: pd.DataFrame,
    ) -> dict[str, Any]:
        clean_df = reviews_df[~reviews_df["is_fake_spam"]].copy()
        spam_df = reviews_df[reviews_df["is_fake_spam"]].copy()

        # 1. Product-Level Review Intelligence Summary
        prod_grp = (
            clean_df.groupby(["product_id", "category", "brand"], as_index=False)
            .agg(
                genuine_review_count=("review_id", "count"),
                avg_rating=("rating", "mean"),
                positive_sentiment_pct=("sentiment_label", lambda s: float(np.mean(s == "Positive") * 100.0)),
                negative_sentiment_pct=("sentiment_label", lambda s: float(np.mean(s == "Negative") * 100.0)),
                avg_delivery_delay_days=("delivery_delay_days", "mean"),
                quality_net_score=("aspect_quality", "mean"),
                quality_pos_pct=("aspect_quality", lambda s: float(np.mean(s == 1) * 100.0)),
                price_net_score=("aspect_price", "mean"),
                delivery_net_score=("aspect_delivery", "mean"),
                delivery_neg_pct=("aspect_delivery", lambda s: float(np.mean(s == -1) * 100.0)),
                size_fit_net_score=("aspect_size_fit", "mean"),
                size_fit_neg_pct=("aspect_size_fit", lambda s: float(np.mean(s == -1) * 100.0)),
                packaging_net_score=("aspect_packaging", "mean"),
                seller_net_score=("aspect_seller", "mean"),
            )
        )

        spam_counts = (
            spam_df.groupby("product_id", as_index=False)
            .size()
            .rename(columns={"size": "spam_filtered_count"})
        )
        prod_summary = prod_grp.merge(spam_counts, on="product_id", how="left")
        prod_summary["spam_filtered_count"] = prod_summary["spam_filtered_count"].fillna(0).astype(int)

        # Merge product title & price from catalogue
        cat_cols = catalogue_df[["product_id", "title", "price_pkr"]].drop_duplicates("product_id")
        prod_summary = prod_summary.merge(cat_cols, on="product_id", how="left")

        # Diagnose root cause & recommended action per product
        actions = []
        is_unfairly_penalized = []
        for _, r in prod_summary.iterrows():
            q_pos = float(r["quality_pos_pct"])
            del_neg = float(r["delivery_neg_pct"])
            sz_neg = float(r["size_fit_neg_pct"])
            avg_rt = float(r["avg_rating"])

            if q_pos >= 65.0 and del_neg >= 35.0 and avg_rt < 4.15:
                is_unfairly_penalized.append(True)
                actions.append("Switch 3PL Courier (High Product Quality, High Delivery Delay Penalty)")
            elif q_pos < 50.0 and avg_rt < 3.5:
                is_unfairly_penalized.append(False)
                actions.append("Quality Audit & Supplier Warning (Intrinsic Defect Risk)")
            elif sz_neg >= 35.0:
                is_unfairly_penalized.append(False)
                actions.append("Calibrate Size Chart & Add Measurement Guide")
            elif avg_rt >= 4.2 and q_pos >= 75.0:
                is_unfairly_penalized.append(False)
                actions.append("Feature in Top-Rated Campaign")
            else:
                is_unfairly_penalized.append(False)
                actions.append("Monitor Standard SLA")

        prod_summary["is_unfairly_penalized_by_courier"] = is_unfairly_penalized
        prod_summary["recommended_action"] = actions

        # Round float columns cleanly
        for col in [
            "avg_rating", "positive_sentiment_pct", "negative_sentiment_pct",
            "avg_delivery_delay_days", "quality_net_score", "quality_pos_pct",
            "price_net_score", "delivery_net_score", "delivery_neg_pct",
            "size_fit_net_score", "size_fit_neg_pct", "packaging_net_score",
            "seller_net_score",
        ]:
            prod_summary[col] = prod_summary[col].round(3)

        # 2. Seller-Level Scorecards
        seller_grp = (
            clean_df.groupby("seller_id", as_index=False)
            .agg(
                total_genuine_reviews=("review_id", "count"),
                distinct_products=("product_id", "nunique"),
                avg_rating=("rating", "mean"),
                avg_delivery_delay_days=("delivery_delay_days", "mean"),
                quality_pos_pct=("aspect_quality", lambda s: float(np.mean(s == 1) * 100.0)),
                delivery_neg_pct=("aspect_delivery", lambda s: float(np.mean(s == -1) * 100.0)),
                packaging_neg_pct=("aspect_packaging", lambda s: float(np.mean(s == -1) * 100.0)),
                seller_pos_pct=("aspect_seller", lambda s: float(np.mean(s == 1) * 100.0)),
            )
        )

        # Compute Composite Seller Health Score (0 to 100)
        # Intrinsic Seller + Product score (excluding courier delay penalty) vs Raw Rating
        seller_grp["intrinsic_quality_index"] = (
            0.60 * seller_grp["quality_pos_pct"]
            + 0.40 * seller_grp["seller_pos_pct"]
        ).round(2)

        seller_tiers = []
        seller_actions = []
        for _, row in seller_grp.iterrows():
            iq = float(row["intrinsic_quality_index"])
            del_neg = float(row["delivery_neg_pct"])
            pkg_neg = float(row["packaging_neg_pct"])

            if iq >= 68.0 and del_neg < 35.0:
                seller_tiers.append("Gold_Verified_Seller")
                seller_actions.append("Eligible for Express Badge & Lower Commission")
            elif iq >= 60.0 and del_neg >= 35.0:
                seller_tiers.append("Courier_Bottlenecked_Seller")
                seller_actions.append("Reassign 3PL Courier Hub (Good Product, Slow Shipping)")
            elif pkg_neg >= 35.0:
                seller_tiers.append("Packaging_Risk_Seller")
                seller_actions.append("Mandate Bubble-Wrap & Box Reinforcement")
            else:
                seller_tiers.append("At_Risk_Quality_Watch")
                seller_actions.append("Trigger Merchandising Quality Review")

        seller_grp["seller_tier"] = seller_tiers
        seller_grp["management_recommendation"] = seller_actions
        for col in [
            "avg_rating", "avg_delivery_delay_days", "quality_pos_pct",
            "delivery_neg_pct", "packaging_neg_pct", "seller_pos_pct",
        ]:
            seller_grp[col] = seller_grp[col].round(2)

        seller_grp = seller_grp.sort_values(
            ["total_genuine_reviews", "intrinsic_quality_index"], ascending=[False, False]
        ).reset_index(drop=True)

        # 3. Category-Level Aspect Heatmap Matrix
        cat_aspect = (
            clean_df.groupby("category", as_index=False)
            .agg(
                review_count=("review_id", "count"),
                avg_rating=("rating", "mean"),
                quality=("aspect_quality", "mean"),
                price=("aspect_price", "mean"),
                delivery=("aspect_delivery", "mean"),
                size_fit=("aspect_size_fit", "mean"),
                packaging=("aspect_packaging", "mean"),
                seller=("aspect_seller", "mean"),
            )
            .sort_values("review_count", ascending=False)
        )

        unfair_gems = prod_summary[prod_summary["is_unfairly_penalized_by_courier"]].sort_values(
            "quality_pos_pct", ascending=False
        )

        return {
            "product_summary_df": prod_summary,
            "seller_scorecards_df": seller_grp,
            "category_aspect_df": cat_aspect,
            "unfairly_penalized_products_count": int(len(unfair_gems)),
            "unfairly_penalized_top_examples": unfair_gems.head(5)[
                [
                    "product_id", "title", "brand", "category", "avg_rating",
                    "quality_pos_pct", "delivery_neg_pct", "avg_delivery_delay_days",
                    "recommended_action",
                ]
            ].to_dict("records"),
            "seller_tier_distribution": seller_grp["seller_tier"].value_counts().to_dict(),
        }


class ReviewIntelligencePipeline:
    """
    End-to-End Orchestrator for Day 4 Tasks 4 & 5.
    Also provides fast in-memory lookup `get_product_review_intelligence(product_id)`
    for the Day 5 FastAPI `/reviews/{product_id}` endpoint and Streamlit Dashboard.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.duckdb_path
        self.sentiment_clf = MultilingualSentimentClassifier()
        self.absa_analyzer = AspectSentimentAnalyzer()
        self.topic_discoverer = ReviewTopicDiscoverer(n_topics=6)
        self.spam_detector = SpamReviewDetector()
        self.insights_engine = SellerInsightsEngine()

        self.product_summary_map: dict[str, dict[str, Any]] = {}
        self.sample_reviews_map: dict[str, list[dict[str, Any]]] = {}

    def run_full_pipeline(
        self,
        persist_to_duckdb: bool = True,
        save_artifacts: bool = True,
    ) -> dict[str, Any]:
        """Run Tasks 4A, 4B, 4C, 5A, and 5B end-to-end and persist results."""
        con = duckdb.connect(str(self.db_path), read_only=True)
        reviews_df = con.execute("SELECT * FROM reviews").df()
        catalogue_df = con.execute(
            "SELECT product_id, title, category, sub_category, brand, price_pkr FROM product_catalogue"
        ).df()
        con.close()

        # 1. Task 4A: Multilingual Sentiment Classification
        sent_eval = self.sentiment_clf.fit_and_evaluate(reviews_df)

        # 2. Task 4B: 6-Aspect Sentiment Analysis (ABSA)
        absa_eval = self.absa_analyzer.fit_and_evaluate(reviews_df)

        # 3. Task 4C: Unsupervised Topic Modeling
        topic_eval = self.topic_discoverer.discover_topics(reviews_df)

        # 4. Task 5A: Fake / Spam Review Detection
        spam_eval = self.spam_detector.fit_and_evaluate(reviews_df)

        # 5. Task 5B: insights from the analyzers' predictions (real reviews have no labels)
        predicted_df = self.predict_review_labels(reviews_df)
        insights = self.insights_engine.generate_insights(predicted_df, catalogue_df)
        prod_summary_df: pd.DataFrame = insights["product_summary_df"]
        seller_df: pd.DataFrame = insights["seller_scorecards_df"]
        cat_aspect_df: pd.DataFrame = insights["category_aspect_df"]
        # "What customers say" one-liner per product (Roman Urdu, numbers from predicted aspects)
        prod_summary_df["what_customers_say"] = prod_summary_df["product_id"].map(customer_summaries(predicted_df))
        self.predicted_df = predicted_df

        # Cache lookup maps for real-time API serving (<5 ms)
        for rec in prod_summary_df.to_dict("records"):
            pid = str(rec["product_id"])
            self.product_summary_map[pid] = rec

        clean_rev = predicted_df[~predicted_df["is_fake_spam"]].sort_values("review_date", ascending=False)
        for pid, grp in clean_rev.groupby("product_id"):
            self.sample_reviews_map[str(pid)] = grp.head(5)[
                ["review_id", "language", "rating", "sentiment_label", "review_title", "review_text", "delivery_delay_days"]
            ].to_dict("records")

        if persist_to_duckdb:
            con_w = duckdb.connect(str(self.db_path), read_only=False)
            con_w.register("prod_summary_view", prod_summary_df)
            con_w.execute("CREATE OR REPLACE TABLE review_intelligence_summary AS SELECT * FROM prod_summary_view")
            con_w.register("seller_scorecards_view", seller_df)
            con_w.execute("CREATE OR REPLACE TABLE seller_scorecards AS SELECT * FROM seller_scorecards_view")
            con_w.close()

        if save_artifacts:
            save_insight_tables(predicted_df)  # falling sentiment, complaints by category / seller
            self._save_reports_and_figures(
                sent_eval=sent_eval,
                absa_eval=absa_eval,
                topic_eval=topic_eval,
                spam_eval=spam_eval,
                prod_summary_df=prod_summary_df,
                seller_df=seller_df,
                cat_aspect_df=cat_aspect_df,
            )

        return {
            "sentiment_evaluation": {
                "overall_accuracy": sent_eval.overall_accuracy,
                "overall_macro_f1": sent_eval.overall_macro_f1,
                "overall_weighted_f1": sent_eval.overall_weighted_f1,
                "per_language_metrics": sent_eval.per_language_metrics,
                "benchmark": sent_eval.benchmark,
                "corpus_agreement_with_generator_labels": sent_eval.corpus_agreement_with_generator_labels,
                "mixed_sentiment_probes": sent_eval.mixed_sentiment_probes,
            },
            "absa_evaluation": absa_eval,
            "topic_discovery": {
                "n_topics": topic_eval["n_topics"],
                "topics": topic_eval["topics"],
                "monthly_trends_sample": topic_eval["monthly_trends_sample"],
            },
            "spam_detection": spam_eval,
            "business_insights": {
                "products_analyzed": int(len(prod_summary_df)),
                "sellers_evaluated": int(len(seller_df)),
                "unfairly_penalized_products_count": insights["unfairly_penalized_products_count"],
                "unfairly_penalized_top_examples": insights["unfairly_penalized_top_examples"],
                "seller_tier_distribution": insights["seller_tier_distribution"],
            },
        }

    def predict_review_labels(self, reviews_df: pd.DataFrame) -> pd.DataFrame:
        """Replace generator labels (sentiment, 6 aspects, spam) with the analyzers' predictions."""
        out = reviews_df.copy()
        texts = _review_texts(out)
        uniq = texts.unique()
        sent = {t: lx.analyze_sentiment(t)["sentiment"] for t in uniq}
        asp = {t: lx.analyze_aspects(t) for t in uniq}
        out["sentiment_label"] = texts.map(sent)
        for a, col in ASPECT_COLUMN_MAP.items():
            out[col] = texts.map(lambda t, a=a: asp[t][a]).astype(int)
        spam = self.spam_detector.predict_corpus(out)
        out["is_fake_spam"] = spam["is_fake_spam"]
        out["spam_reason"] = spam["spam_reason"]
        return out

    def get_product_review_intelligence(self, product_id: str | int) -> dict[str, Any]:
        """Fast lookup for a single product's ABSA & review intelligence summary."""
        if isinstance(product_id, int) or (isinstance(product_id, str) and product_id.isdigit()):
            pid_key = f"SK-{int(product_id):05d}"
        else:
            pid_key = str(product_id).strip().upper()

        if pid_key in self.product_summary_map:
            rec = self.product_summary_map[pid_key]
            return {
                "product_id": pid_key,
                "title": rec.get("title", f"Product {pid_key}"),
                "brand": rec.get("brand", "Unknown"),
                "category": rec.get("category", "Unknown"),
                "genuine_review_count": int(rec["genuine_review_count"]),
                "spam_filtered_count": int(rec["spam_filtered_count"]),
                "avg_rating": float(rec["avg_rating"]),
                "positive_sentiment_pct": float(rec["positive_sentiment_pct"]),
                "negative_sentiment_pct": float(rec["negative_sentiment_pct"]),
                "avg_delivery_delay_days": float(rec["avg_delivery_delay_days"]),
                "aspect_scores": {
                    "quality": float(rec["quality_net_score"]),
                    "price": float(rec["price_net_score"]),
                    "delivery": float(rec["delivery_net_score"]),
                    "size_fit": float(rec["size_fit_net_score"]),
                    "packaging": float(rec["packaging_net_score"]),
                    "seller": float(rec["seller_net_score"]),
                },
                "is_unfairly_penalized_by_courier": bool(rec["is_unfairly_penalized_by_courier"]),
                "recommended_action": str(rec["recommended_action"]),
                "what_customers_say": str(rec.get("what_customers_say", "")),
                "recent_reviews": self.sample_reviews_map.get(pid_key, []),
            }
        return {
            "product_id": pid_key,
            "status": "no_reviews_yet",
            "genuine_review_count": 0,
        }

    def _save_reports_and_figures(
        self,
        sent_eval: SentimentEvaluationResult,
        absa_eval: dict[str, Any],
        topic_eval: dict[str, Any],
        spam_eval: dict[str, Any],
        prod_summary_df: pd.DataFrame,
        seller_df: pd.DataFrame,
        cat_aspect_df: pd.DataFrame,
    ) -> None:
        reports_dir = settings.reports_dir
        figs_dir = settings.figures_dir
        reports_dir.mkdir(parents=True, exist_ok=True)
        figs_dir.mkdir(parents=True, exist_ok=True)

        # Save CSV artifacts
        prod_summary_df.to_csv(reports_dir / "day4_product_review_intelligence.csv", index=False)
        seller_df.to_csv(reports_dir / "day4_seller_scorecards.csv", index=False)

        rows = []
        for task, bench in (
            ("sentiment", sent_eval.benchmark),
            ("aspects", absa_eval["benchmark"]),
            ("spam", spam_eval["benchmark"]),
        ):
            for set_name, systems in bench.items():
                for system, metrics in systems.items():
                    if not isinstance(metrics, dict):
                        continue
                    rows.append(
                        {
                            "task": task,
                            "set": set_name,
                            "system": system,
                            **{k: v for k, v in metrics.items() if not isinstance(v, (dict, list))},
                        }
                    )
        pd.DataFrame(rows).to_csv(reports_dir / "day4_review_intelligence_metrics.csv", index=False)
        (reports_dir / "day4_review_benchmark_errors.json").write_text(
            json.dumps(
                {
                    "sentiment_holdout": sent_eval.benchmark["holdout_30"]["rule analyzer"]["errors"],
                    "spam_holdout": spam_eval["benchmark"]["holdout_10"]["rule detector"]["errors"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Generate Figure 13: 4-Panel Review Intelligence & ABSA Dashboard
        fig, axes = plt.subplots(2, 2, figsize=(16, 11))
        fig.suptitle(
            "ShopKaro Day 4 — Multilingual Review Intelligence, 6-Aspect ABSA & Seller Diagnostics",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )

        # Panel A: Per-Language Sentiment Classification Performance
        ax1 = axes[0, 0]
        langs = [m["language"] for m in sent_eval.per_language_metrics]
        accs = [m["accuracy"] * 100.0 for m in sent_eval.per_language_metrics]
        f1s = [m["macro_f1"] * 100.0 for m in sent_eval.per_language_metrics]
        x = np.arange(len(langs))
        w = 0.35
        ax1.bar(x - w / 2, accs, width=w, label="Accuracy (%)", color="#1f77b4")
        ax1.bar(x + w / 2, f1s, width=w, label="Macro-F1 (%)", color="#2ca02c")
        ax1.set_xticks(x)
        ax1.set_xticklabels(langs, fontweight="bold")
        ax1.set_ylim(0, 110)
        ax1.set_ylabel("Score (%)")
        ax1.set_title("A. Sentiment on 30 held-out hand-written reviews, by language", fontweight="bold")
        ax1.legend(loc="lower right")
        ax1.grid(axis="y", alpha=0.3)
        for idx_bar, (v_acc, v_f1) in enumerate(zip(accs, f1s)):
            ax1.text(idx_bar - w / 2, v_acc + 1.5, f"{v_acc:.1f}%", ha="center", fontsize=9)
            ax1.text(idx_bar + w / 2, v_f1 + 1.5, f"{v_f1:.1f}%", ha="center", fontsize=9)

        # Panel B: 6-Aspect Polarity Distribution Across Genuine Reviews
        ax2 = axes[0, 1]
        asp_labels = [m["aspect"] for m in absa_eval["per_aspect_metrics"]]
        pos_pct = [m["positive_rate_pct"] for m in absa_eval["per_aspect_metrics"]]
        neu_pct = [m["neutral_rate_pct"] for m in absa_eval["per_aspect_metrics"]]
        neg_pct = [m["negative_rate_pct"] for m in absa_eval["per_aspect_metrics"]]
        y_pos = np.arange(len(asp_labels))
        ax2.barh(y_pos, pos_pct, color="#2ca02c", label="Positive (+1)")
        ax2.barh(y_pos, neu_pct, left=pos_pct, color="#bdc3c7", label="Neutral / Unmentioned (0)")
        left_neg = [p + n for p, n in zip(pos_pct, neu_pct)]
        ax2.barh(y_pos, neg_pct, left=left_neg, color="#d62728", label="Negative (-1)")
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(asp_labels, fontweight="bold")
        ax2.set_xlabel("Share of Genuine Reviews (%)")
        ax2.set_title("B. 6-Aspect Sentiment Breakdown (Quality vs Delivery Gap)", fontweight="bold")
        ax2.legend(loc="lower right", fontsize=8)
        ax2.grid(axis="x", alpha=0.3)

        # Panel C: Unsupervised Discovered Review Topics
        ax3 = axes[1, 0]
        topics_sorted = topic_eval["topics"]
        t_names = [t["topic_name"][:36] for t in topics_sorted][::-1]
        t_counts = [t["review_count"] for t in topics_sorted][::-1]
        t_ratings = [t["avg_rating"] for t in topics_sorted][::-1]
        colors_c = ["#2ca02c" if r >= 4.0 else ("#ff7f0e" if r >= 3.0 else "#d62728") for r in t_ratings]
        bars = ax3.barh(np.arange(len(t_names)), t_counts, color=colors_c)
        ax3.set_yticks(np.arange(len(t_names)))
        ax3.set_yticklabels(t_names, fontsize=9)
        ax3.set_xlabel("Number of Reviews")
        ax3.set_title("C. Unsupervised c-TF-IDF Topics Colored by Avg Rating", fontweight="bold")
        ax3.grid(axis="x", alpha=0.3)
        for bar, rt in zip(bars, t_ratings):
            ax3.text(
                bar.get_width() + 25,
                bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width())} ({rt:.1f}★)",
                va="center",
                fontsize=8,
            )
        ax3.set_xlim(0, max(t_counts) * 1.22)

        # Panel D: Product Quality vs Courier Delivery Penalty ("Unfairly Penalized Gems")
        ax4 = axes[1, 1]
        unfair_mask = prod_summary_df["is_unfairly_penalized_by_courier"]
        normal_df = prod_summary_df[~unfair_mask]
        gems_df = prod_summary_df[unfair_mask]
        ax4.scatter(
            normal_df["delivery_neg_pct"],
            normal_df["quality_pos_pct"],
            alpha=0.45,
            c="#1f77b4",
            label=f"Standard SKUs (n={len(normal_df)})",
            s=28,
        )
        ax4.scatter(
            gems_df["delivery_neg_pct"],
            gems_df["quality_pos_pct"],
            alpha=0.85,
            c="#d62728",
            marker="D",
            label=f"Unfairly Penalized by 3PL Courier (n={len(gems_df)})",
            s=42,
        )
        ax4.axvline(35.0, color="#7f8c8d", linestyle="--", linewidth=1)
        ax4.axhline(65.0, color="#7f8c8d", linestyle="--", linewidth=1)
        ax4.set_xlabel("Negative Delivery Aspect Rate (%) — 3PL Courier Slowness")
        ax4.set_ylabel("Positive Quality Aspect Rate (%) — Intrinsic Product Praise")
        ax4.set_title("D. De-Conflating Intrinsic Product Quality vs 3PL Courier Delays", fontweight="bold")
        ax4.legend(loc="lower left", fontsize=8)
        ax4.grid(alpha=0.3)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(figs_dir / "13_review_intelligence_and_absa.png", dpi=160)
        plt.close(fig)

