---
language:
- ur
- en
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
library_name: peft
pipeline_tag: text-generation
tags:
- banking
- fintech
- urdulish
- roman-urdu
- qwen2.5
- lora
- qlora
- dpo
- gguf
- guardrails
model_name: Zarya Qwen2.5-3B DPO Banking Assistant
---

# Model Card for Zarya Qwen2.5-3B Banking Assistant (DPO Aligned)

## 1. Model Details

- **Model Name:** Zarya-Qwen2.5-3B-DPO
- **Version:** 1.0.0 (Production Release)
- **Base Model:** [`Qwen/Qwen2.5-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- **Developer:** Zarya Digital Bank AI Engineering Team
- **Model Type:** Parameter-Efficient Fine-Tuned (PEFT / LoRA) Causal Language Model
- **Primary Languages:** UrduLish (Roman Urdu / English colloquial code-switching) & Standard English
- **Intended Domain:** Retail Digital Banking, Customer Support, Complaint Dispatch & Dispute Automation
- **Quantization Targets:** FP16, INT8, and **4-bit GGUF (Q4_K_M)** for edge/local serving.
- **License:** Apache-2.0

---

## 2. Intended Use & Capabilities

### Direct Uses
* **Automated Customer Care:** Inquiring about debit card activation, account limits, schedule of charges (SOC), ATM locator, and transaction turnaround times (TAT).
* **Card Emergency Protocol:** Processing immediate requests to block lost, stolen, or compromised debit cards with mandatory mobile verification.
* **Complaint Dispatch:** Extracting structured banking dispute tickets (Category, Disputed Amount, SBP Turnaround Time, Escalation Reason).
* **Social Engineering Defense:** Intercepting phishing, lottery scams, and prize caller scams with mandatory State Bank of Pakistan anti-fraud warnings.

### Out-of-Scope & Misuse Warnings
* The model must not provide investment advice, speculative crypto recommendations, or credit risk guarantees.
* Direct fund movement or ledger modification must never be executed purely on LLM token generation; it requires authenticated backend Core Banking API middleware.
* The model must never request or output full customer PINs, OTPs, CVVs, or unmasked 16-digit card numbers.

---

## 3. Training Data & Alignment Lineage

### Phase 1: Supervised Fine-Tuning (SFT)
* **Dataset:** [`sairafatima193/zarya_banking_dataset`](https://huggingface.co/datasets/sairafatima193/zarya_banking_dataset) (2,099 training dialogues, 235 validation dialogues).
* **Curated Dialect:** Natural Pakistani UrduLish code-switching (*"Mera ATM card machine mein phans gaya hai"*, *"Paise kat gaye lekin transfer nahi hue"*).
* **Hyperparameters:** LoRA Rank $r = 16$, $\alpha = 32$, Target Modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`.
* **Hardware:** NVIDIA Tesla GPU with Unsloth BnB 4-bit optimization.
* **Loss Convergence:** Initial loss: $2.3418 \rightarrow$ Final convergence: **$0.0024$**.

### Phase 2: Direct Preference Optimization (DPO)
* **Preference Dataset:** 600 human-reviewed preference pairs (540 train / 60 val) penalizing stiff English, hallucinated fees, and missing mobile confirmations.
* **Hyperparameters:** $\beta = 0.1$, Learning Rate: $5 \times 10^{-5}$, Linear warmup.
* **Compute:** Local NVIDIA RTX 2080 Ti GPU (11GB VRAM).

### Phase 3: LoRA Fusion & GGUF Quantization
* Merged weight deltas: $W_{merged} = W_0 + \frac{32}{16}(B \times A)$.
* Compiled to **4-bit GGUF (Q4_K_M)**: 1.88 GB file size with $<1.2\%$ quality loss.

---

## 4. Evaluation Benchmarks (Golden Test Set: 200 Samples)

| Evaluation Metric | Base Qwen2.5-3B (Zero-Shot) | Zarya SFT Adapter | Zarya SFT + DPO (Final) | Production Target | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Banking Intent Accuracy** | 71.0% | 92.5% | **94.5%** | $\ge 90.0\%$ |  PASSED |
| **UrduLish Tone Compliance** | 28.0% | 88.0% | **96.0%** | $\ge 90.0\%$ |  PASSED |
| **Mobile Verification Protocol**| 12.0% | 84.0% | **98.0%** | $\ge 95.0\%$ |  PASSED |
| **PIN / OTP Refusal Rate** | 65.0% | 94.0% | **100.0%** | $100.0\%$ |  PASSED |
| **Double-Blind Human Win Rate**| 22.0% | 48.0% | **68.0%** | $\ge 50.0\%$ |  PASSED |
| **Quality Retention in 4-bit** | N/A | N/A | **98.8%** | $\ge 97.0\%$ (Loss $<3\%$) |  PASSED |
| **p95 Inference Latency** | 680 ms | 110 ms | **46.5 ms** | $< 3,000$ ms |  PASSED |

---

## 5. Safety, Guardrails & SBP Compliance

The model is embedded inside an enterprise multi-tier guardrails pipeline:
1. **Input Shield:** Blocks prompt injection, jailbreaks, and credential harvesting.
2. **Scam Interceptor:** Immediately triggers the mandated SBP warning upon detecting phishing keywords:
   > *"Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Yeh fraud ho sakta hai — kisi ko na batayein aur foran helpline par report karein."*
3. **Output Sanitizer:** Automatically redacts any full 16-digit card number to `****-****-****-XXXX`.
4. **Audit Log Masker:** Redacts Pakistani CNICs, mobile numbers, and IBANs before storage.

---

## 6. How to Use & Serve

### Python Serving via FastAPI:
```bash
python -m uvicorn src.serve_api:app --host 0.0.0.0 --port 8000
```

### Direct Inference with llama.cpp:
```bash
llama-cli -m quantized_models/zarya-qwen2.5-3b-dpo-q4_k_m.gguf \
  -p "<|im_start|>system\nYou are Zarya Bank's AI customer support assistant.<|im_end|>\n<|im_start|>user\nMera ATM card block karna hai gum ho gaya hai.<|im_end|>\n<|im_start|>assistant\n"
```

