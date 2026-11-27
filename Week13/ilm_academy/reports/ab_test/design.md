# A/B test: adaptive path vs fixed path (Day 5, Task 2)

This is the pre-registration: what we will test, how and what result means what, written down
before a single student is enrolled. Changing any of it after launch makes the result
untrustworthy. The machinery (assignment, sample size, sample-ratio check, analysis, decision
rule) is code in `ilm/evaluation/ab_test.py`, tested in `tests/test_ab_test.py`, and was
rehearsed end to end on fresh simulated students (section 9).

## 1. Why a real test is needed

Day 2 compared the two paths on 1,000 simulated students (`reports/adaptive/`):

| adaptive minus fixed (simulated) | result, 95% interval |
|---|---|
| dropped out before week 4 | **-11 points** [-14.7, -7.5] |
| concepts truly known at the end | **-5.1** [-5.8, -4.4] |
| hours studied | -0.21 [-0.36, -0.07] |

Two reasons this is not enough to change the course for 8,000 students:

1. **We wrote the simulator.** It makes repeated failure push students to drop out, and makes
   prerequisites matter: exactly what the engine exploits. The real effect will be smaller,
   maybe zero.
2. **The simulator found a trade-off.** Adaptive students stay longer but finish knowing fewer
   concepts: the engine makes sure about 9 are really learned, while the fixed path touches about 34
   and some stick. Whether that is good depends on whether real students learn more in the end.
   The test has to measure learning, not only dropout.

## 2. Hypotheses

- **H1 (primary).** Fewer new students drop out before week 4 on the adaptive path than on the
  fixed path.
