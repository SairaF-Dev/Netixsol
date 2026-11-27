# Day 4 learning notes

## Plagiarism detection: flag for a human, never auto-punish (2026-11-27)

### Why code similarity is not an automatic verdict
Two submissions that look alike can mean two completely different things:
1. One student copied from another (or both copied the same source) and tried to hide it.
2. The exercise is short (`is_even`, `to_celsius`) or follows a pattern taught ten minutes earlier
   in the lecture, so honest students naturally wrote almost the same code.

No similarity score can tell those apart with certainty. Every output in `ilm/grading/plagiarism.py`
and `reports/plagiarism/flagged_pairs.html` therefore says **"Possible copying - needs teacher
review"** and never changes a grade automatically.

### Three ways to compare two programs

| detector | what it looks at | catches well | fooled by |
|---|---|---|---|
| **Token fingerprint (MOSS winnowing)** | Python tokens (`tokenize`) with comments/whitespace dropped, user names turned into `V` and literals into `0`/`S`, hashed in 5-token windows and thinned by rightmost-minimum winnowing | renamed variables (`6/6`), changed comments/whitespace (`6/6`) | splitting/merging expressions (`1/6`), dead lines inserted inside windows (`4/6`) |
| **AST sequence** | the syntax tree (`ast`) walked in preorder with variable names, constants and docstrings removed, matched with `SequenceMatcher` | renames (`6/6`), formatting (`6/6`), inserted dead code (`5/6`) | splitting one nested expression into several `Assign` lines (`1/6`) |
| **Embeddings (`bge-small-en-v1.5`)** | dense meaning/word vector of the code, compared by cosine similarity | dead code (`6/6`), reordered lines (`5/5`), split/merged expressions (`4/6`) | renaming every variable (`0/6` after exercise adjustment) and heavy comment changes (`2/6`) |

**Takeaway:** structure detectors (tokens, AST) ignore variable names and comments completely,
while text embeddings rely on words and catch structure edits where names stay familiar. Putting
all three into a small logistic model raised test PR-AUC from `0.782-0.798` (single detectors) to
**`0.942`** (`0.893` precision, `0.735` recall).

### False-positive control on short exercises
On `modulo-02` (`def is_even(n): return n % 2 == 0`), two honest students who only use different
parameter names (`n` vs `num`) score **`1.00`** on raw token similarity and **`1.00`** on raw AST
similarity. On raw AST similarity, `6` of the `12` false positives in our test split came from
that single two-line exercise.

How we adjust each pair **without using any ground-truth labels**:
1. **Compare against the same exercise's cohort:** compute the median and robust spread (MAD/IQR)
   of all pairs on that exercise. When almost everyone's code looks alike, the baseline is high,
   so matching it is unremarkable (`z` near `0`).
2. **Discount canonical one-liners:** on very short submissions (fewer than 24 tokens), overlap
   explained by both students matching the bank's reference solution is treated as expected, and
   tiny token counts receive lower credibility (`n / (n + 8)`).

On the held-out test exercises, this dropped short-exercise false positives to **`0`** across
every detector and cut total false positives in the combined detector from `7` to `3` while lifting
PR-AUC from `0.890` to `0.942`.

### Split by exercise, not by pair
If two pairs from the same exercise sit in `dev` and `test`, the model has already seen that
exercise's length and style distribution during tuning. Splitting the 12 bank exercises `6` dev /
`6` test (`ilm/grading/plagiarism_data.py`) tests whether thresholds picked on one set of
assignments still work on next Sunday's new assignments.

### Never render student code into HTML without escaping
A teacher review page opens student submissions in a real browser. A student who writes
`msg = "<script>...</script>"` in a string literal would run JavaScript in the teacher's browser
if code were pasted straight into HTML. `render_flagged_html` passes every line, identifier and
title through `html.escape(..., quote=True)` before wrapping matched line numbers.

### Check yourself
1. Two students both submit `def to_celsius(x): return round((x - 32) * 5 / 9, 1)` with different
   variable names (`f` vs `temp`). Their token and AST similarity is `1.0`. Why shouldn't that
   automatically count as copying?
2. Why did renaming every variable drop the `bge-small-en-v1.5` z-score recall to `0/6` while
   leaving token and AST similarity at `1.00`?
3. Why must we split `dev` and `test` by **exercise** rather than randomly shuffling pairs?
4. On the test set, `split_merge` copies were the hardest disguise to catch (`1/6` for token and
   AST). What changes inside a 5-token window and an AST when `return round((f - 32) * 5 / 9, 1)`
   is rewritten as three separate assignment lines?

## The base-rate trap (added after review)

The detector scored **89% precision** on the benchmark. That sounds like "9 out of 10 flags
are real". It isn't, in a real class.

- Pairs grow with the **square** of the class: 100 students = 100 x 99 / 2 = **4,950 pairs**
  per exercise. Copies stay few: maybe 5.
- The benchmark had 9% copied pairs; a real class has about 0.1%.
- Our false-alarm rate is 0.88% per honest pair. 0.88% of 4,950 is **about 44 innocent pairs**,
  next to about 4 real ones. Precision falls to **about 8%**.

**Rule: precision depends on how common the thing is.** A test that is 99% accurate still
flags mostly innocent people when the thing it looks for is rare (the same maths as medical
screening).

What we do instead:
1. **Report the false-alarm rate per honest pair**, and expected flags for 30 / 100 / 500
   students, not just precision.
2. **A ranked queue instead of a threshold:** the teacher sees the 5 most similar pairs of each
   exercise. The work stays fixed however big the class is. It does not fix the base rate: with
   1 real copy on an exercise, at most 1 of the 5 is a copy.
3. **Say what the data can't show.** Each test exercise has about 50 honest pairs; a class of 100
   has about 4,950. Whether a real copy still ranks in the top 5 among thousands needs a real
   class's submissions.

### Check yourself
1. Why does the same detector have higher precision for 30 students than for 500?
2. Why is a top-5 queue fairer to the teacher than "every pair over 0.63"?
3. The benchmark's honest solutions were all written by one author. Why might that make the
   detector look better, or worse, than it really is?
