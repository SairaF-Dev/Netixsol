# Sandbox security report (Day 4 Task 1)

Student code runs in a fresh Docker container for every submission (`ilm/grading/sandbox.py`).
Attack results: [attack_report.md](attack_report.md) (regenerate with `python -m ilm.grading.attacks`).

**Result: 24 of 24 attacks contained.** After the suite, Docker still responded and no sandbox
container was left behind.

## Two jobs, two defences

**1. Protect the machine.** Each run gets: no network, 256 MB RAM with no swap, 1 CPU, 64
processes, a read-only filesystem with a 16 MB `/tmp` in RAM, the `nobody` user, every Linux
capability dropped, no privilege escalation, a 1 MB file-size limit, 64 open files, a time
limit and a 64 KB output cap. Nothing from the host is passed in: no environment variables
(so no API key) and no folders.

**Same code, same mark.** `PYTHONHASHSEED=0` fixes set and dict order, so a grade that depends on it cannot change between runs. Python runs with `-s -S` rather than `-I`, because isolated mode ignores every `PYTHON*` variable; the seed was silently ignored until a test caught it.

**2. Protect the grade.** Student code runs in the same process as the test loop, so it can
read and change anything there, including the harness's own variables and Python's built-ins.
So the container is never trusted with the verdict:
- the **expected answers never enter the container**. It only reports what each test call
  returned, and the host compares that with the expected answers;
- only plain built-in values count, compared with exact types (an object whose `==` always
  says yes fails, and so does an `int` subclass);
- the result line carries a random per-run tag and must appear exactly once. Any other
  result-like line is flagged as tampering **for a teacher to review, never as an automatic
  penalty**.

The most instructive attack: the student code read the per-run tag from the harness's memory,
wrote a perfect-looking "all passed" line and exited. The sandbox accepted the line as the
result, and the grade was still 0, because the forged values (999) were compared with
expected answers the container never saw. **A secret the attacker can read protects nothing;
keep the decision where the attacker can't reach.**

## What the attacks found in our own first version
- **Output flood:** after the host stopped reading at the cap, the pipe filled and even
  `docker kill` hung. Fix: keep draining (keep the first 64 KB, discard the rest).
- The first plain runner (`ilm/questions/runner.py`, for our own reference code) trusted the
  first result line it saw, so a student could print a fake one. It stays for author code
  only; student code goes through the sandbox.

## Limits (what this does NOT protect against)
- **A container is not a virtual machine.** All containers share the Linux kernel, so a kernel
  exploit could escape. On this Windows machine, Docker Desktop adds a WSL2 VM around them.
  For a public launch: gVisor (`--runtime=runsc`) or Firecracker microVMs.
- **One time limit per submission.** An infinite loop in one test (when the per-test alarm is
  disabled) uses up the whole run, and every test fails. Task 2 re-runs tests one by one in that
  case, so partial marks survive.
- **Start-up cost** is about 0.9 s per container. Day 5's load test on the 2-core deployment:
  500 submissions in 10 minutes all graded, median 1.8 s to the result, about 48 graded a minute
  at full load (`reports/load_test/report.md`). 3,000 on a Sunday needs more cores or a
  warm container pool.
- **The image is pulled by tag.** For production, pin the digest:
  `python@sha256:61e01f72680f86a5279ad510818ab7b2ee9f049822589d4e34e33e044360356c`.
- `GPG_KEY` in the container's environment is the official Python image's public signing-key
  ID, not a secret.
