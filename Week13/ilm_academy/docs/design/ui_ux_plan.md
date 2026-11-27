# Ilm Academy: UI/UX plan (Day 5)

What the student app and the teacher app look like, what each screen does, and the rules
that keep them looking like a product people use, not a template. Every example on this page
is real content from this project (the reports and data in this repo); nothing is invented
filler.

---

## 0. The stance: real, not "AI-generated"

AI-looking interfaces share a few habits. We avoid them on purpose.

| avoid | do instead |
|---|---|
| purple/indigo gradients, glassmorphism, glowing blobs | one calm ink colour, one accent, flat surfaces, thin borders |
| a hero banner ("Unlock your potential!") on a logged-in screen | open straight into the work: today's next step |
| emoji in headings, "Welcome back! 👋" | plain greeting with a fact: "Ali, 32 days to finish at 30 min a day" |
| three identical cards with an icon each | layouts shaped by the content: a list where it is a list, a table where it is a table |
| everything centred, rounded-2xl, big shadows | left-aligned, 6 px radius, borders, shadows only on things that float (menus, dialogs) |
| vague numbers ("Great progress!") | the real number and what it means ("3 of 65 concepts mastered") |
| lorem ipsum, "John Doe", fake testimonials, stock photos | our data, our two demo learners (Ali, Sara), no photos at all |
| a spinner for everything | skeletons that match the real layout, and the last known data while refreshing |
| colour as the only signal | colour + text label ("High risk", not just a red dot) |

Reference products for the *feel* (not to copy): GitHub Classroom and Linear for the teacher
side (dense, calm, keyboard-friendly); Duolingo's clarity of "one next thing" for the student
side, without its cartoon style.

---

## 1. Who uses it

**Students** (demo learners from the simulator, `reports/learning_path/`):
- **Ali:** strong in loops, weak in functions. 3 concepts mastered, 62 to go, about 32 days at
  30 minutes a day. Writes to the tutor in UrduLish.
- **Sara:** fast but careless (speed factor 0.46: twice as fast as typical). 18 days to finish.
- Context: Pakistani students, mostly on **Android phones**, often on mobile data, often studying
  late ("1 a.m., my recursion code keeps calling itself" is the scenario from Day 3).
  So: **mobile-first, light pages, code editor usable on a phone, works on a slow connection**.

**Teachers:** one teacher, many students. 3,000 assignments arrive every Sunday (Day 4 scenario).
They need to know **who needs help, what is weak across the class, and what to grade or
review**, in minutes, on a laptop. Demo account: "Teacher (demo)", no invented person.

**Founder / admin:** wants proof the platform works: learning gain, time saved, safety. A
read-only "Impact" page, Day 5 Task 2.

---

## 2. Jobs to be done

| who | job | screen | success looks like |
|---|---|---|---|
| student | "What do I do now?" | Today | one clear next step, started in 1 tap |
| student | "I'm stuck at 1 a.m." | Tutor panel | a hint (not the answer) and the lecture minute to rewatch |
| student | "Did my code work, and why not?" | Exercise | result in under 5 s, one thing to fix, no hidden test revealed |
| student | "Am I getting anywhere?" | Path / Progress | concepts mastered, days left, what is next |
| teacher | "Who is about to quit?" | At-risk | ranked list with a reason and a suggested action |
| teacher | "What is weak across the class?" | Class overview | heatmap of mastery by concept, weakest first |
| teacher | "What needs my judgement?" | Review queue | low marks, rule breaks, similarity pairs, tampering flags |
| teacher | "Is the question bank healthy?" | Question bank | questions to retire or relabel, with the evidence |
| founder | "Does it work and is it safe?" | Impact | adaptive vs fixed, tutor leak rate, sandbox report |

---

## 3. Site map

```
Login (student | teacher)
Student                                   Teacher
  Today            (home)                   Class overview   (home)
  Path                                      At-risk students
  Practice  -> Question / Exercise          Student detail   (from any list)
  Tutor     (side panel on every page,      Review queue     (grading + similarity + flags)
             full screen on phone)          Question bank
  Progress                                  Tutor usage & safety
  Settings  (language: English / UrduLish)  Impact           (founder view, read-only)
```

Navigation: student = bottom tab bar on phone (Today, Path, Practice, Progress) with the tutor
as a floating "Ask" button; left sidebar on desktop. Teacher = left sidebar, desktop-first,
still readable on a tablet.

---

## 4. Student screens

