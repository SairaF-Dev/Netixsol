"""
Day 4 — Task 1: Hybrid Search Engine (query parser + BM25 + semantic vectors + RRF + feature re-ranker).

Naming note: the "semantic" index is TF-IDF + SVD (latent semantic analysis), not a neural multilingual
embedding model, and the re-ranker is a hand-weighted feature score, not a neural cross-encoder.
Evaluation: `shopkaro.search.benchmark` (50 development + 20 held-out queries).

Implements:
1. `UrduLishQueryParser`:
   - Parses code-switched Roman Urdu ("UrduLish"), Urdu script, and English queries.
   - Extracts PKR budget caps ("under 5000", "20 hazaar tak", "1.5 lac", "3000 tak").
   - Extracts structured hints: `category_hint`, `color_hint`, `occasion_hint`, `brand_hint`, `sort_preference`.
   - Expands Roman Urdu & Urdu script terms into bilingual canonical search tokens.
2. `OkapiBM25Index`:
   - Vectorized sparse Okapi BM25 lexical retrieval (k1 = 1.5, b = 0.75) over 25,000 SKUs.
3. `SemanticVectorIndex`:
   - Multilingual Word + Character N-Gram TF-IDF + 96-dim L2-normalized SVD semantic embeddings
     handling cross-lingual synonyms and spelling variations ("lehnga" <-> "lehenga").
4. `HybridSearchEngine`:
   - Stage 1: `UrduLishQueryParser` query understanding & constraint extraction.
   - Stage 2: Parallel `OkapiBM25Index` + `SemanticVectorIndex` candidate retrieval.
   - Stage 3: Reciprocal Rank Fusion (`RRF`, k = 60) + Stock & Budget constraint filtering.
   - Stage 4: feature re-ranker (product type, category, colour, occasion, brand, budget, text overlap).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import difflib
import math
from pathlib import Path
import re
import time
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from shopkaro.config.settings import settings

# Roman Urdu + Urdu script -> English translations. Translation only: an entry must not add other product
# types, otherwise the expansion outranks the product the shopper asked for.
URDULISH_SYNONYM_MAP: dict[str, str] = {
    # Kids & school
    "bachon": "kids", "bacho": "kids", "basta": "school bag",
    "بچوں": "kids", "بیگ": "bag", "اسکول": "school",
    # Clothing
    "kapra": "unstitched lawn fabric", "kapre": "clothes", "jora": "suit",
    "لان": "lawn", "سوٹ": "suit", "کپڑے": "clothes",
    # Bridal & wedding
    "shaadi": "shaadi wedding", "shadi": "shaadi wedding", "dulhan": "bridal",
    "barat": "barat wedding", "walima": "walima wedding",
    "شادی": "shaadi wedding", "دلہن": "bridal", "لہنگا": "lehenga",
    # Men
    "mardana": "men", "kameez": "shalwar kameez",
    # Footwear
    "joota": "shoes", "juta": "shoes", "jootay": "shoes", "جوتا": "shoes",
    # Beauty & gifting
    "ammi": "mother", "khushboo": "perfume", "attar": "attar perfume", "تحفہ": "gift",
    # Electronics
    "mobile": "mobile phone smartphone", "phone": "phone smartphone",
    "sasta": "affordable", "sastay": "affordable",
    "coding": "coding programming", "programming": "programming coding",
    # Seasons, home, groceries
    "sardi": "winter", "garam": "warm winter", "garmiyon": "summer", "garmi": "summer",
    "عید": "eid", "استری": "iron",
    "rashan": "groceries", "chawal": "rice",
    "iftaar": "iftar ramadan", "iftar": "iftar ramadan", "ramzan": "ramadan",
}

# Words that describe an occasion or audience, not a product. They count less when deciding which product
# type a query is about, so "shaadi ke liye waistcoat" means a waistcoat, not a wedding dress.
CONTEXT_WORDS: set[str] = {
    "eid", "shaadi", "school", "ramadan", "festive", "summer", "winter", "wedding", "kid", "kids", "men",
    "women", "formal", "traditional", "luxury", "original", "value", "family", "pure", "super", "complete",
    "modern", "heavy", "duty", "signature", "classic", "durable", "premium", "iftar",
}
GIFT_WORDS: set[str] = {"gift", "tohfa", "تحفہ"}
GIFT_TYPES: list[str] = [
    "Embroidered Shawl", "Oud & Attar Perfume Gift Set", "Luxury Eau De Parfum",
    "Herbal Skincare Facial Kit", "Halal Matte Lipstick Set",
]


def _norm_token(tok: str) -> str:
    """Lowercase and drop a plural 's' so "shoes"/"shoe" and "sneakers"/"sneaker" match."""
    tok = tok.lower()
    return tok[:-1] if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") else tok


CATEGORY_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("Kids & School Supplies", ["school bag", "basta", "bachon", "kids", "lunch box", "geometry", "stationery", "بچوں"]),
    ("Bridal & Formal Wear", ["lehenga", "lehnga", "bridal", "dulhan", "barat", "walima", "gharara", "maxi", "shaadi ke liye red"]),
    ("Laptops & Computing", ["laptop", "coding", "programming", "notebook", "core i5", "ryzen", "keyboard", "mouse"]),
    ("Smartphones & Accessories", ["smartphone", "5g", "mobile", "phone", "galaxy", "infinix", "xiaomi", "redmi", "charger", "earbuds", "power bank", "back cover"]),
    ("Women's Lawn & Unstitched", ["lawn", "unstitched", "3-piece", "3 piece", "sapphire", "khaadi", "gul ahmed", "shawl", "kapra", "jora"]),
    ("Men's Kurta & Ethnic", ["kurta", "shalwar kameez", "waistcoat", "mardana", "boski", "junaid jamshed"]),
    ("Footwear & Khussa", ["khussa", "joota", "juta", "chappal", "sneakers", "shoes", "heels", "sandals", "جوتا"]),
    ("Beauty & Fragrances", ["perfume", "attar", "oud", "khushboo", "skincare", "facial", "lipstick", "rose water", "saeed ghani", "hemani"]),
    ("Winter Wear & Jackets", ["winter", "jacket", "puffer", "hoodie", "sardi", "leather jacket", "fleece"]),
    ("Home & Kitchen Appliances", ["air fryer", "blender", "juicer", "microwave", "kettle", "steam iron", "food processor"]),
    ("Groceries & Staples", ["basmati", "rice", "chawal", "masala", "rooh afza", "cooking oil", "rashan", "tea", "danedar"]),
]

COLOR_SYNONYMS: dict[str, list[str]] = {
    "Red": ["red", "crimson", "laal", "surkh", "maroon"],
    "Emerald Green": ["green", "emerald", "hara", "sabz", "olive", "teal", "mint"],
    "Navy Blue": ["blue", "navy", "neela", "royal blue", "ocean blue"],
    "Black": ["black", "kaala", "kala", "phantom black", "matte black"],
    "Pastel Pink": ["pink", "gulabi", "rose", "dusty rose"],
    "White": ["white", "safaid", "ivory", "clear"],
    "Mustard Yellow": ["yellow", "mustard", "peela", "gold", "golden", "champagne"],
    "Space Grey": ["grey", "gray", "silver", "titanium"],
}

OCCASION_SYNONYMS: dict[str, list[str]] = {
    "Eid": ["eid", "chaand raat", "ramadan", "ramzan"],
    "Shaadi/Wedding": ["shaadi", "shadi", "wedding", "bridal", "barat", "walima"],
    "School/Office": ["school", "bachon", "coding", "university", "office", "study"],
    "11.11 Sale": ["11.11", "mega sale", "blessed friday"],
    "Winter": ["winter", "sardi"],
}


@dataclass
class ParsedSearchQuery:
    """Structured representation of a parsed Roman Urdu / English / Urdu search query."""

    raw_query: str
    normalized_query: str
    expanded_query: str
    max_price_pkr: float | None
    min_price_pkr: float | None
    category_hint: str | None
    color_hint: str | None
    occasion_hint: str | None
    brand_hint: str | None
    sort_preference: str
    type_hints: list[str] = field(default_factory=list)


class UrduLishQueryParser:
    """
    Stage 1: Code-Switched Roman Urdu ("UrduLish"), Urdu Script & English Query Parser.

    Extracts PKR price constraints ("under 5000", "20 hazaar tak", "1.5 lac", "3000 tak"),
    category, color, occasion, and brand hints, and expands Roman Urdu vocabulary.
    """

    def __init__(self, known_brands: list[str] | None = None) -> None:
        self.known_brands = sorted(
            known_brands or [],
            key=lambda x: len(x),
            reverse=True,
        )
        self.type_category: dict[str, str] = {}
        self.occasion_tokens: dict[str, set[str]] = {}
        self.type_tokens: dict[str, set[str]] = {}
        self.token_weight: dict[str, float] = {}

    def set_product_types(self, type_category: dict[str, str]) -> None:
        """
        Learn product-type vocabulary from catalogue sub-category names. Each word is weighted by how
        distinctive it is (log inverse frequency across types): "boski" or "waistcoat" identify one type,
        "suit" or "laptop" several. Occasion/audience words get 30% weight.
        """
        self.type_category = dict(type_category)
        self.type_tokens = {
            t: {_norm_token(w) for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 1}
            for t in type_category
        }
        df: Counter[str] = Counter(w for toks in self.type_tokens.values() for w in toks)
        n = len(self.type_tokens)
        self.token_weight = {
            w: math.log(1 + n / c) * (0.3 if w in CONTEXT_WORDS else 1.0) for w, c in df.items()
        }

    def set_occasions(self, occasions: list[str]) -> None:
        """Learn occasion vocabulary from catalogue values ("Bridal/Barat", "Walima", "Jummah/Festive", ...)."""
        generic = {"sale", "daily", "all", "season", "ul"}
        self.occasion_tokens = {
            occ: {_norm_token(w) for w in re.findall(r"[a-z0-9.]+", occ.lower()) if len(w) > 1 and w not in generic}
            for occ in occasions
        }

    def detect_occasion(self, tokens: list[str]) -> str | None:
        """Catalogue occasion with the most matching words; on a tie, the one with fewer words (more specific)."""
        q = {_norm_token(t) for t in tokens}
        best: tuple[int, int, str] | None = None
        for occ, toks in self.occasion_tokens.items():
            hits = len(toks & q)
            if hits and (best is None or (hits, -len(toks)) > (best[0], best[1])):
                best = (hits, -len(toks), occ)
        return best[2] if best else None

    def detect_product_types(self, tokens: list[str]) -> list[str]:
        """Product types the query is about, best match first (ties within 20% kept)."""
        if not self.type_tokens:
            return []
        vocab = list(self.token_weight)
        q: set[str] = set()
        for tok in tokens:
            t = _norm_token(tok)
            if t in self.token_weight:
                q.add(t)
            elif len(t) >= 5:
                # Spelling variants ("lehnga" -> "lehenga", "ghararah" -> "gharara")
                close = difflib.get_close_matches(t, vocab, n=1, cutoff=0.8)
                if close:
                    q.add(close[0])
        scores = {
            typ: sum(self.token_weight[w] for w in toks & q) for typ, toks in self.type_tokens.items()
        }
        best = max(scores.values(), default=0.0)
        hints = [t for t, sc in sorted(scores.items(), key=lambda x: -x[1]) if best >= 1.0 and sc >= 0.8 * best]
        if any(tok in GIFT_WORDS for tok in tokens):
            hints += [t for t in GIFT_TYPES if t in self.type_category and t not in hints]
        return hints

    @staticmethod
    def _extract_price_bounds(text: str) -> tuple[float | None, float | None]:
        """Parse Pakistani PKR price expressions in English and Roman Urdu."""
        q = text.lower().replace(",", "")
        max_price: float | None = None
        min_price: float | None = None

        # 1. Match "X lac" / "X lakh" (1 lac = 100,000 PKR)
        m_lac = re.search(
            r"(?:under|below|upto|up to|less than|tak)?\s*(\d+(?:\.\d+)?)\s*(?:lac|lakh|lacs)",
            q,
        )
        if m_lac:
            max_price = float(m_lac.group(1)) * 100_000.0
        elif "dedh lac" in q or "dedh lakh" in q:
            max_price = 150_000.0

        # 2. Match "X hazaar" / "X hazar" / "Xk" (1 hazaar = 1,000 PKR)
        if max_price is None:
            m_haz = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:hazaar|hazar|hzar|k)\b(?:\s*tak|\s*ke andar)?",
                q,
            )
            if m_haz:
                max_price = float(m_haz.group(1)) * 1_000.0

        # 3. Match "under X" / "below X" / "less than X" / "upto X"
        if max_price is None:
            m_under = re.search(
                r"(?:under|below|less than|upto|up to|max|<=)\s*(?:pkr|rs\.?)?\s*(\d+(?:\.\d+)?)",
                q,
            )
            if m_under:
                val = float(m_under.group(1))
                max_price = val * 1000.0 if val < 100 else val

        # 4a. Match Roman Urdu "X se kam" / "X say kam" / "X se neeche" (less than X)
        if max_price is None:
            m_kam = re.search(
                r"(\d{3,7})\s*(?:pkr|rs|rupay|rupees)?\s*(?:se|say|sy)\s*(?:kam|neeche|nichay|niche)\b",
                q,
            )
            if m_kam:
                max_price = float(m_kam.group(1))

        # 4b. Match Roman Urdu suffix "X tak" / "X ke andar" / "X mein"
        if max_price is None:
            m_tak = re.search(
                r"(\d{3,6})\s*(?:pkr|rs|rupay)?\s*(?:tak|ke andar|mein|wali|wala)\b",
                q,
            )
            if m_tak:
                max_price = float(m_tak.group(1))

        # 5. Match minimum price "above X" / "over X" / "se zyada"
        m_above = re.search(
            r"(?:above|over|more than|min|>=)\s*(?:pkr|rs\.?)?\s*(\d+(?:\.\d+)?)",
            q,
        )
        if m_above:
            min_price = float(m_above.group(1))

        return min_price, max_price

    def parse(self, query: str) -> ParsedSearchQuery:
        raw_q = query.strip()
        q_lower = raw_q.lower()

        min_p, max_p = self._extract_price_bounds(q_lower)

        # Tokenize & expand Roman Urdu / Urdu script synonyms
        tokens = re.findall(r"[\w\u0600-\u06FF]+", q_lower)
        expanded_parts: list[str] = [q_lower]
        for tok in tokens:
            if tok in URDULISH_SYNONYM_MAP:
                expanded_parts.append(URDULISH_SYNONYM_MAP[tok])

        expanded_q = " ".join(expanded_parts)

        # Detect product types first; the category follows from them. Keyword rules are only a fallback.
        type_tokens = re.findall(r"[\w\u0600-\u06FF]+", expanded_q)
        type_hints = self.detect_product_types(type_tokens)
        cat_hint: str | None = None
        hint_cats = {self.type_category[t] for t in type_hints}
        if len(hint_cats) == 1:
            cat_hint = next(iter(hint_cats))
        elif not type_hints:
            for cat_name, kw_list in CATEGORY_KEYWORD_RULES:
                if any(kw in q_lower or kw in expanded_q for kw in kw_list):
                    cat_hint = cat_name
                    break

        # Detect color hint
        color_hint: str | None = None
        for canonical_color, syn_list in COLOR_SYNONYMS.items():
            if any(re.search(rf"\b{re.escape(s)}\b", q_lower) for s in syn_list):
                color_hint = canonical_color
                break

        # Detect occasion hint: catalogue occasions first, legacy synonym list as fallback
        occasion_hint: str | None = self.detect_occasion(type_tokens)
        for canonical_occ, occ_syns in ({} if occasion_hint else OCCASION_SYNONYMS).items():
            if any(s in q_lower or s in expanded_q for s in occ_syns):
                occasion_hint = canonical_occ
                break

        # Detect brand hint
        brand_hint: str | None = None
        for b in self.known_brands:
            if b.lower() in q_lower:
                brand_hint = b
                break

        sort_pref = (
            "price_asc"
            if any(w in q_lower for w in ["sasta", "sastay", "cheap", "lowest price", "budget"])
            else "relevance"
        )

        return ParsedSearchQuery(
            raw_query=raw_q,
            normalized_query=q_lower,
            expanded_query=expanded_q,
            max_price_pkr=max_p,
            min_price_pkr=min_p,
            category_hint=cat_hint,
            color_hint=color_hint,
            occasion_hint=occasion_hint,
            brand_hint=brand_hint,
            sort_preference=sort_pref,
            type_hints=type_hints,
        )


class OkapiBM25Index:
    """
    Stage 2A: Vectorized Sparse Okapi BM25 Lexical Index over 25,000 SKUs.

    BM25(q, d) = sum_{t in q} IDF(t) * [ f(t, d) * (k1 + 1) ] / [ f(t, d) + k1 * (1 - b + b * |d|/avgdl) ]
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b[\w\u0600-\u06FF]{2,}\b",
            ngram_range=(1, 2),
            max_features=35000,
            use_idf=False,
            norm=None,
        )
        self.tf_csr: sp.csr_matrix | None = None
        self.idf_vec: np.ndarray = np.array([], dtype=np.float32)
        self.doc_len_norm: np.ndarray = np.array([], dtype=np.float32)

    def fit(self, corpus: list[str]) -> OkapiBM25Index:
        # Raw term counts because use_idf=False and norm=None
        X_counts = self.vectorizer.fit_transform(corpus).tocsr()
        n_docs = X_counts.shape[0]
        doc_lengths = np.asarray(X_counts.sum(axis=1)).ravel().astype(np.float32)
        avgdl = max(float(np.mean(doc_lengths)), 1.0)
        self.doc_len_norm = (1.0 - self.b) + self.b * (doc_lengths / avgdl)

        # Robertson-Sparck Jones IDF: log( 1 + (N - df + 0.5) / (df + 0.5) )
        df = np.bincount(X_counts.indices, minlength=X_counts.shape[1]).astype(np.float32)
        self.idf_vec = np.log(1.0 + (n_docs - df + 0.5) / (df + 0.5)).astype(np.float32)

        # Precompute BM25-weighted document-term matrix so query scoring is a single matrix-vector product!
        X_coo = X_counts.tocoo()
        denom = X_coo.data + self.k1 * self.doc_len_norm[X_coo.row]
        bm25_data = (
            X_coo.data * (self.k1 + 1.0) / np.maximum(denom, 1e-7)
        ) * self.idf_vec[X_coo.col]
        self.tf_csr = sp.csr_matrix(
            (bm25_data.astype(np.float32), (X_coo.row, X_coo.col)),
            shape=X_counts.shape,
            dtype=np.float32,
        )
        return self

    def score_all(self, query_text: str) -> np.ndarray:
        assert self.tf_csr is not None
        q_vec = self.vectorizer.transform([query_text])
        if q_vec.nnz == 0:
            return np.zeros(self.tf_csr.shape[0], dtype=np.float32)
        # Binary query indicator times precomputed BM25 document-term matrix
        q_bin = (q_vec > 0).astype(np.float32)
        scores = (self.tf_csr @ q_bin.T).toarray().ravel().astype(np.float32)
        return scores


