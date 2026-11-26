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
