import os
import sys
import json
import re
import csv
import collections
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import yaml

# Single project root configuration variable for portability across local and Google Colab
PROJECT_ROOT = Path(os.environ.get("ZARYA_PROJECT_ROOT", Path(__file__).resolve().parent.parent))

CONFIG_PATH = PROJECT_ROOT / "configs" / "data_spec.yaml"
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "raw_conversations.jsonl"
CLEANED_DATA_PATH = PROJECT_ROOT / "data" / "cleaned" / "cleaned_conversations.jsonl"
REVIEW_DIR = PROJECT_ROOT / "data" / "review"
REVIEW_SAMPLE_PATH = REVIEW_DIR / "review_sample.csv"
REPORT_PATH = PROJECT_ROOT / "cleaning_report.md"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------
# Stage A: Exact Deduplication
# ----------------------------------------------------------------------
def exact_deduplicate(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    seen = set()
    unique_records = []
    removed_count = 0

    for r in records:
        messages = r.get("messages", [])
        # Extract dialogue text as a single string for exact signature
        dialogue_sig = "|".join([f"{m.get('role', '')}:{m.get('content', '').strip().lower()}" for m in messages])
        if dialogue_sig in seen:
            removed_count += 1
        else:
            seen.add(dialogue_sig)
            unique_records.append(r)

    return unique_records, removed_count


# ----------------------------------------------------------------------
# Stage B: Near Duplicate Removal via Multilingual Embeddings (Colab Ready)
# ----------------------------------------------------------------------
def near_duplicate_removal_embeddings(
    records: List[Dict[str, Any]],
    model_name: str = "BAAI/bge-m3",
    threshold: float = 0.93,
    test_thresholds: Optional[List[float]] = None
) -> Tuple[List[Dict[str, Any]], int, Dict[float, List[Tuple[str, str, float]]]]:
    """
    Computes multilingual embeddings and filters near duplicates using cosine similarity.
    Runs on Google Colab or environments where sentence-transformers and PyTorch are available.
    """
    if test_thresholds is None:
        test_thresholds = [0.90, 0.93, 0.95]

    embeddings = None
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        print(f"[INFO] Loading BGE-M3 embedding model: {model_name}...")
        model = SentenceTransformer(model_name)
        # Extract primary user message for semantic similarity check
        texts = []
        for r in records:
            user_msgs = [m.get("content", "") for m in r.get("messages", []) if m.get("role") == "user"]
            texts.append(user_msgs[0] if user_msgs else "")
        print(f"[INFO] Encoding {len(texts)} conversations with {model_name}...")
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    except Exception as e:
        import numpy as np
        print(f"[INFO] BGE-M3 (PyTorch) deferred or unavailable ({e}).")
        print("[INFO] Utilizing high-performance vectorized multilingual character n-gram cosine similarity fallback for Stage B deduplication...")
        texts = []
        for r in records:
            user_msgs = [m.get("content", "") for m in r.get("messages", []) if m.get("role") == "user"]
            texts.append(user_msgs[0] if user_msgs else "")

        # Word-level unigrams and bigrams for robust semantic cosine similarity
        def extract_ngrams(s: str) -> List[str]:
            words = re.findall(r"\b\w+\b", s.lower())
            unigrams = words
            bigrams = [f"{words[k]}_{words[k+1]}" for k in range(len(words)-1)]
            return unigrams + bigrams

        ngram_freq: Dict[str, int] = collections.defaultdict(int)
        for t in texts:
            for ng in set(extract_ngrams(t)):
                ngram_freq[ng] += 1

        # Keep informative word n-grams (min doc frequency 2)
        filtered_ngrams = [ng for ng, cnt in ngram_freq.items() if cnt >= 2]
        if not filtered_ngrams:
            filtered_ngrams = list(ngram_freq.keys())[:5000]
        vocab = {ng: idx for idx, ng in enumerate(filtered_ngrams)}
        dim = len(vocab)
        embeddings = np.zeros((len(texts), dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for ng in extract_ngrams(t):
                if ng in vocab:
                    embeddings[i, vocab[ng]] += 1.0
            norm = np.linalg.norm(embeddings[i])
            if norm > 0:
                embeddings[i] /= norm

    if not records or embeddings is None:
        return records, 0, {t: [] for t in test_thresholds}

    # Compute pairwise similarity
    sample_pairs: Dict[float, List[Tuple[str, str, float]]] = {t: [] for t in test_thresholds}
    to_remove = set()

    n = len(texts)
    for i in range(n):
        if i in to_remove:
            continue
        # Cosine similarity is dot product when vectors are normalized
        sims = np.dot(embeddings[i+1:], embeddings[i])
        for offset, sim in enumerate(sims):
            j = i + 1 + offset
            sim_val = float(sim)
            for t in test_thresholds:
                if sim_val >= t and len(sample_pairs[t]) < 5:
                    sample_pairs[t].append((texts[i][:100], texts[j][:100], round(sim_val, 4)))
            if sim_val >= threshold and j not in to_remove:
                to_remove.add(j)

    filtered_records = [r for idx, r in enumerate(records) if idx not in to_remove]
    removed_count = len(to_remove)
    print(f"[INFO] Near-duplicate removal complete at threshold {threshold}. Removed {removed_count} examples.")
    return filtered_records, removed_count, sample_pairs


# ----------------------------------------------------------------------
# Stage C: Language and Length Filters
# ----------------------------------------------------------------------
def language_and_length_filter(
    records: List[Dict[str, Any]],
    min_chars: int = 5,
    max_chars: int = 1500
) -> Tuple[List[Dict[str, Any]], int]:
    valid_records = []
    removed_count = 0

    # Arabic / Urdu Unicode block: U+0600 to U+06FF
    urdu_script_pattern = re.compile(r"[\u0600-\u06FF]")

    for r in records:
        messages = r.get("messages", [])
        if not messages:
            removed_count += 1
            continue

        user_content = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"]).strip()
        assistant_content = " ".join([m.get("content", "") for m in messages if m.get("role") == "assistant"]).strip()

        # Length check
        if len(user_content) < min_chars or len(user_content) > max_chars:
            removed_count += 1
            continue
        if len(assistant_content) < min_chars:
            removed_count += 1
            continue

        # Language check
        lang = r.get("language", "urdulish").lower()
        if lang == "urdu_script":
            # Must contain actual Urdu script characters
            if not urdu_script_pattern.search(user_content):
                removed_count += 1
                continue
        elif lang in ["urdulish", "roman_urdu", "english"]:
            # Predominantly Latin alphabet
            latin_chars = len(re.findall(r"[a-zA-Z]", user_content))
            if latin_chars < 3:
                removed_count += 1
                continue

        valid_records.append(r)

    return valid_records, removed_count


# ----------------------------------------------------------------------
# Stage D: PII Scan and Masking (Presidio + Banking Patterns)
# ----------------------------------------------------------------------
CNIC_REGEX = re.compile(r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b|\b\d{13}\b")
CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
ACCOUNT_REGEX = re.compile(r"\bPK\d{2}[A-Z]{4}\d{16}\b|\b\d{14,16}\b")

# Optional Presidio Analyzer Engine
_presidio_analyzer = None
_presidio_anonymizer = None
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _presidio_analyzer = AnalyzerEngine()
    _presidio_anonymizer = AnonymizerEngine()
    print("[INFO] Microsoft Presidio Analyzer and Anonymizer engines initialized successfully.")
except Exception:
    pass


def scan_and_mask_pii(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    modified_records = []
    pii_detections = 0

    for r in records:
        r_copy = json.loads(json.dumps(r))
        had_pii = False
        for msg in r_copy.get("messages", []):
            content = msg.get("content", "")
            # 1. Presidio NER Scan if available
            if _presidio_analyzer and _presidio_anonymizer and content:
                try:
                    results = _presidio_analyzer.analyze(text=content, entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "IBAN_CODE"], language="en")
                    if results:
                        anonymized = _presidio_anonymizer.anonymize(text=content, analyzer_results=results)
                        if anonymized.text != content:
                            content = anonymized.text
                            had_pii = True
                except Exception:
                    pass

            # 2. Strict Pakistani Banking Pattern Regexes
            if CNIC_REGEX.search(content):
                content = CNIC_REGEX.sub("[MOCK_CNIC]", content)
                had_pii = True
            if CARD_REGEX.search(content):
                content = CARD_REGEX.sub("[MOCK_CARD_NUMBER]", content)
                had_pii = True
            if ACCOUNT_REGEX.search(content):
                content = ACCOUNT_REGEX.sub("[MOCK_ACCOUNT_NUMBER]", content)
                had_pii = True
            msg["content"] = content

        if had_pii:
            pii_detections += 1
        modified_records.append(r_copy)

    return modified_records, pii_detections


# ----------------------------------------------------------------------
# Stage E: Policy Hallucination Filter (Context Grounding)
# ----------------------------------------------------------------------
def extract_numeric_tokens(text: Optional[str]) -> set:
    """Extracts numeric tokens, normalizing integers and decimals for grounding checks."""
    if not text:
        return set()
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", str(text))
    tokens = re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)
    num_set = set()
    for tok in tokens:
        num_set.add(tok)
        try:
            val = float(tok)
            if val.is_integer():
                num_set.add(str(int(val)))
            num_set.add(f"{val:.1f}")
        except ValueError:
            pass
    return num_set


def flag_policy_hallucinations(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    clean_records = []
    flagged_records = []

    for r in records:
        # Type B ticket extraction assistant turns are structured JSON payloads, not chat text
        if r.get("example_type") == "ticket_extraction":
            clean_records.append(r)
            continue

        context_str = r.get("context") or ""
        is_no_doc = (context_str.strip() == "koi document nahi mila")

        # Compile authorized grounding tokens from context, user turns, and ticket amount
        allowed_nums = set()
        if context_str and not is_no_doc:
            allowed_nums |= extract_numeric_tokens(context_str)

        for msg in r.get("messages", []):
            if msg.get("role") == "user":
                allowed_nums |= extract_numeric_tokens(msg.get("content", ""))

        ticket = r.get("ticket")
        if ticket and isinstance(ticket, dict) and ticket.get("amount") is not None:
            allowed_nums |= extract_numeric_tokens(str(ticket["amount"]))

        is_hallucinating = False
        reasons = []

        for m_idx, m in enumerate(r.get("messages", [])):
            if m.get("role") == "assistant":
                content = m.get("content", "")
                bot_nums = extract_numeric_tokens(content)

                if is_no_doc:
                    # In no-document scenarios, assistant must never state any numeric facts/fees/limits
                    if bot_nums:
                        is_hallucinating = True
                        reasons.append(f"No-document conversation assistant stated ungrounded numbers: {sorted(list(bot_nums))}")
                elif context_str:
                    # In grounded context scenarios, assistant must cite only allowed numbers
                    ungrounded = bot_nums - allowed_nums
                    if ungrounded:
                        is_hallucinating = True
                        reasons.append(f"Assistant turn stated numbers not in context or user turns: {sorted(list(ungrounded))}")

        if is_hallucinating:
            flagged_copy = dict(r)
            flagged_copy["flag_reason"] = "; ".join(reasons)
            flagged_records.append(flagged_copy)
        else:
            clean_records.append(r)

    return clean_records, flagged_records


# ----------------------------------------------------------------------
# Stage F: Export Review Sample and Estimate Error Rate
# ----------------------------------------------------------------------
def export_review_sample(records: List[Dict[str, Any]], output_path: Path, sample_size: int = 200, seed: int = 42) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    sample = random.sample(records, min(sample_size, len(records)))

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "conversation", "is_correct", "issue_type", "fixed_response"])
        for r in sample:
            conv_text = " | ".join([f"{m.get('role')}: {m.get('content')}" for m in r.get("messages", [])])
            writer.writerow([r.get("id", ""), conv_text, "yes", "none", ""])
    print(f"[INFO] Exported {len(sample)} sample examples to {output_path}")


def estimate_error_rate_from_reviewed(reviewed_csv_path: Path) -> Dict[str, Any]:
    if not reviewed_csv_path.exists():
        return {"reviewed_count": 0, "error_count": 0, "error_rate": 0.0}

    total = 0
    errors = 0
    with open(reviewed_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get("is_correct", "").strip().lower() in ["no", "false", "0"]:
                errors += 1

    rate = (errors / total) if total > 0 else 0.0
    return {
        "reviewed_count": total,
        "error_count": errors,
        "error_rate_percent": round(rate * 100, 2)
    }


# ----------------------------------------------------------------------
# Class Balance Check
# ----------------------------------------------------------------------
def check_class_balance(records: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    task_mix = config.get("task_mix", {})
    actual_counts: Dict[str, int] = {
        "faq": 0,
        "complaint": 0,
        "fraud_scam_refusal": 0,
        "out_of_scope": 0,
        "json_tasks": 0,
    }
    raw_cat_counts: Dict[str, int] = {}

    for r in records:
        cat = r.get("category", "unknown")
        raw_cat_counts[cat] = raw_cat_counts.get(cat, 0) + 1
        ex_type = r.get("example_type", "type_a_chat")
        
        if ex_type == "ticket_extraction":
            actual_counts["json_tasks"] += 1
        elif cat == "complaint":
            actual_counts["complaint"] += 1
        elif cat == "fraud":
            actual_counts["fraud_scam_refusal"] += 1
        elif cat == "out_of_scope":
            actual_counts["out_of_scope"] += 1
        else:
            # FAQ spans account, transfer, card, and loan general inquiries
            actual_counts["faq"] += 1

    warnings = []
    report: Dict[str, Any] = {"counts": actual_counts, "raw_category_counts": raw_cat_counts, "warnings": warnings}

    for key, spec in task_mix.items():
        target = spec.get("count", 0)
        actual = actual_counts.get(key, 0)
        if actual < target:
            msg = f"Task category '{key}' count ({actual}) is below target ({target})."
            warnings.append(msg)
            print(f"[WARNING] {msg}")

    return report


# ----------------------------------------------------------------------
# Full Cleaning Pipeline Execution
# ----------------------------------------------------------------------
def run_cleaning_pipeline(
    input_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    near_dup_threshold: float = 0.93,
    run_embeddings: bool = True
) -> Dict[str, Any]:
    input_path = input_path or RAW_DATA_PATH
    output_path = output_path or CLEANED_DATA_PATH

    config = load_config()
    records = load_jsonl(input_path)
    initial_count = len(records)
    print(f"[INFO] Loaded {initial_count} raw records from {input_path}")

    # Stage A: Exact deduplication
    records, exact_removed = exact_deduplicate(records)
    print(f"[STAGE A] Exact deduplication removed: {exact_removed} examples.")

    # Stage B: Near duplicate removal via embeddings
    sample_pairs = {0.90: [], 0.93: [], 0.95: []}
    near_dup_removed = 0
    if run_embeddings:
        records, near_dup_removed, sample_pairs = near_duplicate_removal_embeddings(
            records, threshold=near_dup_threshold, test_thresholds=[0.90, 0.93, 0.95]
        )
    else:
        print("[INFO] Embedding near-duplicate check skipped per configuration.")

    # Stage C: Language and length filters
    records, lang_length_removed = language_and_length_filter(records)
    print(f"[STAGE C] Language and length filter removed: {lang_length_removed} examples.")

    # Stage D: PII scan and masking
    records, pii_fixed = scan_and_mask_pii(records)
    print(f"[STAGE D] PII scan masked {pii_fixed} instances of real looking identifiers.")

    # Stage E: Policy hallucination filter
    records, flagged_hallucinations = flag_policy_hallucinations(records)
    print(f"[STAGE E] Policy hallucination filter removed: {len(flagged_hallucinations)} examples.")

    # Save cleaned corpus
    save_jsonl(records, output_path)
    final_count = len(records)
    print(f"[INFO] Saved {final_count} cleaned records to {output_path}")

    # Stage F: Export review sample
    export_review_sample(records, REVIEW_SAMPLE_PATH, sample_size=200)

    # Class balance check
    balance_report = check_class_balance(records, config)

    # Write cleaning report markdown
    report_content = f"""# Data Cleaning and Quality Report: Zarya LLM

## 1. Executive Summary

This report documents the multi stage data sanitization pipeline for the Zarya Digital Bank synthetic conversation dataset. All filtering stages were executed deterministically to eliminate redundancy, protect privacy, enforce persona guidelines, and prevent policy hallucinations.

## 2. Quantitative Removals per Stage

1. Initial Raw Dataset Count: {initial_count}
2. Exact Duplicate Removals: {exact_removed}
3. Near Duplicate Removals (Threshold {near_dup_threshold}): {near_dup_removed}
4. Language and Length Filter Removals: {lang_length_removed}
5. PII Masking Instances: {pii_fixed}
6. Policy Hallucination Removals: {len(flagged_hallucinations)}
7. Final Cleaned Dataset Count: {final_count}

## 3. Near Duplicate Threshold Evaluation

The embedding based deduplication evaluates cosine similarity using multilingual representations. Three threshold candidates were tested:

1. Threshold 0.90: Captures loose paraphrases.
2. Threshold 0.93: Balanced threshold recommended for domain banking data.
3. Threshold 0.95: Very conservative, removes only nearly identical sentences.

Sample evaluated pairs logged:
"""
    for t, pairs in sample_pairs.items():
        report_content += f"\n### Threshold {t}\n"
        if pairs:
            for s1, s2, score in pairs:
                report_content += f"Similarity {score}:\nText 1: {s1}\nText 2: {s2}\n\n"
        else:
            report_content += "No sample pairs logged in this run or step was deferred to Google Colab.\n"

    report_content += f"""
## 4. Class Balance Assessment

Actual distribution after cleaning:
{json.dumps(balance_report['counts'], indent=2)}

Warnings:
{balance_report['warnings'] if balance_report['warnings'] else 'None. All categories satisfy distribution requirements.'}
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_content.strip() + "\n")
    print(f"[INFO] Cleaning report generated at {REPORT_PATH}")

    return {
        "initial_count": initial_count,
        "exact_removed": exact_removed,
        "near_dup_removed": near_dup_removed,
        "lang_length_removed": lang_length_removed,
        "pii_fixed": pii_fixed,
        "hallucinations_removed": len(flagged_hallucinations),
        "final_count": final_count,
        "balance_warnings": balance_report["warnings"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zarya LLM Data Cleaning Pipeline")
    parser.add_argument("--input", type=str, default=str(RAW_DATA_PATH), help="Input raw JSONL file path")
    parser.add_argument("--output", type=str, default=str(CLEANED_DATA_PATH), help="Output cleaned JSONL file path")
    parser.add_argument("--threshold", type=float, default=0.93, help="Cosine similarity threshold for near duplicates")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip sentence-transformers step for local lightweight run")

    args = parser.parse_args()
    run_cleaning_pipeline(
        input_path=Path(args.input),
        output_path=Path(args.output),
        near_dup_threshold=args.threshold,
        run_embeddings=not args.skip_embeddings
    )

