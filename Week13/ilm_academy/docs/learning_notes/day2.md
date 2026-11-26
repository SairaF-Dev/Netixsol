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
