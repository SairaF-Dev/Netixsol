# Urdu OCR Benchmark

## Method

Ten pages from official Pakistan Code Urdu laws (Nastaleeq typesetting, watermark,
one table page, two pages from an image-only Constitution scan) are exported as
image-only PDFs; sources are listed in `data/scanned_urdu/benchmark_cer/manifest.csv`.
The ground truth was drafted by Claude from the page images (Claude is not one of the
compared engines) and corrected line by line by hand; page numbers and the watermark
are excluded. The source PDFs' own text layers are unusable (font-private glyph codes),
so they could not serve as ground truth.

Tesseract (urd+eng), EasyOCR (ur+en) each receive a rendered image of the same PDF page.
Neither engine reads the ground-truth file. CER and WER compare each engine's
recognized text against the paired UTF-8 reference. Latency measures OCR inference
and excludes PDF rendering.

## Results

| OCR Engine          | Average CER   | Average WER   | Average Latency   |
|---------------------|---------------|---------------|-------------------|
| Tesseract (urd+eng) | 70.33%        | 96.68%        | 756.0 ms          |
| EasyOCR (ur+en)     | 32.93%        | 86.87%        | 21765.9 ms        |

## Per-page results

| Document    |   Reference chars |   Tesseract (urd+eng) CER (%) |   Tesseract (urd+eng) WER (%) |   EasyOCR (ur+en) CER (%) |   EasyOCR (ur+en) WER (%) |
|-------------|-------------------|-------------------------------|-------------------------------|---------------------------|---------------------------|
| URDU_GT_001 |               280 |                         77.78 |                        100    |                     43.37 |                     91.67 |
| URDU_GT_002 |               230 |                         78.6  |                         97.87 |                     40.61 |                     85.11 |
| URDU_GT_003 |               561 |                         63.04 |                         92.04 |                     31.25 |                     92.92 |
| URDU_GT_004 |               311 |                         55.48 |                         94.92 |                     23.23 |                     83.05 |
| URDU_GT_005 |               259 |                         48.84 |                         93.44 |                     35.27 |                     86.89 |
| URDU_GT_006 |               320 |                         72.1  |                        103.51 |                     30.72 |                     89.47 |
| URDU_GT_007 |               122 |                         98.35 |                        100    |                     37.19 |                     84.21 |
| URDU_GT_008 |               491 |                         63.67 |                         89.81 |                     23.67 |                     72.22 |
| URDU_GT_009 |               763 |                         80.97 |                         99.19 |                     30.71 |                     87.9  |
| URDU_GT_010 |               761 |                         64.47 |                         96.03 |                     33.29 |                     95.24 |
