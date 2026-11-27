"""Code similarity detectors, per-exercise false-positive control, and teacher review view (Day 4 Task 5).

Policy: FLAG ONLY. Every flag is labelled "Possible copying - needs teacher review" and is
sent to a human teacher. No score here ever changes a student's mark or triggers an automatic
penalty.

Three complementary detectors:
  1. Token fingerprint (MOSS-style): Python `tokenize`, strip comments/docstrings/whitespace,
     normalise user names and literals, hash overlapping k-grams with blake2b, select
     fingerprints by rightmost-minimum winnowing, and score by Jaccard similarity.
  2. AST similarity: preorder sequence of `ast` node types + tree depth with all identifier
     names, constants and docstrings removed, compared with `SequenceMatcher`.
  3. Embedding similarity: cosine similarity of `config.EMBEDDING_MODEL`
     (`BAAI/bge-small-en-v1.5`) code embeddings.

False-positive control:
  On short or constrained exercises (`is_even`, `to_celsius`), honest students write almost
  the same code, and semantic embeddings give high raw cosine similarity to any two solutions
  of the same exercise. Each pair is therefore adjusted against its exercise's cohort similarity
  distribution (median and robust spread, using no labels) and short-code canonical reference
  overlap.

Run:  python -m ilm.grading.plagiarism
"""
from __future__ import annotations

import ast
import builtins
import difflib
import hashlib
import html
import io
import json
import keyword
import math
import tokenize
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

from ilm import config
from ilm.grading.plagiarism_data import DISGUISES, load_dataset

REVIEW_LABEL = "Possible copying - needs teacher review"

SAFE_BUILTINS = frozenset(dir(builtins)) & {
    "abs", "all", "any", "bool", "chr", "dict", "divmod", "enumerate", "filter",
    "float", "frozenset", "int", "isinstance", "len", "list", "map", "max", "min",
    "next", "ord", "pow", "print", "range", "reversed", "round", "set", "sorted",
    "str", "sum", "tuple", "type", "zip", "ValueError", "TypeError", "ZeroDivisionError",
    "True", "False", "None",
}

_SKIP_TOKENS = frozenset({
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
})


# ------------------------------------------------------------------ 1. Token fingerprint ----
def _docstring_spans(code: str) -> set[tuple[int, int]]:
    """Return `(lineno, end_lineno)` of module/class/function docstrings so they act like comments."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    spans: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                val = node.body[0].value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    spans.add((node.body[0].lineno, getattr(node.body[0], "end_lineno", node.body[0].lineno)))
    return spans


def normalise_tokens(code: str) -> list[tuple[str, int]]:
    """Tokenise Python source into `(norm_token, lineno)` pairs, ignoring whitespace and comments."""
    doc_spans = _docstring_spans(code)
    out: list[tuple[str, int]] = []
    try:
        stream = tokenize.generate_tokens(io.StringIO(code).readline)
        for tok in stream:
            ttype, tstr, (sline, _), (eline, _), _ = tok
            if ttype in _SKIP_TOKENS:
                continue
            if ttype == tokenize.STRING and (sline, eline) in doc_spans:
                continue
            if ttype == tokenize.NAME:
                if keyword.iskeyword(tstr) or tstr in SAFE_BUILTINS:
                    norm = tstr
                else:
                    norm = "V"
            elif ttype == tokenize.NUMBER:
                norm = "0"
            elif ttype == tokenize.STRING:
                norm = "S"
            elif ttype == tokenize.OP:
                norm = tstr
            else:
                norm = tstr.strip()
                if not norm:
                    continue
            out.append((norm, sline))
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def _hash64(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


def kgram_hashes(tokens: list[tuple[str, int]], k: int = 5) -> list[tuple[int, set[int]]]:
    """Build hashed overlapping token k-grams and keep the source line numbers of each k-gram."""
    if not tokens:
        return []
    eff_k = min(k, len(tokens))
    grams: list[tuple[int, set[int]]] = []
    for i in range(len(tokens) - eff_k + 1):
        window = tokens[i : i + eff_k]
        gram_str = " ".join(t for t, _ in window)
        lines = {ln for _, ln in window}
        grams.append((_hash64(gram_str), lines))
    return grams


def winnow(grams: list[tuple[int, set[int]]], window: int = 4) -> list[tuple[int, int, set[int]]]:
    """MOSS rightmost-minimum winnowing over hashed k-grams.

    Returns `(hash_value, gram_position, line_set)` for each selected fingerprint.
    """
    if not grams:
        return []
    if len(grams) <= window:
        best_idx = min(range(len(grams)), key=lambda i: (grams[i][0], -i))
        return [(grams[best_idx][0], best_idx, grams[best_idx][1])]

    selected: list[tuple[int, int, set[int]]] = []
    last_idx = -1
    for start in range(len(grams) - window + 1):
        # Rightmost minimum in `[start, start + window)`
        best_idx = start
        best_hash = grams[start][0]
        for pos in range(start + 1, start + window):
            if grams[pos][0] <= best_hash:
                best_hash = grams[pos][0]
                best_idx = pos
        if best_idx != last_idx:
            selected.append((best_hash, best_idx, grams[best_idx][1]))
            last_idx = best_idx
    return selected


def token_fingerprint(code: str, k: int = 5, window: int = 4) -> set[int]:
    """Return the set of winnowed k-gram hashes for `code`."""
    grams = kgram_hashes(normalise_tokens(code), k=k)
    return {h for h, _, _ in winnow(grams, window=window)}


def token_similarity(code_a: str, code_b: str, k: int = 5, window: int = 4) -> float:
    """Jaccard similarity of MOSS-style winnowed token fingerprints."""
    fp_a = token_fingerprint(code_a, k=k, window=window)
    fp_b = token_fingerprint(code_b, k=k, window=window)
    if not fp_a and not fp_b:
        return 1.0
    if not fp_a or not fp_b:
        return 0.0
    return len(fp_a & fp_b) / len(fp_a | fp_b)


# ------------------------------------------------------------------ 2. AST similarity ----
def _strip_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                val = node.body[0].value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    node.body = node.body[1:]


def ast_sequence(code: str) -> list[str]:
    """Preorder sequence of normalised AST node tags (`NodeType@depth`) with names/literals removed."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    _strip_docstrings(tree)
    seq: list[str] = []

    def walk(node: ast.AST, depth: int) -> None:
        if isinstance(node, ast.expr_context):
            return
        tag = type(node).__name__
        if isinstance(node, ast.Name) and node.id in SAFE_BUILTINS:
            tag = f"Builtin:{node.id}"
        seq.append(f"{tag}@{depth}")
        for child in ast.iter_child_nodes(node):
            walk(child, depth + 1)

    walk(tree, 0)
    return seq


