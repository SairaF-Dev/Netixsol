# Model Selection Document: Zarya Digital Bank UrduLish LLM

**Project**: Zarya Digital Bank UrduLish Banking Assistant  
**Author**: Antigravity AI Engineering Team  
**Date**: October 2026  
**Status**: APPROVED — Champion Model Selected  

---

## 1. Executive Summary & Objective

Zarya Digital Bank requires an on-premise, enterprise-grade Large Language Model capable of handling high-volume bilingual customer interactions (UrduLish, Roman Urdu, Urdu Script, English) across 31 banking intents, automated JSON ticket extraction, and strict regulatory adherence (State Bank of Pakistan banking guidelines).

Following Day 2 Task 1 baseline evaluations, two leading open-weight ~3B parameter foundation models were shortlisted for deep comparative evaluation:
1. **`Qwen/Qwen2.5-3B-Instruct`** (Alibaba Cloud / Qwen Team)
2. **`meta-llama/Llama-3.2-3B-Instruct`** (Meta AI)

### Decision Outcome
**Selected Foundation Model: `Qwen/Qwen2.5-3B-Instruct`**  
The selection is driven primarily by **commercial licensing (Apache 2.0 vs Meta Community License)**, **air-gapped VPC deployment independence (ungated vs gated repository)**, **multilingual pretraining architecture**, and **ultra-low QLoRA memory footprint (1.95 GB base in 4-bit)**.

---

## 2. Comparative Matrix: Qwen 2.5 3B vs Llama 3.2 3B

| Evaluation Dimension | `Qwen/Qwen2.5-3B-Instruct` | `meta-llama/Llama-3.2-3B-Instruct` | Impact on Zarya Digital Bank |
| :--- | :--- | :--- | :--- |
| **Exact Parameter Count** | **3.09 Billion** | 3.21 Billion | Qwen is ~4% smaller, yielding faster latency. |
| **Open-Source License** | **Apache 2.0** (Fully permissive) | Meta Llama 3.2 Community License | **Decisive**: Apache 2.0 allows unrestricted commercial deployment with zero regulatory friction. |
| **Repository Accessibility** | **Public & Open Access** (Ungated) | Gated (Requires Meta license approval & HF token) | CI/CD pipelines and air-gapped banking servers can fetch weights without external authentication dependencies. |
| **Vocabulary Size** | **151,665 tokens** | 128,256 tokens | Qwen's larger vocabulary provides extensive multilingual subword coverage. |
| **Native Context Length** | **128k tokens** (32k recommended) | 128k tokens | Both support deep multi-turn dialogue histories. |
| **Attention Architecture** | Grouped Query Attention (GQA) (16 Q-heads, 2 KV-heads) | Grouped Query Attention (GQA) (24 Q-heads, 8 KV-heads) | High throughput with minimal KV-cache memory consumption. |
| **RoPE Base Frequency ($\theta$)** | 1,000,000 | 500,000 | Robust long-context position interpolation. |
| **Base VRAM (BF16)** | **~6.18 GB** | ~6.42 GB | Fits on 8GB-16GB GPUs without quantization. |
| **Base VRAM (INT8)** | **~3.09 GB** | ~3.21 GB | High-throughput low-latency serving on edge hardware. |
| **Base VRAM (4-bit NF4)** | **~1.95 GB** | ~2.08 GB | Allows QLoRA fine-tuning on a single 16GB T4 GPU with batch size $\ge 4$. |

---

## 3. Empirical Tokenizer Analysis on Banking Corpus

Using the golden test set (`data/golden/golden_test.jsonl`), both tokenizers were evaluated across real customer queries and banking responses in all 4 target linguistic formats.

### Compression Efficiency Across Languages

