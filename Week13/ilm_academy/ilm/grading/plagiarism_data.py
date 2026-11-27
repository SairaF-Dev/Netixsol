"""Synthetic plagiarism benchmark built from bank code exercises (Day 4 Task 5).

Why synthetic with planted copies:
  Real student copying rarely comes with a verified ground-truth label. To measure precision,
  recall and which disguises slip past each detector, we build a known-answer dataset from 12
  coding exercises in `ilm/questions/bank/*.yaml`:
    - 6 independent honest solutions per exercise, written in genuinely different styles
      (loops vs comprehensions, dict.get vs if/else, index while-loops, helpers, etc.).
      On very short exercises (`modulo-02`, `floats-04`), honest students naturally converge
      on almost identical 1-2 line formulas, testing false-positive control.
    - Planted copies derived from distinct honest solutions using six realistic disguises:
      `comments_whitespace`, `rename`, `reorder_lines`, `for_to_while`, `dead_code`,
      and `split_merge`.
    - Exercise-level split into `dev` (6 exercises) and `test` (6 exercises) with a fixed seed,
      so thresholds and model weights chosen on `dev` are evaluated on unseen exercises.

Run:  python -m ilm.grading.plagiarism_data
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from ilm import config

DISGUISES = (
    "comments_whitespace",
    "rename",
    "reorder_lines",
    "for_to_while",
    "dead_code",
    "split_merge",
)

SHORT_EXERCISES = ("modulo-02", "floats-04")


def _specs() -> list[dict]:
    """Return the 12 exercises with independent honest solutions and planted disguised copies.

    Each planted copy derives from its own honest key (`source`), so two submissions share an
    origin if and only if one was copied from the other.
    """
    return [
        # --------------------------------------------------------- 1. modulo-02 (short) ----
        {
            "exercise_id": "modulo-02",
            "short": True,
            "honest": {
                "h1": ("direct_mod", """
def is_even(n):
    return n % 2 == 0
"""),
                "h2": ("direct_mod_alt_name", """
def is_even(num):
    return num % 2 == 0
"""),
                "h3": ("if_else_return", """
def is_even(x):
    if x % 2 == 0:
        return True
    else:
        return False
"""),
                "h4": ("negated_bool", """
def is_even(val):
    return not bool(val % 2)
"""),
                "h5": ("divmod_check", """
def is_even(number):
    quotient, remainder = divmod(number, 2)
    if remainder == 0:
        return True
    return False
"""),
                "h6": ("bitwise_mask", """
def is_even(k):
    last_bit = k & 1
    return last_bit == 0
"""),
            },
            "copies": [
                ("h5", "rename", """
def is_even(val):
    q_part, rem_part = divmod(val, 2)
    if rem_part == 0:
        return True
    return False
"""),
                ("h3", "comments_whitespace", """
# Check parity of an integer input
def is_even(x):
    # Remainder zero means divisible by two
    if x % 2 == 0:
        return True

    else:
        # Odd case
        return False
"""),
                ("h6", "dead_code", """
def is_even(k):
    sign_flag = 1 if k >= 0 else -1
    last_bit = k & 1
    _unused = sign_flag * 2
    return last_bit == 0
"""),
                ("h1", "split_merge", """
def is_even(n):
    rem = n % 2
    ans = rem == 0
    return ans
"""),
            ],
        },
        # --------------------------------------------------------- 2. floats-04 (short) ----
        {
            "exercise_id": "floats-04",
            "short": True,
            "honest": {
                "h1": ("one_liner", """
def to_celsius(f):
    return round((f - 32) * 5 / 9, 1)
"""),
                "h2": ("one_liner_alt", """
def to_celsius(temp_f):
    return round((temp_f - 32) * 5 / 9, 1)
"""),
                "h3": ("two_step", """
def to_celsius(fahrenheit):
    celsius = (fahrenheit - 32) * 5 / 9
    return round(celsius, 1)
"""),
                "h4": ("named_constants", """
def to_celsius(deg_f):
    freezing_offset = 32.0
    scale = 5.0 / 9.0
    raw_c = (deg_f - freezing_offset) * scale
    return round(raw_c, 1)
"""),
                "h5": ("helper_func", """
def _shift_and_scale(val):
    return (val - 32) * 5 / 9

def to_celsius(f):
    converted = _shift_and_scale(f)
    return round(converted, 1)
"""),
                "h6": ("fraction_form", """
def to_celsius(reading):
    shifted = reading - 32
    numerator = shifted * 5
    return round(numerator / 9, 1)
"""),
            },
            "copies": [
                ("h4", "rename", """
def to_celsius(inp):
    base_point = 32.0
    factor = 5.0 / 9.0
    deg_c = (inp - base_point) * factor
    return round(deg_c, 1)
"""),
                ("h4", "reorder_lines", """
def to_celsius(deg_f):
    scale = 5.0 / 9.0
    freezing_offset = 32.0
    raw_c = scale * (deg_f - freezing_offset)
    return round(raw_c, 1)
"""),
                ("h5", "comments_whitespace", """
def _shift_and_scale(val):
    \"\"\"Apply standard Fahrenheit to Celsius formula.\"\"\"
    return (val - 32) * 5 / 9


