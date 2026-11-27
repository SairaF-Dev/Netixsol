# Code feedback (Day 4 Task 3)

Feedback for 50 submissions; every page is in [feedback_pages.md](feedback_pages.md).

| check | result |
|---|---|
| hidden test inputs or answers shown to the student | 0 |
| with a lesson + video-timestamp link | 50 / 50 |
| with a code-quality tip (Ruff / Pylint / radon) | 9 |
| LLM explanations used / blocked as a leak | 0 / 0 |

## The one improvement chosen, by kind of submission

Priority: make it run > follow the task's rule > fix a wrong result > speed > code quality. Kinds are the private labels in `ilm/grading/submissions.py`.

| improvement | submissions (by kind) |
|---|---|
| code quality | clumsy 3, correct 1 |
| fix a wrong result | crashes 2, edge_case 6, hardcoded 1, prints 1, wrong 9 |
| follow the task | edge_case 1, rule_broken 7, wrong 1 |
| make it run | broken 1, crashes 1, timeout 2 |
| speed | clumsy 1, slow 1 |
| well done | clumsy 1, correct 10, rule_broken 1 |

## Limits

- With 1 visible test per exercise, most failures are hidden; the student learns how a hidden test failed (crashed with KeyError, returned None, wrong value), never its input.
- The tools do not judge readability: s14 (if-chain that overwrites a variable) gets no tip although a human marked it down for clarity. That is the LLM layer's job, or a teacher's.
- The LLM explanation is gated by the tutor's leak checks (passes the tests, near copy, another exercise's answer, mentions a hidden test). A leak in plain words would rely on that gate's limits (see reports/tutor_eval/README.md).
- Lesson links come from the course search on the concept; one link per concept, not per mistake.
