# LoRA and QLoRA Technical Theory & Architecture Guide

**Project**: Zarya Digital Bank UrduLish Banking LLM  
**Target Architecture**: `Qwen/Qwen2.5-3B-Instruct`  
**Author**: Antigravity AI Engineering Team  
**Date**: October 2026  

---

## 1. What LoRA Does and Why It Saves Memory

### 1.1 The Mathematical Formulation of LoRA
Traditional full fine-tuning (FFT) updates all parameters $W_0 \in \mathbb{R}^{d \times k}$ of a pre-trained model by learning a full weight modification matrix $\Delta W$:
$$W = W_0 + \Delta W$$

For a 3-billion parameter model, storing full optimizer states (such as first and second moments in AdamW: $m_t$ and $v_t$) requires $3 \times 4 \times 2 = 24\text{ GB}$ of GPU memory *just for the optimizer*, on top of model weights and activation memory.

**Low-Rank Adaptation (LoRA)** (Hu et al., 2021) hypothesizes that the intrinsic rank of weight updates during downstream task adaptation is much lower than the full matrix dimension ($r \ll \min(d, k)$). LoRA decomposes the update $\Delta W$ into the product of two low-rank matrices $B$ and $A$:

$$\Delta W = \frac{\alpha}{r} (B \cdot A)$$

Where:
- $W_0 \in \mathbb{R}^{d \times k}$ is the **frozen** pre-trained weight matrix.
- $A \in \mathbb{R}^{r \times k}$ is initialized with Gaussian noise $\mathcal{N}(0, \sigma^2)$.
- $B \in \mathbb{R}^{d \times r}$ is initialized to **zero** (ensuring $\Delta W = 0$ at step 0 so training starts smoothly from base model behavior).
- $r$ is the chosen rank dimension ($r \ll d, k$).
- $\frac{\alpha}{r}$ is a constant scaling factor.

During the forward pass with input activation $X \in \mathbb{R}^{b \times s \times k}$:
$$h = X W_0^T + \frac{\alpha}{r} X A^T B^T$$

```
               Forward Pass Architecture in LoRA
               
                      Input Vector X
                      (Dimension k)
                           |
             +-------------+-------------+
             |                           |
             v                           v
     [ Frozen Base W_0 ]          [ LoRA Matrix A ] (Down-project to r)
       (Shape: d x k)             (Shape: r x k, Gaussian init)
             |                           |
             |                           v
             |                    [ LoRA Matrix B ] (Up-project to d)
             |                    (Shape: d x r, Zero init)
             |                           |
             |                           v
             |                     Scale by (alpha / r)
             |                           |
             +-------------( + )---------+
                             |
                             v
                       Output Vector h
                       (Dimension d)
```

### 1.2 Memory Footprint: Why LoRA Shrinks VRAM
In AdamW, memory consumption is partitioned into:
1. **Model Weights**: Stored in 16-bit (2 bytes/param) or 4-bit (0.5 bytes/param).
2. **Gradients**: Stored in 16-bit (2 bytes/param) for trainable parameters only.
3. **Optimizer States**: 8 bytes/param (FP32 momentum $m_t$ + variance $v_t$) for trainable parameters only.
4. **Activations & KV Cache**: Temporary storage for backpropagation.

By freezing $W_0$, gradients and optimizer states are stored **only for $A$ and $B$**. For Qwen 2.5 3B with $r=16$, trainable parameters represent **less than 0.5%** of total weights (~14M vs 3.09B).

```
Full Fine-Tuning vs LoRA vs QLoRA Memory Distribution (Qwen 2.5 3B, Seq Len 1024)
+-------------------------------------------------------------------------------+
| Method         | Base Weights | Gradients & Optimizer | Activations | Peak VRAM|
+-------------------------------------------------------------------------------+
| Full Fine-Tune | 6.18 GB      | 24.72 GB (AdamW FP32) | ~4.5 GB     | ~35.4 GB |
| LoRA (FP16)    | 6.18 GB      | 0.12 GB (Trainable)   | ~4.5 GB     | ~10.8 GB |
| QLoRA (NF4 4b) | 1.95 GB      | 0.12 GB (Trainable)   | ~2.7 GB     | ~4.8 GB  |
+-------------------------------------------------------------------------------+
```

