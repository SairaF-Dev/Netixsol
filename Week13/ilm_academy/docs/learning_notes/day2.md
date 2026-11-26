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
Mastered when P(knows) >= 0.95 (the classic threshold).
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
