"""Offline, fast tests for code similarity detection and teacher review output (Day 4 Task 5)."""
from __future__ import annotations

import copy
import re

import numpy as np
import pytest

from ilm import config
from ilm.grading import plagiarism, plagiarism_data
from ilm.grading.plagiarism import (
    REVIEW_LABEL,
    ast_similarity,
    fit_on_dev,
    render_flagged_html,
    run_benchmark,
    score_pairs,
    token_fingerprint,
    token_similarity,
)
from ilm.grading.plagiarism_data import DISGUISES, build_dataset, save_dataset


def _fast_char_ngram_embed(codes: list[str], dim: int = 64) -> np.ndarray:
    """Deterministic, offline character-trigram hashing embedder for fast unit tests."""
    mat = np.zeros((len(codes), dim), dtype=np.float64)
    for row_idx, text in enumerate(codes):
        cleaned = re.sub(r"\s+", " ", text.strip())
        for i in range(max(1, len(cleaned) - 2)):
            tri = cleaned[i : i + 3]
            bucket = sum((idx + 1) * ord(ch) for idx, ch in enumerate(tri)) % dim
            mat[row_idx, bucket] += 1.0
        if np.linalg.norm(mat[row_idx]) == 0:
            mat[row_idx, 0] = 1.0
    return mat


ORIGINAL = """
def count_letters(word):
    counts = {}
    for ch in word:
        if ch in counts:
            counts[ch] += 1
        else:
            counts[ch] = 1
    return counts
"""

RENAMED_COPY = """
def count_letters(text_input):
    tally = {}
    for symbol in text_input:
        if symbol in tally:
            tally[symbol] += 1
        else:
            tally[symbol] = 1
    return tally
"""

COMMENT_WHITESPACE_COPY = """
# Count each character in the input string
def count_letters( word ):
    \"\"\"Return a dictionary mapping characters to frequencies.\"\"\"
    counts   =   {}

    # Walk over every character
    for ch in word:
        if ch in counts:
            counts[ ch ] += 1   # seen before
        else:
            counts[ ch ] = 1    # first occurrence

    return counts
"""

INDEPENDENT_SOLUTION = """
from collections import Counter

def count_letters(word):
    return {k: word.count(k) for k in sorted(set(word)) if Counter(word)[k] > 0}
"""


def test_whitespace_and_comments_do_not_change_fingerprint_score():
    fp_orig = token_fingerprint(ORIGINAL)
    fp_noisy = token_fingerprint(COMMENT_WHITESPACE_COPY)
    assert fp_orig == fp_noisy
    assert token_similarity(ORIGINAL, COMMENT_WHITESPACE_COPY) == 1.0
    assert (
        token_similarity(ORIGINAL, INDEPENDENT_SOLUTION)
        == token_similarity(COMMENT_WHITESPACE_COPY, INDEPENDENT_SOLUTION)
    )
    assert ast_similarity(ORIGINAL, COMMENT_WHITESPACE_COPY) == 1.0


def test_renamed_copy_scores_higher_than_independent_solution():
    tok_copy = token_similarity(ORIGINAL, RENAMED_COPY)
    tok_indep = token_similarity(ORIGINAL, INDEPENDENT_SOLUTION)
    ast_copy = ast_similarity(ORIGINAL, RENAMED_COPY)
    ast_indep = ast_similarity(ORIGINAL, INDEPENDENT_SOLUTION)

    assert tok_copy == 1.0
    assert ast_copy == 1.0
    assert tok_copy > tok_indep + 0.5
    assert ast_copy > ast_indep + 0.3


def test_false_positive_control_dampens_short_canonical_convergence():
    subs = [
        {"submission_id": "m_s1", "exercise_id": "modulo-02", "code": "def is_even(n):\n    return n % 2 == 0\n"},
        {"submission_id": "m_s2", "exercise_id": "modulo-02", "code": "def is_even(num):\n    return num % 2 == 0\n"},
        {"submission_id": "m_s3", "exercise_id": "modulo-02", "code": "def is_even(x):\n    return (x & 1) == 0\n"},
        {"submission_id": "c_s1", "exercise_id": "dictionaries-03", "code": ORIGINAL},
        {"submission_id": "c_s2", "exercise_id": "dictionaries-03", "code": RENAMED_COPY},
        {"submission_id": "c_s3", "exercise_id": "dictionaries-03", "code": INDEPENDENT_SOLUTION},
        {
            "submission_id": "c_s4",
            "exercise_id": "dictionaries-03",
            "code": "def count_letters(s):\n    d = {}\n    i = 0\n    while i < len(s):\n        d[s[i]] = d.get(s[i], 0) + 1\n        i += 1\n    return d\n",
        },
    ]
    pairs = [
        {"pair_id": "m_12", "exercise_id": "modulo-02", "split": "dev", "sub_a": "m_s1", "sub_b": "m_s2", "copied": False, "disguise": None},
        {"pair_id": "m_13", "exercise_id": "modulo-02", "split": "dev", "sub_a": "m_s1", "sub_b": "m_s3", "copied": False, "disguise": None},
        {"pair_id": "m_23", "exercise_id": "modulo-02", "split": "dev", "sub_a": "m_s2", "sub_b": "m_s3", "copied": False, "disguise": None},
        {"pair_id": "c_12", "exercise_id": "dictionaries-03", "split": "dev", "sub_a": "c_s1", "sub_b": "c_s2", "copied": True, "disguise": "rename"},
        {"pair_id": "c_13", "exercise_id": "dictionaries-03", "split": "dev", "sub_a": "c_s1", "sub_b": "c_s3", "copied": False, "disguise": None},
        {"pair_id": "c_14", "exercise_id": "dictionaries-03", "split": "dev", "sub_a": "c_s1", "sub_b": "c_s4", "copied": False, "disguise": None},
        {"pair_id": "c_34", "exercise_id": "dictionaries-03", "split": "dev", "sub_a": "c_s3", "sub_b": "c_s4", "copied": False, "disguise": None},
    ]
    refs = {
        "modulo-02": "def is_even(n):\n    return n % 2 == 0\n",
        "dictionaries-03": "def count_letters(word):\n    counts = {}\n    for ch in word:\n        counts[ch] = counts.get(ch, 0) + 1\n    return counts\n",
    }
    scored = {
        r["pair_id"]: r
        for r in score_pairs(subs, pairs, reference_by_exercise=refs, embed_fn=_fast_char_ngram_embed)
    }
    # Raw token similarity is 1.0 on both the trivial 1-liner pair and the real multi-line copy,
    # whereas exercise-adjusted similarity suppresses the trivial 1-liner convergence.
    assert scored["m_12"]["token_raw"] == 1.0
    assert scored["c_12"]["token_raw"] == 1.0
    assert scored["m_12"]["token_adj"] == 0.0
    assert scored["c_12"]["token_adj"] > 1.5