### 4.1 Today (home)

Purpose: one next step, no decisions needed.

```
+------------------------------------------------------+
| Ilm Academy                               Ali  (o)   |
+------------------------------------------------------+
| Ali, 32 days to finish at 30 min a day               |
| 3 of 65 concepts mastered                            |
|                                                      |
| NEXT                                                 |
| +--------------------------------------------------+ |
| | Strings                         about 26 minutes | |
| | Lesson: CS50P Lecture 0 - Functions, Variables   | |
| | [ Start ]                      [ Watch lesson ]  | |
| +--------------------------------------------------+ |
|                                                      |
| QUICK CHECKS (you probably know these)  18 . 1.6 h   |
|  Running a program & print     3 min    [Check]      |
|  Comments                      2 min    [Check]      |
|  Indentation & code blocks     2 min    [Check]      |
|  Show all 18                                         |
|                                                      |
| PRACTISE MORE                                        |
|  String methods (strip, title, split)   weakest      |
|  match statement                                     |
+------------------------------------------------------+
| Today    Path    Practice    Progress        [Ask]   |
+------------------------------------------------------+
```

Content is the real plan output: next concept, minutes estimate, quick checks, weakest concepts
(`ilm/adaptive/path.py`). The UrduLish version of the header uses the plan's own message:
*"Ali, Type conversion aur Lists & indexing pe tumhari grip zabardast hai, shabaash! ...
Roz sirf 30 minute do, aur poora course 32 din mein complete."*

States: **first visit** (no answers yet): "Start with a 5-question placement check, about 6
minutes" instead of a plan. **All done**: the number of concepts mastered and a review list.
**Offline**: last plan shown, "You're offline. Answers will sync when you're back."

### 4.2 Path

Purpose: see the whole route and why it is in this order.

- Vertical list grouped by lecture (CS50P L0 Functions, Variables -> L1 Conditionals -> ...).
- Each row: concept, a mastery bar (P(known), shown as words + bar: "Probably known 0.92"),
  kind (Quick check / Learn), time estimate, and status ("Ready" or "After Defining functions").
- Locked rows are greyed with the reason in text, never just a padlock icon.
- Tapping a row opens the concept: the lesson link with video timestamp, its questions, and
  "Why is this here?" (its prerequisites).

### 4.3 Question (MCQ / short answer)

- Stem, code block (monospace, syntax-highlighted, horizontally scrollable on phone), options
  as full-width tap targets (min 44 px high).
- After answering: correct -> one line of why + Next. Wrong -> the misconception behind the
  chosen option, from the question's own `misconceptions` field, e.g. for `17 % 5`:
  *"% gives the remainder, not the quotient (that is 17 // 5)."* Then "Try a similar one" or
  "Ask the tutor".
- Progress inside a session: "Question 3 of about 8", not a fake percentage.

### 4.4 Code exercise

Purpose: write, run, get feedback, without ever being handed the solution.

```
Desktop                                        Phone: tabs [Task] [Code] [Result]
+---------------------------+-------------------------------+
| count_letters             |  1 def count_letters(word):   |
| Write count_letters(word) |  2     counts = {}            |
| that returns a dictionary |  3     for ch in word:        |
| mapping each letter to    |  4         counts[ch] = 1     |
| how many times it         |  5     return counts          |
| appears.                  |                               |
| count_letters("aab")      |  [ Run tests ]   Saved 12:04  |
| returns {"a": 2, "b": 1}  +-------------------------------+
|                           | 1 of 3 tests passed  (3.3/10) |
| Lesson: CS50P L2 Loops    | x count_letters("aab") should |
|                           |   give {'a': 2, 'b': 1}, got  |
|                           |   {'a': 1, 'b': 1}            |
|                           | x 1 hidden test: wrong value  |
|                           |                               |
|                           | Next step: count_letters("aab")|
|                           | should give {'a': 2, 'b': 1}, |
|                           | but your code returned        |
|                           | {'a': 1, 'b': 1}. Trace it by |
|                           | hand with that input.         |
|                           | Rewatch: Loops notes:         |
|                           |   Dictionaries (part 3)       |
|                           | [ Ask the tutor about this ]  |
+---------------------------+-------------------------------+
```

- Editor: CodeMirror 6 (light, works on phones), Python highlighting, autosave to the device.
- Result panel is exactly the Day 4 feedback (`ilm/grading/feedback.py`): visible failures in
  full, hidden ones only as count + kind, one next step, lesson link. Never more than one
  "Next step".
