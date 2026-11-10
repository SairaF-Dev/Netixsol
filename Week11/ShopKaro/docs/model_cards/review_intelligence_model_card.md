# Model Card: ShopKaro Review Intelligence (sentiment, aspects, spam)

_Rewritten 2026-11-09. The previous card cited a "500 gold-standard annotated test set" that does not exist and a
results table (91.8% sentiment, 94.2% spam F1, 54 gems) that no code produced._

## What it is
Rule-based analyzer for English, Roman Urdu and Urdu-script reviews (`src/shopkaro/reviews/lexicon_analyzer.py`):
- **Sentiment** (Positive / Neutral / Negative): clauses are split at punctuation and contrast words (but, however,
  lekin, magar, par, مگر, لیکن); each clause is scored from polar words with negation handling ("not worth",
  "acha nahi", "اچھا نہیں"). Praise plus complaint with no overall verdict = Neutral (mixed).
- **Aspects** (quality, price, delivery, size_fit, packaging, seller -> -1 / 0 / +1): an aspect counts as mentioned
  when one of its words appears in a clause; polarity comes from an aspect-specific word if present ("mehnga",
  "tang", "late", "on time") or from the clause.
- **Spam** with a reason (`promo_link`, `duplicate_bot`, `extreme_burst`).

Topics (4C) use TF-IDF + SVD + KMeans + c-TF-IDF; they are unsupervised and not scored here.

## Why rules and not a trained model
The only training data is synthetic: 8,000 reviews from 11 templates. Models trained on it memorised the
templates (100% on a random split) and failed on new text (50% sentiment accuracy, aspect predictions worse than
predicting nothing). See the table below.

## Evaluation (`src/shopkaro/reviews/benchmark.py`, `reports/day4_review_intelligence_metrics.csv`)

| Task | Set | Baseline | Previous trained model* | **Rule analyzer** |
| :--- | :--- | :---: | :---: | :---: |
| Sentiment accuracy (macro-F1) | Dev (60) | always Positive 40%; word count 83% | 53% (0.48) | 100% (1.00) |
| Sentiment accuracy (macro-F1) | **Held-out (30)** | always Positive 40%; word count 57% | 50% (0.41) | **77% (0.75)** |
| Aspects: cells correct (macro-F1) | Dev (60) | all "not mentioned" 78% (0.29) | 19% (0.14) | 98% (0.98) |
| Aspects: cells correct (macro-F1) | **Held-out (30)** | all "not mentioned" 78% (0.29) | 25% (0.24) | **89% (0.66)**; detection precision 1.00, recall 0.59 |
| Spam F1 (precision / recall) | Dev (16) | old regex 0.50 | 0.50 | 1.00 |
| Spam F1 (precision / recall) | **Held-out (10)** | old regex 0.57 | 0.29 | **0.89 (1.00 / 0.80)** |

\* TF-IDF + logistic regression / random forest trained on the synthetic corpus, measured once on the same
benchmark before it was replaced (it had reported 1.000 on a random split of the corpus; measured before two dev aspect labels were corrected).

**Why the old 1.000 scores were wrong.** The 8,000 synthetic reviews come from 11 sentence templates (777
distinct texts once brand and product names are filled in), so a random 80/20 split puts the same sentences in
training and test. The sentiment model was also given the star rating and delivery delay as inputs, and the
sentiment label is computed from exactly those two numbers. The spam "test set" was three fixed spam sentences
repeated ~130 times each. And the business insights (the "54 unfairly penalised gems") were computed from the
generator's labels, not from any model.

**What replaced it.**
- `src/shopkaro/reviews/benchmark.py`: 60 dev + 30 held-out reviews written by hand in English, Roman Urdu and
  Urdu script (equal thirds), with sentiment and per-aspect labels, plus 16 + 10 spam / hard-genuine examples
  (genuine reviews in capitals, with phone numbers, with the word "fake"). The held-out sets were written before
  any change and were not used for tuning; words that appear only in them were kept out of the rules.
- `src/shopkaro/reviews/lexicon_analyzer.py`: a transparent rule analyzer (clause splitting, negation in English
  and Urdu word order, aspect-specific words such as "mehnga" for price or "tang" for size, waiting-time
  expressions for delivery, spam signals). Trained models cannot learn from 11 templates; a multilingual neural
  model fine-tuned on real labelled reviews is the proper next step.
- Business insights (product summaries, seller tiers, "unfairly penalised" products) are now computed from the
  analyzer's predictions, as they would be on real reviews.

**Caveat.** One person wrote both the rules and the benchmark, so even the held-out score is likely optimistic; an
independent annotator would give a fairer number. 30 held-out reviews is small (accuracy +-15 points at 95%).

## Intended use
Aspect scorecards per product and seller, separating product quality from courier delays, and filtering obvious
promotional / bot spam. Not suitable for automatic penalties against sellers without human review.

## Limitations
- Vocabulary-bound: misses words not in the lexicon (held-out aspect recall 0.59).
- No sarcasm handling; mixed reviews are always Neutral even when the reviewer has an overall verdict.
- Spam rules catch promotional and bot patterns, not subtle fake praise or coordinated campaigns (no reviewer or
  timing data is used).
- Same author wrote rules and benchmark; numbers are likely optimistic.
- Next step: fine-tune a multilingual transformer (e.g. XLM-R) on real labelled ShopKaro reviews.