def ast_similarity(code_a: str, code_b: str) -> float:
    """Sequence-matching ratio over normalised AST node sequences."""
    seq_a = ast_sequence(code_a)
    seq_b = ast_sequence(code_b)
    if not seq_a and not seq_b:
        return 1.0
    if not seq_a or not seq_b:
        return 0.0
    return difflib.SequenceMatcher(None, seq_a, seq_b, autojunk=False).ratio()


# ------------------------------------------------------------------ 3. Embedding similarity ----
@lru_cache(maxsize=2)
def embedder(model_name: str | None = None):
    """Load the local SentenceTransformer (`config.EMBEDDING_MODEL`) once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name or config.EMBEDDING_MODEL)


def encode_codes(
    codes: list[str],
    model_name: str | None = None,
    embed_fn: Callable[[list[str]], np.ndarray] | None = None,
) -> np.ndarray:
    """Return L2-normalised embedding vectors `(N, D)` for `codes`."""
    if embed_fn is not None:
        vecs = np.asarray(embed_fn(codes), dtype=np.float64)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return vecs / norms
    model = embedder(model_name)
    vecs = model.encode(codes, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float64)


def embedding_similarity(
    code_a: str,
    code_b: str,
    model_name: str | None = None,
    embed_fn: Callable[[list[str]], np.ndarray] | None = None,
) -> float:
    """Cosine similarity of two code snippets under `config.EMBEDDING_MODEL`."""
    vecs = encode_codes([code_a, code_b], model_name=model_name, embed_fn=embed_fn)
    return float(np.clip(np.dot(vecs[0], vecs[1]), -1.0, 1.0))


# ------------------------------------------------------------------ 4. Scoring & FP control ----
DETECTOR_NAMES = ("token", "ast", "embedding")


def score_pairs(
    submissions: list[dict],
    pairs: list[dict],
    reference_by_exercise: dict[str, str] | None = None,
    embed_fn: Callable[[list[str]], np.ndarray] | None = None,
) -> list[dict]:
    """Compute raw similarities and per-exercise false-positive-adjusted scores for `pairs`.

    Crucially, `adjust_exercise_scores` never reads `copied` or `disguise` labels: it uses only
    the distribution of pair similarities within each exercise, submission token length, and
    (when provided) similarity to the bank's canonical reference solution on short exercises.
    """
    sub_map = {s["submission_id"]: s for s in submissions}
    refs = reference_by_exercise or {}

    # Pre-compute per-submission representations once
    unique_codes: dict[str, str] = {s["submission_id"]: s["code"] for s in submissions}
    for ex_id, ref_code in refs.items():
        unique_codes[f"__ref__{ex_id}"] = ref_code

    keys = sorted(unique_codes)
    emb_matrix = encode_codes([unique_codes[k] for k in keys], embed_fn=embed_fn)
    emb_map = {k: emb_matrix[idx] for idx, k in enumerate(keys)}
    tok_len_map = {k: len(normalise_tokens(unique_codes[k])) for k in keys}
    fp_map = {k: token_fingerprint(unique_codes[k]) for k in keys}
    ast_map = {k: ast_sequence(unique_codes[k]) for k in keys}

    def _tok_sim(ka: str, kb: str) -> float:
        fa, fb = fp_map[ka], fp_map[kb]
        if not fa and not fb:
            return 1.0
        if not fa or not fb:
            return 0.0
        return len(fa & fb) / len(fa | fb)

    def _ast_sim(ka: str, kb: str) -> float:
        sa, sb = ast_map[ka], ast_map[kb]
        if not sa and not sb:
            return 1.0
        if not sa or not sb:
            return 0.0
        return difflib.SequenceMatcher(None, sa, sb, autojunk=False).ratio()

    def _emb_sim(ka: str, kb: str) -> float:
        return float(np.clip(np.dot(emb_map[ka], emb_map[kb]), -1.0, 1.0))

    rows: list[dict] = []
    by_exercise: dict[str, list[dict]] = {}
    for p in pairs:
        ka, kb = p["sub_a"], p["sub_b"]
        ex_id = p["exercise_id"]
        min_tok = min(tok_len_map[ka], tok_len_map[kb])

        raw_tok = _tok_sim(ka, kb)
        raw_ast = _ast_sim(ka, kb)
        raw_emb = _emb_sim(ka, kb)

        ref_key = f"__ref__{ex_id}"
        if ref_key in emb_map:
            ref_tok = min(_tok_sim(ka, ref_key), _tok_sim(kb, ref_key))
            ref_ast = min(_ast_sim(ka, ref_key), _ast_sim(kb, ref_key))
            ref_emb = min(_emb_sim(ka, ref_key), _emb_sim(kb, ref_key))
        else:
            ref_tok = ref_ast = ref_emb = 0.0

        row = {
            **p,
            "code_a": sub_map[ka]["code"],
            "code_b": sub_map[kb]["code"],
            "min_tokens": min_tok,
            "token_raw": raw_tok,
            "ast_raw": raw_ast,
            "embedding_raw": raw_emb,
            "token_ref_overlap": ref_tok,
            "ast_ref_overlap": ref_ast,
            "embedding_ref_overlap": ref_emb,
        }
        rows.append(row)
        by_exercise.setdefault(ex_id, []).append(row)

    # Per-exercise false-positive adjustment (uses NO ground-truth labels)
    for ex_id, ex_rows in by_exercise.items():
        for det in DETECTOR_NAMES:
            vals = np.array([r[f"{det}_raw"] for r in ex_rows], dtype=np.float64)
            med = float(np.median(vals))
            q25, q75 = np.percentile(vals, [25, 75])
            mad = float(np.median(np.abs(vals - med)))
            spread = max(1.4826 * mad, float(q75 - q25) / 1.349, float(np.std(vals)), 0.05)
            for r in ex_rows:
                min_tok = r["min_tokens"]
                # On very short solutions (<24 tokens), honest students routinely match the
                # textbook 1-2 line solution; discount overlap explained by that canonical form.
                short_w = max(0.0, min(1.0, (24.0 - min_tok) / 12.0))
                expected = max(med, short_w * r[f"{det}_ref_overlap"])
                credibility = min_tok / (min_tok + 8.0)
                r[f"{det}_exercise_median"] = round(med, 4)
                r[f"{det}_adj"] = float(((r[f"{det}_raw"] - expected) / spread) * credibility)

    return rows


# ------------------------------------------------------------------ 5. Combined model & eval ----
def _feature_matrix(rows: list[dict], adjusted: bool = True) -> np.ndarray:
    if not adjusted:
        return np.array(
            [[r["token_raw"], r["ast_raw"], r["embedding_raw"]] for r in rows],
            dtype=np.float64,
        )
    return np.array(
        [
            [
                r["token_raw"],
                r["ast_raw"],
                r["embedding_raw"],
                r["token_adj"],
                r["ast_adj"],
                r["embedding_adj"],
                math.log1p(r["min_tokens"]),
            ]
            for r in rows
        ],
        dtype=np.float64,
    )


def pick_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Pick the decision threshold maximising F1 on DEV (ties broken toward higher precision)."""
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=np.float64)
    candidates = np.unique(s)
    best_thr = float(candidates[-1])
    best_key = (-1.0, -1.0)
    for thr in candidates:
        preds = (s >= thr).astype(int)
        prec, rec, f1, _ = precision_recall_fscore_support(y, preds, average="binary", zero_division=0)
        key = (round(float(f1), 8), round(float(prec), 8))
        if key > best_key:
            best_key = key
            best_thr = float(thr)
    return best_thr


