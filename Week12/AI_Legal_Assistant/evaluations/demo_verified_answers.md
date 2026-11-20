# Demo: 5 answers with verified citations (Day 2)

Pipeline: retrieval configuration `rerank` → Gemini answer (short answer, explanation, citations
with quotes) → code verification of every citation (`src/rag/verify.py`: passage exists, Act/case
matches, section/paragraph exists in the corpus, quote appears verbatim). Unverified citations are
removed; an answer with none left becomes "No sufficient source found". Then a conclusion check
(`src/rag/conclusion_check.py`) asks whether the conclusion actually follows from the retrieved passages;
an answer that fails is drafted once more with the reviewer's note, and withheld if it fails again.

## Example from the brief (Roman Urdu, statute)

Verified citations shown: 1; removed by verification: 0.

```text
================================================================================
QUESTION: Agar consideration unlawful ho to kya contract void hai?
================================================================================

SHORT ANSWER
  Ji haan, agar kisi muahiday (agreement) ka consideration ya maqsad (object) unlawful ho to woh muahida void hota hai.

EXPLANATION
  Contract Act, 1872 ki Section 23 wazeh karti hai ke har woh muahida jiska consideration ya maqsad unlawful ho, woh void qarar diya jata hai.

CITATIONS (verified against the source text)
  [1] Contract Act, 1872, Section 23 - What considerations and objects are lawful and what not, page 19
      "Every agreement of which the object or consideration is unlawful is void."

SOURCES RETRIEVED (rerank)
  1. Contract Act, 1872 | Section 23 | page 19
  2. Contract Act, 1872 | Section 24 | page 21
  3. Contract Act, 1872 | Section 23 | page 19
  4. Lahore High Court | Writ Petition No.12069 of 2010 | para 22 | page 28
  5. Contract Act, 1872 | Section 25 | page 21

This is research assistance from the firm's document corpus, not legal advice.
```

## Penal Code (English)

Verified citations shown: 1; removed by verification: 0.

```text
================================================================================
QUESTION: What is the punishment for qatl-e-amd under the Pakistan Penal Code?
================================================================================

SHORT ANSWER
  The punishment for qatl-e-amd includes death as qisas, death or life imprisonment as ta'zir, or imprisonment for up to twenty-five years depending on the circumstances and the applicability of qisas.

EXPLANATION
  Under Section 302 of the Pakistan Penal Code, an offender is liable to death as qisas, or death or life imprisonment as ta'zir if proof under section 304 is unavailable. If qisas is not applicable according to Islamic Injunctions, the punishment is imprisonment for up to twenty-five years, unless the principle of fasad-fil-arz is attracted, in which case death or life imprisonment applies.

CITATIONS (verified against the source text)
  [1] Pakistan Penal Code, 1860, Section 302 - Punishment of qatl-e-amd, page 103
      "Whoever commits qatl-e-amd shall, subject to the provisions of this Chapter be __ (a) punished with death as qisas; (b) punished with death for imprisonment for life as ta'zir having regard to the facts and circumstances of the case, if the proof in either of the forms specified in section 304 is not available; or (c) punished with imprisonment of either description for a term which may extend to twenty- five years, where according to the Injunctions of Islam the punishment of qisas is not applicable."

SOURCES RETRIEVED (rerank)
  1. Pakistan Penal Code, 1860 | Section 316 | page 108
  2. Pakistan Penal Code, 1860 | Section 302 | page 103
  3. Pakistan Penal Code, 1860 | Section 324 | page 109
  4. Pakistan Penal Code, 1860 | Section 308 | page 105
  5. Pakistan Penal Code, 1860 | Section 320 | page 108

This is research assistance from the firm's document corpus, not legal advice.
```

## Urdu script (statute)

Verified citations shown: 0; removed by verification: 0.

