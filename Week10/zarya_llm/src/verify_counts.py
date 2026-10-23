import sys
import json
from pathlib import Path
from collections import Counter

import seed_stats


OUT_FILE = Path("verify_counts_output.txt")


class Tee:
    def __init__(self, filename):
        self.file = open(filename, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def run_verification():
    batch_files = [
        ("Batch 1", seed_stats.BATCH1_FILE, 30),
        ("Batch 2", seed_stats.BATCH2_FILE, 16),
        ("Batch 3", seed_stats.BATCH3_FILE, 11),
        ("Batch 4", seed_stats.BATCH4_FILE, 10),
        ("Batch 5", seed_stats.BATCH5_FILE, 10),
        ("Batch 6", seed_stats.BATCH6_FILE, 10),
        ("Batch 7", seed_stats.BATCH7_FILE, 13),
    ]

    all_seeds = []
    file_counts = {}

    print("======================================================================")
    print("VERIFY COUNTS: DATASET VERIFICATION SUITE")
    print("======================================================================")
    print("\n[SECTION 1] Checking Seed Files and Example Counts")

    files_ok = True
    for name, fpath, expected_count in batch_files:
        if not fpath.exists():
            print(f"  [FAIL] Missing file: {fpath}")
            files_ok = False
            continue
        seeds = seed_stats.load_jsonl(fpath)
        actual_count = len(seeds)
        file_counts[name] = actual_count
        all_seeds.extend(seeds)
        status = "[PASS]" if actual_count == expected_count else "[FAIL]"
        if actual_count != expected_count:
            files_ok = False
        print(f"  {status} {name} ({fpath.name}): {actual_count} seeds (expected {expected_count})")

    total_expected = 100
    total_actual = len(all_seeds)
    print(f"\n  Total Type A Seeds Found: {total_actual} (expected {total_expected})")
    if total_actual != total_expected:
        files_ok = False

    print("\n[SECTION 2] Checking Seed ID Uniqueness")
    seen_ids = set()
    dup_ids = []
    for s in all_seeds:
        sid = s.get("id")
        if sid in seen_ids:
            dup_ids.append(sid)
        seen_ids.add(sid)

    if not dup_ids and len(seen_ids) == 100:
        print(f"  [PASS] All {len(seen_ids)} seed IDs are strictly unique (seed_001 to seed_100).")
    else:
        print(f"  [FAIL] Duplicate or missing IDs found: duplicates={dup_ids}, count={len(seen_ids)}")
        files_ok = False

    print("\n[SECTION 3] Combined Dataset Distributions")
    cat_counts = Counter(s.get("category") for s in all_seeds)
    lang_counts = Counter(s.get("language") for s in all_seeds)
    turn_counts = Counter("Multi turn" if s.get("is_multi_turn") else "Single turn" for s in all_seeds)
    ticket_counts = Counter("With Ticket Meta" if s.get("ticket") is not None else "Conversational only" for s in all_seeds)

    ctx_counts = Counter()
    for s in all_seeds:
        ctx = s.get("context")
        if ctx is None:
            ctx_counts["Without Context"] += 1
        elif "koi document nahi mila" in ctx.lower() or "no document" in ctx.lower():
            ctx_counts["No Document"] += 1
        else:
            ctx_counts["With Grounded Context"] += 1

    print("\n  Category Distribution:")
    for cat, cnt in cat_counts.most_common():
        pct = (cnt / total_actual) * 100
        print(f"    {cat:<18}: {cnt:>3} ({pct:>5.1f}%)")

    print("\n  Language Distribution:")
    for lang, cnt in lang_counts.most_common():
        pct = (cnt / total_actual) * 100
        print(f"    {lang:<18}: {cnt:>3} ({pct:>5.1f}%)")

    print("\n  Turn Type Distribution:")
    for t_type, cnt in turn_counts.most_common():
        pct = (cnt / total_actual) * 100
        print(f"    {t_type:<18}: {cnt:>3} ({pct:>5.1f}%)")

    print("\n  Ticket Metadata Distribution (Type B Sources):")
    for t_meta, cnt in ticket_counts.most_common():
        pct = (cnt / total_actual) * 100
        print(f"    {t_meta:<22}: {cnt:>3} ({pct:>5.1f}%)")

    print("\n  Context Distribution:")
    for c_type, cnt in ctx_counts.most_common():
        pct = (cnt / total_actual) * 100
        print(f"    {c_type:<24}: {cnt:>3} ({pct:>5.1f}%)")

    print("\n[SECTION 4] Type B JSON Tasks Verification")
    if not seed_stats.JSON_TASKS_FILE.exists():
        print(f"  [FAIL] Missing JSON tasks file: {seed_stats.JSON_TASKS_FILE}")
        files_ok = False
    else:
        type_b_tasks = seed_stats.load_jsonl(seed_stats.JSON_TASKS_FILE)
        expected_type_b = 36
        actual_type_b = len(type_b_tasks)
        if actual_type_b == expected_type_b:
            print(f"  [PASS] Total Type B Tasks: {actual_type_b} (expected {expected_type_b})")
        else:
            print(f"  [FAIL] Total Type B Tasks: {actual_type_b} (expected {expected_type_b})")
            files_ok = False

    print("\n[SECTION 5] Executing Full Seed Validation Suite")
    validation_passed = seed_stats.print_type_a_stats(all_seeds, "All 100 Seeds Combined Validation")
    if seed_stats.JSON_TASKS_FILE.exists():
        b_passed = seed_stats.print_type_b_stats(seed_stats.JSON_TASKS_FILE)
        if not b_passed:
            validation_passed = False

    if not files_ok or not validation_passed:
        print("\n[FINAL RESULT] VERIFICATION FAILED")
        return 1
    else:
        print("\n[FINAL RESULT] ALL 100 SEEDS AND TYPE B TASKS FULLY VERIFIED WITH ZERO ERRORS")
        return 0


def main():
    tee = Tee(OUT_FILE)
    old_stdout = sys.stdout
    sys.stdout = tee
    try:
        ret = run_verification()
        return ret
    finally:
        sys.stdout = old_stdout
        tee.close()


if __name__ == "__main__":
    sys.exit(main())

