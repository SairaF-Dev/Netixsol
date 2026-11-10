# Migration to the brief's libraries (Python 3.11) — 2026-11-10

The project ran on Python 3.14, where several libraries the brief names do not install, so each component had a
scikit-learn / NumPy stand-in. This migration moved to a Python 3.11 environment (`.venv311`) with the real
libraries and re-measured every affected component on the same data and benchmarks. A library replaced its
stand-in only when it did at least as well; one did not and was rejected.

## Environment
- Python 3.11.9, `requirements.txt` pins a tested set (numpy 1.26.4, pandas 2.2.3, lightgbm 4.6.0, prophet 1.5.0,
  implicit 0.7.1, torch 2.5.1 CPU, sentence-transformers 3.3.1, bertopic 0.17.4).
- Older pins are deliberate: Windows Smart App Control on the development machine blocked brand-new binary builds
  (pandas, pyarrow, torch, implicit 0.7.2, regex, sentencepiece); LightGBM 4.7 crashed next to pandas 2.2;
  `implicit` 0.7.1 needs a one-line NumPy shim (documented in `collaborative.py`).
- Every component still falls back to its stand-in if its library is missing, so the old environment keeps working.
- No GPU or Colab needed. One-off cost: embedding the 25,000-product catalogue took ~24 min on CPU (cached).

## Results (same data, same benchmarks, before -> after)

| Component | Library | Metric | Stand-in | Real library | Decision |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Search semantic retriever | sentence-transformers (`intfloat/multilingual-e5-small`) | Semantic-only NDCG@10, held-out 20 | 0.585 | **0.714** | **Adopted** |
| Full hybrid search | (uses the above) | NDCG@10 dev 50 / held-out 20 | 0.957 / 0.800 | **0.964 / 0.832** | Adopted; gain not significant (held-out +0.032, CI [-0.11, +0.17]) |
| | | Latency p95 | ~13 ms | 67 ms | within the 100 ms target |
| Search cross-encoder (top 50) | sentence-transformers `CrossEncoder` (mMiniLMv2, multilingual) | held-out NDCG@10 | 0.832 | **0.837** | Adopted (brief requirement); gain not significant, +~0.7 s/search |
| Personalised search (CF re-rank) | on neural search | held-out NDCG@10 plain -> personalised | 0.012 -> 0.064 | 0.010 -> **0.069** | new-product gain now significant (47 better / 13 worse) |
| Recommender: ALS | `implicit` | NDCG@10 / hit rate@10, 5,000 users | 0.1278 / 18.0% | **0.1299 / 18.9%** | Adopted |
| Hybrid two-tower (uses ALS) | | NDCG@10 | 0.1298 | **0.1333** | now marginally above item-CF (0.1307); item-CF stays in production (A/B-validated, gap untested) |
| Forecasting: Prophet | `prophet` | Category WAPE 14 d / 30 d | 6.84% / 7.52% | **6.22% / 6.65%** | Adopted |
| Forecasting: gradient boosting | `lightgbm` | Category WAPE 14 d | 6.12% | **6.04%** | Adopted (same algorithm; inventory results unchanged: 143 critical, replay -89.9% lost units) |
| Review topics | `bertopic` (+ Roman Urdu stop words) | (unsupervised) | TF-IDF+SVD+KMeans | BERTopic | Adopted; keywords now content words |
| Review sentiment | pretrained multilingual models (`lxyuan/distilbert-base-multilingual-cased-sentiments-student`, `tabularisai/multilingual-sentiment-analysis`) | held-out accuracy, 30 reviews | rules 76.7% | 46.7% (Roman Urdu 30%) | **Rejected** — kept the rules |

## What this changes in the headline numbers
- Held-out search NDCG@10: 0.800 -> **0.832** (keyword-only on current data 0.602). Two of the four known held-out
  gaps (Urdu-script "jacket" and "mobile phone") are fixed; one brand query ("tapal chai") got worse.
- Review sentiment, topics labels and the "unfairly penalised" count (1) are unchanged.
- The XLM-R based `cardiffnlp` sentiment model could not be tested: its weights exist only as a legacy PyTorch
  pickle that crashed (native segfault) on this machine; the two models above ship safetensors.

## Re-running
```powershell
.\.venv311\Scripts\python.exe scripts\run_day2_task4.py            # recommenders incl. ALS
.\.venv311\Scripts\python.exe scripts\run_day3_task2_task3.py      # forecasting backtest incl. Prophet / LightGBM
.\.venv311\Scripts\python.exe scripts\run_day3_task4_task5.py      # inventory plan
.\.venv311\Scripts\python.exe scripts\run_day4_task1.py            # search benchmark (neural)
.\.venv311\Scripts\python.exe -m shopkaro.search.personalization_eval
.\.venv311\Scripts\python.exe scripts\run_day4_task4_task5.py      # reviews incl. BERTopic
```