def to_celsius(f):
    # Convert first, then round to 1 decimal place
    converted = _shift_and_scale(f)
    return round(converted, 1)
"""),
                ("h6", "dead_code", """
def to_celsius(reading):
    shifted = reading - 32
    kelvin_offset = 273.15
    numerator = shifted * 5
    if kelvin_offset < 0:
        numerator = 0
    return round(numerator / 9, 1)
"""),
            ],
        },
        # --------------------------------------------------------- 3. elif_else-01 ----
        {
            "exercise_id": "elif_else-01",
            "short": False,
            "honest": {
                "h1": ("elif_chain_top_down", """
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    else:
        return "F"
"""),
                "h2": ("cutoff_table_loop", """
def grade(score):
    cutoffs = [(90, "A"), (80, "B"), (70, "C")]
    for limit, letter in cutoffs:
        if score >= limit:
            return letter
    return "F"
"""),
                "h3": ("bottom_up_elif", """
def grade(marks):
    if marks < 70:
        return "F"
    elif marks < 80:
        return "C"
    elif marks < 90:
        return "B"
    return "A"
"""),
                "h4": ("sequential_overwrite", """
def grade(points):
    result = "F"
    if points >= 70:
        result = "C"
    if points >= 80:
        result = "B"
    if points >= 90:
        result = "A"
    return result
"""),
                "h5": ("dict_thresholds", """
def grade(s):
    bands = {"A": 90, "B": 80, "C": 70}
    for label, minimum in bands.items():
        if s >= minimum:
            return label
    return "F"
"""),
                "h6": ("nested_ternary", """
def grade(val):
    if val < 70:
        return "F"
    return "A" if val >= 90 else ("B" if val >= 80 else "C")
"""),
            },
            "copies": [
                ("h1", "comments_whitespace", """
def grade(score):
    # Assign letter grade based on 90 / 80 / 70 boundaries
    if score >= 90:
        return "A"

    elif score >= 80:
        return "B"

    elif score >= 70:
        return "C"
    else:
        return "F"
"""),
                ("h2", "for_to_while", """
def grade(score):
    cutoffs = [(90, "A"), (80, "B"), (70, "C")]
    idx = 0
    while idx < len(cutoffs):
        limit, letter = cutoffs[idx]
        if score >= limit:
            return letter
        idx += 1
    return "F"
"""),
                ("h3", "rename", """
def grade(pct):
    if pct < 70:
        return "F"
    elif pct < 80:
        return "C"
    elif pct < 90:
        return "B"
    return "A"
"""),
                ("h4", "reorder_lines", """
def grade(points):
    result = "F"
    if points >= 90:
        return "A"
    if points >= 70:
        result = "C"
    if points >= 80:
        result = "B"
    return result
"""),
                ("h5", "dead_code", """
def grade(s):
    max_possible = 100
    bands = {"A": 90, "B": 80, "C": 70}
    checked = 0
    for label, minimum in bands.items():
        checked += 1
        if s >= minimum and max_possible >= 100:
            return label
    return "F"
"""),
                ("h6", "split_merge", """
def grade(val):
    below_pass = val < 70
    if below_pass:
        return "F"
    upper_tier = "B" if val >= 80 else "C"
    final_letter = "A" if val >= 90 else upper_tier
    return final_letter
"""),
            ],
        },
        # --------------------------------------------------------- 4. while_loops-04 ----
        {
            "exercise_id": "while_loops-04",
            "short": False,
            "honest": {
                "h1": ("standard_while", """
def collatz_steps(n):
    steps = 0
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        steps += 1
    return steps
"""),
                "h2": ("recursive_collatz", """