- **H2 (must not fail).** Their learning gain is not meaningfully worse (non-inferiority, margin
  0.2 SD of the fixed path's gain).
- Secondary: time to mastery, dropout by the end of the course, teacher hours.

## 3. Who, and how they are split

- **Who:** new students enrolling after launch, all of them, nobody hand-picked. Current students
  stay on the path they know: switching someone mid-course muddles both arms.
- **Unit:** the student. The path is personal, so one student's arm hardly affects another's.
  Sections and teachers are shared by both arms, so a teacher cannot "favour" one arm.
- **Split:** 50/50 by a hash of the student id (`assign()`: SHA-256 with a salt fixed before
  launch). The same student always gets the same arm, the split needs no stored table, and nobody
  chooses who goes where.
- **Checks before any result is read:**
  - the sample-ratio check (`srm()`): stop if p < 0.001, because the split is broken;
  - pre-test balance: a standardised difference under 0.1.
- **What both arms get:** the same lessons, tutor, grader, teachers, deadlines and certificate.
  Only the order and the amount of practice differ.

## 4. Metrics, each defined so both arms are measured the same way

| | metric | how it is measured | why this way |
|---|---|---|---|
| **Primary** | dropout before week 4 | no activity in weeks 4-5 after enrolling (week counted from each student's own start) | the client's problem: 45% today |
| Must not fail | **learning gain** | post-test minus placement pre-test | see the rules below |
| Secondary | time to mastery | hours of study until a student first passes the neutral checkpoint quiz of a core concept. Kaplan-Meier, with dropping out as censoring | not the engine's own "mastered", which the fixed arm does not have |
| Secondary | dropout by the end of the course | as above, at the course end | does the week-4 effect last? |
| Secondary | teacher hours | minutes logged on the dashboard per student per week (review queue open to decision, at-risk outreach), by arm | see section 6 |
| Guardrail | study hours | total time on the platform | the engine must not win by making students work 20% longer |
| Guardrail | tutor safety | refused or flagged tutor answers, per 100 hints | adaptive students may use the tutor more |
| Guardrail | complaints | support tickets and survey "the course is too slow or too fast" | |

**How the post-test is set:**

- 40 questions written before launch, drawn from bank questions never used in practice.
- It covers the whole course, not only the concepts one arm practises, so breadth counts.
- It is marked automatically, and the teachers do not know students' arms.

**Students who drop out still count.** Everyone assigned is analysed (intention to treat).
Dropouts are invited to the post-test with a small incentive. If more than 30% of either arm
have no post-test, learning gain is reported as a range (Lee bounds), not a single number.
Comparing only the students who finished would reward the arm that loses its weaker students.

## 5. How many students and for how long

The smallest effect worth shipping is **4 points**: dropout from 45% to 41%, which keeps about
320 more of every 8,000 students. That is far below the simulator's 11 points, on purpose.

| detect a drop of | students per arm (alpha 0.05 two-sided, power 80%) |
|---|---|
| 3 points | 4,307 |
| **4 points (planned)** | **2,420** |
| 5 points | 1,547 |
| 8 points | 602 |
| 11 points (the simulator's) | 317 |

- **Enrol 5,324 new students** (2 × 2,420, plus 10% for accounts that never start).
- **Duration:** enrolment lasts as long as it takes to reach 5,324 new students; at the
  client's real intake rate that is the number to plug in. Then **5 weeks of follow-up** for
  the primary metric and to the course end for the rest.
- Do not end early because "it looks significant": the analysis is planned once, at the end.

**Pre-test as a covariate.** Adjusting for the placement pre-test (ANCOVA) will narrow the
intervals for learning gain. It is not counted in the sample size, so the plan stays
conservative.

## 6. Teacher hours saved

Auto-grading is in both arms, so the A/B test cannot measure the hours it saves. That needs its
own measurement:

| | |
|---|---|
| Before launch | time 3 teachers marking the same 100 random submissions by hand, to get minutes per submission |
| During the test | the dashboard logs review-queue time (open to decision) |
| Saved per week | 3,000 submissions × (1 − share still reviewed) × minutes ÷ 60 |
| Today's estimate | with an assumed 3 minutes and the measured 28% reviewed (a mark under 4 on the 50 graded submissions): **about 108 hours a week**. The 3 minutes is an assumption until the timing study replaces it |

The A/B test does measure whether the adaptive path changes teacher time: for example, fewer
at-risk students to contact, or more questions from confused students. That is the teacher-hours
row in section 4.

## 7. The decision rule (fixed now)

| result | decision |
|---|---|
| split broken (sample-ratio p < 0.001) | the result is invalid: fix the bug and rerun |
| dropout lower (interval below 0) **and** learning gain not worse than the margin **and** study-hours guardrail OK | **ship the adaptive path** |
| dropout lower **but** learning gain may be worse | **do not ship as is:** students stay but learn less. Tune the pace (for example, the mastery threshold) and run a new test with a new salt |
| dropout higher (interval above 0) | do not ship |
| anything else | keep the fixed path: no clear benefit |

`decide()` in `ilm/evaluation/ab_test.py` applies exactly this table.

## 8. Stopping, ethics and pitfalls

- **One interim look, for harm only.** At half enrolment, stop if the adaptive arm's dropout is
  higher with z above 2.8. That is a strict line, so the final test keeps its 5%. There is no
  early stop for success.
- **Nobody is worse off than today.** The control arm is the current course, and both arms get
  the same teachers, tutor and certificate. Students are told at sign-up that the order of
  lessons is being improved and can differ between students. The data stays the platform's
  normal learning data.
- **Novelty.** Dropout is measured per student from their own start, so early enrolees and late
  enrolees count alike. The end-of-course dropout checks that the effect lasts.
- **Peeking and many metrics.** There is one primary metric. The secondary metrics are reported
  with intervals but cannot by themselves make the decision. Subgroups (Urdu-preferring
  students, students with low pre-tests) are pre-named here; any other subgroup is a hint for
  the next test, not a result.
- **Instrumentation.**
  - Run a 1-week A/A test before launch: both arms on the fixed path, to check that the logging
    and the analysis find "no difference".
  - Log the arm on every event.
  - A bug that loses one arm's events shows up as a sample-ratio alarm.

## 9. Rehearsal on fresh simulated students

`python -m ilm.evaluation.ab_test` → `rehearsal.json`.

**Setup.**

- 4,840 **fresh** simulated students: seed 2028, never used for training, tuning or Day 2's
  confirmation.
- Both paths were run on every student. The rehearsal then shows each student **only under the
  arm the hash gave them**, which is what a real test sees.
- The simulated fixed-path dropout was 45.3%, close to the client's 45%.

**1. Is the analysis honest? (A/A test).** The fixed path was compared with itself under 1,000
different splits.

| | expected | found |
|---|---|---|
| "significant" dropout differences | about 5% | 5.6% (within chance: ±1.4 points at 1,000 runs) |
| sample-ratio alarms (p < 0.001) | about 1 | 3 |

So the analysis does not invent effects.

**2. The A/B test at the planned size** (2,415 fixed, 2,425 adaptive; sample ratio p = 0.89;
pre-test balance −0.05 SD):

| adaptive minus fixed | result, 95% interval | the truth (same students under both paths) |
|---|---|---|
| dropout before week 4 | **−8.1 points** [−10.8, −5.3] | −7.2 |
| learning gain (concepts) | **−5.5** [−6.0, −4.9], margin −2.4 | −5.6 |
| dropout by the end | −5.1 points [−7.7, −2.5] | −4.0 |
| study hours | −0.06 [−0.22, +0.09] | −0.17 |
| hours per concept learned | +0.005 [−0.02, +0.03] | 0.000 |

The test recovers the truth within its intervals.

**Decision: "do not ship as is: students stay but learn less; tune the pace and test again".**
The simulator's trade-off is real in the simulation, and the rule catches it. A test that
measured only dropout would have shipped a path that halves what students learn (a gain of 7.6
concepts instead of 13.1). That is why learning gain is a must-not-fail metric.

**3. Power.**

| per arm | how often the test detects the simulator's drop |
|---|---|
| 2,420 (planned) | 100% (the simulator's effect, about 7-8 points, is far above the planned 4) |
| 500 | 64%: a small pilot would miss it a third of the time |

The planned size also has 80% power for the much smaller 4-point effect (section 5).

**What the rehearsal shows and does not show.** It shows that the machinery works end to end:
the split, the checks, the analysis and the decision rule, on data where the answer is known. It
does not predict the real result, because the simulator rewards what the engine does.

**The next step before a real launch** follows from it: tune the engine's pace (fewer repeats of
a concept once it is likely known, so students cover more of the course), confirm in the
simulator that the gain recovers without losing the dropout effect, then run this test.