- Running state: "Running your code in a safe sandbox..." with elapsed seconds (about 1 s). If
  over 10 s: "Your code is taking a long time. Is there a loop that never ends?"
- Blocked code (sandbox): calm message, no accusation: "Your code tried to reach the internet,
  which exercises can't do."

### 4.5 Tutor panel

Purpose: the Socratic tutor from Day 3, available everywhere.

- Desktop: right-side panel (380 px). Phone: full screen sheet with a back arrow.
- Opens with context already attached: "About: count_letters, your last run (1 of 3 passed)".
- Replies show their **sources as links under the message** (lesson + timestamp), built from
  source ids, exactly as the tutor returns them.
- Hint ladder made visible: a small stepper "Hint 1 of 4: a question" -> "2: the concept" ->
  "3: part of a line" -> "4: a similar example". The student chooses "Another hint", so getting
  more help is a deliberate act, not automatic.
- Language follows the student: UrduLish in, UrduLish out; a toggle in Settings forces one.
- Refusals are short and kind, never preachy: "That's not in our course, so I won't guess. Ask
  me anything about Python and I'll point you to the lesson."
- Empty state: three real starters from the course, e.g. "Why does my function keep calling
  itself?", "print aur return mein kya farq hai?", "What does input() give back?".

### 4.6 Progress

- Concepts mastered over time (a simple line, weeks on the x-axis).
- This week: answers, minutes, accuracy last 10. No streak guilt ("You broke your streak!").
- Strongest / weakest concepts with a "Practise" link.

---

## 5. Teacher screens

### 5.1 Class overview (home)

```
+-----------+--------------------------------------------------------------------+
| Ilm       | Class overview                        Week {w} . {n} students      |
| Academy   |                                                                    |
|           |  Active this week {active}   At risk {high} high . {medium} medium |
| Overview  |  Mastered (avg) {avg} of 65 concepts   Review queue {items} items  |
| At risk   |                                                                    |
| Review    |  Weakest concepts this week                                        |
| Questions |  {concept}                              ######..........  {pct} know|
| Tutor     |  {concept}                              #######.........  {pct}     |
| Impact    |  {concept}                              ########........  {pct}     |
|           |                                                                    |
|           |  Mastery by concept and student group          [ by lecture v ]    |
|           |            L0  L0  L0  L1  L1  L2  L2  L3 ...                       |
|           |  Group A   ##  ##  #   ##  #   .   .   .                            |
|           |  Group B   ##  #   #   #   .   .   .   .                            |
+-----------+--------------------------------------------------------------------+
```