def test_thresholds_are_picked_on_dev_only():
    ds = build_dataset(seed=42)
    # 1. Passing any test row into `fit_on_dev` must fail loudly
    fake_rows = score_pairs(ds["submissions"][:20], ds["pairs"][:15], embed_fn=_fast_char_ngram_embed)
    fake_rows[0]["split"] = "test"
    with pytest.raises(ValueError, match="dev only"):
        fit_on_dev(fake_rows)

    # 2. Flipping every ground-truth label in `test` must not change ANY threshold or weight
    ds_flipped_test = copy.deepcopy(ds)
    for p in ds_flipped_test["pairs"]:
        if p["split"] == "test":
            p["copied"] = not p["copied"]
            p["disguise"] = "rename" if p["copied"] else None

    rep_normal, _, _ = run_benchmark(dataset=ds, embed_fn=_fast_char_ngram_embed)
    rep_flipped, _, _ = run_benchmark(dataset=ds_flipped_test, embed_fn=_fast_char_ngram_embed)

    for key in rep_normal["dev"]:
        assert rep_normal["dev"][key]["threshold"] == rep_flipped["dev"][key]["threshold"]
        assert rep_normal["test"][key]["threshold"] == rep_flipped["test"][key]["threshold"]
    assert rep_normal["combined_weights_standardised"] == rep_flipped["combined_weights_standardised"]
    assert rep_normal["combined_intercept"] == rep_flipped["combined_intercept"]


def test_html_escapes_code_safely_and_uses_review_label():
    malicious_row = {
        "pair_id": "xss_pair",
        "exercise_id": "strings-04<script>evil()</script>",
        "sub_a": 'sub_a"<img src=x onerror=alert(1)>',
        "sub_b": "sub_b&<b>tag</b>",
        "code_a": 'def greet(name):\n    msg = "<script>alert(\'xss\')</script>"\n    return msg + name\n',
        "code_b": 'def greet(user):\n    out = "<img src=x onerror=steal()>"\n    return out + user\n',
        "combined": 0.94,
        "token_raw": 1.0,
        "token_adj": 3.1,
        "ast_raw": 1.0,
        "ast_adj": 2.9,
        "embedding_raw": 0.91,
        "embedding_adj": 2.4,
    }
    doc = render_flagged_html(
        [malicious_row],
        threshold=0.5,
        stems_by_exercise={malicious_row["exercise_id"]: "Write greet(name) <iframe src='bad'>"},
        split_label="test<svg onload=bad()>",
    )

    assert "<script>" not in doc
    assert "<img " not in doc
    assert "<iframe" not in doc
    assert "<svg " not in doc
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in doc
    assert REVIEW_LABEL in doc
    assert "plagiarism detected" not in doc.lower()


def test_dataset_is_deterministic_exercise_split_and_isolated():
    d1 = build_dataset(seed=42)
    d2 = build_dataset(seed=42)
    assert d1 == d2

    dev_ex = set(d1["summary"]["dev_exercises"])
    test_ex = set(d1["summary"]["test_exercises"])
    assert len(dev_ex) == 6 and len(test_ex) == 6
    assert dev_ex.isdisjoint(test_ex)
    assert {p["disguise"] for p in d1["pairs"] if p["copied"]} == set(DISGUISES)

    # Saving writes to conftest's temporary PROCESSED_DIR, never the real repo data/ folder
    saved = save_dataset()
    out_dir = config.PROCESSED_DIR / "plagiarism"
    assert str(config.PROJECT_ROOT / "data") not in str(out_dir) or ".pytest_tmp" in str(out_dir)
    assert (out_dir / "submissions.json").exists()
    assert len(saved["submissions"]) == 140


@pytest.mark.slow
def test_real_bge_embedding_similarity():
    sim_copy = plagiarism.embedding_similarity(ORIGINAL, RENAMED_COPY)
    unrelated = "class Money:\n    def __init__(self, amount):\n        self.amount = amount\n"
    sim_unrelated = plagiarism.embedding_similarity(ORIGINAL, unrelated)
    assert sim_copy > sim_unrelated
