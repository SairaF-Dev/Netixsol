# Urdu OCR Benchmark

## Status: Not run

The previous report contained simulated OCR outputs derived from the ground-truth
text, not recognition results from the PDF images. Those metrics have been
withdrawn and must not be used.

The benchmark code now renders the PDF pages and sends the image pixels to
Tesseract and EasyOCR. A valid comparison has not yet been produced because this
environment has neither the Tesseract executable with Urdu/English language data
nor the optional EasyOCR package installed.

Install both tools as described in the project README, then run:

```powershell
.\.venv\Scripts\python.exe main.py --ocr-eval
```

The command writes actual per-page CER, WER, and OCR inference latency to the
CSV and Markdown reports. Do not interpret the generated benchmark fixtures as
authentic scanned legal records.
