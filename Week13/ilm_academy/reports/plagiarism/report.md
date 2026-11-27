# Code similarity & plagiarism review report (Day 4 Task 5)

> **Policy:** `Possible copying - needs teacher review`. Flags go to a teacher queue with a side-by-side diff; no student mark is ever lowered or penalised automatically.

Reproduce: `python -m ilm.grading.plagiarism` (dataset built with `python -m ilm.grading.plagiarism_data`, embedding model `BAAI/bge-small-en-v1.5`).

## Dataset & exercise-level split

- **Exercises:** 12 bank coding exercises (`6` dev: csv_files-03, dictionaries-03, floats-04, iterating_lists-01, recursion-05, sets-02; `6` test: elif_else-01, iterating_lists-03, modulo-02, nested_data-02, nested_loops-02, while_loops-04).
- **Submissions:** 140 (72 independent honest solutions in varied styles, 68 planted disguised copies; every submission passes the bank unit tests).
- **Pairs:** 375 dev pairs (35 copied) and 375 test pairs (34 copied). All thresholds and logistic weights were fitted on **dev** only; **test** was scored once.

## Test split results (scored once, thresholds frozen on dev)

| Detector | Cut-off (dev) | Precision | Recall | F1 | PR-AUC | FP (short-ex FP) | Missed copies |
|---|---:|---:|---:|---:|---:|---:|---:|
| Token fingerprint (raw) | 0.357 | 0.700 | 0.618 | 0.656 | 0.705 | 9 (1) | 13 |
| Token fingerprint (exercise-adjusted) | 0.851 | 0.578 | 0.765 | 0.658 | 0.782 | 19 (0) | 8 |
| AST sequence (raw) | 0.786 | 0.657 | 0.676 | 0.667 | 0.739 | 12 (6) | 11 |
| AST sequence (exercise-adjusted) | 1.092 | 0.551 | 0.794 | 0.651 | 0.798 | 22 (0) | 7 |
| Embedding bge-small (raw) | 0.954 | 0.778 | 0.618 | 0.689 | 0.731 | 6 (0) | 13 |
| Embedding bge-small (exercise-adjusted) | 1.321 | 0.611 | 0.647 | 0.629 | 0.741 | 14 (0) | 12 |
| Combined logistic (raw only) | 0.342 | 0.811 | 0.882 | 0.845 | 0.890 | 7 (1) | 4 |
| Combined logistic (exercise-adjusted) | 0.634 | 0.893 | 0.735 | 0.806 | 0.942 | 3 (0) | 9 |

## In a real class: read this before trusting the precision above

The benchmark is 9% copied pairs. A real class has n(n-1)/2 pairs per exercise but only a few copies, so the false-alarm rate per honest pair (**0.88%** here) decides how much work a threshold creates. Assumption: copied pairs per exercise as listed; same false-alarm rate and recall as the test split.

| students | pairs per exercise | copied pairs (assumed) | expected flags | true | false | precision |
|---:|---:|---:|---:|---:|---:|---:|
| 30 | 435 | 2 | 5.3 | 1.5 | 3.8 | 28% |
| 100 | 4,950 | 5 | 47.2 | 3.7 | 43.5 | 8% |
| 500 | 124,750 | 15 | 1108.4 | 11.0 | 1097.4 | 1% |

So a threshold does not scale: at 100 students most flags would be innocent pairs.

## Ranked review queue (what the teacher view now shows)

Instead of every pair over a cut-off, the teacher sees the **top k pairs of each exercise** (k = 5, chosen on dev). The work is fixed (k pairs per exercise) whatever the class size, and the teacher reviews the most similar pairs first. Test split:

| k per exercise | pairs reviewed | real copies among them | precision@k | recall@k |
|---:|---:|---:|---:|---:|
| 1 | 6 | 6 | 100% | 18% |
| 3 | 18 | 18 | 100% | 53% |
| 5 | 30 | 29 | 97% | 85% |
| 10 | 60 | 34 | 57% | 100% |

Read precision@k with the base rate in mind: each test exercise has about 6 planted copies, so a top-5 queue can be almost all copies. With 1 copy on an exercise, a top-5 queue is at most 20% copies. **The queue fixes the teacher's workload, not the base rate.**

Where does a real copy rank? 94% of test copies score above every honest pair of their exercise, but there are only 41-60 honest pairs per exercise here. A class of 100 has ~4,950, and this data cannot say how many of those would outscore a copy. Measuring that needs a real class-sized set of honest submissions.

Each student's single most similar pair is in `report.json` (`student_max_scores_test_top15`) for a per-student view.

## Dev split reference (used to choose cut-offs and combined weights)

| Detector | Cut-off | Precision | Recall | F1 | PR-AUC | FP (short-ex FP) |
|---|---:|---:|---:|---:|---:|---:|
| Token fingerprint (raw) | 0.357 | 0.815 | 0.629 | 0.710 | 0.729 | 5 (1) |
| Token fingerprint (exercise-adjusted) | 0.851 | 0.694 | 0.714 | 0.704 | 0.773 | 11 (1) |
| AST sequence (raw) | 0.786 | 0.808 | 0.600 | 0.689 | 0.679 | 5 (1) |
| AST sequence (exercise-adjusted) | 1.092 | 0.560 | 0.800 | 0.659 | 0.724 | 22 (3) |
| Embedding bge-small (raw) | 0.954 | 0.788 | 0.743 | 0.765 | 0.779 | 7 (1) |
| Embedding bge-small (exercise-adjusted) | 1.321 | 0.735 | 0.714 | 0.725 | 0.759 | 9 (1) |
| Combined logistic (raw only) | 0.342 | 0.821 | 0.914 | 0.865 | 0.890 | 7 (1) |
| Combined logistic (exercise-adjusted) | 0.634 | 0.935 | 0.829 | 0.879 | 0.919 | 2 (1) |

