# Preference Dataset Documentation (DPO / RLHF)

**Project**: Zarya Digital Bank UrduLish Banking LLM  
**Target Format**: Direct Preference Optimization (DPO) Triplet `(prompt, chosen, rejected)`  
**Total Pairs**: 600 records (540 Train / 60 Validation)  
**Date**: October 2026  
**Status**: GENERATED & VALIDATED  

---

## 1. Executive Summary & Objective

In **Day 3 Task 3**, we constructed a targeted preference dataset consisting of **600 pairwise comparisons** to align the fine-tuned model via **Direct Preference Optimization (DPO)**.

While Supervised Fine-Tuning (SFT) teaches the model syntax, dialogue format, and banking vocabulary, it cannot guarantee that the model will never default to low-probability harmful responses (such as asking for an OTP, offering speculative crypto advice, or speaking informally with *tum*). DPO directly increases the log-likelihood of preferred banking responses while penalizing safety violations.

---

## 2. Rejection Taxonomy & Distribution

The dataset targets the exact failure modes discovered during Day 2 baseline and SFT testing:

| Rejection Category | Pair Count | Failure Mode Description | Desired Policy Behavior |
| :--- | :---: | :--- | :--- |
| **`credential_leak`** | **100** | Asks customer for PIN, OTP, CVV, or passwords. | Strictly refuse and warn customer against sharing codes (SBP rule). |
| **`policy_hallucination`** | **51** | Promises instant refunds or quotes unverified zero fees. | Grounded in schedule of charges; realistic TATs. |
| **`excessive_length_verbose`** | **112** | Western corporate apologetic padding (> 40 words). | Concise, mobile-first instant replies ($\le 25$ words). |
| **`missing_ji_or_informal`** | **61** | Omits *Ji* or uses disrespectful pronoun *tum* / *tu*. | Respectful honorific *Ji* and polite pronoun *Aap*. |
| **`out_of_scope_advice`** | **95** | Gives crypto, stock picking, or political advice. | Polite boundary refusal explaining banking scope. |
| **`multiple_confusing_questions`**| **64** | Asks 3 questions at once in a single turn. | Single clear, actionable question at a time. |
| **`no_escalation_on_fraud`** | **117** | Advises passive waiting during active financial fraud. | Urgent security escalation to human officer. |
| **TOTAL** | **600** | Balanced across 31 banking intents | **Complete Alignment Coverage** |

---

## 3. Dataset Schema & Concrete Example

Each record in `data/dpo/preference_pairs.jsonl` follows standard Hugging Face / TRL DPOTrainer schema:

```json
{
  "id": "dpo_pair_0235",
  "category": "account",
  "intent": "open_account",
  "rejection_reason": "missing_ji_or_informal",
  "prompt": "<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n",
  "chosen": "Ji, a customer may hold up to 11 active accounts under the same CNIC. Are you asking about a particular type of account?",
  "rejected": "Aap ka masla note kar liya hai. Baad mein check karein."
}
```

### Side-by-Side Comparison of a Preference Pair

- **Rejection Reason**: `missing_ji_or_informal`
- **Chosen Response (What the bank wants)**:
  > *"Ji, a customer may hold up to 11 active accounts under the same CNIC. Are you asking about a particular type of account?"*
- **Rejected Response (What the model must avoid)**:
  > *"Aap ka masla note kar liya hai. Baad mein check karein."*

---

## 4. Train / Validation Split Strategy

- **`data/dpo/dpo_train.jsonl`**: 540 pairs (90%) for DPO gradient updates.
- **`data/dpo/dpo_val.jsonl`**: 60 pairs (10%) held out for monitoring implicit reward margins ($r_w - r_l$) and validation loss.
- **Stratification**: Both splits maintain identical category distributions to prevent evaluation distribution shift.
