# Model cards

There is one card for each model the platform uses. Each says what the model is for, what it
was trained and tested on, how well it did, and what it must not be used for. Every number comes
from a report in `reports/` that a script regenerates.

**One caveat applies to several cards.** Some evaluations use **simulated students**
(`ilm/learners/simulator.py`). We wrote the simulator, so where it agrees with a model it
validates the pipeline, not real-world accuracy. Those rows say "simulated".

| | model | decides | used live? |
|---|---|---|---|
| 1 | Knowledge tracing (BKT per concept) | what a student knows | yes |
| 2 | IRT 2PL | which questions are broken or mislabelled | teacher view |
| 3 | Adaptive engine | what a student does next | yes (learning paths) |
| 4 | Dropout early warning (LightGBM) | who a teacher contacts | teacher view |
| 5 | Socratic tutor (Gemini) | what the tutor says | yes |
| 6 | Lecture search (BM25 + bge-small) | which lesson the tutor cites | yes |
| 7 | Code grader | the mark | yes |
| 8 | Copy detector | which pairs a teacher reviews | teacher view |
| 9 | Question generator and difficulty predictor (Gemini) | draft questions | offline, then teacher review |
| 10 | Whisper transcription | lecture text for search | offline |

---

## 1. Knowledge tracing: BKT per concept

| | |
|---|---|
| **Purpose** | P(student knows concept) after each answer. It decides "mastered" and feeds the path, the practice screen and the class heatmap |
| **Model** | Bayesian Knowledge Tracing (pyBKT, with forgetting). One parameter set per concept (65), in `models/bkt_concept_params.csv` |
| **Mastery rule** | earned when P(known) ≥ 0.95 **and** the last 3 answers are right; lost when P(known) < 0.95 |
| **Benchmark (real students)** | ASSISTments, split by student, test scored once: DKT 0.770 AUC > SAKT 0.747 > **BKT 0.738** > PFA 0.736 > best baseline 0.711 (`reports/tracing/results.md`) |
| **Why BKT, not DKT** | DKT is 0.03 AUC better, but BKT is per concept and readable ("P(known) = 0.82"), it updates with one formula per answer on the server, and it needs no GPU. That fits a teacher-facing product |
| **Simulated check** | 95% of the engine's "mastered" calls were truly known (`reports/adaptive/`). P(known) alone is weakly calibrated: AUC 0.66 against the truth with only 3 answers per concept; the 3-in-a-row rule is what makes "mastered" trustworthy |
| **Limits** | 7 concepts had degenerate fits and use median parameters. The parameters were fitted on simulated answers to our own question bank, so refit them on real answers after launch |
| **Not for** | grades, certificates or anything that blocks a student. It is an estimate for choosing practice |

## 2. Item response theory: 2PL

| | |
|---|---|
| **Purpose** | difficulty (b) and discrimination (a) for each question. It finds broken questions for the Question bank page |
| **Data** | 107,298 simulated answers, 978 students, 195 questions (`reports/irt/summary.json`) |
| **Results (simulated)** | **12 of 12 planted bad questions found**, with 1 false alarm (precision 0.92). Difficulty recovery: Spearman 0.68 |
| **Decision rule** | retire if a < 0.3 (strong and weak students do about the same) or a < 0 (strong students do worse); relabel if the measured level is 2 or more away from the author's label |
| **Limits** | the simulator's true difficulty is the author's guess plus noise, which flatters the author's labels. 30 questions are never asked on the fixed path, so they are unmeasured |
| **Not for** | retiring a question automatically. A teacher decides on the Question bank page |

## 3. Adaptive engine

| | |
|---|---|
| **Purpose** | the next concept and question for each student: the path on the Today and Path pages |
| **Ideas** | prerequisites from the concept graph; questions in the 60-80% success zone (ZPD) from IRT; Thompson sampling among good candidates; spaced reviews |
| **Results (simulated, 1,000 fresh students, paired)** | dropout before week 4: **−11 points** [−14.7, −7.5]. Concepts truly known at the end: **−5.1** [−5.8, −4.4]. Ablations: prerequisites matter most; ZPD and the bandit barely matter |
| **The trade-off** | the engine goes deep (about 9 concepts it makes sure are learned), while the fixed path goes broad (about 34 touched). The A/B rehearsal's decision rule says **do not ship as is** (`reports/ab_test/design.md`) |
| **Limits** | the simulator rewards exactly what the engine does. There is no real-student evidence yet; that is what the A/B test is for |
| **Not for** | locking content. A student can open any exercise |

## 4. Dropout early warning

