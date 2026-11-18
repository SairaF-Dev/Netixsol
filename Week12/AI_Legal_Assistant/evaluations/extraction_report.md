# Structure Extraction Coverage

Documents: 13 English statutes, 40 Urdu laws (OCR), 225 judgments,
53 CUAD contracts (the 20 synthetic contracts use their generated JSON and are not counted).
Urdu laws are split by page, not by section: EasyOCR drops the "۔" after Urdu
section numbers, so section headings cannot be detected reliably.

"Found in" measures whether a field was extracted, **not** whether it is correct;
correctness has not been checked against a hand-labelled set. Fields that cannot be
found are left empty rather than filled with defaults.

| Type            | Field                             | Found in         |
|-----------------|-----------------------------------|------------------|
| Statute         | documents with sections           | 13/13 (100%)     |
| Statute         | sections / articles / rules found | 2861             |
| Statute         | sections with start page          | 2861/2861 (100%) |
| Statute         | preamble                          | 12/13 (92%)      |
| Urdu law (OCR)  | laws with OCR text                | 40/40 (100%)     |
| Urdu law (OCR)  | pages with text (one unit each)   | 1596             |
| Urdu law (OCR)  | pages still without OCR text      | 0                |
| Urdu law (OCR)  | year from official title          | 40/40 (100%)     |
| Judgment        | case number                       | 213/225 (95%)    |
| Judgment        | petitioner / appellant            | 201/225 (89%)    |
| Judgment        | respondent                        | 199/225 (88%)    |
| Judgment        | bench / author judge              | 211/225 (94%)    |
| Judgment        | year                              | 221/225 (98%)    |
| Judgment        | date of hearing                   | 169/225 (75%)    |
| Judgment        | case-law citations                | 174/225 (77%)    |
| Judgment        | statutes cited                    | 187/225 (83%)    |
| Judgment        | numbered paragraphs (>= 3)        | 212/225 (94%)    |
| Judgment        | holding with outcome word         | 218/225 (97%)    |
| Judgment        | pages still needing OCR           | 0/225 (0%)       |
| Contract (CUAD) | title                             | 53/53 (100%)     |
| Contract (CUAD) | two parties                       | 32/53 (60%)      |
| Contract (CUAD) | effective date                    | 38/53 (72%)      |
| Contract (CUAD) | governing law                     | 37/53 (70%)      |
| Contract (CUAD) | 3+ clauses                        | 46/53 (87%)      |
