# Marking scheme used for `assistant_marks.csv`

**Who marked:** the coding assistant, at the project owner's request, not a teacher. Report
these as "assistant marks". A real teacher's marks (one row per submission in
`reference_marks_TEMPLATE.csv`) can replace or join them later.

**How:** blind. Marked from `marking_pack.md` only (exercise text + code, shuffled). The
private `kind` labels in `submissions.json` were not opened before marking. The scheme was
written before reading any submission.

| mark | meaning |
|---|---|
| 10 | correct on every reasonable input, follows every rule in the task, clean |
| 8-9 | correct, but clumsy, needlessly slow, or a small style issue |
| 5-7 | works for normal input but misses an edge case the task mentions or implies |
| 2-4 | wrong result, but the right idea is visibly there |
| 0-1 | does not run, or no meaningful attempt |

**Rule broken** (works, but ignores an explicit rule such as "recursive", "use a for loop",
"no str()", "without max()", "use try/except"): capped at 4, because the task tests that skill.

Judgement calls, so a second marker can check them:
- s24 `sorted(nums)[-1]`: 7. It follows the letter of "without max()" but sidesteps the loop
  the exercise practises.
- s22 `max(nums)`: 3, below the cap, because it shows no loop logic at all.
- s29 bare `except:`: 8. Correct and uses try/except, but catches every error.
- s30 returns 0 instead of None: 5. Wrong for half of the task's cases (invalid input).
