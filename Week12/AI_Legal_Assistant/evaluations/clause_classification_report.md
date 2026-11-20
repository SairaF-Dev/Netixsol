# Clause classification: LLM vs fine-tuned model (Day 4, Task 1)

Test passages: 482 from the 51 CUAD test contracts (150 sentences no lawyer marked, the rest marked with one or more of 28 clause types). The fine-tuned model never saw these contracts. `support` = marked test passages of that type: types with few passages have unreliable scores.

| | LLM (Gemini, zero-shot) | Legal-BERT-small, 3 epochs (laptop CPU) | deberta-v3-base, best of 5 epochs (Colab T4) | legal-bert-base-uncased, best of 5 epochs (Colab T4) | legal-bert-small-uncased, best of 8 epochs (Colab T4) |
|---|---:|---:|---:|---:|---:|
| Micro F1 | 0.79 | 0.69 | 0.75 | 0.80 | 0.79 |
| Macro F1 (28 types) | 0.77 | 0.59 | 0.68 | 0.77 | 0.77 |
| False alarms on unmarked sentences | 12% | 14% | 11% | 11% | 15% |
| Cost | 33 requests, ~76,251 input tokens | free; 100.4 min training on CPU | free; 15.7 min training on GPU | free; 8.8 min training on GPU | free; 4.3 min training on GPU |
| Time per passage | 620 ms (API) | 50 ms (CPU) | 5.7 ms (GPU) | 3.0 ms (GPU) | 1.0 ms (GPU) |

F1 per clause type:

| Clause type | Support | LLM (Gemini, zero-shot) | Legal-BERT-small, 3 epochs (laptop CPU) | deberta-v3-base, best of 5 epochs (Colab T4) | legal-bert-base-uncased, best of 5 epochs (Colab T4) | legal-bert-small-uncased, best of 8 epochs (Colab T4) |
|---|---:|---:|---:|---:|---:|---:|
| License Grant | 28 | 0.88 | 0.85 | 0.86 | 0.86 | 0.88 |
| Cap On Liability | 24 | 0.77 | 0.74 | 0.87 | 0.86 | 0.83 |
| Anti-Assignment | 15 | 0.81 | 0.72 | 0.72 | 0.78 | 0.76 |
| Audit Rights | 15 | 0.88 | 0.83 | 0.86 | 0.93 | 0.87 |
| Insurance | 15 | 0.93 | 0.90 | 0.93 | 0.93 | 0.97 |
| Expiration Date | 18 | 0.67 | 0.73 | 0.88 | 0.84 | 0.82 |
| Governing Law | 15 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Post-Termination Services | 15 | 0.57 | 0.62 | 0.62 | 0.75 | 0.65 |
| Minimum Commitment | 16 | 0.62 | 0.71 | 0.67 | 0.75 | 0.71 |
| Revenue/Profit Sharing | 15 | 0.89 | 0.83 | 0.83 | 0.93 | 0.93 |
| Exclusivity | 20 | 0.79 | 0.55 | 0.62 | 0.77 | 0.82 |
| Rofr/Rofo/Rofn | 15 | 0.77 | 0.67 | 0.73 | 0.64 | 0.86 |
| Ip Ownership Assignment | 15 | 0.85 | 0.83 | 0.83 | 0.85 | 0.86 |
| Non-Transferable License | 18 | 0.73 | 0.44 | 0.59 | 0.57 | 0.65 |
| Non-Compete | 15 | 0.76 | 0.56 | 0.62 | 0.69 | 0.62 |
| Change Of Control | 15 | 0.69 | 0.61 | 0.72 | 0.75 | 0.69 |
| Termination For Convenience | 15 | 0.90 | 0.81 | 0.81 | 0.84 | 0.80 |
| Renewal Term | 16 | 0.97 | 0.91 | 0.94 | 0.94 | 0.91 |
| Warranty Duration | 12 | 0.76 | 0.59 | 0.80 | 0.77 | 0.67 |
| Covenant Not To Sue | 7 | 0.92 | 0.92 | 0.93 | 1.00 | 1.00 |
| Volume Restriction | 9 | 0.36 | 0.00 | 0.57 | 0.88 | 0.63 |
| Uncapped Liability | 15 | 0.64 | 0.00 | 0.62 | 0.86 | 0.77 |
| Irrevocable Or Perpetual License | 15 | 0.90 | 0.85 | 0.80 | 0.90 | 0.90 |
| Competitive Restriction Exception | 11 | 0.74 | 0.00 | 0.00 | 0.00 | 0.43 |
| Notice Period To Terminate Renewal | 12 | 0.87 | 0.72 | 0.74 | 0.79 | 0.77 |
| Liquidated Damages | 7 | 0.86 | 0.00 | 0.40 | 0.77 | 0.71 |
| Joint Ip Ownership | 4 | 1.00 | 0.00 | 0.00 | 0.86 | 0.86 |
| Affiliate License-Licensee | 12 | 0.14 | 0.00 | 0.00 | 0.00 | 0.27 |