- The `{fields}` above are filled by `GET /class/overview` at run time; this plan does not make
  up class numbers. In the demo they come from the simulator's cohort (1,000 students, `python
  -m ilm.learners.simulator`); the weakest concepts are whatever the mastery data says that week.
- Heatmap: single-hue sequential scale (light = few know it, dark = most know it), with the
  value on hover/tap and a legend in words. Rows = groups (or students when filtered),
  columns = concepts in course order, grouped by lecture.
- Every number links to its list (118 high risk -> the At-risk page filtered).

### 5.2 At-risk students

Real levels and actions from the dropout model (`reports/dropout/report.md`):

| level | what the teacher sees | suggested action |
|---|---|---|
| High | top 10% by risk | "Call within 24 hours" |
| Medium | next 20% | "Send an UrduLish nudge in the app / WhatsApp" |
| Low | the rest | weekly summary only (not listed by default) |

Each row: student, level (text + colour), the **reason** from SHAP in words ("Struggling: 7
of last 10 wrong" or "Inactive: no answers for 9 days"), last active, and the action as a
button ("Mark as called", "Send nudge"). Reason-specific actions: struggling -> easier
questions + offer the tutor on the last mistake; inactive -> reminder at their usual study time
+ a 10-minute quick win.

Never show a raw probability alone ("0.734"); show the level and the reason.

### 5.3 Student detail

Path progress, mastery per concept (same bars as the student sees), recent answers with
misconceptions, tutor conversations (with consent note), submissions and feedback. The teacher
sees what the student sees, plus the risk reason.

### 5.4 Review queue

One queue for everything that needs a human, in priority order:

1. **Possible copying - needs teacher review:** the ranked queue from Day 4 Task 5 (top 5
   pairs per exercise), side-by-side code with matching lines highlighted, and the scores.
   Buttons: "Not copying", "Talk to students", "Escalate". No "Plagiarism detected" anywhere.
2. **Tampering flags** from the sandbox ("output contains fake result lines").
3. **Low marks to check:** marks under 4 where tests can't see a good idea (Day 4 Task 2:
   off-by-one or print-instead-of-return gets 0 from tests; a human gives 3-4).
4. **Rubric-graded written answers** where the LLM grader is unsure (Day 4 Task 4).

Each item shows why it is in the queue, in one line. Keyboard: J/K to move, 1/2/3 for actions.

### 5.5 Question bank

From Day 3 (`reports/difficulty/`, `reports/question_gen/`):
- Health summary: 225 questions; **13 to retire** (strong and weak students do equally well,
  so they don't measure anything; includes all 12 planted bad ones), **40 to relabel**
  (author's difficulty 2+ levels from measured).
- Table: question, concept, type, author difficulty vs measured, discrimination, decision,
  with "Retire" / "Relabel to 4" buttons.
- Generated questions waiting for review (v2: 143 accepted by the code gates), clearly marked
  "Generated, not yet answered by students".

### 5.6 Tutor usage & safety

- Conversations per day, top concepts asked about, share in UrduLish.
- Safety, from `reports/tutor_eval/README.md`: answer leaks in evaluation (run 1: 6 of 51;
  v2: 0 of 51 + 0 of 24 held-out; v3: 0 of 24 on a second held-out set), jailbreaks resisted, leaks blocked live by the
  checker. Each number links to its report.

### 5.7 Impact (founder view)

Adaptive vs fixed path (Day 2): week-3 dropout -11 points, concepts known -5.1 (depth vs
breadth, shown honestly), teacher hours saved by auto-grading, the A/B test design (Day 5 Task 2),
and the safety numbers. Every chart has a one-sentence takeaway above it, written from the
data, and a "How this was measured" link.

---

## 6. Visual design

**Idea:** a well-made school notebook: paper-white surfaces, dark ink, one green accent.
Calm and serious; this is a place to concentrate, not a game.

### Colour (CSS variables, light theme first; dark theme for late-night study)

| token | light | dark | use |
|---|---|---|---|
| `--ink` | #1B1F23 | #E6E8EB | text |
| `--ink-2` | #57606A | #9AA4AE | secondary text |
| `--paper` | #FBFAF7 | #111417 | page background (warm off-white, not pure white) |
| `--surface` | #FFFFFF | #181C20 | cards, panels |
| `--line` | #E3E1DA | #2A3036 | borders, dividers |
| `--accent` | #0F6B5C | #3FB59E | primary buttons, links, focus ring (deep teal-green) |
| `--accent-soft` | #E4F1EE | #15302B | selected rows, hint backgrounds |
| `--ok` | #1A7F37 | #3FB950 | passed tests (always with a check mark + text) |
| `--warn` | #9A6700 | #D29922 | medium risk, "needs review" |
| `--bad` | #C4321F | #F85149 | failed tests, high risk (always with text) |

Heatmap: a 6-step scale of `--accent` from 8% to 100%, never red-to-green (colour-blind
students and teachers).

### Type
- UI: **IBM Plex Sans** (400, 500, 600). Readable, a little technical, not the default Inter.
- Code: **IBM Plex Mono** (same family, so code and text sit well together).
- Scale: 13 / 15 / 17 / 20 / 24 / 32 px. Body 15 px on desktop, 16 px on phones. Numbers use
  tabular figures in tables and stats.
- Sentence case everywhere ("Review queue", not "Review Queue"); no all-caps except tiny labels.

### Shape and spacing
- 4 px grid; spacing 4 / 8 / 12 / 16 / 24 / 32 / 48.
- Radius: 6 px (inputs, buttons, cards), 10 px only for sheets and dialogs.
- Borders (1 px `--line`) separate things; shadows only on menus, popovers and dialogs.
- Icons: Lucide, 1.5 px stroke, 16/20 px, always next to a word, never decorative.

### Motion
Short and functional: 120-180 ms for panels and hovers; respect `prefers-reduced-motion`.
No confetti. A correct answer gets a check mark and the next button, that's all.

---

## 7. Words (microcopy)

- Say the fact, then the action: "1 of 3 tests passed. Trace count_letters("aab") by hand."
- Use the student's name only where a teacher would.
- Errors explain what to do: "We couldn't reach the server. Your code is saved on this phone."
- Never blame: "Your code tried to read a file outside the exercise", not "Malicious code detected".
- UrduLish copy is written like a Pakistani teacher talks (the tutor's style), not machine-translated.

Banned words and phrases: "Unlock", "Supercharge", "Seamless", "Revolutionize", "Journey",
"Oops!", "Awesome!" after every action, "AI-powered" as a label on every feature.

---

## 8. Accessibility and performance

- WCAG 2.1 AA contrast (all token pairs above checked at 4.5:1 for text).
- Everything works with the keyboard; visible focus ring (2 px `--accent`).
- Tap targets at least 44 x 44 px; the code editor has a larger font option.
- Screen readers: test results are a list with "passed" / "failed" in text; charts have a table view.
- Budget: first load under 200 KB of JavaScript (gzip) for the student app; editor and charts
  load only on the screens that use them. Usable on a slow 3G connection.
- Drafts (code and answers) saved on the device, so a dropped connection loses nothing.

---

## 9. Build choices

| need | choice | why |
|---|---|---|
| app | React 18 + Vite + TypeScript | fast build, typed API calls |
| routing / data | React Router, TanStack Query | caching, retries, "last known data while refreshing" |
| styling | CSS modules + the tokens above (no UI kit defaults) | kits' default look is part of the "AI-generated" feel; we own every style |
| accessible primitives | Radix UI (unstyled) for dialog, menu, tabs, tooltip | behaviour and a11y without a look |
| code editor | CodeMirror 6 | small, mobile-friendly |
| charts | hand-built SVG for the heatmap; Recharts for line/bar | the heatmap is the hero chart, so it is built exactly to spec |
| auth | FastAPI issues a JWT in an httpOnly cookie; role = student / teacher | role-based access (Day 5 Task 3) |
| hosting | Vercel (app) + Oracle Cloud VM with Docker (API, DB, sandbox) + Caddy for HTTPS | see the deployment discussion |

---

## 10. API the screens need (FastAPI, `ilm/api`)

| screen | endpoint | backed by |
|---|---|---|
| Today, Path | `GET /me/path` | `ilm/adaptive/path.py` |
| Question | `GET /practice/next`, `POST /answers` | adaptive engine, mastery tracker |
| Exercise | `POST /submissions` -> `GET /submissions/{id}` | sandbox, grader, feedback |
| Tutor | `POST /tutor/ask`, `POST /tutor/hint` | `ilm/tutor/tutor.py` |
| Class overview | `GET /class/overview`, `GET /class/heatmap` | mastery per student |
| At risk | `GET /class/at-risk` | `ilm/analytics/dropout.py` |
| Review queue | `GET /review`, `POST /review/{id}` | grader, plagiarism queue, sandbox flags |
| Question bank | `GET /questions/health` | difficulty + IRT reports |
| Tutor safety | `GET /tutor/stats` | tutor logs + eval reports |

---

## 11. The 10-minute demo, screen by screen

| minute | show | screen |
|---|---|---|
| 0-1 | two learners, two different paths (Ali 32 days, Sara 18 days) | Today, as Ali then Sara |
| 1-3 | stuck on recursion: tutor gives hint 1, then 2, with the video minute | Exercise + Tutor panel |
| 3-4 | jailbreak attempt refused, calmly | Tutor panel |
| 4-5 | submit code: partial marks, one next step, hidden test not revealed | Exercise |
| 5-6 | submit a fork bomb: blocked, the app stays up | Exercise |
| 6-7 | a similarity pair in the review queue, side by side, "Not copying" | Review queue |
| 7-9 | class heatmap, weakest concept, at-risk list with reasons and actions | Teacher overview, At risk |
| 9-10 | impact and safety numbers, each linked to how it was measured | Impact |

---

## 12. Build order

1. Tokens + layout shells (student tab bar, teacher sidebar), login, routing.
2. Exercise screen with the real sandbox, grader and feedback (the most-used and most-demoed screen).
3. Tutor panel.
4. Today + Path.
5. Teacher overview + heatmap, At risk.
6. Review queue (similarity side by side).
7. Question bank, Tutor safety, Impact.
8. Empty / loading / error / offline states on every screen; accessibility pass; phone pass on a
   real Android device.

## 13. Open questions

1. Real student names, or keep "Ali" and "Sara" as demo learners? (Recommended: demo learners,
   labelled as such.)
2. Should teachers see tutor conversations by default, or only with the student's consent?
3. WhatsApp nudges: real integration, or a "Copy message" button for the demo?