```text
================================================================================
QUESTION: اگر معاہدے میں خلاف ورزی کی صورت میں جرمانے کی رقم طے ہو تو کیا عدالت اس سے زیادہ رقم دلا سکتی ہے؟
================================================================================

No sufficient source found.

(A first answer was rejected by the conclusion check: The provided passages discuss the court's power to grant specific performance despite a penalty clause, but they do not address whether the court can award damages exceeding the amount specified in that clause.)

SOURCES RETRIEVED (rerank)
  1. مخصوص دادرسی ایکٹ ، ۱۸۷۷ء | page 19
  2. مخصوص دادرسی ایکٹ ، ۱۸۷۷ء | page 16
  3. قانون معاہدہ ایکٹ ،۱۸۷۲ء | page 66
  4. انسداد دہشت گردی ایکٹ ۱۹۹۷ء | page 39
  5. مجموعہ تعزیرات پاکستان ۱۸۶۰ء | page 240

This is research assistance from the firm's document corpus, not legal advice.
```

## Case law (English)

Verified citations shown: 3; removed by verification: 0.

```text
================================================================================
QUESTION: What did the Supreme Court say about the duty of police when a court dismisses a pre-arrest bail application?
================================================================================

SHORT ANSWER
  When a court dismisses a pre-arrest bail application, police authorities are legally bound to execute the arrest immediately and in good faith, without waiting for further instructions or assuming a stay exists.

EXPLANATION
  The Supreme Court clarified that the mere filing of a petition in a higher court does not act as an implied stay of arrest. Investigating officers must enforce judicial orders promptly, as failure to do so undermines the criminal justice system and the specific judicial determination that arrest is necessary for an effective investigation.

CITATIONS (verified against the source text)
  [1] Zahid Khan, etc v. The State through Prosecutor General, Punjab and another, para 3, page 2
      "Absent such an order, a refusal of bail remains fully operative and must be implemented promptly and in good faith by investigating authorities."
  [2] Zahid Khan, etc v. The State through Prosecutor General, Punjab and another, para 6, page 3
      "This Court, therefore, finds it imperative to state clearly that investigating officers and police authorities are legally bound to act upon court orders dismissing pre-arrest bail immediately, without waiting for further instructions or presuming the existence of any stay where none has been granted."
  [3] Zahid Khan, etc v. The State through Prosecutor General, Punjab and another, para 2, page 1
      "Prompt and faithful enforcement of judicial orders is fundamental to the criminal justice system. Once pre-arrest bail is declined by a competent court of law and the accused stands exposed to arrest in accordance with law."

SOURCES RETRIEVED (rerank)
  1. Supreme Court of Pakistan | CRL.P. 645-L/2025 | para 3 | page 2
  2. Supreme Court of Pakistan | CRL.P. 645-L/2025 | paras 6-7 | page 3
  3. Supreme Court of Pakistan | CRL.P. 645-L/2025 | para 2 | page 1
  4. Supreme Court of Pakistan | CRL.P. 645-L/2025 | para 4 | page 2
  5. Supreme Court of Pakistan | CRL.P. 46/2024 | opening | page 1

This is research assistance from the firm's document corpus, not legal advice.
```

## Not in the corpus (must refuse)

Verified citations shown: 0; removed by verification: 0.

```text
================================================================================
QUESTION: What are the registration requirements for a private limited company under the Companies Act, 2017?
================================================================================

No sufficient source found.

SOURCES RETRIEVED (rerank)
  1. Supreme Court of Pakistan | C.A. 430/2026 | para 26 | page 22
  2. Supreme Court of Pakistan | C.A. 431/2026 | para 7 | page 4
  3. Supreme Court of Pakistan | C.A. 430/2026 | para 31 | page 28
  4. Supreme Court of Pakistan | C.A. 430/2026 | para 27 | page 24
  5. Lahore High Court | Civil Revision No.504 of 2015 | para 4 | page 2

This is research assistance from the firm's document corpus, not legal advice.
```