class SemanticVectorIndex:
    """
    Stage 2B: Multilingual Semantic Dense Embedding Index (Word + Char N-Gram SVD, 96-Dim).

    Captures semantic similarity and typo tolerance ("lehnga" == "lehenga", "sapfire" == "sapphire")
    via L2-normalized dense embeddings.
    """

    def __init__(self, embedding_dim: int = 96, random_state: int = 42) -> None:
        self.embedding_dim = embedding_dim
        self.random_state = random_state
        self.word_vec = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=20000,
            sublinear_tf=True,
        )
        self.char_vec = TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=15000,
            sublinear_tf=True,
        )
        self.svd = TruncatedSVD(n_components=embedding_dim, random_state=random_state)
        self.doc_embeddings: np.ndarray = np.empty((0, embedding_dim), dtype=np.float32)

    def fit(self, corpus: list[str]) -> SemanticVectorIndex:
        import hashlib
        import pickle

        cache_path = settings.models_dir / "search_semantic_index.pkl"
        # Fingerprint the corpus text: a regenerated catalogue with the same size must not
        # reuse embeddings of the old titles.
        corpus_hash = hashlib.sha256("".join(corpus).encode("utf-8")).hexdigest()
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("corpus_hash") == corpus_hash:
                    self.word_vec = cached["word_vec"]
                    self.char_vec = cached["char_vec"]
                    self.svd = cached["svd"]
                    self.doc_embeddings = cached["doc_embeddings"]
                    return self
            except Exception:
                pass

        W = self.word_vec.fit_transform(corpus)
        C = self.char_vec.fit_transform(corpus)
        combined = sp.hstack([W, C * 0.65], format="csr")
        dense = self.svd.fit_transform(combined)
        self.doc_embeddings = normalize(dense, norm="l2", axis=1).astype(np.float32)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(
                {
                    "word_vec": self.word_vec,
                    "char_vec": self.char_vec,
                    "svd": self.svd,
                    "doc_embeddings": self.doc_embeddings,
                    "corpus_hash": corpus_hash,
                },
                f,
            )
        return self

    def encode_query(self, query_text: str) -> np.ndarray:
        W_q = self.word_vec.transform([query_text])
        C_q = self.char_vec.transform([query_text])
        combined_q = sp.hstack([W_q, C_q * 0.65], format="csr")
        dense_q = self.svd.transform(combined_q)
        return normalize(dense_q, norm="l2", axis=1).ravel().astype(np.float32)

    def score_all(self, query_text: str) -> np.ndarray:
        q_emb = self.encode_query(query_text)
        return (self.doc_embeddings @ q_emb).astype(np.float32)


