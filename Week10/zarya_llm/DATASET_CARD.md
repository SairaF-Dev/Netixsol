---
language:
- ur
- en
license: apache-2.0
task_categories:
- text-generation
- text2text-generation
tags:
- banking
- fintech
- urdulish
- roman-urdu
- qwen2.5
- lora
- qlora
- instruction-tuning
pretty_name: Zarya Digital Bank UrduLish Assistant Dataset
size_categories:
- 1K<n<10K
---

# Dataset Card: Zarya Digital Bank UrduLish Assistant Dataset

## 1. Dataset Summary

The **Zarya Digital Bank Assistant Dataset** is an enterprise-grade synthetic banking conversation corpus crafted to fine-tune compact open-source language models (specifically **Qwen 2.5 3B Instruct**) for retail digital banking in Pakistan. 

The dataset establishes natural conversational fluency in **UrduLish** (an authentic informal blend of Roman Urdu and English vocabulary), enforces strict State Bank of Pakistan compliance and safety guardrails, refuses credential disclosure requests, and outputs deterministic, machine-readable structured complaint tickets.

### Key Dataset Metrics:
* **Total Cleaned & Verified Examples**: 2,534
* **Train Split (90%)**: 2,099 examples
* **Validation Split (10%)**: 235 examples
* **Human-Verified Golden Test Set**: 200 examples (isolated, zero training contamination)
* **Dual Example Architecture**:
  * **Type A (Customer Chat)**: Polite natural language replies using *Ji* and *aap*, strictly grounded in context documents, zero raw JSON.
  * **Type B (Structured Extraction)**: Plain dialogue transcript input mapped to pure, validated JSON complaint ticket output conforming to `BankingTicket` schema.

---

## 2. Dataset Splits and Partitioning

| Split | Description | Examples | Percentage |
| :--- | :--- | :---: | :---: |
| **Train** | Cleaned training split for LoRA / QLoRA SFT fine-tuning | 2,099 | 89.9% of clean |
| **Validation** | Stratified validation set for checkpoint selection & perplexity | 235 | 10.1% of clean |
| **Golden Test** | Human-verified golden benchmarks, never seen during training | 200 | Standalone Benchmark |
| **Total** | Full curated dataset corpus | **2,534** | **100.0%** |

---

## 3. Linguistic Distribution

The corpus captures authentic linguistic patterns of retail banking customers across Pakistan:

| Language Mode | Examples | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **UrduLish** | 1,578 | 62.3% | Natural blend of Roman Urdu with English banking terminology |
| **Roman Urdu** | 506 | 20.0% | Phonetically transcribed Urdu in Latin script |
| **English** | 364 | 14.4% | Professional Pakistani banking English |
| **Urdu Script** | 86 | 3.4% | Standard Arabic/Nastaliq Unicode script |

---

## 4. Operational Category Distribution

The dataset spans 31 distinct banking intents across 7 core operational banking categories:

| Category | Train | Val | Golden Test | Total | Share (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Fraud & Scams** | 531 | 60 | 39 | 630 | 24.9% |
| **Customer Complaints** | 418 | 47 | 40 | 505 | 19.9% |
| **Card Operations** | 277 | 31 | 24 | 332 | 13.1% |
| **Fund Transfers** | 321 | 36 | 42 | 399 | 15.7% |
| **Account Inquiries** | 213 | 23 | 20 | 256 | 10.1% |
| **Loans & Financing** | 215 | 24 | 22 | 261 | 10.3% |
| **Out of Scope** | 124 | 14 | 13 | 151 | 6.0% |

---

## 5. Structured Output Schema (Type B Ticket Extraction)

For ticket extraction tasks, the model outputs pure parseable JSON without code fences conforming to the following Pydantic schema:

```json
{
  "intent": "transfer_failed",
  "category": "transfer",
  "priority": "medium",
  "amount": 3000.0,
  "time_mentioned": "kal raat",
  "summary": "Raast transfer failed but funds debited from account",
  "customer_very_angry": false,
  "escalate_to_human": false
}
```

### Deterministic Human Escalation Rules:
The field `escalate_to_human` evaluates to `true` if and only if:
1. `category == "fraud"` (potential scams, phishing links, social engineering calls)
2. `amount >= 50000.0` (high value transaction disputes)
3. `customer_very_angry == true` (severely escalated customer sentiment)

---

## 6. How to Use with Hugging Face & Qwen 2.5

```python
from datasets import load_dataset
from transformers import AutoTokenizer

# Load the dataset
dataset = load_dataset("json", data_files={
    "train": "data/train/train.jsonl",
    "validation": "data/val/val.jsonl",
    "test": "data/golden/golden_test.jsonl"
})

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

# Format conversations using the official chat template
def apply_template(example):
    prompt_text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False
    )
    return {"text": prompt_text}

formatted_dataset = dataset.map(apply_template)
print(formatted_dataset["train"][0]["text"])
```

---

## 7. Quality, Privacy, and Ethical Guardrails

1. **Synthetic Data Policy**: All customer names, transaction IDs, phone numbers, and account records are 100% synthetically generated.
2. **PII Masking**: Sanitized via Microsoft Presidio and strict regex patterns matching Pakistani CNIC, 16-digit debit cards, and IBAN numbers.
3. **No Credential Harvesting**: Assistant strictly refuses to request, accept, or process customer OTPs, PINs, or CVVs.
4. **Zero Policy Hallucinations**: Assistant numbers and fees are strictly grounded in retrieved synthetic context documents (`Documents:`). If no documents are retrieved (`koi document nahi mila`), the assistant refers to the helpline with 0 numbers.
