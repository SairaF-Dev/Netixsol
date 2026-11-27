# Load test: 500 code submissions in 10 minutes (Day 5, Task 3)

**Result: passed.** All 500 submissions were graded, with 0 errors, and the last one finished
23 seconds after the 10-minute window ended. A student typically waited **1.8 s** from pressing
Submit to seeing the result (95% waited 6.4 s or less). In the deadline burst of 100 submissions
sent at once, all 100 were graded within 2 minutes 5 seconds, but the median wait rose to 55 s.

Run on 2026-11-27, 18:19-18:33 UTC, on the live deployment. Raw output: `steady.json`,
`burst.json`, `monitor.log` (load, free memory and running sandbox containers, every 5 s).

## Setup

| | |
|---|---|
| Machine | GitHub Codespace, 2 CPU cores, 8 GB RAM (the live deployment, `docs/deployment.md`) |
| Server | `uvicorn ilm.api.main:app`, `ILM_ENV=prod`, 4 grading workers |
| Per submission | Docker sandbox (no network, 256 MB, 1 CPU), every test including hidden and edge cases, code-quality checks, feedback, lesson link |
| Client | `python -m ilm.api.loadtest` (standard library only), run inside the codespace |
| Measured | Time from `POST /api/submissions` until `GET /api/submissions/{id}` reports `done`. Polled every 1 s, so times are up to about 1 s high |
| Mix | The 50 hand-marked submissions (`data/grading/submissions.json`) sent in rotation, 10 times each: correct, wrong, crashing, rule-breaking, slow, and **2 infinite loops** (each holds a worker for the full time limit) |

## Results

| | Steady: 500 over 10 min | Burst: 100 at once |
|---|---|---|
| Finished / errors / unfinished | 500 / 0 / 0 | 100 / 0 / 0 |
| Time to send them all | 598.8 s | 1.2 s |
| Last result after | 622.1 s | 124.7 s |
| Wait, median (p50) | **1.76 s** | 55.2 s |
| Wait, p95 | **6.44 s** | 100.4 s |
| Wait, worst | 34.9 s | 124.6 s |
| p50 / p95 without the infinite loops | 1.73 s / 4.56 s | 52.5 s / 99.4 s |
| Graded per minute | 48.2 | 48.1 |

The monitor recorded a peak load average of 8.1 on 2 cores (about four runnable tasks per core),
and free memory never fell below 5.8 GB. Memory was never the limit: **CPU was**.

## What it means

- **The spec's target is met**: 500 in 10 minutes, all graded, and nearly every student sees the
  result within a few seconds.
- **There is little spare capacity.** Under full load the machine grades about 48 a minute, and
  the target asks for 50. The steady run kept up because submissions arrived spread out and most
  are quick (median 1.2 s on the server). A heavier mix, with more infinite loops, would build a
  queue.
- **A real deadline rush queues up.** 100 at once took 2 minutes to clear. Nothing was lost, and
  each student's page keeps waiting for its own result.
- **Scaling:** more cores is the lever. Each submission is one sandbox container, so the 4 workers
  can be raised on a 4-core machine. On a server we control, a warm pool of containers would also
  remove Docker's start-up cost from every run.

## Honest caveats

- **The per-student limit was raised for the test only.** Normally each student can submit 12 times
  a minute, and the test sends 500 from 2 demo accounts. The runner started the server with
  `ILM_SUBMIT_PER_MINUTE=100000`, then restarted it with the normal limit afterwards.
- **The client ran on the same machine.** That leaves out internet delay but adds the client's own
  CPU use, so it is slightly pessimistic for the server and leaves out the network.
- **The client sends the session cookie itself.** In prod the cookie is Secure (HTTPS only), so a
  normal cookie jar does not send it to `http://127.0.0.1`. The first attempt got 401 on every
  call for that reason.
- **Two earlier attempts were cut short** when the codespace shut down after its 30-minute idle
  timeout: background SSH commands do not count as activity. The run reported here kept an SSH
  session open, streaming progress, from start to finish.
- **The tutor and question practice were not part of the test.** The tutor is bounded by the
  Gemini free quota (per-student limits of 8 a minute and 80 a day), not by this server.

## Re-run

Inside the codespace, from `Week13/ilm_academy`:

```bash
# restart the server with ILM_SUBMIT_PER_MINUTE=100000 first, and restore it afterwards
ILM_LOADTEST_PASSWORD=<demo password> python -m ilm.api.loadtest --total 500 --minutes 10
ILM_LOADTEST_PASSWORD=<demo password> python -m ilm.api.loadtest --burst 100
```