| Language Category | Words Tested | Qwen 2.5 Tokens / Word | Llama 3.2 Tokens / Word | Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **UrduLish** (Mixed Roman/English) | 1,175 | 1.88 | 1.77 | Both models achieve sub-2.0 tokens/word, avoiding catastrophic subword fragmentation. |
| **Roman Urdu** (Pure transliterated) | 1,491 | 1.76 | 1.72 | Negligible difference (~2.3%). Common banking terms (*paise*, *kat*, *shanakhti*) map smoothly. |
| **English** (Formal banking) | 1,317 | 1.47 | 1.40 | High efficiency across standard financial terminology. |
| **Urdu Script** (Perso-Arabic) | 1,616 | 2.61 | 2.56 | Both handle Urdu Unicode glyphs natively without falling back to raw byte-level inflation. |
| **Overall Corpus Average** | **5,599** | **1.93** | **1.86** | Both tokenizers are production-grade for Pakistani fintech workflows. |

### Why Tokenizer Efficiency Matters
In legacy models (such as LLaMA-2 with a 32k vocabulary), Roman Urdu suffered from severe subword splittings, averaging **3.8 to 4.5 tokens per word**. At 1.76–1.88 tokens per word, modern 128k+ tokenizers reduce token generation volume by **over 55%**, directly cutting inference latency and time-to-first-token in half.

---

## 4. Hardware Sizing & Training Budget Estimation

The target deployment environment for Zarya Digital Bank includes on-premise local servers and cloud fine-tuning infrastructure (Google Colab / AWS g4dn.xlarge with NVIDIA T4 16GB).

### VRAM Requirements for Fine-Tuning (Batch Size = 4, Sequence Length = 1,024)

```
+--------------------------------------------------------------------------+
| METHOD                 | BASE WEIGHTS | ADAPTERS / OPTIM | ACTIVATIONS  | TOTAL VRAM |
+--------------------------------------------------------------------------+
| Full Fine-Tuning (FP16)| 6.18 GB      | 18.54 GB (AdamW) | ~8.00 GB     | ~32.72 GB  | (Requires A100 40GB)
| LoRA (FP16 Base)       | 6.18 GB      | 0.45 GB          | ~4.20 GB     | ~10.83 GB  | (Fits on T4 16GB)
| QLoRA (NF4 4-bit Base) | 1.95 GB      | 0.25 GB          | ~2.60 GB     | ~4.80 GB   | (Fits easily on T4 16GB)
+--------------------------------------------------------------------------+
```

* **Selected QLoRA Configuration**:
  - Base Precision: 4-bit NormalFloat (`bitsandbytes` NF4)
  - Compute Dtype: `bfloat16` (or `float16` on T4)
  - Double Quantization: Enabled (saves additional ~0.37 bits/param)
  - Target Modules: All linear projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`)
  - Peak Training VRAM: **~4.8 GB** (leaves ~11 GB safety headroom on a 16 GB T4 GPU, preventing CUDA Out-of-Memory crashes).

---

## 5. Regulatory, Compliance & Risk Assessment

1. **State Bank of Pakistan (SBP) Data Governance**:
   - Sending banking chat transcripts containing customer account references, disputed sums, or phone numbers to external APIs violates local data sovereignty guidelines.
   - Self-hosting an open-source model ensures zero data leakage beyond the bank's internal VPC.
2. **Commercial Licensing Risk**:
   - Meta Llama 3.2 is governed by the Meta Community License. In enterprise audits, clauses regarding Meta's discretion, acceptable use restrictions, and user caps can introduce legal ambiguity.
   - Qwen 2.5 3B is released under the **permissive Apache 2.0 license**, granting irrevocable commercial rights, sublicensing, and modification without proprietary constraints.
3. **Model Weights Provenance & Supply Chain**:
   - `Qwen/Qwen2.5-3B-Instruct` provides SHA-256 verified safetensors weights freely downloadable directly without third-party authorization gates.

---

## 6. Final Recommendation

**Deploy `Qwen/Qwen2.5-3B-Instruct` as the base model for all subsequent Capstone stages:**
1. **Day 2 Task 3 & 4**: Fine-tune via QLoRA on `data/train/train.jsonl` (2,099 records) with assistant token masking.
2. **Day 3**: Align using DPO (Direct Preference Optimization).
3. **Day 4**: Merge LoRA adapter into base weights and export to GGUF (Q4_K_M) / vLLM serving.
4. **Day 5**: Containerize in FastAPI backend with SBP-compliant local guardrails.

