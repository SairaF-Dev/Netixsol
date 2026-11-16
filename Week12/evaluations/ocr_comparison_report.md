# Urdu OCR Benchmark

## Method

Tesseract (urd+eng), EasyOCR (ur+en) each receive a rendered image of the same PDF page.
Neither engine reads the ground-truth file. CER and WER compare each engine's
recognized text against the paired UTF-8 reference. Latency measures OCR inference
and excludes PDF rendering.

## Results

| OCR Engine          | Average CER   | Average WER   | Average Latency   |
|---------------------|---------------|---------------|-------------------|
| Tesseract (urd+eng) | 89.68%        | 115.30%       | 1537.5 ms         |
| EasyOCR (ur+en)     | 85.98%        | 131.11%       | 53461.2 ms        |

## Per-page results

| Document    |   Reference chars |   Tesseract (urd+eng) CER (%) |   Tesseract (urd+eng) WER (%) |   EasyOCR (ur+en) CER (%) |   EasyOCR (ur+en) WER (%) |
|-------------|-------------------|-------------------------------|-------------------------------|---------------------------|---------------------------|
| URDU_GT_001 |               445 |                         86.97 |                        114.46 |                     84.94 |                    130.12 |
| URDU_GT_002 |               484 |                         87.81 |                        117.58 |                     83.88 |                    130.77 |
| URDU_GT_003 |               466 |                         93.13 |                        117.65 |                     84.76 |                    132.94 |
| URDU_GT_004 |               437 |                         87.41 |                        112.05 |                     87.41 |                    137.35 |
| URDU_GT_005 |               423 |                         91.02 |                        117.05 |                     84.87 |                    122.73 |
| URDU_GT_006 |               430 |                         92.56 |                        114.46 |                     86.74 |                    134.94 |
| URDU_GT_007 |               452 |                         90.04 |                        117.39 |                     86.73 |                    127.17 |
| URDU_GT_008 |               439 |                         88.84 |                        115.85 |                     86.56 |                    128.05 |
| URDU_GT_009 |               456 |                         87.72 |                        113.64 |                     85.31 |                    127.27 |
| URDU_GT_010 |               403 |                         91.32 |                        112.82 |                     88.59 |                    139.74 |