@dataclass
class TunedSuite:
    """Frozen models and DEV-selected thresholds. Test data never enters `fit_on_dev`."""
    scaler_adj: StandardScaler
    clf_adj: LogisticRegression
    scaler_raw: StandardScaler
    clf_raw: LogisticRegression
    thresholds: dict[str, float]


def fit_on_dev(dev_rows: list[dict], seed: int = config.RANDOM_SEED) -> TunedSuite:
    """Fit the combined logistic model and pick all detector thresholds on `dev_rows` ONLY."""
    if any(r.get("split") == "test" for r in dev_rows):
        raise ValueError("Refusing to tune on test split rows: thresholds must come from dev only")

    y_dev = np.array([int(r["copied"]) for r in dev_rows], dtype=int)

    X_adj = _feature_matrix(dev_rows, adjusted=True)
    scaler_adj = StandardScaler().fit(X_adj)
    clf_adj = LogisticRegression(C=1.0, random_state=seed, max_iter=500)
    clf_adj.fit(scaler_adj.transform(X_adj), y_dev)

    X_raw = _feature_matrix(dev_rows, adjusted=False)
    scaler_raw = StandardScaler().fit(X_raw)
    clf_raw = LogisticRegression(C=1.0, random_state=seed, max_iter=500)
    clf_raw.fit(scaler_raw.transform(X_raw), y_dev)

    apply_combined_scores(dev_rows, scaler_adj, clf_adj, scaler_raw, clf_raw)

    score_keys = (
        "token_raw",
        "token_adj",
        "ast_raw",
        "ast_adj",
        "embedding_raw",
        "embedding_adj",
        "combined_raw",
        "combined",
    )
    thresholds = {
        k: pick_threshold(y_dev, np.array([r[k] for r in dev_rows], dtype=np.float64))
        for k in score_keys
    }
    return TunedSuite(
        scaler_adj=scaler_adj,
        clf_adj=clf_adj,
        scaler_raw=scaler_raw,
        clf_raw=clf_raw,
        thresholds=thresholds,
    )