def collatz_steps(num):
    if num == 1:
        return 0
    if num % 2 == 0:
        return 1 + collatz_steps(num // 2)
    return 1 + collatz_steps(3 * num + 1)
"""),
                "h3": ("ternary_while", """
def collatz_steps(val):
    count = 0
    while val > 1:
        val = val // 2 if val % 2 == 0 else 3 * val + 1
        count += 1
    return count
"""),
                "h4": ("helper_next_term", """
def _next_collatz(x):
    if x & 1:
        return 3 * x + 1
    return x // 2

def collatz_steps(n):
    hops = 0
    current = n
    while current != 1:
        current = _next_collatz(current)
        hops += 1
    return hops
"""),
                "h5": ("history_list", """
def collatz_steps(start):
    chain = [start]
    while chain[-1] != 1:
        last = chain[-1]
        if last % 2 == 1:
            chain.append(last * 3 + 1)
        else:
            chain.append(last // 2)
    return len(chain) - 1
"""),
                "h6": ("divmod_loop", """
def collatz_steps(n):
    turns = 0
    while True:
        if n == 1:
            break
        q, r = divmod(n, 2)
        n = q if r == 0 else 3 * n + 1
        turns = turns + 1
    return turns
"""),
            },
            "copies": [
                ("h1", "rename", """
def collatz_steps(seed):
    counter = 0
    while seed != 1:
        if seed % 2 == 0:
            seed = seed // 2
        else:
            seed = 3 * seed + 1
        counter += 1
    return counter
"""),
                ("h2", "comments_whitespace", """
def collatz_steps(num):
    \"\"\"Count Collatz hailstone steps recursively until reaching 1.\"\"\"
    # Base case
    if num == 1:
        return 0

    # Even branch vs odd branch
    if num % 2 == 0:
        return 1 + collatz_steps(num // 2)
    return 1 + collatz_steps(3 * num + 1)
"""),
                ("h3", "split_merge", """
def collatz_steps(val):
    count = 0
    while val > 1:
        is_even_val = (val % 2 == 0)
        even_next = val // 2
        odd_next = 3 * val + 1
        val = even_next if is_even_val else odd_next
        count = count + 1
    return count
"""),
                ("h4", "reorder_lines", """
def collatz_steps(n):
    current = n
    hops = 0
    while current != 1:
        hops += 1
        current = _next_collatz(current)
    return hops

def _next_collatz(x):
    if not (x & 1):
        return x // 2
    return 3 * x + 1
"""),
                ("h5", "dead_code", """
def collatz_steps(start):
    chain = [start]
    peak = start
    while chain[-1] != 1:
        last = chain[-1]
        if last > peak:
            peak = last
        if last % 2 == 1:
            chain.append(last * 3 + 1)
        else:
            chain.append(last // 2)
    return len(chain) - 1
"""),
                ("h6", "for_to_while", """
def collatz_steps(n):
    turns = 0
    for _ in range(100000):
        if n == 1:
            break
        q, r = divmod(n, 2)
        n = q if r == 0 else 3 * n + 1
        turns = turns + 1
    return turns
"""),
            ],
        },
        # --------------------------------------------------------- 5. iterating_lists-01 ----
        {
            "exercise_id": "iterating_lists-01",
            "short": False,
            "honest": {
                "h1": ("for_counter", """
def count_long(words, n):
    count = 0
    for w in words:
        if len(w) > n:
            count += 1
    return count
"""),
                "h2": ("generator_sum", """
def count_long(words, limit):
    return sum(1 for word in words if len(word) > limit)
"""),
                "h3": ("list_comp_len", """
def count_long(items, min_len):
    longer = [item for item in items if len(item) > min_len]
    return len(longer)
"""),
                "h4": ("while_index", """
def count_long(words, n):
    idx = 0
    matched = 0
    while idx < len(words):
        if len(words[idx]) > n:
            matched = matched + 1
        idx = idx + 1
    return matched
"""),
                "h5": ("filter_lambda", """
def count_long(seq, threshold):
    kept = list(filter(lambda s: len(s) > threshold, seq))
    return len(kept)
"""),
                "h6": ("continue_skip_short", """
def count_long(tokens, cutoff):
    tally = 0
    for tok in tokens:
        if len(tok) <= cutoff:
            continue
        tally += 1
    return tally
"""),
            },
            "copies": [
                ("h1", "for_to_while", """
def count_long(words, n):
    count = 0
    i = 0
    while i < len(words):
        w = words[i]
        if len(w) > n:
            count += 1
        i += 1
    return count
"""),
                ("h2", "comments_whitespace", """
def count_long(words, limit):
    # Count words strictly longer than limit
    return sum(
        1
        for word in words
        if len(word) > limit
    )
"""),
                ("h3", "split_merge", """
def count_long(items, min_len):
    return len([item for item in items if len(item) > min_len])
"""),
                ("h4", "reorder_lines", """
def count_long(words, n):
    matched = 0
    idx = 0
    while idx < len(words):
        current_len = len(words[idx])
        idx = idx + 1
        if current_len > n:
            matched = matched + 1
    return matched
"""),
                ("h5", "rename", """
def count_long(word_list, bound):
    filtered_words = list(filter(lambda txt: len(txt) > bound, word_list))
    return len(filtered_words)
"""),
                ("h6", "dead_code", """
def count_long(tokens, cutoff):
    tally = 0
    skipped = 0
    for tok in tokens:
        if len(tok) <= cutoff:
            skipped += 1
            continue
        tally += 1
    return tally
"""),
            ],
        },
        # --------------------------------------------------------- 6. iterating_lists-03 ----
        {
            "exercise_id": "iterating_lists-03",
            "short": False,
            "honest": {
                "h1": ("slice_scan", """
def largest(nums):
    best = nums[0]
    for x in nums[1:]:
        if x > best:
            best = x
    return best
"""),
                "h2": ("while_cursor", """
def largest(values):
    current_max = values[0]
    pos = 1
    while pos < len(values):
        if values[pos] > current_max:
            current_max = values[pos]
        pos += 1
    return current_max
"""),
                "h3": ("none_sentinel", """
def largest(arr):
    champion = None
    for elem in arr:
        if champion is None or elem > champion:
            champion = elem
    return champion
"""),
                "h4": ("recursive_divide", """
def largest(nums):
    if len(nums) == 1:
        return nums[0]
    mid = len(nums) // 2
    left_big = largest(nums[:mid])
    right_big = largest(nums[mid:])
    return left_big if left_big >= right_big else right_big
"""),
                "h5": ("reduce_pair", """
from functools import reduce

def largest(numbers):
    return reduce(lambda a, b: a if a > b else b, numbers)
"""),
                "h6": ("index_range_loop", """
def largest(items):
    top_idx = 0
    for i in range(1, len(items)):
        if items[i] > items[top_idx]:
            top_idx = i
    return items[top_idx]
"""),
            },
            "copies": [
                ("h1", "comments_whitespace", """
def largest(nums):
    # Start with first element so negative lists work properly
    best = nums[0]

    for x in nums[1:]:
        # Update running maximum
        if x > best:
            best = x

    return best
"""),
                ("h2", "rename", """
def largest(seq):
    peak_val = seq[0]
    cursor = 1
    while cursor < len(seq):
        if seq[cursor] > peak_val:
            peak_val = seq[cursor]
        cursor += 1
    return peak_val
"""),
                ("h3", "dead_code", """
def largest(arr):
    champion = None
    seen_count = 0
    for elem in arr:
        seen_count += 1
        if champion is None or elem > champion:
            champion = elem
    if seen_count == 0:
        return None
    return champion
"""),
                ("h4", "reorder_lines", """
def largest(nums):
    n_len = len(nums)
    if n_len == 1:
        return nums[0]
    mid = n_len // 2
    right_big = largest(nums[mid:])
    left_big = largest(nums[:mid])
    return right_big if right_big > left_big else left_big
"""),
                ("h5", "split_merge", """
from functools import reduce

def _pick_bigger(a, b):
    if a > b:
        return a
    return b

def largest(numbers):
    ans = reduce(_pick_bigger, numbers)
    return ans
"""),
                ("h6", "for_to_while", """
def largest(items):
    top_idx = 0
    i = 1
    while i < len(items):
        if items[i] > items[top_idx]:
            top_idx = i
        i += 1
    return items[top_idx]
"""),
            ],
        },
        # --------------------------------------------------------- 7. nested_loops-02 ----
        {
            "exercise_id": "nested_loops-02",
            "short": False,
            "honest": {
                "h1": ("nested_append", """
def multiplication_table(n):
    table = []
    for r in range(1, n + 1):
        row = []
        for c in range(1, n + 1):
            row.append(r * c)
        table.append(row)
    return table
"""),
                "h2": ("nested_comprehension", """
def multiplication_table(size):
    return [[row * col for col in range(1, size + 1)] for row in range(1, size + 1)]
"""),
                "h3": ("outer_loop_inner_comp", """
def multiplication_table(n):
    grid = []
    for factor in range(1, n + 1):
        line = [factor * k for k in range(1, n + 1)]
        grid.append(line)
    return grid
"""),
                "h4": ("while_nested", """
def multiplication_table(limit):
    matrix = []
    i = 1
    while i <= limit:
        current_row = []
        j = 1
        while j <= limit:
            current_row.append(i * j)
            j += 1
        matrix.append(current_row)
        i += 1
    return matrix
"""),
                "h5": ("step_range_rows", """
def multiplication_table(n):
    rows = []
    for base in range(1, n + 1):
        rows.append(list(range(base, base * n + 1, base)))
    return rows
"""),
                "h6": ("preallocated_grid", """
def multiplication_table(dim):
    board = [[0] * dim for _ in range(dim)]
    for r_idx in range(dim):
        for c_idx in range(dim):
            board[r_idx][c_idx] = (r_idx + 1) * (c_idx + 1)
    return board
"""),
            },
            "copies": [
                ("h1", "rename", """
def multiplication_table(num):
    out_grid = []
    for y in range(1, num + 1):
        cur_line = []
        for x in range(1, num + 1):
            cur_line.append(y * x)
        out_grid.append(cur_line)
    return out_grid
"""),
                ("h2", "split_merge", """
def multiplication_table(size):
    span = range(1, size + 1)
    result = [
        [row * col for col in span]
        for row in span
    ]
    return result
"""),
                ("h3", "for_to_while", """
def multiplication_table(n):
    grid = []
    factor = 1
    while factor <= n:
        line = [factor * k for k in range(1, n + 1)]
        grid.append(line)
        factor += 1
    return grid
"""),
                ("h4", "comments_whitespace", """
def multiplication_table(limit):
    \"\"\"Build an n-by-n multiplication matrix with nested while loops.\"\"\"
    matrix = []
    i = 1
    while i <= limit:
        current_row = []
        j = 1
        # Fill row i
        while j <= limit:
            current_row.append(i * j)
            j += 1
        matrix.append(current_row)
        i += 1
    return matrix
"""),
                ("h5", "dead_code", """
def multiplication_table(n):
    rows = []
    total_cells = n * n
    for base in range(1, n + 1):
        step_size = base
        if total_cells < 0:
            step_size = 1
        rows.append(list(range(base, base * n + 1, step_size)))
    return rows
"""),
                ("h6", "reorder_lines", """
def multiplication_table(dim):
    board = [[0] * dim for _ in range(dim)]
    for c_idx in range(dim):
        for r_idx in range(dim):
            board[r_idx][c_idx] = (c_idx + 1) * (r_idx + 1)
    return board
"""),
            ],
        },
        # --------------------------------------------------------- 8. dictionaries-03 ----
        {
            "exercise_id": "dictionaries-03",
            "short": False,
            "honest": {
                "h1": ("dict_get", """
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = counts.get(ch, 0) + 1
    return counts
"""),
                "h2": ("if_in_else", """
def count_letters(text):
    freq = {}
    for letter in text:
        if letter in freq:
            freq[letter] += 1
        else:
            freq[letter] = 1
    return freq
"""),
                "h3": ("setdefault_pattern", """
def count_letters(s):
    tally = {}
    for char in s:
        tally.setdefault(char, 0)
        tally[char] = tally[char] + 1
    return tally
"""),
                "h4": ("collections_counter", """
from collections import Counter

def count_letters(word):
    return dict(Counter(word))
"""),
                "h5": ("unique_preserve_count", """
def count_letters(word):
    seen = {}
    for symbol in dict.fromkeys(word):
        seen[symbol] = word.count(symbol)
    return seen
"""),
                "h6": ("defaultdict_int", """
from collections import defaultdict

def count_letters(phrase):
    buckets = defaultdict(int)
    for c in phrase:
        buckets[c] += 1
    return dict(buckets)
"""),
            },
            "copies": [
                ("h1", "for_to_while", """
def count_letters(word):
    counts = {}
    pos = 0
    while pos < len(word):
        ch = word[pos]
        counts[ch] = counts.get(ch, 0) + 1
        pos += 1
    return counts
"""),
                ("h2", "reorder_lines", """
def count_letters(text):
    freq = {}
    for letter in text:
        if letter not in freq:
            freq[letter] = 1
        else:
            freq[letter] += 1
    return freq
"""),
                ("h3", "rename", """
def count_letters(token_str):
    char_map = {}
    for glyph in token_str:
        char_map.setdefault(glyph, 0)
        char_map[glyph] = char_map[glyph] + 1
    return char_map
"""),
                ("h4", "split_merge", """
from collections import Counter

def count_letters(word):
    bag = Counter(word)
    plain = dict(bag)
    return plain
"""),
                ("h5", "dead_code", """
def count_letters(word):
    seen = {}
    length_cache = len(word)
    for symbol in dict.fromkeys(word):
        _ = length_cache
        seen[symbol] = word.count(symbol)
    return seen
"""),
                ("h6", "comments_whitespace", """
from collections import defaultdict


def count_letters(phrase):
    # Accumulate frequencies with defaultdict(int), then convert to plain dict
    buckets = defaultdict(int)
    for c in phrase:
        buckets[c] += 1

    return dict(buckets)
"""),
            ],
        },
        # --------------------------------------------------------- 9. nested_data-02 ----
        {
            "exercise_id": "nested_data-02",
            "short": False,
            "honest": {
                "h1": ("for_append", """
def names_in_house(students, house):
    names = []
    for student in students:
        if student["house"] == house:
            names.append(student["name"])
    return names
"""),
                "h2": ("list_comprehension", """
def names_in_house(roster, target_house):
    return [entry["name"] for entry in roster if entry["house"] == target_house]
"""),
                "h3": ("filter_and_map", """
def names_in_house(records, house):
    matching = filter(lambda rec: rec.get("house") == house, records)
    return [rec["name"] for rec in matching]
"""),
                "h4": ("while_index_scan", """
def names_in_house(students, house_name):
    out = []
    idx = 0
    while idx < len(students):
        person = students[idx]
        if person["house"] == house_name:
            out.append(person["name"])
        idx += 1
    return out
"""),
                "h5": ("continue_mismatch", """
def names_in_house(pupils, wanted):
    collected = []
    for p in pupils:
        if p.get("house") != wanted:
            continue
        collected.append(p.get("name"))
    return collected
"""),
                "h6": ("recursive_filter", """
def names_in_house(students, house):
    if not students:
        return []
    head, tail = students[0], students[1:]
    rest = names_in_house(tail, house)
    if head["house"] == house:
        return [head["name"]] + rest
    return rest
"""),
            },
            "copies": [
                ("h1", "rename", """
def names_in_house(people, group):
    matched_names = []
    for item in people:
        if item["house"] == group:
            matched_names.append(item["name"])
    return matched_names
"""),
                ("h2", "split_merge", """
def names_in_house(roster, target_house):
    chosen = [
        entry["name"]
        for entry in roster
        if entry["house"] == target_house
    ]
    return chosen
"""),
                ("h3", "comments_whitespace", """
def names_in_house(records, house):
    # Keep only records belonging to the requested house
    matching = filter(lambda rec: rec.get("house") == house, records)

    # Extract student names in order
    return [rec["name"] for rec in matching]
"""),
                ("h4", "reorder_lines", """
def names_in_house(students, house_name):
    idx = 0
    out = []
    total = len(students)
    while idx < total:
        person = students[idx]
        idx += 1
        if person["house"] == house_name:
            out.append(person["name"])
    return out
"""),
                ("h5", "for_to_while", """
def names_in_house(pupils, wanted):
    collected = []
    k = 0
    while k < len(pupils):
        p = pupils[k]
        k += 1
        if p.get("house") != wanted:
            continue
        collected.append(p.get("name"))
    return collected
"""),
                ("h6", "dead_code", """
def names_in_house(students, house):
    if not students:
        return []
    head, tail = students[0], students[1:]
    target_label = str(house)
    rest = names_in_house(tail, house)
    if head["house"] == target_label:
        return [head["name"]] + rest
    return rest
"""),
            ],
        },
        # --------------------------------------------------------- 10. csv_files-03 ----
        {
            "exercise_id": "csv_files-03",
            "short": False,
            "honest": {
                "h1": ("for_int_sum", """
def average_score(rows):
    total = 0
    for row in rows:
        total += int(row["score"])
    return total / len(rows)
"""),
                "h2": ("generator_float", """
def average_score(records):
    return sum(float(r["score"]) for r in records) / len(records)
"""),
                "h3": ("running_count_and_sum", """
def average_score(entries):
    acc = 0.0
    n_rows = 0
    for item in entries:
        acc = acc + float(item["score"])
        n_rows = n_rows + 1
    return acc / n_rows
"""),
                "h4": ("list_scores_mean", """
def average_score(data):
    scores = [int(d["score"]) for d in data]
    return sum(scores) / len(scores)
"""),
                "h5": ("statistics_mean", """
import statistics

def average_score(rows):
    numeric = [float(row["score"]) for row in rows]
    return float(statistics.mean(numeric))
"""),
                "h6": ("map_getter", """
def average_score(table):
    parsed = list(map(lambda r: int(r["score"]), table))
    total_pts = sum(parsed)
    return total_pts / len(parsed)
"""),
            },
            "copies": [
                ("h1", "for_to_while", """
def average_score(rows):
    total = 0
    i = 0
    while i < len(rows):
        total += int(rows[i]["score"])
        i += 1
    return total / len(rows)
"""),
                ("h2", "split_merge", """
def average_score(records):
    n_items = len(records)
    sum_scores = sum(float(r["score"]) for r in records)
    mean_val = sum_scores / n_items
    return mean_val
"""),
                ("h3", "reorder_lines", """
def average_score(entries):
    n_rows = 0
    acc = 0.0
    for item in entries:
        n_rows = n_rows + 1
        acc = acc + float(item["score"])
    return acc / n_rows
"""),
                ("h4", "comments_whitespace", """
def average_score(data):
    # Convert string CSV scores to integers first
    scores = [int(d["score"]) for d in data]

    # Compute arithmetic mean
    return sum(scores) / len(scores)
"""),
                ("h5", "rename", """
import statistics

def average_score(csv_dicts):
    vals = [float(line["score"]) for line in csv_dicts]
    return float(statistics.mean(vals))
"""),
                ("h6", "dead_code", """
def average_score(table):
    parsed = list(map(lambda r: int(r["score"]), table))
    min_possible = 0
    total_pts = sum(parsed) + min_possible
    return total_pts / len(parsed)
"""),
            ],
        },
        # --------------------------------------------------------- 11. sets-02 ----
        {
            "exercise_id": "sets-02",
            "short": False,
            "honest": {
                "h1": ("set_comp_sorted", """
def unique_houses(students):
    return sorted({s["house"] for s in students})
"""),
                "h2": ("set_add_loop", """
def unique_houses(roster):
    houses = set()
    for person in roster:
        houses.add(person["house"])
    return sorted(houses)
"""),
                "h3": ("list_membership_sort", """
def unique_houses(records):
    seen = []
    for rec in records:
        h = rec["house"]
        if h not in seen:
            seen.append(h)
    seen.sort()
    return seen
"""),
                "h4": ("dict_fromkeys_keys", """
def unique_houses(students):
    ordered_unique = dict.fromkeys(s["house"] for s in students)
    result = list(ordered_unique.keys())
    result.sort()
    return result
"""),
                "h5": ("map_set_sorted", """
def unique_houses(pupils):
    extracted = map(lambda p: p["house"], pupils)
    distinct = list(set(extracted))
    return sorted(distinct)
"""),
                "h6": ("while_collect_set", """
def unique_houses(items):
    found = set()
    idx = 0
    while idx < len(items):
        found.add(items[idx]["house"])
        idx += 1
    out = list(found)
    out.sort()
    return out
"""),
            },
            "copies": [
                ("h1", "split_merge", """
def unique_houses(students):
    unique_set = {s["house"] for s in students}
    ordered = sorted(unique_set)
    return ordered
"""),
                ("h2", "for_to_while", """
def unique_houses(roster):
    houses = set()
    k = 0
    while k < len(roster):
        houses.add(roster[k]["house"])
        k += 1
    return sorted(houses)
"""),
                ("h3", "rename", """
def unique_houses(entries):
    collected = []
    for row in entries:
        grp = row["house"]
        if grp not in collected:
            collected.append(grp)
    collected.sort()
    return collected
"""),
                ("h4", "comments_whitespace", """
def unique_houses(students):
    # Deduplicate houses with dict.fromkeys, then sort in place
    ordered_unique = dict.fromkeys(s["house"] for s in students)
    result = list(ordered_unique.keys())

    result.sort()
    return result
"""),
                ("h5", "dead_code", """
def unique_houses(pupils):
    total_pupils = len(pupils)
    extracted = map(lambda p: p["house"], pupils)
    distinct = list(set(extracted))
    if total_pupils < 0:
        return []
    return sorted(distinct)
"""),
                ("h6", "reorder_lines", """
def unique_houses(items):
    idx = 0
    found = set()
    n_len = len(items)
    while idx < n_len:
        cur = items[idx]["house"]
        idx += 1
        found.add(cur)
    out = list(found)
    out.sort()
    return out
"""),
            ],
        },
        # --------------------------------------------------------- 12. recursion-05 ----
        {
            "exercise_id": "recursion-05",
            "short": False,
            "honest": {
                "h1": ("compact_and_slice", """
def is_palindrome(s):
    if len(s) <= 1:
        return True
    return s[0] == s[-1] and is_palindrome(s[1:-1])
"""),
                "h2": ("early_false_guard", """
def is_palindrome(text):
    if len(text) < 2:
        return True
    if text[0] != text[-1]:
        return False
    return is_palindrome(text[1:-1])
"""),
                "h3": ("index_helper_recursion", """
def _check_bounds(word, left, right):
    if left >= right:
        return True
    if word[left] != word[right]:
        return False
    return _check_bounds(word, left + 1, right - 1)

def is_palindrome(s):
    return _check_bounds(s, 0, len(s) - 1)
"""),
                "h4": ("explicit_zero_one_cases", """
def is_palindrome(word):
    n = len(word)
    if n == 0:
        return True
    elif n == 1:
        return True
    else:
        if word[0] == word[n - 1]:
            return is_palindrome(word[1:n - 1])
        return False
"""),
                "h5": ("inner_closure_recursion", """
def is_palindrome(s):
    def walk(i):
        j = len(s) - 1 - i
        if i >= j:
            return True
        return s[i] == s[j] and walk(i + 1)
    return walk(0)
"""),
                "h6": ("first_last_unpack", """
def is_palindrome(chars):
    if not chars or len(chars) == 1:
        return True
    first = chars[0]
    last = chars[-1]
    middle = chars[1:-1]
    if first == last:
        return is_palindrome(middle)
    return False
"""),
            },
            "copies": [
                ("h1", "split_merge", """
def is_palindrome(s):
    short_enough = len(s) <= 1
    if short_enough:
        return True
    ends_match = (s[0] == s[-1])
    if not ends_match:
        return False
    inner = s[1:-1]
    return is_palindrome(inner)
"""),
                ("h2", "comments_whitespace", """
def is_palindrome(text):
    \"\"\"Recursive palindrome check on string `text`.\"\"\"
    if len(text) < 2:
        return True

    # Mismatched outer characters fail immediately
    if text[0] != text[-1]:
        return False

    return is_palindrome(text[1:-1])
"""),
                ("h3", "rename", """
def _mirror_ok(buf, lo, hi):
    if lo >= hi:
        return True
    if buf[lo] != buf[hi]:
        return False
    return _mirror_ok(buf, lo + 1, hi - 1)

def is_palindrome(s):
    return _mirror_ok(s, 0, len(s) - 1)
"""),
                ("h4", "dead_code", """
def is_palindrome(word):
    n = len(word)
    step_tag = n % 2
    if n == 0:
        return True
    elif n == 1:
        return True
    else:
        if word[0] == word[n - 1] and step_tag >= 0:
            return is_palindrome(word[1:n - 1])
        return False
"""),
                ("h5", "reorder_lines", """
def is_palindrome(s):
    total_len = len(s)
    def walk(i):
        j = total_len - 1 - i
        if j <= i:
            return True
        if s[i] != s[j]:
            return False
        return walk(i + 1)
    return walk(0)
"""),
                ("h6", "for_to_while", """
def is_palindrome(chars):
    while len(chars) > 1:
        first = chars[0]
        last = chars[-1]
        middle = chars[1:-1]
        if first != last:
            return False
        chars = middle
    return True
"""),
            ],
        },
    ]


def build_dataset(seed: int = config.RANDOM_SEED) -> dict:
    """Construct deterministic submissions and exercise-split pairs."""
    rng = random.Random(seed)
    specs = _specs()

    short_specs = [s for s in specs if s["short"]]
    std_specs = [s for s in specs if not s["short"]]
    rng.shuffle(short_specs)
    rng.shuffle(std_specs)

    dev_ids = {short_specs[0]["exercise_id"], *(s["exercise_id"] for s in std_specs[:5])}
    test_ids = {short_specs[1]["exercise_id"], *(s["exercise_id"] for s in std_specs[5:])}
    assert not (dev_ids & test_ids) and len(dev_ids) == 6 and len(test_ids) == 6

    submissions: list[dict] = []
    pairs: list[dict] = []

    for spec in sorted(specs, key=lambda x: x["exercise_id"]):
        ex_id = spec["exercise_id"]
        split = "dev" if ex_id in dev_ids else "test"

        raw_items = []
        for h_key, (style, code) in spec["honest"].items():
            raw_items.append({
                "local_key": h_key,
                "origin_key": h_key,
                "is_copy": False,
                "disguise": None,
                "style": style,
                "code": code.strip("\n") + "\n",
            })
        for idx, (src_key, disguise, code) in enumerate(spec["copies"], start=1):
            assert disguise in DISGUISES, f"unknown disguise {disguise}"
            assert src_key in spec["honest"], f"missing source {src_key} in {ex_id}"
            raw_items.append({
                "local_key": f"c{idx}",
                "origin_key": src_key,
                "is_copy": True,
                "disguise": disguise,
                "style": f"copy_of_{src_key}_{disguise}",
                "code": code.strip("\n") + "\n",
            })

        # Shuffle within each exercise so submission numbering never leaks honest vs copy
        rng.shuffle(raw_items)
        key_to_sub_id: dict[str, str] = {}
        ex_subs: list[dict] = []
        for pos, item in enumerate(raw_items, start=1):
            sub_id = f"{ex_id}__s{pos:02d}"
            key_to_sub_id[item["local_key"]] = sub_id
            ex_subs.append((sub_id, item))

        built_ex_subs: list[dict] = []
        for sub_id, item in ex_subs:
            built_ex_subs.append({
                "submission_id": sub_id,
                "exercise_id": ex_id,
                "split": split,
                "short_exercise": bool(spec["short"]),
                "is_copy": item["is_copy"],
                "source_id": key_to_sub_id[item["origin_key"]] if item["is_copy"] else None,
                "origin_id": key_to_sub_id[item["origin_key"]],
                "disguise": item["disguise"],
                "style": item["style"],
                "code": item["code"],
            })
        submissions.extend(built_ex_subs)

        for i in range(len(built_ex_subs)):
            for j in range(i + 1, len(built_ex_subs)):
                a, b = built_ex_subs[i], built_ex_subs[j]
                copied = a["origin_id"] == b["origin_id"]
                disguise = (a["disguise"] or b["disguise"]) if copied else None
                pairs.append({
                    "pair_id": f"{a['submission_id']}__{b['submission_id']}",
                    "exercise_id": ex_id,
                    "split": split,
                    "short_exercise": bool(spec["short"]),
                    "sub_a": a["submission_id"],
                    "sub_b": b["submission_id"],
                    "copied": copied,
                    "disguise": disguise,
                })

    summary = {
        "seed": seed,
        "exercises": len(specs),
        "dev_exercises": sorted(dev_ids),
        "test_exercises": sorted(test_ids),
        "submissions": len(submissions),
        "honest_submissions": sum(not s["is_copy"] for s in submissions),
        "copied_submissions": sum(s["is_copy"] for s in submissions),
        "pairs": len(pairs),
        "by_split": {
            sp: {
                "exercises": sorted(dev_ids if sp == "dev" else test_ids),
                "pairs": sum(p["split"] == sp for p in pairs),
                "copied_pairs": sum(p["split"] == sp and p["copied"] for p in pairs),
                "non_copied_pairs": sum(p["split"] == sp and not p["copied"] for p in pairs),
                "by_disguise": {
                    d: sum(p["split"] == sp and p["disguise"] == d for p in pairs)
                    for d in DISGUISES
                },
            }
            for sp in ("dev", "test")
        },
    }
    return {"submissions": submissions, "pairs": pairs, "summary": summary}


def save_dataset(out_dir: Path | None = None, seed: int = config.RANDOM_SEED) -> dict:
    """Build and write `submissions.json`, `pairs.json` and `summary.json`."""
    target = out_dir or (config.PROCESSED_DIR / "plagiarism")
    target.mkdir(parents=True, exist_ok=True)
    data = build_dataset(seed=seed)
    (target / "submissions.json").write_text(
        json.dumps(data["submissions"], indent=1), encoding="utf-8"
    )
    (target / "pairs.json").write_text(
        json.dumps(data["pairs"], indent=1), encoding="utf-8"
    )
    (target / "summary.json").write_text(
        json.dumps(data["summary"], indent=1), encoding="utf-8"
    )
    return data


def load_dataset(in_dir: Path | None = None, seed: int = config.RANDOM_SEED) -> dict:
    """Load saved dataset if present, otherwise build and save it."""
    target = in_dir or (config.PROCESSED_DIR / "plagiarism")
    subs_path = target / "submissions.json"
    pairs_path = target / "pairs.json"
    sum_path = target / "summary.json"
    if subs_path.exists() and pairs_path.exists() and sum_path.exists():
        return {
            "submissions": json.loads(subs_path.read_text(encoding="utf-8")),
            "pairs": json.loads(pairs_path.read_text(encoding="utf-8")),
            "summary": json.loads(sum_path.read_text(encoding="utf-8")),
        }
    return save_dataset(out_dir=target, seed=seed)


def verify_against_bank(data: dict | None = None) -> list[str]:
    """Run every submission in the plagiarism dataset against its bank exercise's unit tests."""
    from ilm.questions.runner import run_tests
    from ilm.questions.validate import load_bank

    bank = {q.id: q for q in load_bank()[0]}
    ds = data or build_dataset()
    errors: list[str] = []
    for sub in ds["submissions"]:
        q = bank[sub["exercise_id"]]
        res = run_tests(sub["code"], [t.model_dump() for t in q.tests])
        if not res.all_passed:
            errors.append(f"{sub['submission_id']} ({sub['style']}): {res.error or res.details}")
    return errors


def main() -> None:
    data = save_dataset()
    errs = verify_against_bank(data)
    if errs:
        for e in errs:
            print("ERROR", e)
        raise SystemExit(1)
    out = config.PROCESSED_DIR / "plagiarism"
    print(json.dumps(data["summary"], indent=1))
    print(f"Saved verified dataset ({len(data['submissions'])} submissions, {len(data['pairs'])} pairs) -> {out}")


if __name__ == "__main__":
    main()
