# Day 2 learning notes

## Part 1: Knowledge tracing (2026-11-26)

### The idea
Knowledge tracing = estimate what a student knows from their past answers, and check the
estimate by **predicting their next answer**.

### The one rule
To predict answer 10, a model may use answers 1-9, never answer 10. The **future-blind test**
flips one answer and checks that the model's prediction for that answer (and everything
before it) does not change. A deliberately cheating model fails it, which proves the test works.

### Fair comparison
- **Student-level split**: every student is wholly in train, validation or test.
- Settings are chosen on **validation** students. **Test** students are scored once per model.
- Baselines first: a fancy model is only worth it if it beats "the student's accuracy so far".

### Scores
| score | question | scale |
|---|---|---|
| AUC | pick a right and a wrong answer at random: how often does the model rank the right one higher? | 0.5 coin flip, 1.0 perfect |
| accuracy | how often is "p >= 0.5" the right call? | always saying "right" already gets 66% here |
| RMSE | how far off are the probabilities? | lower is better |

### The models
| model | how it thinks | in one line |
|---|---|---|
| PFA | weighted tally per skill of earlier successes and failures | logistic regression; a teacher can read the weights |
| BKT | two hidden states per skill: knows / does not know yet | 4 numbers per skill: prior, learns, guesses, slips |
| DKT | an LSTM keeps a running "memory" of all answers | can discover that skills are related |
| SAKT | attention: which past answers matter for THIS question? | the idea behind transformers |

### Engineering lessons
- **Stop patching, look upstream.** pyBKT 1.4.3 breaks on NumPy 2 and new scikit-learn.
  One small patch is fine; a chain of patches is a private fork. The maintainers had already
  fixed both (unreleased), so we pin their exact commit in requirements.txt.
- **If the best setting is at the edge of the grid, extend the grid.** "Student so far"
  looked best at m=20 (the largest tried); the real optimum was 40-80.
- **Code that re-does something already true confuses readers.** Removed a line in deep.py
  that "carried" a token that the shifting had already put there.

- **Windows + worker processes need `if __name__ == "__main__":`.** pyBKT trains skills in
  parallel processes; on Windows each worker re-imports the main script. My tuning script was
  piped in on stdin, which cannot be re-imported, so every worker crashed and wrote 7.7 MB of
  errors. The small test data never used parallel workers, so the tests could not catch it.
  Fix: tuning lives in `python -m ilm.tracing.tune`, behind the guard (same idea as question
  `own_modules-01` in our bank). Then I checked the new run actually stayed quiet.

### Check yourself
1. "Always predict right" gets 66% accuracy. Why does that make accuracy a weak way to
   compare models, and why does AUC not have this problem?
2. Why are the test students used only once per model?
3. BKT's "slip" and "guess": give a Python-course example of each.

## Part 2: IRT and question health (2026-11-26)

### The idea
Knowledge tracing asks "what does the STUDENT know?". IRT asks "what is the QUESTION like?".
- ability (theta): one number per student
- difficulty (b): the ability needed for a 50/50 chance
- discrimination (a): how sharply the question separates strong from weak students
- 1PL: every question has the same a. 2PL: each question has its own a.

### Finding bad questions
- a near 0: strong and weak students do equally well, so the question measures nothing.
- a clearly NEGATIVE: strong students do WORSE. Almost always a wrong answer key.
  This is how the ~40 MCQs that running code cannot check will be checked.

### Result on the simulated course (IRT saw only right/wrong answers)
- Found 12 of 12 planted bad questions that were asked; 1 false alarm (a = 0.27, near the line).
- 30 of 225 questions are NEVER asked by the fixed path (3 per concept), including 2 planted
  bad ones. The adaptive engine can use them.
- Difficulty recovered only moderately (rank correlation 0.68): the simulator also has
  guessing, concept knowledge and learning, which 2PL does not model. Useful, but simplified.
- My 1-5 difficulty guesses vs IRT: 0.57. Informative, far from exact (Day 3 calibration).

### Bugs and fixes
- **The scale drifted**: a*(theta - b) is unchanged if every theta shrinks 3x and every a grows 3x.
  The fitted a came out ~3x too big. Fix: rescale abilities to mean 0, spread 1 afterwards
  (what every IRT tool does).
- **A wrong-key question got stuck at a = +0.33**: starting from a = +1, the optimiser escaped
  by pushing b to -5.9. Fix: write questions as slope*theta + intercept, start from a 1PL fit,
  and run until it really converges.
- **Crying wolf**: noise put two useless questions at a = -0.1, and they were sent for
  answer-key review. Now "answer key" needs a < -0.3; near zero is "weak".
- **A label that hid a finding**: "too few answers to judge" really meant "never asked".

### Check yourself
4. A question has a = -0.9. What would you check first, and why?
5. Why does IRT use only each student's FIRST answer to a question?
6. Why can a model find every bad question and still estimate difficulty only roughly?

## Part 3: Mastery per concept, and debugging long jobs (2026-11-26)

