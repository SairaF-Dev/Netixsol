# Day 1 learning notes

## Part 0: Setup (2026-11-26)

### What we did and why
| Step | Why it matters |
|---|---|
| Separate venv on Python 3.11 | ML libraries publish wheels for older Pythons first; 3.14/3.15 would fail to install. A venv keeps this project's versions apart from other weeks. |
| `requirements.txt` + `requirements.lock.txt` | The first says *what* we need, the second *exactly which versions worked*. Docker/Codespaces install the lock file, so they don't get surprise upgrades. |
| `ilm/config.py` holds all paths | One place to change; tests can redirect paths with env vars. |
| `tests/conftest.py` sets temp paths first | Tests must never overwrite real data. A test checks this rule itself. |
| `scripts/check_env.py` | "pip install succeeded" does not prove a library *imports*; this checks every one. |

### Bugs we hit and how we found them
1. **A command hung.** A stray `cat > file` with no input waited for the keyboard forever.
   *Debug question:* "What is this process waiting for?"
2. **Retrieval returned the wrong chunk.** The query was "my function keeps calling itself"; the result was "functions", the expected one "recursion".
   - Hypothesis A: the distance metric (L2 vs cosine). **Rejected.** The vectors already had length 1, so both give the same ranking.
   - Hypothesis B: the small model leans on shared words ("function"). **Supported.** MiniLM failed and bge-small passed.
   - We did **not** reword the query to make the test pass. We switched models, and the final choice will come from a proper benchmark.
3. **Temp folder not deleted.** Chroma's PersistentClient keeps its SQLite file locked on Windows. The smoke test now uses the in-memory client.

### Check yourself (answer in your own words below)
1. Why does the project use `requirements.lock.txt` in Docker and not `requirements.txt`?
2. If I set `ILM_DATA_DIR=D:\tmp\x` before running a script, what changes?
3. Two vectors both have length 1. Why do cosine similarity and L2 distance then rank results identically?
4. Why is "it passed on 3 sentences" not evidence that an embedding model is good?
5. What does VAD do in Whisper, and why did 10 seconds of silence give 0 segments?

**My answers:**

1.
2.
3.
4.
5.

## Part 4: Question bank (2026-11-26)

### What we did and why
- One format (`ilm/questions/schema.py`) for three question types: MCQ, short answer, coding.
  Day 2 (IRT), Day 3 (generation, calibration) and Day 4 (grading) all read this same format.
- Every question carries: main concept, difficulty 1-5 (OUR GUESS, a "prior"; IRT measures the
  real one on Day 2), and a Bloom's level (remember, understand, apply, analyze, evaluate, create).
- Every wrong MCQ option names the misconception behind it, so a wrong answer tells the tutor
  WHAT to teach, not just THAT the student is wrong.
- The lesson link is not stored on the question: it comes from the concept's `taught_in`.
  One source of truth, so the two can never disagree.

### "Don't trust the author": the validator RUNS the answers
- "What does this print?": the snippet is executed and the marked option must be the real output.
- Coding questions: the reference solution must pass all tests, AND a do-nothing stub and a
  typical wrong solution (`buggy`) must FAIL at least one test. A test nothing can fail grades nothing.
- Each run is a separate process with a 5-second timeout (protects against our own infinite loops).
  This is NOT a sandbox for student code; that is Day 4.
- Two different comparisons: checking AUTHORS is exact (case matters: "Hello World" is not
  "hello world"); grading STUDENTS' short answers is lenient on case and spacing.

### Bugs we hit
- YAML: an unquoted `{"a": 2}` or `lambda n: n` inside a value is read as a key. The validator
  first CRASHED on it; now it reports file + line and keeps checking the other files.
- A validator that passes everything proves nothing: `tests/test_questions.py` plants each kind
  of mistake (wrong answer, weak tests, broken solution, typo in a field, infinite loop) and checks
  that it is caught.

### Check yourself
6. Why is difficulty written down now if IRT will measure it on Day 2 anyway?
7. In `square(n)`, the tests `square(2) == 4` and `square(0) == 0` pass for the right solution.
   Why are they still bad tests? (Hint: try `n * 2` and `n + n`.)
8. Pick any MCQ in `bank/cs50p-l2.yaml`. For each wrong option, could a real student believe its
   misconception? Write one better distractor if not.
9. About 40 MCQs (e.g. "what is self?") cannot be checked by running code. How could we still
   catch a wrong answer key in them? (Hint: Day 2 data.)
