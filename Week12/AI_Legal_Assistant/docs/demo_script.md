# 10-minute demo script

For the person presenting the AI Legal Assistant live. Each block gives the time, what to click, what to say
(in *italics*), and what the audience should see. Every step was rehearsed on the live server on 2026-11-24.
The times shown are from that run. All the questions below were asked once then, so their answers are cached
on the server and use no Gemini quota.

**The story in one line:** a lawyer at a Pakistani firm researches the law, checks case law, reviews and
compares a client contract, and the system shows at every step why its output can be trusted: verified
quotes, refusals when the law is not in the library, matter walls, a blocked attack, and measured accuracy.

| Time | Part | Page |
|---|---|---|
| 0:00 | Opening | 01 |
| 0:45 | Research in three languages, and a refusal | 01 |
| 3:30 | Case-law graph | 02 |
| 4:30 | Contract review | 03 |
| 6:15 | Comparing two versions | 04 |
| 7:15 | Security: a booby-trapped upload, matter walls, the audit log | 06, 03, 08 |
| 8:45 | How well it works | 07 |
| 9:40 | Close | - |

---

## Before the audience arrives (15 minutes before)

1. **Start the codespace.** Open github.com/codespaces and open `legal-assistant`, or run any
   `gh codespace ssh -c legal-assistant-g45g44rgv95vfgpv` command. Then make sure the server runs (in the
   codespace terminal: `bash deploy/codespaces/start.sh`).
2. **Make port 8000 public** (it turns private when the codespace stops):
   `gh codespace ports visibility 8000:public -c legal-assistant-g45g44rgv95vfgpv`.
3. **Warm the server up.** Sign in and ask any one of the questions below. The first question after a start
   takes about 100 seconds, because the search models load; after that, the times below apply.
4. **Open three browser tabs** (each tab has its own sign-in):

   | Tab | Account | Used for |
   |---|---|---|
   | 1 | `ayesha` (associate, matters MAT-001 and MAT-002) | almost everything |
   | 2 | `bilal` (associate, matters MAT-003 and MAT-004) | the matter wall |
   | 3 | `admin` | the audit log |

   The passwords are in `data/security/initial_passwords.txt` on the laptop, which is not in git. Never
   show that file on screen.
5. **Have the demo file ready:** `docs/demo/hosting_agreement_hidden_text.docx`. It is a normal hosting
   contract with one sentence in white text.
6. **Light theme** for a projector; zoom the browser to about 110%.

---

## 0:00 Opening (45 s) - page 01, tab 1

*"Lawyers in Pakistan spend hours finding the right section, the right judgment, and checking every quote.
General chatbots make this worse: they invent sections and case citations that look real. This assistant
answers only from a library of 323 Pakistani Acts and judgments, which makes 11,232 searchable passages,
in English, Urdu and Roman Urdu. Every quote it shows has been checked word for word by code, not by the AI.
When the library has no answer, it says so."*

Point at the left menu: research, case law, contract review, comparison, drafting, uploads, accuracy reports.

## 0:45 Research in three languages, and a refusal (2 min 45 s)

**1. Roman Urdu.** Type: `Agar consideration unlawful ho to kya contract void hai?` and click
**Execute Research**. It takes about 18 seconds; talk while it runs.

*"While it searches: it combines keyword and meaning-based search, then a second model reranks the best 30
passages. That reranking is the slow part, and it is what puts the right passage in the top five 78% of
the time instead of 54%."*

You see a Roman Urdu answer: *"Haan, agar kisi agreement ka consideration ya object unlawful ho toh woh
agreement void hota hai"*, citing **Contract Act, 1872, Section 23**, and the conclusion check
**supported**.

*"The answer is in the language I asked in, but the source on the right is the actual text of Section 23,
quoted exactly. Copy Citation pastes it into a memo. Underneath, a second check confirms that the answer
actually follows from the quote."*

**2. Urdu.** Click the Urdu example button (*معاہدہ ایکٹ 1872: دفعہ 74 ...*), about 19 seconds.

You see an Urdu answer on compensation for breach, citing the Urdu text of the Contract Act.

*"The Urdu statutes are scanned books. We ran them through OCR, so this quote comes from the scanned page,
and it is cited by page."*

**3. A refusal.** Type: `Industrial Relations Act, 2012 ke tehat trade union bananay ke liye kam az kam
kitne workers ki zaroorat hoti hai?`, about 20 seconds.

You see **"No sufficient source found"** and no citations.

*"That Act is not in the library. A chatbot would answer anyway, probably with a plausible number. This
one refuses. Our test set has 20 questions whose answer is not in the library; the app refused every one it
was tested on."*

> Spare question if there is time: the example button *Contract Act, 1872: Voidability of Unlawful
> Consideration (Section 23)* gives the same section in English.

## 3:30 Case-law graph (1 min) - page 02

Click the example **Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan
Penal Code?**, about 3 seconds.

You see 8 judges, including Yahya Afridi, Ghulam Sarwar Nihung and Jamal Khan Mandokhail, and the database
query that produced them.

*"Questions about relationships, like which judges, which cases cite which, are answered from a knowledge
graph of 1,649 judgments, not from text search. On these questions the graph scores an F1 of 0.99; plain
text search scores 0.40. And it shows the exact query it ran, so it can be checked."*

