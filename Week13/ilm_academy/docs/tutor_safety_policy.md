# Tutor safety policy

This policy covers the Socratic tutor in the student app: the **Ask the tutor** panel and the
hint ladder on exercises. Each rule names the code that enforces it and how it is measured.
**A rule that rests on the prompt alone is not counted as enforced.**

Code: `ilm/tutor/tutor.py`, `ilm/api/tutor_api.py`. Evaluation: `reports/tutor_eval/README.md`.

## 1. What the tutor is for

The tutor helps beginners learn Python from the course: CS50P and MIT 6.0001. It explains
concepts and guides a stuck student towards their own answer. It is not a solution service, a
general chatbot or a marker.

## 2. The rules

| # | rule | enforced by | measured |
|---|---|---|---|
| R1 | **Never give the solution** to an exercise, quiz or assignment, however it is asked | code in every reply is **run against the exercise's tests**; **near-copy check** (token shape within 20% edit distance of the solution, names hidden); **other-exercise check** (does the code solve another exercise?); MCQ and short replies must not contain the key | leak rate on 50 conversations plus held-out exercises |
| R2 | **Answer only from course sources**; say so when they do not cover the question | numbered sources in the prompt; **links are built by the server** from the cited numbers, so a link cannot be invented; an uncovered question gets a polite redirect | correctness (judge plus manual) |
| R3 | **Hints rise one rung at a time:** 1 a guiding question, 2 the concept, 3 a partial hint pointing at the student's code, 4 a worked example of a different problem | the server picks the rung, not the model. Rung 3 must contain a `___` blank; rung 4 must be a different problem and pass the near-copy check | rung-format rate |
| R4 | **Rules cannot be changed from the conversation** (role play, "I am the teacher", "ignore previous instructions", fake formats) | rule 3 of the system prompt, **and** R1's checks run whatever the model was persuaded to write | 15 jailbreak conversations |
| R5 | **Stay on Python and the course**; be warm, never mock a mistake | prompt; off-topic routing | refusal-right rate; judge tone score |
| R6 | **Fail honestly.** With no model (quota or network), say the tutor is unavailable | `TutorUnavailable` → HTTP 503 and a plain message; no cached or invented answer | — |
| R7 | **Match the student:** English or UrduLish (auto-detected or chosen), explanation depth by mastery | language detector; style by BKT level | language-match rate |

## 3. When a draft breaks a rule

1. **First draft leaks:** one retry, told *why* it leaked. For example: "your example is a renamed
   copy of the solution", or "your code solves the exercise `sum_to`".
2. **Second draft also leaks:** drop to rung 2. The concept explanation contains no code to leak.
3. **Rung 2 also fails:** a fixed safe message that points to the next rung or the lesson.

The student never sees a leaking draft. The usage log records that a leak was blocked.

## 4. Limits on use

| | |
|---|---|
| Per student | 8 requests a minute, 80 a day (`tutor_api.PER_MINUTE`, `PER_DAY`) → HTTP 429 with a plain message |
| Message size | 1,500 characters; code 20,000 characters |
| Who | logged-in students only. Teachers see aggregate safety numbers, not conversations |

## 5. Privacy

- **What the student types is not stored.** The log keeps metadata only: request kind, rung,
  language, whether a leak was blocked, and whether the topic was outside the course. Those feed
  the teacher's **Tutor safety** page.
- **Storing conversations is an open decision.** Letting teachers read conversations needs the
  student's consent and a retention period. Until both are decided, nothing is kept.
- **What goes to the model provider:** the course sources, the exercise and the student's code
  and message are sent to the Gemini API to produce a reply. The API key stays on the server and
  never reaches the browser or the sandbox.

## 6. Current results

| run | leaks (code checks) | jailbreaks resisted | fixed fallbacks | rung format |
|---|---|---|---|---|
| run 1 (prompt + test-running check) | 12% (6 of 51) | 93% | 0 | 95% |
| run 2 (+ near-copy, other-exercise) | **0%** (51) | **100%** | 4 | 77% |
| run 2, held-out exercises | **0%** (24) | n/a | 5 | 62% |
| run 3, new held-out exercises (+ informed retry, rung-2 drop) | **0%** (24) | n/a | **0** | 90% |

**What the results mean:**

- **"0%" is not "never".** 0 leaks in 24 held-out turns bounds the true rate at about 12%
  (rule of three).
- **The LLM judge does not catch leaks.** It flagged 0 of the 6 leaks found by the code checks
  in run 1, so leak numbers rest on the code checks only.

## 7. Known gaps (open)

| gap | example | next step |
|---|---|---|
| close in meaning, not in syntax | rung 4 shows `first_item` for an exercise asking for `last_item` | a vetted rung-4 example library per exercise, or a semantic check |
| over-refusal | "why is 0.1 + 0.2 not 0.3?" refused, though CS50P lecture 5 covers it | widen retrieval for float questions; re-measure |
| long conversations | each rung is a separate call; slow pressure over many turns is not tested | multi-turn jailbreak cases |
| rung 1 length | sometimes longer than its 2-sentence limit | a length check that retries |
| evaluation incomplete | runs 2-3 not judged; run 3 main set at 20 of 74 turns (free quota) | finish on a day with quota |

## 8. Incidents

If a teacher or student reports a leaked solution or an inappropriate reply:

1. Note the exercise, the rung and the time. The log has no conversation text, so ask the
   student for a screenshot.
2. Add the case to `ilm/tutor/eval_cases.py` (held-out if it is a new exercise).
3. Fix the **check**, not just the prompt.
4. Re-run `python -m ilm.tutor.evaluate`.

A fix counts only when the new case passes and the old ones still do.

## 9. Review

Re-run the evaluation after any change to the prompt, the model, the checks or the question
bank, and at least once each term. The policy owner is the course lead.
