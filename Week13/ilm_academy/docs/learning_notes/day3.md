# Day 3 learning notes

## Part 1: Grounded tutor (RAG) (2026-11-27)

### The idea
RAG = Retrieval-Augmented Generation. Before the model answers, we **search the course**
and paste the best pieces into the prompt. The model answers from those pieces, not from
memory, so it explains things the way *our* lecture did and can point to the exact minute
of the video.

### Links can't be made up
The model sees numbered sources `[1]...[5]` and only tells us *which numbers* it used. Our
code turns the numbers into lesson and video-timestamp links. A URL the model writes itself
is never shown. **Rule: let the model choose; let code build anything that must be exact.**

### Adapting to the student
- Mastery (P(known) from Day 2): below 0.4 = new (analogy + tiny example + check question),
  0.4 to 0.8 = developing (example + common mistake), 0.8 and up = strong (edge case, deeper why).
- Language: 2 or more Roman-Urdu marker words ("kya", "hai", "bhai", ...) = reply in UrduLish.

## Part 2: Socratic hint ladder

| rung | gives | never gives |
|---|---|---|
| 1 guiding question | one question that points at the next thought | code, the answer |
| 2 concept pointer | the concept + where in the lesson to rewatch | code for this exercise |
| 3 partial hint | ONE line of their code with the key part as `___` | the rest |
| 4 similar example | a full example of a DIFFERENT problem, same idea | their solution |

### Defence in depth
A prompt is a request, not a guarantee. So every reply goes through a check that
**runs any code in it against the exercise's tests**. If it passes, it is a leak, even if
the function was renamed. On a leak: one retry with a stricter instruction, then a fixed
safe message. "Write factorial for me" in a free question is spotted by the function name
and sent to rung 1, so the free-question path can't be used to get the answer.

## Part 3: Evaluating the tutor

### Three layers, from most to least trustworthy
1. **Automatic checks**: code with no opinion. Leak (the test-running check), refusal
   (off-topic means no sources), routing, language, rung format, system prompt never repeated.
2. **LLM judge**: a *different, stronger* model (gemini-3.5-flash; the tutor is
   3.1-flash-lite) scores correctness, giveaway, rung-following, manipulation, pedagogy and
   tone with a written rubric. A model grading its own family tends to be too kind.
3. **Manual ratings** on a sample: tell us how far to trust layer 2.

### Why the judge is needed at all
The code check only catches *code that passes the tests*. A step-by-step recipe in plain
words ("loop over the words, if the length is more than n add one...") gives the answer away
too, but no test can run it. Only a reader, human or model, catches that.

### Write the test set before the first run
If you write tests after seeing the tutor's answers, you'll write the ones it already passes
without noticing. The 50 conversations were fixed in `ilm/tutor/eval_cases.py` first.

### What run 1 found: disguised copies
Run 1 leaked in 6 of 51 exercise turns, and the test-running check missed every one, because
none of the leaked code *passed the tests as written*:

| reply | why it is still the answer |
|---|---|
| `ScoreKeeper` / `points` / `add_point` | `Counter` with every name changed |
| `get_square`: `return int(s) ** 2` | delete `** 2` and it is `to_int` |
| `(x + y + z) / 2` | `average` with 3 changed to 2 |
| `return round((f - ___) * 5 / 9, 1)` | the whole one-line answer; the blank (32) is in the question |
| whole `to_int` with `int(s)` blanked | one blank in a complete function |
| recursive `sum_to` as the "different problem" | `sum_to` is ANOTHER exercise, and this passes its tests |

### The near-copy check (v2)
Turn code into its *shape*: names become `N`, strings `S`, and keywords and built-ins stay
(`int`, `range`). Then count the token edits needed to turn the reply into the solution. A
reply 20% or fewer edits away is the solution. A `___` blank may stand for up to 5 tokens for
free, because a blank hides one piece and what matters is how much of the *rest* is given away.
The 20% line was checked on pairs that are different problems by definition: across the
bank's 52 exercises, 2 of 2,652 pairs fall under it.

### Syntax is not meaning
On held-out set 2, `first_item` (`items[0]`) was offered as the example for `last_item`.
Its syntax is far from the solution, but its logic is one character away. A shape comparison
can't see that; a reader (the judge, or a person) can. That is why there are three layers.

### Safety vs helpfulness
v2's stricter prompt made rung 4 stop showing examples, and 5 of 24 held-out replies were the
fixed "I won't give the solution" message. It was safe but unhelpful. v3 keeps the same
checker (so the same safety) and fixes helpfulness: the retry says *why* the draft leaked, and
a rung that keeps leaking drops to the concept rung instead of the fixed message. On unseen
exercises the fixed message went from 5 to 0.
**Rule: put safety in a checker that gates the output. Then you can tune the prompt for
helpfulness without risking safety.**

### Held-out sets get used up
Held-out set 1 tested v2. Its results shaped v3, so it no longer counts as unseen for v3, and
v3 is tested on held-out set 2. Once you have changed something because of a test set, that
set can't tell you whether the change generalises.

### "0 leaks in 50" is not "never leaks"
**Rule of three:** if something happened 0 times in n tries, the true rate is probably
(95%) below 3/n. 0 in 50 means "below about 6%", not "0%". More tests make the bound tighter.

### Check yourself
1. Why are the tutor's links built from source numbers instead of taken from the model's text?
2. A hint passes the leak check, but the student could submit it after deleting one line.
   Which layer should catch that, and why can't running the tests?
3. The tutor scores 0 leaks on the 50 conversations after you fixed the 6 it failed. Why is
   that weak evidence, and what would be strong evidence?
4. v2 was perfectly safe. Why was it still worse than v3?