## How much per-exercise false-positive control helps

On short or constrained exercises (`modulo-02` `is_even`, `floats-04` `to_celsius`), independent honest students write almost identical 1-2 line code, and `bge-small-en-v1.5` gives high cosine similarity to any two solutions solving the same task. Adjusting each pair against its exercise's median/spread and canonical short-solution overlap (without using any labels) changes test results as follows:

- **Token fingerprint:** F1 `+0.002`, PR-AUC `+0.077`, false positives `9 -> 19` (on short exercises: `1 -> 0`).
- **AST sequence:** F1 `-0.016`, PR-AUC `+0.059`, false positives `12 -> 22` (on short exercises: `6 -> 0`).
- **Embedding:** F1 `-0.060`, PR-AUC `+0.009`, false positives `6 -> 14` (on short exercises: `0 -> 0`).
- **Combined logistic detector:** F1 `-0.039`, PR-AUC `+0.052`, false positives `7 -> 3` (on short exercises: `1 -> 0`).

## Which disguises each detector catches vs misses (test split, `caught / total`)

| Disguise | Token (adj) | AST (adj) | Embedding (adj) | Combined |
|---|---:|---:|---:|---:|
| `comments_whitespace` | 6/6 (100%) | 6/6 (100%) | 2/6 (33%) | 5/6 (83%) |
| `rename` | 6/6 (100%) | 6/6 (100%) | 0/6 (0%) | 6/6 (100%) |
| `reorder_lines` | 4/5 (80%) | 4/5 (80%) | 5/5 (100%) | 4/5 (80%) |
| `for_to_while` | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| `dead_code` | 4/6 (67%) | 5/6 (83%) | 6/6 (100%) | 4/6 (67%) |
| `split_merge` | 1/6 (17%) | 1/6 (17%) | 4/6 (67%) | 1/6 (17%) |

### Why each detector misses what it misses

- **Token fingerprint (winnowed 5-grams):** catches `100%` of `comments_whitespace` and `rename` copies, but contiguous 5-token windows shatter on `split_merge` (`1/6`, 17%), interleaved `dead_code` (`4/6`, 67%) and `reorder_lines` (`4/5`, 80%).
- **AST sequence:** ignores names, constants and formatting (`100%` on `rename` and `comments_whitespace`) and handles `dead_code` better than k-grams (`5/6`, 83%, because `SequenceMatcher` skips inserted nodes), but drops sharply on `split_merge` (`1/6`, 17%), where one nested expression turns into several `Assign` statements, and misses `1/5` `reorder_lines`.
- **Code embeddings (`BAAI/bge-small-en-v1.5`):** catch semantic/lexical carry-over on `dead_code` (`6/6`), `reorder_lines` (`5/5`) and `split_merge` (`4/6`, 67%), but `bge-small-en-v1.5` is a general English retrieval model rather than a code syntax model: full variable `rename` (`0/6`, 0%) and added comments/docstrings (`2/6`, 33%) pull the adjusted embedding score below the dev cut-off.
- **Combined logistic detector:** reaches `0.942` PR-AUC and `0.893` precision (`3` false positives out of `341` honest pairs, `0` on short exercises), catching `25/34` copies (`73.5%` recall); `5` of the `9` misses are `split_merge` rewrites where temporary variables reshape both k-grams and AST nodes.

## Honest limits

1. **One-line exercises have no safe fingerprint.** When the natural answer is `return n % 2 == 0` or `return round((f - 32) * 5 / 9, 1)`, a copied 1-liner and an honest 1-liner are byte-for-byte equivalent up to variable names. Suppressing false alarms there inevitably misses trivial-exercise copies unless the copy carries unusual structure or dead code.
2. **Synthetic disguises vs real collusion.** Our 140 submissions pass real unit tests and cover six classic transformations, but real students also translate solutions via an LLM or collaborate verbally, producing semantically equivalent code with fresh structure that all three detectors can miss.
3. **Cohort baseline needs a batch.** Per-exercise median/MAD normalisation assumes at least ~8-10 submissions on the exercise (and that fewer than half the pairs colluded). On the very first 2-3 submissions, only the reference-solution baseline is stable.
4. **Similarity is not proof of copying.** Two students who watched the same CS50P lecture a minute before submitting often write the lecturer's exact pattern independently. That is why every output uses *"Possible copying - needs teacher review"* in [flagged_pairs.html](flagged_pairs.html) and leaves the decision to a human.
5. **The benchmark is not real students.** All honest solutions were written by one author in one session, so they may be more alike, or alike in different ways, than real students' code. The disguises were designed by the same author as the detectors, so they test what the detectors were built to catch. A real evaluation needs real submissions with confirmed cases.
6. **Base rate.** The precision in the main table holds only at the benchmark's 9% copied pairs; see "In a real class" above. Use the ranked queue, not the threshold.
