# Test-based grading vs reference marks (Day 4 Task 2)

50 submissions (10 bank exercises x 5), graded in the Docker sandbox. Reference: assistant marks (blind, scheme in data/grading/marking_scheme.md), NOT a teacher.

## Agreement, adding one part at a time

| grader | MAE (marks /10) | within 1 | within 2 | Spearman | quadratic kappa | grader - ref |
|---|---|---|---|---|---|---|
| bank tests only | 2.03 | 48% | 70% | 0.731 | 0.641 | +1.26 |
| + edge tests | 1.95 | 48% | 70% | 0.753 | 0.662 | +1.05 |
| + rule checks | 0.99 | 66% | 88% | 0.922 | 0.915 | +0.09 |
| + speed check (final) | 0.95 | 68% | 88% | 0.926 | 0.917 | +0.05 |

Final grader: 1 timed-out runs re-run test by test, 10 rule violations capped at 4, 2 correct-but-slow (-1).

## By kind of submission (labels from submissions.py, used only after marking)

| kind | n | grader mean | reference mean | MAE |
|---|---|---|---|---|
| broken | 1 | 0.0 | 1.0 | 1.0 |
| clumsy | 5 | 9.8 | 8.8 | 1.0 |
| correct | 11 | 10.0 | 10.0 | 0.0 |
| crashes | 3 | 3.2 | 3.3 | 1.17 |
| edge_case | 7 | 5.0 | 5.1 | 1.26 |
| hardcoded | 1 | 2.7 | 1.0 | 1.7 |
| prints | 1 | 0.0 | 3.0 | 3.0 |
| rule_broken | 8 | 4.8 | 4.0 | 0.75 |
| slow | 1 | 9.0 | 8.0 | 1.0 |
| timeout | 2 | 0.8 | 2.0 | 1.15 |
| wrong | 10 | 3.1 | 3.4 | 1.53 |

## Where they disagree by more than 2 marks

- **s04** (recursion-03, wrong): grader 0.0, reference 3.0. Reference: base case returns 0 so every result is 0; recursive structure is right. Grader: 0/6 tests.
- **s09** (modulo-02, prints): grader 0.0, reference 3.0. Reference: prints instead of returning (returns None); the check itself is right. Grader: 0/8 tests.
- **s24** (iterating_lists-03, rule_broken): grader 10.0, reference 7.0. Reference: correct and avoids max() literally but sidesteps the loop the exercise practises; slower (sorting). Grader: 6/6 tests.
- **s43** (while_loops-03, wrong): grader 0.0, reference 3.0. Reference: starts at 0 and loops while n > 10: every count is one too low. Grader: 0/7 tests.
- **s47** (sets-02, wrong): grader 8.0, reference 5.0. Reference: removes duplicates but does not sort (the task asks for alphabetical order). Grader: 4/5 tests.
- **s32** (for_loops-01, edge_case): grader 1.7, reference 4.0. Reference: range(1, n) stops early: misses n itself for every n >= 1. Grader: 1/6 tests.

## What the table says

- **Tests alone over-mark** (+1.3 on average): code that ignores the task's rule (a loop where recursion is asked, `max()`, `str()`) still passes every test. The AST rule check brings agreement from kappa 0.64 to 0.92; edge tests and the speed check add little on these 50.
- **The big remaining gaps are 'right idea, wrong result'**: off-by-one loops or printing instead of returning fail every test (grader 0), while a human gives 3-4 for the visible idea. Tests cannot see ideas; that is what Task 3's feedback is for, and why a human reviews low marks.
- **Other gaps are policy or weak tests**: `sorted(nums)[-1]` respects the letter of "without max()" (grader 10, human 7), and an unsorted `set` result passes 4 of 5 tests because few tests check order.
- Same code, same mark: the sandbox fixes `PYTHONHASHSEED`, so set/dict order (and a grade that depends on it) cannot change between runs.

## Limits

- The reference is the assistant's blind marks, not a teacher's. Fill `data/grading/reference_marks_TEMPLATE.csv` with a teacher's marks and rerun to replace it.
- The edge tests were written after reading the submissions, so the 'edge' rows may fit these 50 better than new ones. 'bank tests only' is the clean measurement.
- Rule checks and the marking scheme follow the same course policy (a broken rule caps at 4), so agreement on rule-breaking submissions is partly by design; the table shows how much they add.
- Partial marks are the share of tests passed. A teacher also gives credit for a visible right idea (e.g. code that crashes on every call), which tests cannot see.