---

## 2. Key Hyperparameters: Rank, Alpha, and Target Modules

### 2.1 Rank ($r$)
- Defines the inner dimension of low-rank matrices $A$ and $B$.
- Controls the **expressive capacity** of the adaptation.
- For simple style transfer or tone adjustment, $r=4$ or $r=8$ suffices.
- For complex domain tasks like Zarya Bank (which combines bilingual transliteration, intent extraction, and strict JSON schema generation), **$r=16$ or $r=32$** provides the required expressiveness without overfitting.

### 2.2 Scaling Factor Alpha ($\alpha$) and Ratio $\frac{\alpha}{r}$
- Scales the adapter output before adding it back to the frozen base activations: $\Delta W = \frac{\alpha}{r} BA$.
- A standard heuristic is setting **$\alpha = 2 \times r$** (or $\frac{\alpha}{r} = 2.0$ or $1.0$).
- When experimenting with different ranks $r \in \{8, 16, 32\}$, keeping the ratio $\frac{\alpha}{r}$ constant (e.g., $16/8 = 2$, $32/16 = 2$, $64/32 = 2$) ensures that the magnitude of updates remains stable and prevents learning rate instability.

### 2.3 Target Modules: Attention vs All-Linear Projections
In early LoRA implementations, only query and value matrices ($W_q, W_v$) were adapted. However, research (Dettmers et al., 2023) demonstrated that adapting **all linear projections** across both Multi-Head Self-Attention (MHSA) and Feed-Forward Networks (MLP) substantially improves performance:

For `Qwen/Qwen2.5-3B-Instruct`:
- **Attention Projections**: `q_proj`, `k_proj`, `v_proj`, `o_proj`
- **MLP / Feed-Forward Projections**: `gate_proj`, `up_proj`, `down_proj`

Applying adapters to all 7 projection types allows the model to learn both **contextual relationship shifts** (attention) and **new domain factual patterns / vocabulary grounding** (MLP).

---

## 3. QLoRA: Quantized Base Model + High-Precision Adapters

QLoRA (Dettmers et al., 2023) enables parameter-efficient fine-tuning on consumer-grade hardware through three core innovations:

```
+----------------------------------------------------------------------------+
|                             QLoRA ARCHITECTURE                             |
|                                                                            |
|   +--------------------------------------------------------------------+   |
|   | 1. NF4 Quantized Base Weights (W_0)                                |   |
|   |    - 4-bit NormalFloat data type                                   |   |
|   |    - Information-theoretically optimal for normal distributions   |   |
|   |    - Memory: ~0.5 bytes / parameter (~1.95 GB total)               |   |
|   +--------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v (Dequantize on-the-fly to BF16)       |
|                                                                            |
|   +--------------------------------------------------------------------+   |
|   | 2. LoRA Adapters (A & B)                                           |   |
|   |    - Unquantized 16-bit (BF16 / FP16)                              |   |
|   |    - High precision gradients and optimizer updates                |   |
|   +--------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|   +--------------------------------------------------------------------+   |
|   | 3. Double Quantization (DQ) + Paged Optimizers                     |   |
|   |    - Quantizes quantization constants (saves ~0.37 bits/param)     |   |
|   |    - Pages optimizer memory to CPU RAM during peak allocation      |   |
|   +--------------------------------------------------------------------+   |
+----------------------------------------------------------------------------+
```

### 3.1 NormalFloat 4 (NF4)
Standard 4-bit integers (INT4) divide the dynamic range linearly. However, neural network weights follow a zero-centered normal distribution $\mathcal{N}(0, \sigma^2)$. NF4 builds quantiles such that each of the $2^4 = 16$ discrete bins contains an equal probability mass under the standard normal distribution. This minimizes information loss and preserves pre-trained capabilities.

### 3.2 Double Quantization (DQ)
In standard block-wise quantization, each block of 64 parameters requires a 32-bit floating-point scale factor (adding $32 / 64 = 0.5$ bits per parameter). Double Quantization treats these scale factors as inputs to a second 8-bit quantization step with block size 256, reducing scale memory overhead from 0.5 bits/param to 0.127 bits/param—a net saving of ~0.37 bits per parameter (~140 MB for a 3B model).