CROSS_ENCODER_TOP_N = 50  # brief: cross-encoder reranking for the top 50 results
CROSS_ENCODER_WEIGHT = 0.25  # chosen on the 50 dev queries (0.9638 -> 0.9673); held-out 0.832 -> 0.837, not significant; +~0.7 s/query on CPU


class NeuralSemanticIndex:
    """
    Stage 2B (neural): multilingual sentence embeddings (default `intfloat/multilingual-e5-small`, 384-d), so
    English, Roman Urdu and Urdu-script queries meet product text in one vector space without a hand-made lexicon.
    Same interface as `SemanticVectorIndex`. Document embeddings are cached on disk by model + corpus hash.
    e5 models expect "query: " / "passage: " prefixes.
    """

    def __init__(self, model_name: str | None = None, batch_size: int = 64) -> None:
        self.model_name = model_name or settings.search_embedding_model
        self.batch_size = batch_size
        self.model: Any = None
        self.doc_embeddings: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self._is_e5 = "e5" in self.model_name.lower()

    def _load_model(self) -> Any:
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name, device="cpu")
            self.model.max_seq_length = 128
        return self.model

    def fit(self, corpus: list[str]) -> NeuralSemanticIndex:
        import hashlib

        key = hashlib.sha256((self.model_name + "\x00" + "\x00".join(corpus)).encode("utf-8")).hexdigest()[:16]
        cache_path = settings.models_dir / f"search_neural_embeddings_{key}.npy"
        if cache_path.exists():
            self.doc_embeddings = np.load(cache_path)
            self._load_model()  # load the query encoder at startup, not on the first user's search
            return self
        prefix = "passage: " if self._is_e5 else ""
        emb = self._load_model().encode(
            [prefix + doc for doc in corpus],
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self.doc_embeddings = emb.astype(np.float32)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        for old in settings.models_dir.glob("search_neural_embeddings_*.npy"):
            old.unlink(missing_ok=True)  # keep only the current catalogue's embeddings
        np.save(cache_path, self.doc_embeddings)
        return self

    def encode_query(self, query_text: str) -> np.ndarray:
        prefix = "query: " if self._is_e5 else ""
        return self._load_model().encode(
            [prefix + query_text], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )[0].astype(np.float32)

    def score_all(self, query_text: str) -> np.ndarray:
        return (self.doc_embeddings @ self.encode_query(query_text)).astype(np.float32)


def neural_embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    return True


def make_semantic_index() -> SemanticVectorIndex | NeuralSemanticIndex:
    mode = settings.search_embeddings.lower()
    if mode == "neural" or (mode == "auto" and neural_embeddings_available()):
        return NeuralSemanticIndex()
    return SemanticVectorIndex(embedding_dim=96, random_state=42)


class HybridSearchEngine:
    """
    Full 4-Stage ShopKaro Hybrid Search Engine:
    1. `UrduLishQueryParser` (Roman Urdu + Urdu Script + PKR Price/Category/Color/Occasion extraction)
    2. Parallel `OkapiBM25Index` + `SemanticVectorIndex` candidate retrieval
    3. Reciprocal Rank Fusion (`RRF`, k = 60) + Metadata/Budget filtering
    4. Feature re-ranker (hand-weighted; not a neural cross-encoder)
    """

    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k
        self._cross_encoder: Any = None  # loaded lazily; False = disabled / unavailable
        self.ce_weight = CROSS_ENCODER_WEIGHT
        self.catalogue_df: pd.DataFrame = pd.DataFrame()
        self.records: list[dict[str, Any]] = []
        self.parser: UrduLishQueryParser | None = None
        self.bm25_index = OkapiBM25Index(k1=1.5, b=0.75)
        self.semantic_index = make_semantic_index()

        # Vectorized arrays for ultra-fast filtering & cross-encoder scoring
        self.prices: np.ndarray = np.array([], dtype=np.float32)
        self.in_stock_mask: np.ndarray = np.array([], dtype=bool)
        self.is_hero_mask: np.ndarray = np.array([], dtype=bool)
        self.categories: list[str] = []
        self.colors: list[str] = []
        self.occasions: list[str] = []
        self.brands: list[str] = []
        self.titles_lower: list[str] = []
        self.full_text_lower: list[str] = []

    def fit_from_duckdb(self, con: duckdb.DuckDBPyConnection) -> HybridSearchEngine:
        self.catalogue_df = con.execute(
            """
            SELECT
                product_id,
                title,
                description,
                category,
                sub_category,
                brand,
                color,
                occasion,
                price_pkr,
                on_sale,
                discount_pct,
                margin_pct,
                stock_qty,
                in_stock,
                is_curated_hero
            FROM product_catalogue
            ORDER BY product_id;
            """
        ).df()

        self.records = self.catalogue_df.to_dict("records")
        known_brands = sorted(self.catalogue_df["brand"].astype(str).unique().tolist())
        self.parser = UrduLishQueryParser(known_brands=known_brands)
        self.parser.set_product_types(
            self.catalogue_df.drop_duplicates("sub_category").set_index("sub_category")["category"].astype(str).to_dict()
        )
        self.sub_categories = self.catalogue_df["sub_category"].astype(str).tolist()
        self.parser.set_occasions(sorted(self.catalogue_df["occasion"].astype(str).unique().tolist()))

        self.prices = self.catalogue_df["price_pkr"].to_numpy(dtype=np.float32)
        self.in_stock_mask = self.catalogue_df["in_stock"].to_numpy(dtype=bool)
        self.is_hero_mask = self.catalogue_df["is_curated_hero"].to_numpy(dtype=bool)
        self.categories = self.catalogue_df["category"].astype(str).tolist()
        self.colors = self.catalogue_df["color"].astype(str).tolist()
        self.occasions = self.catalogue_df["occasion"].astype(str).tolist()
        self.brands = self.catalogue_df["brand"].astype(str).tolist()
        self.titles_lower = self.catalogue_df["title"].astype(str).str.lower().tolist()

        corpus: list[str] = []
        for r in self.records:
            doc = (
                f"{r['title']} {r['title']} {r['category']} {r['sub_category']} "
                f"{r['brand']} {r['color']} {r['occasion']} {r['description']}"
            )
            corpus.append(doc)
        self.full_text_lower = [c.lower() for c in corpus]

        self.bm25_index.fit(corpus)
        self.semantic_index.fit(corpus)
        return self

    def search_bm25_only(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """Baseline 1: Lexical Okapi BM25 search on raw query (no UrduLish expansion or budget filter)."""
        scores = self.bm25_index.score_all(query)
        scores[~self.in_stock_mask] = -1e9
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return self._format_results(top_idx, scores[top_idx], mode="1. Lexical Only (Okapi BM25)")

    def search_semantic_only(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """Baseline 2: Dense Semantic Vector search on raw query (no RRF or constraint filter)."""
        scores = self.semantic_index.score_all(query)
        scores[~self.in_stock_mask] = -1e9
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return self._format_results(
            top_idx, scores[top_idx], mode="2. Semantic Vector Only (Dense Cosine)"
        )

    def _cross_encoder_rerank(
        self, query: str, pool: list[tuple[int, float, float]], top_n: int = CROSS_ENCODER_TOP_N
    ) -> list[tuple[int, float, float]]:
        """
        Re-score the top `top_n` feature-ranked candidates with a multilingual cross-encoder (query and product text
        read together). final = z(feature score) + weight * z(cross-encoder score), both standardised over the top
        `top_n`, so product type / budget rules from the feature score still dominate. No-op if unavailable.
        """
        ce = self._get_cross_encoder()
        if ce is None or self.ce_weight <= 0 or len(pool) < 2:
            return pool
        head, tail = pool[:top_n], pool[top_n:]
        docs = [
            f"{self.records[i]['title']}. {self.records[i]['sub_category']}, {self.records[i]['category']}, "
            f"{self.records[i]['color']}, {self.records[i]['occasion']}, {self.records[i]['brand']}"
            for i, _, _ in head
        ]
        ce_scores = np.asarray(ce.predict([(query, d) for d in docs], batch_size=64, show_progress_bar=False), dtype=float)
        feat = np.array([x[1] for x in head], dtype=float)
        z = lambda v: (v - v.mean()) / (v.std() + 1e-9)  # noqa: E731
        final = z(feat) + self.ce_weight * z(ce_scores)
        order = np.argsort(-final, kind="stable")
        offset = float(final.min()) - 1.0  # keep the re-ranked head above the tail
        rescored = [(head[j][0], float(final[j]), head[j][2]) for j in order]
        return rescored + [(i, offset - n * 1e-6, r) for n, (i, _, r) in enumerate(tail)]

    def _get_cross_encoder(self) -> Any:
        if self._cross_encoder is False:
            return None
        if self._cross_encoder is None:
            mode = settings.search_cross_encoder.lower()
            if mode == "off" or (mode == "auto" and not neural_embeddings_available()):
                self._cross_encoder = False
                return None
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder(settings.search_cross_encoder_model, device="cpu", max_length=128)
        return self._cross_encoder

    def search_hybrid(
        self,
        query: str,
        k: int = 10,
        candidate_pool: int = 150,
        only_in_stock: bool = True,
        cross_encode: bool = True,
    ) -> tuple[list[dict[str, Any]], ParsedSearchQuery]:
        """
        Stage 1–4 Full Hybrid Search:
        1. Parse query via `UrduLishQueryParser`.
        2. Score all 25,000 SKUs with BM25 and Semantic Embeddings on expanded query.
        3. Fuse Top-`candidate_pool` candidates via Reciprocal Rank Fusion (`RRF`, k=60).
        4. Feature re-ranking: product type, category, colour, occasion, brand, budget and text overlap.
        """
        assert self.parser is not None
        parsed = self.parser.parse(query)

        bm25_scores = self.bm25_index.score_all(parsed.expanded_query)
        sem_scores = self.semantic_index.score_all(parsed.expanded_query)

        if only_in_stock:
            bm25_scores[~self.in_stock_mask] = -1e9
            sem_scores[~self.in_stock_mask] = -1e9

        # Pre-boost items satisfying hard budget & category hints before RRF pool selection
        constraint_bonus = np.zeros_like(bm25_scores)
        if parsed.max_price_pkr is not None:
            within_budget = self.prices <= parsed.max_price_pkr
            constraint_bonus[within_budget] += 0.25
            constraint_bonus[~within_budget] -= 2.5
        if parsed.min_price_pkr is not None:
            above_min = self.prices >= parsed.min_price_pkr
            constraint_bonus[~above_min] -= 2.5

        bm25_adj = bm25_scores + constraint_bonus * 3.0
        sem_adj = sem_scores + constraint_bonus * 0.3

        top_bm25 = np.argpartition(bm25_adj, -candidate_pool)[-candidate_pool:]
        top_bm25 = top_bm25[np.argsort(bm25_adj[top_bm25])[::-1]]

        top_sem = np.argpartition(sem_adj, -candidate_pool)[-candidate_pool:]
        top_sem = top_sem[np.argsort(sem_adj[top_sem])[::-1]]

        # Stage 3: Reciprocal Rank Fusion (RRF)
        rrf_scores: dict[int, float] = {}
        for rank_idx, doc_idx in enumerate(top_bm25, start=1):
            d_i = int(doc_idx)
            rrf_scores[d_i] = rrf_scores.get(d_i, 0.0) + 1.0 / (self.rrf_k + rank_idx)
        for rank_idx, doc_idx in enumerate(top_sem, start=1):
            d_i = int(doc_idx)
            rrf_scores[d_i] = rrf_scores.get(d_i, 0.0) + 1.0 / (self.rrf_k + rank_idx)

        # Candidates of the detected product type(s) join the pool, so a type the text scores missed can rank.
        if parsed.type_hints:
            type_set = set(parsed.type_hints)
            type_idx = np.array([i for i, t in enumerate(self.sub_categories) if t in type_set], dtype=int)
            if len(type_idx):
                fused = bm25_adj[type_idx] + 10.0 * sem_adj[type_idx]
                for d_i in type_idx[np.argsort(fused)[::-1][:candidate_pool]]:
                    rrf_scores.setdefault(int(d_i), 0.0)

        # Stage 4: feature re-ranking over the candidate pool (hand-weighted, not a neural cross-encoder)
        q_tokens = set(re.findall(r"[\w\u0600-\u06FF]{2,}", parsed.expanded_query))
        stop_words = {"ke", "liye", "under", "tak", "for", "in", "with", "and", "the", "chahiye"}
        q_tokens = q_tokens - stop_words

        max_bm25 = max(float(bm25_scores.max()), 1e-6)
        reranked_pool: list[tuple[int, float, float]] = []

        for doc_idx, rrf_val in rrf_scores.items():
            if only_in_stock and not self.in_stock_mask[doc_idx]:
                continue

            price = float(self.prices[doc_idx])
            # Hard budget compliance penalty
            budget_score = 0.0
            if parsed.max_price_pkr is not None:
                if price <= parsed.max_price_pkr:
                    budget_score += 0.45
                else:
                    budget_score -= 3.0
            if parsed.min_price_pkr is not None and price < parsed.min_price_pkr:
                budget_score -= 3.0

            cat_match = (
                0.40
                if (parsed.category_hint and self.categories[doc_idx] == parsed.category_hint)
                else 0.0
            )
            type_match = 0.90 if self.sub_categories[doc_idx] in parsed.type_hints else 0.0

            color_match = 0.0
            if parsed.color_hint:
                doc_col = self.colors[doc_idx].lower()
                target_col = parsed.color_hint.lower()
                if target_col in doc_col or any(
                    s in doc_col for s in COLOR_SYNONYMS.get(parsed.color_hint, [])
                ):
                    color_match = 0.35

            occ_match = 0.0
            if parsed.occasion_hint:
                if (
                    parsed.occasion_hint.lower() in self.occasions[doc_idx].lower()
                    or parsed.occasion_hint.lower() in self.titles_lower[doc_idx]
                ):
                    occ_match = 0.25

            brand_match = (
                0.45
                if (
                    parsed.brand_hint
                    and parsed.brand_hint.lower() == self.brands[doc_idx].lower()
                )
                else 0.0
            )

            # Cross-encoder token overlap on title + description
            doc_text = self.full_text_lower[doc_idx]
            overlap_cnt = sum(1 for t in q_tokens if t in doc_text)
            overlap_ratio = overlap_cnt / max(len(q_tokens), 1)

            norm_bm25 = float(max(bm25_scores[doc_idx], 0.0)) / max_bm25
            sem_val = float(max(sem_scores[doc_idx], 0.0))

            # Slight boost for cheap items when sort_preference == "price_asc"
            price_sort_bonus = (
                0.20 * (1.0 / (1.0 + price / 10000.0))
                if parsed.sort_preference == "price_asc"
                else 0.0
            )

            feature_score = (
                rrf_val * 15.0
                + 0.35 * norm_bm25
                + 0.30 * sem_val
                + 0.45 * overlap_ratio
                + cat_match
                + type_match
                + color_match
                + occ_match
                + brand_match
                + budget_score
                + price_sort_bonus
            )
            reranked_pool.append((doc_idx, feature_score, rrf_val))

        reranked_pool.sort(key=lambda x: x[1], reverse=True)
        if cross_encode:
            reranked_pool = self._cross_encoder_rerank(query, reranked_pool)
        top_slice = reranked_pool[:k]
        top_indices = np.array([x[0] for x in top_slice], dtype=int)
        top_scores = np.array([x[1] for x in top_slice], dtype=np.float32)

        return (
            self._format_results(
                top_indices,
                top_scores,
                mode="3. Hybrid Search (BM25 + Semantic + RRF + feature + cross-encoder re-ranker)",
                parsed=parsed,
            ),
            parsed,
        )

    def _format_results(
        self,
        indices: np.ndarray,
        scores: np.ndarray,
        mode: str,
        parsed: ParsedSearchQuery | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for rank, (idx, sc) in enumerate(zip(indices, scores, strict=False), start=1):
            rec = self.records[int(idx)]
            price = float(rec["price_pkr"])
            within_budget = (
                True
                if (parsed is None or parsed.max_price_pkr is None)
                else (price <= parsed.max_price_pkr)
            )
            results.append(
                {
                    "rank": rank,
                    "product_id": str(rec["product_id"]),
                    "title": str(rec["title"]),
                    "category": str(rec["category"]),
                    "sub_category": str(rec["sub_category"]),
                    "brand": str(rec["brand"]),
                    "color": str(rec["color"]),
                    "occasion": str(rec["occasion"]),
                    "price_pkr": price,
                    "on_sale": bool(rec["on_sale"]),
                    "discount_pct": float(rec["discount_pct"]),
                    "in_stock": bool(rec["in_stock"]),
                    "within_budget": within_budget,
                    "score": round(float(sc), 4),
                    "search_mode": mode,
                }
            )
        return results


SEARCH_SYSTEM_NAMES = (
    "1. Lexical Only (Okapi BM25)",
    "2. Semantic Vector Only (Dense Cosine)",
    "3. Hybrid Search (BM25 + Semantic + RRF + feature + cross-encoder re-ranker)",
)


def evaluate_search_architectures(
    engine: HybridSearchEngine,
    catalogue: pd.DataFrame,
    k: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Compare keyword, semantic and hybrid search on the 50 development queries and 20 held-out queries
    (`shopkaro.search.benchmark`). Returns (summary per set and system, per-query results, significance).
    """
    from shopkaro.search.benchmark import HOLDOUT_QUERIES, QUERIES, evaluate_systems, paired_comparison

    bm25, sem, hyb = SEARCH_SYSTEM_NAMES
    systems = {
        bm25: lambda q: engine.search_bm25_only(q, k=k),
        sem: lambda q: engine.search_semantic_only(q, k=k),
        hyb: lambda q: engine.search_hybrid(q, k=k)[0],
    }
    summaries, per_queries, significance = [], [], {}
    for set_name, queries in (("dev_50", QUERIES), ("holdout_20", HOLDOUT_QUERIES)):
        summary, per_q = evaluate_systems(systems, catalogue, queries, k=k)
        summary.insert(0, "query_set", set_name)
        per_q.insert(0, "query_set", set_name)
        summaries.append(summary)
        per_queries.append(per_q)
        significance[set_name] = {
            "hybrid_vs_keyword": paired_comparison(per_q, bm25, hyb),
            "hybrid_vs_semantic": paired_comparison(per_q, sem, hyb),
        }
    return pd.concat(summaries, ignore_index=True), pd.concat(per_queries, ignore_index=True), significance


def run_day4_task1_hybrid_search(
    db_path: Path | None = None,
) -> tuple[pd.DataFrame, HybridSearchEngine, dict[str, list[dict[str, Any]]]]:
    """
    Execute Day 4 — Task 1:
    1. Fit `HybridSearchEngine` (query parser + BM25 + semantic vectors + RRF + feature re-ranker).
    2. Evaluate keyword vs semantic vs hybrid on 50 development + 20 held-out labelled queries
       (graded relevance, catalogue-wide NDCG@10, paired bootstrap + sign test).
    3. Return top results for the 4 demo queries from the brief.

    Returns the development-set summary (3 rows: keyword, semantic, hybrid).
    """
    import json

    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)
    engine = HybridSearchEngine(rrf_k=60).fit_from_duckdb(con)
    catalogue = con.execute("SELECT * FROM product_catalogue").df()
    con.close()

    summary_df, per_query_df, significance = evaluate_search_architectures(engine, catalogue, k=10)
    out = settings.reports_dir
    out.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out / "day4_search_comparison.csv", index=False)
    per_query_df.to_csv(out / "day4_search_per_query.csv", index=False)
    (out / "day4_search_significance.json").write_text(json.dumps(significance, indent=2), encoding="utf-8")

    demo_queries = [
        "eid ke liye lawn suit under 5000",
        "bachon ke liye school bag",
        "shaadi ke liye red lehenga 20 hazaar tak",
        "laptop for coding under 1.5 lac",
    ]
    demo_outputs: dict[str, list[dict[str, Any]]] = {}
    for dq in demo_queries:
        res, _ = engine.search_hybrid(dq, k=5)
        demo_outputs[dq] = res

    dev_summary = summary_df[summary_df["query_set"] == "dev_50"].drop(columns="query_set").reset_index(drop=True)
    return dev_summary, engine, demo_outputs