### Mastery = BKT's P(knows the concept)
After each answer, two steps:
1. **Evidence (Bayes' rule).** A right answer raises the belief, but less when guessing is easy.
   A wrong answer lowers it, but less when careless slips are common.
2. **Learning.** Practice itself may have taught them: add `learns` x the remaining doubt.
Mastered when P(knows) >= 0.95 (the classic threshold). *Later changed: see Part 5.*
Our 10-line tracker (`ilm/tracing/mastery.py`) gives the same predictions as pyBKT to
4 decimals, so the adaptive engine can use it directly.

### Debugging jobs that run for a long time
- **A silent hour can mean slow, stuck or broken; from outside they look the same.** Every
  long job now prints one line per epoch.
- **Look at each process, not just "is it running".** BKT's 12 worker processes had used
  1-2 CPU-seconds each in 25 minutes: idle, waiting for each other (a deadlock), not slow.
  Fix: pyBKT with parallel=False.
- **Measure before guessing.** One DKT epoch takes 7 seconds in the foreground, yet the
  background job ran for over an hour without finishing one setting. Running BKT and DKT
  together oversubscribed the CPU (10 PyTorch threads fighting other processes).
  Fix: one heavy job at a time.

### Check yourself
7. A student answers 3 loops questions right in a row. Why does their mastery go up LESS
   on a 4-option MCQ than on a coding question?
8. A background job has printed nothing for an hour. Name three different things that
   could be happening, and how you would tell them apart.

## Part 4: Final knowledge-tracing scores (test students, scored once)

| model | AUC | accuracy | RMSE | train time |
|---|---|---|---|---|
| DKT (LSTM, 128) | **0.770** | **0.736** | **0.423** | 4 min |
| SAKT (attention, 128) | 0.747 | 0.722 | 0.432 | 8 min |
| BKT with forgetting | 0.738 | 0.717 | 0.436 | 77 min |
| PFA | 0.736 | 0.713 | 0.436 | 2 s |
| student's accuracy so far | 0.711 | 0.691 | 0.448 | 0 |
| skill average | 0.624 | 0.658 | 0.467 | 0 |
| everyone's average | 0.500 | 0.646 | 0.478 | 0 |

- Every real model beats every baseline; DKT wins clearly.
- SAKT beats DKT in many papers but not here: ~2,700 training students suit the simpler LSTM.
- BKT and PFA tie, but BKT's numbers MEAN something (knows / learns / guesses / slips), so
  BKT drives mastery in the adaptive engine; accuracy is not the only reason to pick a model.
- "Everyone's average" is 64.6% accurate with AUC 0.500: accuracy alone can fool you.

## Part 5: A confident number with little evidence, and the adaptive engine

### The bug the simulator caught
When the tracker said "at least 95% sure they know it", only 44.5% truly knew it. Cause: the
history has 3 answers per concept, too few for pyBKT to tell "learned fast" from "got lucky";
some concepts got learn rates near 1, so 1-2 right answers jumped P(known) past 0.95.

### Fixes
1. **Earn mastery with evidence:** P(known) >= 0.95 AND 3 right in a row (ASSISTments' rule).
2. **Lose it only when P(known) drops below 0.95 again** (hysteresis, like a thermostat):
   one careless slip no longer sends a student back to relearn a concept.
3. **Degenerate parameters** (guess + slip >= 1: a right answer would LOWER the belief) are
   replaced by the healthy concepts' median: 7 of 65 concepts.
Now 95% of the engine's "mastered" calls are true.

### Adaptive vs fixed path (1,000 fresh simulated students, same students on both)
| adaptive minus fixed | result (95% interval) |
|---|---|
| quit by week 3 | **-11.0 points** [-14.7, -7.5] |
| concepts truly known at the end | **-5.1** [-5.8, -4.4] |

- **Depth vs breadth:** the fixed path touches ~34 concepts (3 questions each, learned or
  not; some stick by chance); the engine works through ~9 and makes sure they are learned.
- **Ablations:** prerequisites matter most; ZPD and the bandit barely matter; reviews cost
  the most time.
- **Development vs fresh students:** the fix was found on the seed-2026 students, so the
  claim is checked on seed 2027, the same rule as never tuning on the test set.

## Part 6: Personalised learning path

- **Path:** every unmastered concept in prerequisite order; "quick check" if P(known) >= 0.8
  already, otherwise a lesson; "after X" when a prerequisite is missing.
- **Time:** expected answers to mastery (simulating BKT 400 times with the same mastery
  rule) x typical seconds per answer x the student's own speed.
  Checked on 2,554 cases: median actual / estimate = 0.92 (unbiased), but only 57% within x2.
- **Message:** a template filled with the plan's own numbers, not an LLM, so it can never
  promise "2 weeks" when the plan says 32 days.

## Part 7: Dropout early warning

- **Setup:** at the end of each week, predict "won't come back next week" from answers so far.
- **PR-AUC, not accuracy:** about 1 in 5 quit each week, so "nobody quits" is 80% accurate and
  useless. PR-AUC's zero-skill value is the base rate (0.195), not 0.5.
- **Results:** LightGBM 0.317, logistic 0.324. The simulator's own rule scored directly
  (the ceiling) gets 0.307 from visible data and 0.386 if you could see hidden motivation.
  Both models are at the ceiling, and LightGBM cannot beat logistic because the rule IS logistic.
- **SHAP:** for each student, how much each feature pushed THIS prediction up or down.
  The top driver, accuracy on the last 10 answers, is exactly the simulator's rule.
- **Correlated features share credit:** "empty week" got 0 because "answers this week = 0" says
  the same thing; low SHAP does not always mean "doesn't matter".
- **Risk levels by capacity:** top 10% = mentor call, next 20% = nudge, the rest = nothing extra.
  Flagging 30% catches about half the quitters.

### Check yourself
9. You must ship a tracing model to a school with no GPU, and teachers ask "why does it think
   Ali hasn't learned loops?". Which model, and what do you give up?
10. The adaptive engine's students are right 19 points more often. Why is that NOT evidence
    they learned more?
11. Why are the risk levels set by capacity (top 10%) and not "probability above 50%"?
12. SHAP says "empty week" has zero influence. Does inactivity not matter? What else could
    explain it?