| | |
|---|---|
| **Purpose** | a weekly list of at-risk students, with the reason in words and an action (At risk page) |
| **Model** | LightGBM on 15 weekly activity features: answers, sessions, empty weeks, days since last visit, accuracy (total, this week, last 10, change), wrong streak, speed, code share (`ilm/analytics/dropout.py`). Reasons come from SHAP |
| **Results (simulated test cohort, scored once)** | PR-AUC **0.317**, against a base rate of 0.195. The logistic baseline gets 0.324. The ceiling from observable data is 0.307, and 0.386 with hidden motivation (`reports/dropout/report.md`) |
| **What that means** | both models reach the best that observable data allows. The rest of the simulated dropout is chance or hidden motivation. LightGBM is kept for its SHAP reasons; the baseline is equally good |
| **Risk levels** | high: 38.6% of these students drop out, so a mentor calls within 24 hours. Medium: 21.1%, so a nudge. Low: 15.7%, normal summary |
| **Limits** | only 23% of all dropouts are in the high group. A "low" student can still leave |
| **Not for** | any penalty, or any message that tells a student they are "at risk". It is for teacher outreach |

## 5. Socratic tutor

| | |
|---|---|
| **Purpose** | answers course questions and gives a 4-rung hint ladder, never the solution |
| **Model** | `gemini-3.1-flash-lite` through the Gemini API (`LLM_MODEL`) |
| **Grounding** | only the numbered lecture sources it is given. The server builds the links from those numbers |
| **Safety layers** | prompt rules; code in replies run against the tests; near-copy check; other-exercise check; one informed retry, then rung 2, then a fixed message. Policy: `docs/tutor_safety_policy.md` |
| **Results** | leaks fell from 12% in run 1 to **0%** in runs 2-3 (50 conversations plus 24 held-out turns). Jailbreaks resisted: 100% of 15 in run 2. The judge's correctness score: 98% (run 1) |
| **Limits** | 0 leaks in 24 held-out turns still allows up to about 12% (rule of three). Examples that are close in meaning but not in syntax are not caught. Some over-refusal. Evaluation runs 2-3 are not yet judged, because of the free quota |
| **Not for** | marking, or anything outside the Python course |

## 6. Lecture search

| | |
|---|---|
| **Purpose** | finds the lecture passages the tutor answers from; links to a lesson and timestamp |
| **Model** | an LLM rewrite of the question, then BM25 and `BAAI/bge-small-en-v1.5` vectors (Chroma), merged by reciprocal rank fusion |
| **Data** | 1,093 chunks from 11 CS50P and MIT 6.0001 lectures, plus slides and notes |
| **Results (held-out, 16 questions)** | MRR **0.958**, hit@1 0.94, hit@5 1.00. Without the rewrite: hybrid 0.913, bge-small alone 0.844, BM25 0.865 |
| **Limits** | only 16 held-out questions; English lectures only, so UrduLish questions depend on the rewrite |

## 7. Code grader

| | |
|---|---|
| **Purpose** | a mark out of 10 for a coding exercise |
| **How** | sandboxed tests (bank tests plus edge tests), with partial marks by test; AST rule checks; a speed check. Re-runs test by test after a timeout |
| **Results (50 submissions)** | quadratic kappa **0.917**, MAE 0.95 marks, 88% within 2 marks. Tests alone: kappa 0.64 (`reports/grading/report.md`) |
| **The reference** | blind marks from the assistant using a written scheme (`data/grading/marking_scheme.md`), **not a teacher** |
| **Limits** | "right idea, wrong result" gets 0 from tests, where a human gives 3-4. That is why marks under 4 go to the teacher's review queue |
| **Not for** | final grades without the review queue |

## 8. Copy detector

| | |
|---|---|
| **Purpose** | ranks pairs of submissions to the same exercise by similarity, for the Review queue |
| **Model** | logistic regression combining token fingerprints, AST sequence and bge-small embedding similarity, adjusted for each exercise |
| **Results (test exercises, scored once)** | PR-AUC **0.942**, precision 0.89, recall 0.74 at the dev cut-off. Ranked queue: the top 3 per exercise were 100% real copies (`reports/plagiarism/report.md`) |
| **Base rate** | 0.88% false alarms per honest pair. At 100 students a threshold would give 8% precision, so the teacher sees the **top 5 pairs per exercise** instead |
| **Limits** | the copies were planted by us. Short exercises have few ways to write them, so similar code is not proof |
| **Not for** | any automatic penalty. Every flag reads "Possible copying: needs teacher review" |

## 9. Question generator and difficulty predictor

| | |
|---|---|
| **Purpose** | drafts new practice questions; predicts how hard a question is before students answer it |
| **Model** | `gemini-3.5-flash-lite` |
| **Generator gates** | format, flaws, truth (code is run), duplicates. **82%** accepted (143 of 175). The independent solver gate has not run yet, because of the quota (`reports/question_gen/v2/`) |
| **Difficulty** | Spearman with IRT difficulty: LLM 0.33, author 0.56. The LLM over-predicts success (74% predicted against 52% observed) (`reports/difficulty/report.md`) |
| **Limits** | the comparison favours the author by construction (caveat at the top) |
| **Not for** | publishing without a teacher's review |

## 10. Whisper transcription

| | |
|---|---|
| **Purpose** | turns lecture videos into timestamped text for search and links |
| **Model** | Whisper small, through `faster-whisper` (`WHISPER_MODEL`) |
| **Results** | WER **3.0%** over 11 lectures (189,093 reference words), against the official captions (`reports/transcription_wer.json`) |
| **Limits** | English only. Code read aloud is the weakest part |
