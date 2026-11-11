# Khan & Associates - Urdu OCR Comparison Benchmark Report

## 1. Executive Summary
This evaluation benchmarks **2 OCR Tools** across **10 complex Urdu legal documents** (including Court Powers of Attorney, Bail Applications, Tenancy Agreements, Land Sale Deeds, and Constitutional Preambles).

The benchmark rigorously calculates:
* **Character Error Rate (CER)**: $\text{CER} = \frac{S + D + I}{N}$
* **Word Error Rate (WER)**: $\text{WER} = \frac{S_w + D_w + I_w}{N_w}$
* **Inference Latency (ms)**: Wall-clock processing time per page.

## 2. Comparative Performance Overview

| OCR Engine                               | Avg CER (%)   | Avg WER (%)   | Avg Latency   | Error Characteristics             |
|------------------------------------------|---------------|---------------|---------------|-----------------------------------|
| Tool 1: LexicalMorph_OCR_v1 (Baseline)   | 1.67%         | 15.50%        | 115.3 ms      | Moderate (Ligature joins/drops)   |
| Tool 2: DeepContextual_OCR_v2 (Advanced) | 0.13%         | 0.69%         | 285.3 ms      | High (Preserves Nastaliq context) |

## 3. Per-Document Detailed Breakdown (10 Urdu Pages)

| Doc ID      | Sample Document Title                    |   Chars | Tool 1 CER   | Tool 1 WER   | Tool 2 CER   | Tool 2 WER   |
|-------------|------------------------------------------|---------|--------------|--------------|--------------|--------------|
| URDU_GT_001 | وکالت نامہ برائے عدالت عالیہ لاہور       |     445 | 2.02%        | 19.28%       | 0.0%         | 0.0%         |
| URDU_GT_002 | درخواست برائے ضمانت بعد از گرفتاری زیر د |     484 | 1.24%        | 10.99%       | 0.21%        | 1.1%         |
| URDU_GT_003 | استغاثہ زیر دفعہ 489-ایف تعزیرات پاکستان |     466 | 0.86%        | 8.24%        | 0.0%         | 0.0%         |
| URDU_GT_004 | معاہدہ کرایہ داری برائے رہائشی مکان      |     437 | 1.6%         | 16.87%       | 0.23%        | 1.2%         |
| URDU_GT_005 | بیان حلفی اشٹام پیپر                     |     423 | 0.95%        | 7.95%        | 0.24%        | 1.14%        |
| URDU_GT_006 | قانونی نوٹس زیر دفعہ 8 ڈیفامیشن آرڈیننس  |     430 | 1.16%        | 10.84%       | 0.0%         | 0.0%         |
| URDU_GT_007 | بعدالت جناب جج صاحب فیملی کورٹ، ملتان    |     452 | 2.43%        | 21.74%       | 0.22%        | 1.09%        |
| URDU_GT_008 | بعدالت جناب سول جج صاحب درجہ اول، گوجران |     439 | 2.28%        | 18.29%       | 0.23%        | 1.22%        |
| URDU_GT_009 | دیباچہ آئین اسلامی جمہوریہ پاکستان 1973  |     456 | 2.19%        | 21.59%       | 0.22%        | 1.14%        |
| URDU_GT_010 | بیع نامہ قطعی برائے اراضی زرعی           |     403 | 1.99%        | 19.23%       | 0.0%         | 0.0%         |

## 4. Key Findings & Engineering Recommendation
1. **Nastaliq Ligatures**: Tool 1 suffers from frequent character-split errors on joint cursive letters (e.g. `ریاست` read as `ریا ست`, `پاکستان` as `پا کستان`), leading to a **1.67% CER**.
2. **Contextual Recognition**: Tool 2 leverages sequential context, cutting the CER down to **0.13%** (an 91.9% error reduction).
3. **Recommendation**: Khan & Associates should adopt **Tool 2 (Deep Contextual OCR)** for production legal indexing, with a fast fallback to Tool 1 when batch throughput is prioritized.
