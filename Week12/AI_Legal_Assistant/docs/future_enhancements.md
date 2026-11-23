# Future enhancements

What would make the assistant more accurate, safer and ready for real use, in order of value. Each item names
the evidence behind it - a measured gap, a red-team finding or a known shortcut - so it can be checked.

## 1. Accuracy

| Enhancement | Why (evidence) | How |
|---|---|---|
| **Section numbers for Urdu laws** | The 40 Urdu statutes come from scans (OCR character error about 33%), so they are cited by page, not by section, and Urdu keyword search is weak. | Better OCR (a fine-tuned Urdu model), then align each Urdu law with its English version to carry section numbers across; character n-grams for Urdu keyword search. |
| **A lawyer-checked evaluation set** | The 100 evaluation questions, the graph answer keys and the conclusion-check review were drafted by an AI model and only partly checked by a person. The blind rating of 30 answers is the first fully human judgment. | Have a lawyer review all 100 questions and their reference answers; grow the set with real questions from the firm. |
| **Finish the Day 2 comparison** | The answer metrics for the last two retrieval steps (metadata filters, parent-child) were not run for lack of Gemini quota. | Run them; adopt either step only if it beats the current default. |
| **A stronger conclusion check** | It caught the wrong conclusions it was tested on (4 of 4 flags right), but on 79 answers only, and it is itself a language model. | A larger labelled set; a second, different model as checker; show its reasoning to the lawyer. |
| **More case law** | 225 judgments from two courts. | Add the other High Courts and older reported judgments; keep the graph extraction measured (precision / recall per relationship). |
| **Contract extraction** | Two CUAD contracts are still split wrongly (one is a scan), and party names are found in 60% of contracts. | OCR for scanned contracts; a model for parties and dates checked against a hand-labelled sample. |

## 2. Security (from the red-team report)

| Enhancement | Why | How |
|---|---|---|
| **Mask personal data before it reaches the model** | A CNIC or phone number typed into a question is sent to Gemini as typed; only the logs are masked. | Replace identifiers with placeholders (`[CNIC-1]`) before the call and put them back in the answer. |
| **A limit per user** | One signed-in user can use up the whole day's Gemini quota. | A daily question limit per user, and a rate limit at a reverse proxy. |
| **More languages in the upload scanner** | An injection in French passes the scanner (the prompt fence still stopped it in the review). | Patterns for more languages, or a small classifier trained on injection examples. |
| **Single sign-on and two-factor sign-in** | Accounts are local, with passwords only. | Sign-in through the firm's Microsoft or Google accounts; matters taken from the firm's practice-management system. |
| **Close the open pages** | `/api/health` and `/api/docs` answer without sign-in (they hold no data). | Only "ok / not ok" for anonymous health checks; API docs behind sign-in. |
| **Browser-side review** | Not covered by the red team (e.g. script injection through rendered text). | The front end already inserts all text as text, never as HTML; add a content-security policy and an automated scan. |
| **Encryption and retention** | Uploaded contracts are stored as files on the server's disk. | Encrypted storage, a retention period per matter, deletion when a matter closes. |

## 3. Product

| Enhancement | Why |
|---|---|
| **Feedback on every answer** | A "helpful / wrong" button turns daily use into new evaluation data, like the blind rating. |
| **Matter workspaces** | Save questions, reviews and drafts per matter, so a team sees each other's work on the same file. |
| **Track changes in Word** | Reviews come as margin comments today; suggested wording as real tracked changes would save the lawyer retyping. |
| **The firm's own precedents** | Search the firm's past opinions and agreements (per matter, with the same access rules) alongside public law. |
| **Citation alerts** | Warn when a cited judgment is later overruled or distinguished, using the knowledge graph. |
| **Urdu interface** | The answers already follow the question's language; the pages themselves are in English. |

## 4. Operations

| Enhancement | Why |
|---|---|
| **An always-on host** | The free live link (GitHub Codespaces) stops after 4 hours idle and runs about 60 hours a month. A small paid server (2 vCPU, 4 GB) or a cloud container service would keep it up; the Docker image is ready for either. |
| **A real database for state** | Jobs, accounts and matters live in SQLite and JSON files - fine for one server, not for several. Move them to PostgreSQL. |
| **Monitoring and alerts** | Health is checked by hand today. Send `/api/health` to an uptime monitor and alert on `down`, blocked uploads and denied access. |
| **Smaller models** | ONNX Runtime already cut the image from 4.41 to 2.68 GB and memory from 2.5 to 1.7 GB. The 8-bit model versions would cut memory further, after checking they keep the same rankings. |
| **Automatic backups** | Back up `data/security`, uploads, the index and the answer cache on a schedule (admin guide, section 8). |

---

This is an engineering prototype for evaluation, not a product giving legal advice. Every output is a draft
for a qualified lawyer to check.
