"""50 student submissions for Day 4 Task 2 (grader vs reference marks).

10 bank exercises x 5 submissions, written to cover what a teacher meets on a Sunday: clean
correct code, correct but clumsy or slow code, code that misses an edge case, wrong logic,
broken code, and code that passes every test while breaking a rule in the task ("without
max()", "recursive", "no str()"). That last group is where test-based grading and a teacher
SHOULD disagree.

`kind` is our private label for the analysis. It is never shown to the marker:
`python -m ilm.grading.submissions` writes the blind marking pack (exercise + code only).
"""
from __future__ import annotations

import csv
import json

from ilm import config

S = []


def add(exercise, kind, code):
    S.append({"id": f"s{len(S) + 1:02d}", "exercise": exercise, "kind": kind, "code": code.strip("\n") + "\n"})


# ---- recursion-03 factorial
add("recursion-03", "correct", """
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)
""")
add("recursion-03", "rule_broken", """
def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
""")
add("recursion-03", "edge_case", """
def factorial(n):
    if n == 1:
        return 1
    return n * factorial(n - 1)
""")
add("recursion-03", "wrong", """
def factorial(n):
    if n == 0:
        return 0
    return n * factorial(n - 1)
""")
add("recursion-03", "broken", """
def factorial(n):
    if n == 0
        return 1
    return n * factorial(n - 1)
""")
# ---- modulo-02 is_even
add("modulo-02", "correct", """
def is_even(n):
    return n % 2 == 0
""")
add("modulo-02", "clumsy", """
def is_even(n):
    if n % 2 == 0:
        return True
    elif n % 2 == 1:
        return False
    else:
        return False
""")
add("modulo-02", "wrong", """
def is_even(n):
    return n % 2 == 1
""")
add("modulo-02", "prints", """
def is_even(n):
    print(n % 2 == 0)
""")
add("modulo-02", "edge_case", """
def is_even(n):
    return n % 2 == 0 and n > 0
""")
# ---- elif_else-01 grade
add("elif_else-01", "correct", """
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    return "F"
""")
add("elif_else-01", "edge_case", """
def grade(score):
    if score > 90:
        return "A"
    elif score > 80:
        return "B"
    elif score > 70:
        return "C"
    else:
        return "F"
""")
add("elif_else-01", "wrong", """
def grade(score):
    if score >= 70:
        return "C"
    elif score >= 80:
        return "B"
    elif score >= 90:
        return "A"
    else:
        return "F"
""")
add("elif_else-01", "clumsy", """
def grade(score):
    letter = "F"
    if score >= 70:
        letter = "C"
    if score >= 80:
        letter = "B"
    if score >= 90:
        letter = "A"
    return letter
""")
add("elif_else-01", "hardcoded", """
def grade(score):
    if score == 95:
        return "A"
    return "F"
""")
# ---- dictionaries-03 count_letters
add("dictionaries-03", "correct", """
def count_letters(word):
    counts = {}
    for ch in word:
        if ch in counts:
            counts[ch] += 1
        else:
            counts[ch] = 1
    return counts
""")
add("dictionaries-03", "wrong", """
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = 1
    return counts
""")
add("dictionaries-03", "slow", """
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] = word.count(ch)
    return counts
""")
add("dictionaries-03", "crashes", """
def count_letters(word):
    counts = {}
    for ch in word:
        counts[ch] += 1
    return counts
""")
add("dictionaries-03", "correct", """
def count_letters(word):
    result = {}
    for letter in word:
        result[letter] = result.get(letter, 0) + 1
    return result
""")
# ---- iterating_lists-03 largest
add("iterating_lists-03", "correct", """
def largest(nums):
    best = nums[0]
    for n in nums[1:]:
        if n > best:
            best = n
    return best
""")
add("iterating_lists-03", "rule_broken", """
def largest(nums):
    return max(nums)
""")
add("iterating_lists-03", "edge_case", """
def largest(nums):
    biggest = 0
    for n in nums:
        if n > biggest:
            biggest = n
    return biggest
""")
add("iterating_lists-03", "rule_broken", """
def largest(nums):
    return sorted(nums)[-1]
""")
add("iterating_lists-03", "wrong", """
def largest(nums):
    biggest = nums[0]
    for n in nums:
        if n < biggest:
            biggest = n
    return biggest
""")
# ---- try_except-02 to_int
add("try_except-02", "correct", """
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None
""")
add("try_except-02", "rule_broken", """
def to_int(s):
    if s.lstrip("-").isdigit():
        return int(s)
    return None
""")
add("try_except-02", "edge_case", """
def to_int(s):
    if s.isdigit():
        return int(s)
    return None
""")
add("try_except-02", "clumsy", """
def to_int(s):
    try:
        x = int(s)
    except:
        x = None
    return x
""")
add("try_except-02", "wrong", """
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return 0
""")
# ---- for_loops-01 sum_to
add("for_loops-01", "correct", """
def sum_to(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
""")
add("for_loops-01", "edge_case", """
def sum_to(n):
    total = 0
    for i in range(1, n):
        total += i
    return total
""")
add("for_loops-01", "rule_broken", """
def sum_to(n):
    return n * (n + 1) // 2
""")
add("for_loops-01", "rule_broken", """
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
        i += 1
    return total
""")
add("for_loops-01", "timeout", """
def sum_to(n):
    total = 0
    i = 1
    while i <= n:
        total += i
    return total
""")
# ---- recursion-05 is_palindrome
add("recursion-05", "correct", """
def is_palindrome(s):
    if len(s) <= 1:
        return True
    if s[0] != s[-1]:
        return False
    return is_palindrome(s[1:-1])
""")
add("recursion-05", "rule_broken", """
def is_palindrome(s):
    return s == s[::-1]
""")
add("recursion-05", "wrong", """
def is_palindrome(s):
    if len(s) <= 1:
        return True
    return s[0] == s[-1]
""")
add("recursion-05", "crashes", """
def is_palindrome(s):
    if len(s) == 1:
        return True
    return s[0] == s[-1] and is_palindrome(s[1:-1])
""")
add("recursion-05", "clumsy", """
def is_palindrome(s):
    if len(s) == 0:
        return True
    elif len(s) == 1:
        return True
    else:
        if s[0] == s[len(s) - 1]:
            return is_palindrome(s[1:len(s) - 1])
        else:
            return False
""")
# ---- while_loops-03 count_digits
add("while_loops-03", "correct", """
def count_digits(n):
    count = 0
    while n > 0:
        n = n // 10
        count += 1
    return count
""")
add("while_loops-03", "rule_broken", """
def count_digits(n):
    return len(str(n))
""")
add("while_loops-03", "wrong", """
def count_digits(n):
    count = 0
    while n > 10:
        n //= 10
        count += 1
    return count
""")
add("while_loops-03", "timeout", """
def count_digits(n):
    count = 0
    while n > 0:
        n / 10
        count += 1
    return count
""")
add("while_loops-03", "edge_case", """
def count_digits(n):
    count = 1
    while n > 10:
        n //= 10
        count += 1
    return count
""")
# ---- sets-02 unique_houses
add("sets-02", "correct", """
def unique_houses(students):
    houses = set()
    for s in students:
        houses.add(s["house"])
    return sorted(houses)
""")
add("sets-02", "wrong", """
def unique_houses(students):
    return list({s["house"] for s in students})
""")
add("sets-02", "clumsy", """
def unique_houses(students):
    result = []
    for s in students:
        if s["house"] not in result:
            result.append(s["house"])
    result.sort()
    return result
""")
add("sets-02", "wrong", """
def unique_houses(students):
    return sorted([s["house"] for s in students])
""")
add("sets-02", "crashes", """
def unique_houses(students):
    return sorted(set(students["house"]))
""")

SUBMISSIONS = S
OUT = config.PROJECT_ROOT / "data" / "grading"


def marking_pack() -> str:
    """Blind pack for the marker: exercise text + code only (no kind, no tests, no hints), shuffled."""
    from ilm.questions.validate import load_bank
    bank = {q.id: q for q in load_bank()[0]}
    import random
    L = []
    for s in random.Random(13).sample(SUBMISSIONS, len(SUBMISSIONS)):   # no "correct comes first" pattern
        L += [f"### {s['id']}", f"Exercise: {bank[s['exercise']].stem}", "```python", s["code"].rstrip(), "```", ""]
    return "\n".join(L)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "submissions.json").write_text(json.dumps(SUBMISSIONS, indent=1), encoding="utf-8")
    (OUT / "marking_pack.md").write_text(marking_pack(), encoding="utf-8")
    with (OUT / "reference_marks_TEMPLATE.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "mark", "reason"])
        for s in SUBMISSIONS:
            w.writerow([s["id"], "", ""])
    print(f"{len(SUBMISSIONS)} submissions -> {OUT}")


if __name__ == "__main__":
    main()