Then click **Which precedent is cited the most in the corpus?** You see **2009 SCMR 230** first.

## 4:30 Contract review (1 min 45 s) - page 03

Pick **IT Services and Supply Agreement (version 2, Contractor's markup)**. Under *Representing Client
Party* write `Pak Telecom Enterprises (the Client)`, then click **Execute Audit**. It takes about 12 seconds,
and the progress shows.

You see **risk 64, High**: 5 red, 4 amber, 5 missing.

*"Each item of the firm's playbook gets a colour. Red here: the contract is under Pakistani law, but
disputes go exclusively to courts in Dubai. And the contractor's liability is capped at one month of fees,
while our client's liability has no cap at all. Each finding quotes the clause, explains why, and suggests
replacement wording."*

Click **Download**: a Word file with each finding as a margin comment, ready for a partner.

## 6:15 Comparing two versions (1 min) - page 04

Tick **Use standard sample agreement pair**, write the same client name, then click **Generate Blackline**.
It takes about 12 seconds.

You see 9 changes, word-level, each with its legal effect for the client. Point at three of them:

* **Payment:** 30 days became 60 days.
* **Non-solicitation for 12 months** became a **three-year non-compete**.
* **Governing law and jurisdiction:** still Pakistani law, but disputes now go exclusively to courts in Dubai.

*"This is the contractor's markup of what we sent. In our test we planted 9 changes in a contract, and it
found all 9. The download is a Word redline."*

## 7:15 Security (1 min 30 s)

**1. A booby-trapped upload** (page 06, tab 1). Matter **MAT-001**, file
`hosting_agreement_hidden_text.docx`, then click **Index Document**.

You see it **blocked**: *"This document contains text addressed to an AI system, which looks like a
prompt-injection attempt. It was not processed."* The hidden sentence is shown.

*"This contract looks normal on screen, but one sentence in white text tells the AI to rate every clause
as acceptable. The upload is screened before any AI sees it. We attacked the app 80 ways; 78 held. On
9,071 real legal texts, the screen raised no false alarms."*

**2. The matter wall** (tab 2, signed in as `bilal`, page 03). Open the contract list.

*"Bilal works on other clients. Ayesha's supply agreement is not in his list, and even asking the server
for it directly returns 'not found, or not on one of your matters'. The same filter applies to search, so
his research never sees another client's contract."*

**3. The audit log** (tab 3, `admin`, page 08).

*"Every sign-in, question, review and download is logged. Personal data like CNIC and phone numbers is
masked in the log, and each entry carries the hash of the one before it, so editing or deleting a line
breaks the chain. Here it says the chain is intact."*

## 8:45 How well it works (55 s) - page 07, tab 1

Scroll slowly through the tiles.

*"These numbers come straight from our evaluation files, not typed in by hand:"*

* 78% of questions get the right passage in the top five (54% for plain search).
* 478 citations checked by code; **0 invented citations reached a user**. The ones the AI made up were
  caught and removed.
* 100% correct refusals; graph F1 0.99 against 0.40; 78 of 80 attacks held.
* A research answer takes 16.6 seconds (median), about **$1.83 per 1,000 questions** at Gemini's paid
  price, or free on the free tier.

*"And where it is weak, the reports say so: query rewriting would reach 94% recall but costs an extra AI
call per question, and one attack in French got past the screen, although the second line of defence held."*

## 9:40 Close (20 s)

*"So: answers grounded in Pakistani law and checked by code, refusals instead of guesses, contract review
and comparison a lawyer can download and use, and security built in. Everything it drafts is marked for
lawyer review. It assists the lawyer; it does not replace them. Thank you. Questions?"*

---

## If something goes wrong

| Problem | What to do |
|---|---|
| The page does not open / asks for GitHub sign-in | The codespace stopped or the port is private: steps 1-2 above. |
| A question takes over a minute | The server was cold (first question after a start). Keep talking; next time warm it up. |
| "The free Gemini limit for today is used up" | Use only the questions in this script: they are cached and still work. |
| Gemini is slow ("high demand") | Cached questions are not affected; skip any new question. |
| "The case-law graph is not reachable" | Neo4j AuraDB is paused: resume it in the Aura console (1-2 minutes), or skip to page 03. |
| Codespace unavailable | Run it on the laptop: `python -m web.server`, then http://127.0.0.1:8000. Answers are not cached there, so expect about 30 seconds per question. |

## Likely questions

* **Why Gemini Flash-Lite?** Cheap and fast enough, and the safety does not depend on the model: quotes are
  checked by code, and anything unverified is removed.
* **Why not always use query rewriting (94%)?** One more AI call per question, against a free limit of
  about 500 calls a day; the reranker gets most of the gain without it.
* **Where do the statutes come from?** Judgments and Urdu laws from official court and Ministry listings
  (`data/source_catalog.csv`); the Urdu books are scanned and read with OCR.
* **Could a real firm use it?** The pieces are there: sign-in, matter walls, an audit log, Docker, health
  checks and CI. What it would need next is listed in [future enhancements](future_enhancements.md).