### 3.3 Paged Optimizers
To prevent CUDA Out-of-Memory (OOM) errors during long sequence processing or sudden activation bursts, QLoRA utilizes CUDA Unified Memory to automatically page optimizer state tensors between GPU VRAM and CPU system RAM when memory pressure exceeds safe thresholds.

---

## 4. Full Fine-Tuning vs LoRA vs QLoRA: When to Use Which

| Criterion | Full Fine-Tuning (FFT) | LoRA (16-bit Base) | QLoRA (4-bit Base) |
| :--- | :--- | :--- | :--- |
| **GPU Memory Needed** | Very High ($\ge 40\text{ GB}$) | Moderate (12–16 GB) | **Minimal (4–6 GB)** |
| **Compute Cost** | Expensive | Moderate | **Lowest** |
| **Training Throughput** | Fastest (no dequant overhead) | Fast | ~15–20% slower than pure FP16 |
| **Risk of Catastrophic Forgetting** | High | Low | **Lowest (Base is completely frozen)** |
| **Multi-Task Serving** | Must deploy separate base model per task | Swap lightweight adapter files (20–50 MB) at runtime | Swap lightweight adapter files (20–50 MB) at runtime |
| **Serving Latency Overhead** | Zero | Zero (Merge weights: $W = W_0 + \frac{\alpha}{r}BA$) | Zero when merged to FP16/GGUF |
| **Best Used For** | Pretraining new base models from scratch or radical syntax shift | Enterprise fine-tuning on high-tier GPUs (A100/H100) | **Domain adaptation, safety alignment & JSON structured output on accessible hardware (T4/RTX 4090)** |

---

## 5. Chat Templates & Assistant-Only Loss Masking

### 5.1 The Danger of Unmasked Training
In standard causal language modeling, the cross-entropy loss is computed over all tokens in the sequence:
$$\mathcal{L}_{\text{naive}} = -\frac{1}{T} \sum_{t=1}^T \log P(x_t \mid x_{<t})$$

If user prompt tokens are included in the loss calculation:
1. The model wastes gradient capacity learning to predict user typos, conversational slang, and random customer sentence structures.
2. The model exhibits "prompt regurgitation" or hallucinated user turns during inference.
3. It dilutes the learning signal for the target banking persona, JSON formatting, and refusal logic.

### 5.2 Assistant-Only Loss Masking Mechanism
In our pipeline, training sequences are formatted using the standard Qwen ChatML template:

```
<|im_start|>system
You are Zarya Bank's AI customer support assistant...<|im_end|>
<|im_start|>user
Mera ATM card block karna hai gum ho gaya hai.<|im_end|>
<|im_start|>assistant
Ji, aap ka card hifazat ke khatir fori block kar diya gaya hai...<|im_end|>
```

Using PyTorch cross-entropy masking, all tokens corresponding to the **System Prompt** and **User Prompt** are assigned a label index of `-100` (`IGNORE_INDEX` in PyTorch):

```
Token Indices:  [  15,  842, 2981, 104, 3812, 491, 1928,  842, 9123, 104, 281, 4920, 182 ]
Tokens:         [ <sys> You  are  ...  <usr> Mera card ... <asst> Ji,  aap   ka   ...  <end> ]
Labels / Loss:  [ -100, -100, -100, ..., -100, -100, ...  -100, 4920, 182,  ...,  <end> ]
                   |____________________________________|   |________________________|
                             NO LOSS COMPUTED                   LOSS COMPUTED HERE ONLY
```

$$\mathcal{L}_{\text{assistant}} = -\frac{1}{N_{\text{assistant}}} \sum_{i \in \text{assistant}} \log P(x_i \mid x_{<i})$$

This ensures that **100% of gradient updates** are dedicated to mastering:
1. Opening with the required cultural honorific *Ji*.
2. Generating valid, strict JSON structures without markdown code fences.
3. Polite and concise responses ($\le 25$ words).
4. SBP-compliant fraud refusal and escalation protocols.

