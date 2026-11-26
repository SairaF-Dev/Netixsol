# Ilm Academy: AI Tutor & Adaptive Learning Platform (Week 13 Capstone)

Ilm Academy has 8,000 online students on one fixed path, and 45% drop out before week 4.
This platform maps what there is to learn, estimates what each student knows, adapts the
path, tutors in a Socratic way, grades code safely and gives teachers a dashboard.

## Setup (Windows, Python 3.11)

```powershell
py -3.11 -m venv .venv311
.venv311\Scripts\python.exe -m pip install -r requirements.lock.txt
copy .env.example .env        # then fill in the API key
.venv311\Scripts\python.exe scripts\check_env.py
.venv311\Scripts\python.exe -m pytest            # add -m "not slow" to skip real-model tests
```

Use Python 3.11. The machine default (3.14/3.15) lacks wheels for several ML libraries.
`requirements.txt` lists what we depend on; `requirements.lock.txt` pins the exact versions we tested.

## Layout

| Folder | What lives there |
|---|---|
| `ilm/content` | Whisper transcription, slide/notes extraction, vector DB |
| `ilm/graph` | Concept graph (40+ Python concepts) and DAG checks |
| `ilm/questions` | Question bank schema and validator |
| `ilm/learners` | ASSISTments/EdNet loaders, 1,000-student simulator |
| `ilm/tracing` | BKT, PFA, DKT/SAKT, IRT (Day 2) |
| `ilm/adaptive` | Recommender, bandit, spaced repetition, paths (Day 2) |
| `ilm/tutor` | RAG tutor, hint ladder, guardrails (Day 3) |
| `ilm/grading` | Sandbox, tests, feedback, rubric, plagiarism (Day 4) |
| `ilm/api`, `ilm/apps` | FastAPI, student and teacher apps (Day 5) |
| `ilm/config.py` | Every path and setting, one place |
| `tests/` | pytest; tests run on a temp data dir, never on `data/` |
| `docs/learning_notes/` | What was learned each day |

## Engineering rules

1. Every number in a report comes from a script that can be re-run; the report names the script.
2. A component is named after what it really is (no "LightGBM" that is secretly something else).
3. Knowledge-tracing models are compared on real data (ASSISTments) with a student-level split.
4. The adaptive engine never reads the simulator's hidden true ability.
5. Tests never write to `data/`, `models/` or `reports/`.

## Status

- [x] Day 1 setup: environment, structure, config, test isolation, retrieval smoke test
- [x] Day 1 Task 1: content ingestion: 11 Whisper transcripts (WER 3.0%), 1,093 chunks in Chroma, retrieval benchmark: LLM rewrite + hybrid search chosen on dev, holdout MRR 0.96 (`reports/retrieval/`)
- [x] Day 1 Task 2: concept graph (65 concepts, DAG-validated, visualised)
- [x] Day 1 Task 3: question bank (225 questions, every answer checked by running code: `python -m ilm.questions.validate`)
- [x] Day 1 Task 4: learner data (ASSISTments 2009-10 cleaned: 525,534 rows -> 283,105 real answers) and a simulator of 1,000 students + Ali and Sara, dropout calibrated to 45% before week 4
- [x] Day 1 Task 5: EDA notebook (`notebooks/day1_eda.ipynb`): accuracy per concept, learning curves, dropout points, hardest concepts, each with an insight computed from the numbers (`reports/eda/insights.csv`)
- [x] Day 2 Task 1: knowledge tracing on ASSISTments, student-level split, test scored once: DKT 0.770 AUC > SAKT 0.747 > BKT 0.738 > PFA 0.736 > best baseline 0.711 (`reports/tracing/results.md`)
- [x] Day 2 Task 2: BKT mastery per concept (earned with 3 in a row, hysteresis) and 1PL/2PL IRT: 12/12 planted bad questions found (`reports/irt/`, `reports/mastery/`)
- [x] Day 2 Task 3: adaptive engine (prerequisites, 60-80% ZPD, Thompson sampling, spaced repetition) vs fixed path on fresh students: -11 pts week-3 dropout, -5.1 concepts known (`reports/adaptive/`)
- [x] Day 2 Task 4: personalised learning path with time estimates (median actual/estimate 0.92) and UrduLish message (`reports/learning_path/`)
- [x] Day 2 Task 5: dropout early warning: LightGBM + SHAP, PR-AUC 0.317 vs ceiling 0.307 (visible data), risk levels with actions (`reports/dropout/report.md`)