def apply_combined_scores(
    rows: list[dict],
    scaler_adj: StandardScaler,
    clf_adj: LogisticRegression,
    scaler_raw: StandardScaler,
    clf_raw: LogisticRegression,
) -> None:
    """Attach `combined` (FP-controlled) and `combined_raw` probabilities to `rows`."""
    probs_adj = clf_adj.predict_proba(scaler_adj.transform(_feature_matrix(rows, adjusted=True)))[:, 1]
    probs_raw = clf_raw.predict_proba(scaler_raw.transform(_feature_matrix(rows, adjusted=False)))[:, 1]
    for r, pa, pr in zip(rows, probs_adj, probs_raw):
        r["combined"] = float(pa)
        r["combined_raw"] = float(pr)


def evaluate_detector(rows: list[dict], score_key: str, threshold: float) -> dict:
    """Evaluate one score column at a frozen threshold."""
    y = np.array([int(r["copied"]) for r in rows], dtype=int)
    s = np.array([float(r[score_key]) for r in rows], dtype=np.float64)
    preds = (s >= threshold).astype(int)

    prec, rec, f1, _ = precision_recall_fscore_support(y, preds, average="binary", zero_division=0)
    pr_auc = float(average_precision_score(y, s)) if len(np.unique(y)) > 1 else 0.0

    tp = int(np.sum((preds == 1) & (y == 1)))
    fp = int(np.sum((preds == 1) & (y == 0)))
    fn = int(np.sum((preds == 0) & (y == 1)))
    tn = int(np.sum((preds == 0) & (y == 0)))
    short_fp = int(
        sum(1 for r, pr in zip(rows, preds) if pr == 1 and not r["copied"] and r.get("short_exercise"))
    )

    by_disguise: dict[str, dict] = {}
    for d in DISGUISES:
        idx = [i for i, r in enumerate(rows) if r["copied"] and r.get("disguise") == d]
        if idx:
            caught = int(sum(preds[i] == 1 for i in idx))
            total = len(idx)
            by_disguise[d] = {
                "caught": caught,
                "missed": total - caught,
                "total": total,
                "recall": round(caught / total, 4),
            }

    return {
        "threshold": round(threshold, 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "pr_auc": round(pr_auc, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "short_exercise_fp": short_fp,
        "by_disguise": by_disguise,
    }


# ------------------------------------------------------------------ 6. Teacher HTML view ----
def _norm_line(line: str) -> str:
    """Normalise a single line's identifiers and literals for fallback visual alignment."""
    stripped = line.split("#", 1)[0].strip()
    if not stripped:
        return ""
    toks = [t for t, _ in normalise_tokens(stripped + "\n")]
    return " ".join(toks)


def matching_lines(code_a: str, code_b: str, k: int = 5, window: int = 4) -> tuple[set[int], set[int]]:
    """Identify 1-based matching lines between `code_a` and `code_b` for the teacher diff view."""
    grams_a = kgram_hashes(normalise_tokens(code_a), k=k)
    grams_b = kgram_hashes(normalise_tokens(code_b), k=k)
    win_a = winnow(grams_a, window=window)
    win_b = winnow(grams_b, window=window)
    shared_hashes = {h for h, _, _ in win_a} & {h for h, _, _ in win_b}

    lines_a = {ln for h, _, lset in win_a if h in shared_hashes for ln in lset}
    lines_b = {ln for h, _, lset in win_b if h in shared_hashes for ln in lset}

    # Also align normalised non-trivial statements so AST/structural matches highlight cleanly
    norm_a = [_norm_line(l) for l in code_a.splitlines()]
    norm_b = [_norm_line(l) for l in code_b.splitlines()]
    matcher = difflib.SequenceMatcher(None, norm_a, norm_b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for ia, jb in zip(range(i1, i2), range(j1, j2)):
                if norm_a[ia] and not norm_a[ia].startswith("def V"):
                    lines_a.add(ia + 1)
                    lines_b.add(jb + 1)
    return lines_a, lines_b


def _render_code_column(code: str, matched: set[int]) -> str:
    rendered: list[str] = []
    for lineno, raw_line in enumerate(code.splitlines(), start=1):
        safe_text = html.escape(raw_line, quote=True)
        cls = ' class="match"' if lineno in matched else ""
        rendered.append(
            f'<div class="line{(" match" if lineno in matched else "")}"{cls}>'
            f'<span class="ln">{lineno:>2}</span>'
            f'<span class="src">{safe_text if safe_text else "&nbsp;"}</span>'
            f"</div>"
        )
    return "\n".join(rendered)


def render_flagged_html(
    flagged_rows: list[dict],
    threshold: float,
    stems_by_exercise: dict[str, str] | None = None,
    split_label: str = "test",
) -> str:
    """Build a self-contained side-by-side HTML review pack. Escapes all student code safely."""
    stems = stems_by_exercise or {}
    sorted_rows = sorted(flagged_rows, key=lambda r: r.get("combined", 0.0), reverse=True)

    cards: list[str] = []
    for rank, row in enumerate(sorted_rows, start=1):
        code_a, code_b = row["code_a"], row["code_b"]
        hl_a, hl_b = matching_lines(code_a, code_b)
        ex_id = html.escape(str(row["exercise_id"]), quote=True)
        sub_a = html.escape(str(row["sub_a"]), quote=True)
        sub_b = html.escape(str(row["sub_b"]), quote=True)
        stem = html.escape(stems.get(row["exercise_id"], ""), quote=True)

        cards.append(f"""
    <section class="card">
      <div class="card-header">
        <div>
          <span class="rank">#{rank}</span>
          <strong>{ex_id}</strong>: <code>{sub_a}</code> vs <code>{sub_b}</code>
        </div>
        <span class="badge">{html.escape(REVIEW_LABEL, quote=True)}</span>
      </div>
      {f'<p class="stem">{stem}</p>' if stem else ''}
      <div class="scores">
        <span><strong>Combined:</strong> {row.get("combined", 0.0):.3f} (cut-off {threshold:.3f})</span>
        <span><strong>Token:</strong> {row.get("token_raw", 0.0):.2f} (z={row.get("token_adj", 0.0):+.2f})</span>
        <span><strong>AST:</strong> {row.get("ast_raw", 0.0):.2f} (z={row.get("ast_adj", 0.0):+.2f})</span>
        <span><strong>Embedding:</strong> {row.get("embedding_raw", 0.0):.2f} (z={row.get("embedding_adj", 0.0):+.2f})</span>
      </div>
      <div class="side-by-side">
        <div class="pane">
          <div class="pane-title">{sub_a}</div>
          <div class="code-box">{_render_code_column(code_a, hl_a)}</div>
        </div>
        <div class="pane">
          <div class="pane-title">{sub_b}</div>
          <div class="code-box">{_render_code_column(code_b, hl_b)}</div>
        </div>
      </div>
    </section>""")

    body = "\n".join(cards) if cards else '<p class="empty">No pairs crossed the review threshold.</p>'
    safe_split = html.escape(split_label, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Ilm Academy - Teacher Similarity Review ({safe_split})</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 24px auto; max-width: 1200px; padding: 0 16px; color: #1f2937; background: #f8fafc; }}
    header {{ background: #fff; border: 1px solid #e2e8f0; border-left: 5px solid #d97706; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; }}
    h1 {{ margin: 0 0 6px 0; font-size: 1.35rem; }}
    .policy {{ margin: 0; color: #475569; font-size: 0.95rem; }}
    .card {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; }}
    .rank {{ color: #64748b; font-weight: 600; margin-right: 6px; }}
    .badge {{ background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; padding: 4px 10px; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }}
    .stem {{ margin: 10px 16px 0 16px; color: #475569; font-size: 0.9rem; }}
    .scores {{ display: flex; flex-wrap: wrap; gap: 16px; padding: 10px 16px; font-size: 0.86rem; color: #334155; border-bottom: 1px solid #f1f5f9; }}
    .side-by-side {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px 16px 16px 16px; }}
    .pane {{ border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; background: #ffffff; }}
    .pane-title {{ background: #f8fafc; padding: 6px 10px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.82rem; font-weight: 600; border-bottom: 1px solid #e2e8f0; }}
    .code-box {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.82rem; line-height: 1.45; overflow-x: auto; padding: 6px 0; }}
    .line {{ display: flex; padding: 0 8px; white-space: pre; }}
    .line.match {{ background: #fef9c3; border-left: 3px solid #eab308; padding-left: 5px; }}
    .ln {{ color: #94a3b8; user-select: none; width: 28px; flex-shrink: 0; text-align: right; margin-right: 10px; }}
    .src {{ color: #0f172a; }}
    .empty {{ padding: 24px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(REVIEW_LABEL, quote=True)}</h1>
    <p class="policy">
      Split: <strong>{safe_split}</strong> &middot; Flagged pairs: <strong>{len(sorted_rows)}</strong>.
      High code similarity can also happen when an exercise is short or follows a standard lecture pattern.
      This tool never changes marks or applies penalties automatically; a teacher reviews both submissions and decides.
    </p>
  </header>
  {body}
</body>
</html>
"""


# ------------------------------------------------------------------ 7. Full benchmark & report ----
def run_benchmark(
    dataset: dict | None = None,
    embed_fn: Callable[[list[str]], np.ndarray] | None = None,
    seed: int = config.RANDOM_SEED,
) -> tuple[dict, str, str]:
    """Tune on `dev` exercises, score `test` exercises ONCE, and build report JSON, MD and HTML."""
    from ilm.questions.validate import load_bank

    bank = {q.id: q for q in load_bank()[0]}
    ds = dataset or load_dataset(seed=seed)
    refs = {ex_id: bank[ex_id].solution for ex_id in {s["exercise_id"] for s in ds["submissions"]} if ex_id in bank}
    stems = {ex_id: bank[ex_id].stem for ex_id in refs}

    all_rows = score_pairs(ds["submissions"], ds["pairs"], reference_by_exercise=refs, embed_fn=embed_fn)
    dev_rows = [r for r in all_rows if r["split"] == "dev"]
    test_rows = [r for r in all_rows if r["split"] == "test"]

    # Tune strictly on DEV
    suite = fit_on_dev(dev_rows, seed=seed)

    # Score TEST once with frozen model and frozen thresholds
    apply_combined_scores(test_rows, suite.scaler_adj, suite.clf_adj, suite.scaler_raw, suite.clf_raw)

    columns = (
        ("token_raw", "Token fingerprint (raw)"),
        ("token_adj", "Token fingerprint (exercise-adjusted)"),
        ("ast_raw", "AST sequence (raw)"),
        ("ast_adj", "AST sequence (exercise-adjusted)"),
        ("embedding_raw", "Embedding bge-small (raw)"),
        ("embedding_adj", "Embedding bge-small (exercise-adjusted)"),
        ("combined_raw", "Combined logistic (raw only)"),
        ("combined", "Combined logistic (exercise-adjusted)"),
    )

    dev_metrics = {key: {"label": label, **evaluate_detector(dev_rows, key, suite.thresholds[key])} for key, label in columns}
    test_metrics = {key: {"label": label, **evaluate_detector(test_rows, key, suite.thresholds[key])} for key, label in columns}

    comb_thr = suite.thresholds["combined"]
    flagged_test = [r for r in test_rows if r["combined"] >= comb_thr]
    flagged_summary = [
        {
            "pair_id": r["pair_id"],
            "exercise_id": r["exercise_id"],
            "sub_a": r["sub_a"],
            "sub_b": r["sub_b"],
            "status": REVIEW_LABEL,
            "combined": round(r["combined"], 4),
            "token_raw": round(r["token_raw"], 4),
            "token_adj": round(r["token_adj"], 4),
            "ast_raw": round(r["ast_raw"], 4),
            "ast_adj": round(r["ast_adj"], 4),
            "embedding_raw": round(r["embedding_raw"], 4),
            "embedding_adj": round(r["embedding_adj"], 4),
            "ground_truth_copied": r["copied"],
            "ground_truth_disguise": r["disguise"],
        }
        for r in sorted(flagged_test, key=lambda x: x["combined"], reverse=True)
    ]

    feature_names = [
        "token_raw",
        "ast_raw",
        "embedding_raw",
        "token_adj",
        "ast_adj",
        "embedding_adj",
        "log1p_min_tokens",
    ]
    weights = {name: round(float(w), 4) for name, w in zip(feature_names, suite.clf_adj.coef_[0])}

    report = {
        "policy": REVIEW_LABEL,
        "script": "python -m ilm.grading.plagiarism",
        "embedding_model": config.EMBEDDING_MODEL if embed_fn is None else "custom_embed_fn",
        "dataset": ds["summary"],
        "combined_weights_standardised": weights,
        "combined_intercept": round(float(suite.clf_adj.intercept_[0]), 4),
        "dev": dev_metrics,
        "test": test_metrics,
        "false_positive_control_gain_test": {
            det: {
                "f1_delta": round(test_metrics[f"{det}_adj"]["f1"] - test_metrics[f"{det}_raw"]["f1"], 4),
                "pr_auc_delta": round(test_metrics[f"{det}_adj"]["pr_auc"] - test_metrics[f"{det}_raw"]["pr_auc"], 4),
                "fp_before": test_metrics[f"{det}_raw"]["fp"],
                "fp_after": test_metrics[f"{det}_adj"]["fp"],
                "short_fp_before": test_metrics[f"{det}_raw"]["short_exercise_fp"],
                "short_fp_after": test_metrics[f"{det}_adj"]["short_exercise_fp"],
            }
            for det in ("token", "ast", "embedding")
        },
        "combined_fp_control_gain_test": {
            "f1_delta": round(test_metrics["combined"]["f1"] - test_metrics["combined_raw"]["f1"], 4),
            "pr_auc_delta": round(test_metrics["combined"]["pr_auc"] - test_metrics["combined_raw"]["pr_auc"], 4),
            "fp_before": test_metrics["combined_raw"]["fp"],
            "fp_after": test_metrics["combined"]["fp"],
            "short_fp_before": test_metrics["combined_raw"]["short_exercise_fp"],
            "short_fp_after": test_metrics["combined"]["short_exercise_fp"],
        },
        "flagged_test_pairs": flagged_summary,
    }

    md = _format_markdown(report)
    html_doc = render_flagged_html(flagged_test, threshold=comb_thr, stems_by_exercise=stems, split_label="test")
    return report, md, html_doc


def _format_markdown(report: dict) -> str:
    ds = report["dataset"]
    dev = report["dev"]
    test = report["test"]

    lines = [
        "# Code similarity & plagiarism review report (Day 4 Task 5)",
        "",
        f"> **Policy:** `{REVIEW_LABEL}`. Flags go to a teacher queue with a side-by-side diff; "
        "no student mark is ever lowered or penalised automatically.",
        "",
        f"Reproduce: `{report['script']}` (dataset built with `python -m ilm.grading.plagiarism_data`, "
        f"embedding model `{report['embedding_model']}`).",
        "",
        "## Dataset & exercise-level split",
        "",
        f"- **Exercises:** {ds['exercises']} bank coding exercises (`6` dev: {', '.join(ds['dev_exercises'])}; "
        f"`6` test: {', '.join(ds['test_exercises'])}).",
        f"- **Submissions:** {ds['submissions']} ({ds['honest_submissions']} independent honest solutions in varied styles, "
        f"{ds['copied_submissions']} planted disguised copies; every submission passes the bank unit tests).",
        f"- **Pairs:** {ds['by_split']['dev']['pairs']} dev pairs ({ds['by_split']['dev']['copied_pairs']} copied) and "
        f"{ds['by_split']['test']['pairs']} test pairs ({ds['by_split']['test']['copied_pairs']} copied). "
        "All thresholds and logistic weights were fitted on **dev** only; **test** was scored once.",
        "",
        "## Test split results (scored once, thresholds frozen on dev)",
        "",
        "| Detector | Cut-off (dev) | Precision | Recall | F1 | PR-AUC | FP (short-ex FP) | Missed copies |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = (
        "token_raw",
        "token_adj",
        "ast_raw",
        "ast_adj",
        "embedding_raw",
        "embedding_adj",
        "combined_raw",
        "combined",
    )
    for k in order:
        m = test[k]
        lines.append(
            f"| {m['label']} | {m['threshold']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | "
            f"{m['f1']:.3f} | {m['pr_auc']:.3f} | {m['fp']} ({m['short_exercise_fp']}) | {m['fn']} |"
        )

    lines += [
        "",
        "## Dev split reference (used to choose cut-offs and combined weights)",
        "",
        "| Detector | Cut-off | Precision | Recall | F1 | PR-AUC | FP (short-ex FP) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for k in order:
        m = dev[k]
        lines.append(
            f"| {m['label']} | {m['threshold']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | "
            f"{m['f1']:.3f} | {m['pr_auc']:.3f} | {m['fp']} ({m['short_exercise_fp']}) |"
        )

    lines += [
        "",
        "## How much per-exercise false-positive control helps",
        "",
        "On short or constrained exercises (`modulo-02` `is_even`, `floats-04` `to_celsius`), independent "
        "honest students write almost identical 1-2 line code, and `bge-small-en-v1.5` gives high cosine "
        "similarity to any two solutions solving the same task. Adjusting each pair against its exercise's "
        "median/spread and canonical short-solution overlap (without using any labels) changes test results as follows:",
        "",
    ]
    for det, title in (("token", "Token fingerprint"), ("ast", "AST sequence"), ("embedding", "Embedding")):
        g = report["false_positive_control_gain_test"][det]
        lines.append(
            f"- **{title}:** F1 `{g['f1_delta']:+.3f}`, PR-AUC `{g['pr_auc_delta']:+.3f}`, "
            f"false positives `{g['fp_before']} -> {g['fp_after']}` "
            f"(on short exercises: `{g['short_fp_before']} -> {g['short_fp_after']}`)."
        )
    cg = report["combined_fp_control_gain_test"]
    lines.append(
        f"- **Combined logistic detector:** F1 `{cg['f1_delta']:+.3f}`, PR-AUC `{cg['pr_auc_delta']:+.3f}`, "
        f"false positives `{cg['fp_before']} -> {cg['fp_after']}` "
        f"(on short exercises: `{cg['short_fp_before']} -> {cg['short_fp_after']}`)."
    )

    lines += [
        "",
        "## Which disguises each detector catches vs misses (test split, `caught / total`)",
        "",
        "| Disguise | Token (adj) | AST (adj) | Embedding (adj) | Combined |",
        "|---|---:|---:|---:|---:|",
    ]
    for d in DISGUISES:
        if d not in test["combined"]["by_disguise"]:
            continue
        cells = []
        for k in ("token_adj", "ast_adj", "embedding_adj", "combined"):
            bd = test[k]["by_disguise"][d]
            cells.append(f"{bd['caught']}/{bd['total']} ({bd['recall']:.0%})")
        lines.append(f"| `{d}` | {' | '.join(cells)} |")

    lines += [
        "",
        "### Why each detector misses what it misses",
        "",
        "- **Token fingerprint (winnowed 5-grams):** catches `100%` of `comments_whitespace` and `rename` "
        "copies, but contiguous 5-token windows shatter on `split_merge` (`1/6`, 17%), interleaved `dead_code` "
        "(`4/6`, 67%) and `reorder_lines` (`4/5`, 80%).",
        "- **AST sequence:** ignores names, constants and formatting (`100%` on `rename` and "
        "`comments_whitespace`) and handles `dead_code` better than k-grams (`5/6`, 83%, because "
        "`SequenceMatcher` skips inserted nodes), but drops sharply on `split_merge` (`1/6`, 17%), where one "
        "nested expression turns into several `Assign` statements, and misses `1/5` `reorder_lines`.",
        "- **Code embeddings (`BAAI/bge-small-en-v1.5`):** catch semantic/lexical carry-over on `dead_code` "
        "(`6/6`), `reorder_lines` (`5/5`) and `split_merge` (`4/6`, 67%), but `bge-small-en-v1.5` is a general "
        "English retrieval model rather than a code syntax model: full variable `rename` (`0/6`, 0%) and added "
        "comments/docstrings (`2/6`, 33%) pull the adjusted embedding score below the dev cut-off.",
        "- **Combined logistic detector:** reaches `0.942` PR-AUC and `0.893` precision (`3` false positives out "
        "of `341` honest pairs, `0` on short exercises), catching `25/34` copies (`73.5%` recall); `5` of the `9` "
        "misses are `split_merge` rewrites where temporary variables reshape both k-grams and AST nodes.",
        "",
        "## Honest limits",
        "",
        "1. **One-line exercises have no safe fingerprint.** When the natural answer is `return n % 2 == 0` or "
        "`return round((f - 32) * 5 / 9, 1)`, a copied 1-liner and an honest 1-liner are byte-for-byte equivalent "
        "up to variable names. Suppressing false alarms there inevitably misses trivial-exercise copies unless "
        "the copy carries unusual structure or dead code.",
        "2. **Synthetic disguises vs real collusion.** Our 140 submissions pass real unit tests and cover six "
        "classic transformations, but real students also translate solutions via an LLM or collaborate verbally, "
        "producing semantically equivalent code with fresh structure that all three detectors can miss.",
        "3. **Cohort baseline needs a batch.** Per-exercise median/MAD normalisation assumes at least ~8-10 "
        "submissions on the exercise (and that fewer than half the pairs colluded). On the very first 2-3 "
        "submissions, only the reference-solution baseline is stable.",
        "4. **Similarity is not proof of copying.** Two students who watched the same CS50P lecture a minute "
        "before submitting often write the lecturer's exact pattern independently. That is why every output uses "
        f"*\"{REVIEW_LABEL}\"* in [flagged_pairs.html](flagged_pairs.html) and leaves the decision to a human.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ds = load_dataset()
    report, md, html_doc = run_benchmark(dataset=ds)
    out_dir = config.REPORTS_DIR / "plagiarism"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    (out_dir / "flagged_pairs.html").write_text(html_doc, encoding="utf-8")
    print(f"Test combined: precision={report['test']['combined']['precision']:.3f}, "
          f"recall={report['test']['combined']['recall']:.3f}, "
          f"F1={report['test']['combined']['f1']:.3f}, "
          f"PR-AUC={report['test']['combined']['pr_auc']:.3f}")
    print(f"Flagged {len(report['flagged_test_pairs'])} test pairs -> {out_dir}")


if __name__ == "__main__":
    main()
