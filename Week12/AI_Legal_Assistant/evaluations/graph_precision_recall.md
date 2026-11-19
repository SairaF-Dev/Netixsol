# Graph extraction: precision and recall (Day 3, Task 2)

Extractor: regex only (`src/graph/regex_extract.py`). Script: `python -m evaluations.graph_extraction_eval`.
Answer keys were made by Claude (an AI model, not a person) from the judgment text, without looking at the
extractor's output:

* **Development set** (`evaluations/graph_gold_20.json`): 20 judgments (12 Supreme Court, 8 Lahore High
  Court). Its errors were used to improve the extractor, so its scores after the fixes are optimistic.
* **Held-out set** (`evaluations/graph_gold_heldout_5.json`): 5 other judgments, annotated after the fixes
  and never used to change the extractor: the fairer estimate (but small).

Precision / recall (number of links in the answer key in brackets):

| Link type | Before fixes (development) | After fixes (development) | After fixes (held-out) |
|---|---:|---:|---:|
| Precedent citations (CITES / FOLLOWS / ...) | 100% / 81% | 100% / 99% (123) | 100% / 95% (20) |
| Statute provisions (REFERS_TO / INTERPRETS) | 96% / 54% | 97% / 92% (124) | 100% / 96% (23) |
| Judges (SAT_ON) | 100% / 93% | 100% / 100% (43) | 100% / 100% (9) |

What the fixes were (all regex / rules, no LLM): law names ending in "Procedure" and containing "of"
("Code of Civil Procedure", "Transfer of Property Act"); "Section 382-B, Cr.P.C." (comma, hyphen);
"Order XVII Rule 3"; sub-clauses inside lists ("337-L (i), (ii), 506"); short names a judgment defines
("the Code", "the Act"); a section without a law named takes the law named last in the same paragraph;
Indian AIR / SCC and "SCP" citations; footnote numbers glued to citations; judge names cleaned of page text;
spelling variants merged.

## Entity resolution (whole graph)

Acts that are still more than one node (the same law written in different ways):

| Act | Nodes |
|---|---|
| ata | PKLAW_011, EXT:eeee-of-the-anti-terrorism-act |
| sales-tax-act | EXT:sales-tax-act, EXT:sales-tax-special-procedure |

Judge nodes: 52; 0 still not a clean name: none.
The same judge split by spelling: none. Merged spellings are kept on the Judge node as `aliases`.

## Remaining errors

### Development set

#### SC_crl.p._46_2024
- **provisions** wrong: ('ppc', 'SECTION 497')
#### SC_j.p._41_2023
- **provisions** missed: ('qso', 'ARTICLE 17'), ('qso', 'ARTICLE 2')
#### SC_c.a._842_2024
- **provisions** missed: ('constitution', 'ARTICLE 222')
#### SC_c.p._1106_2024
- **provisions** wrong: ('constitution', 'ARTICLE 98')
#### SC_c.u.o._1_2025
- **provisions** wrong: ('constitution', 'ARTICLE 175')
#### SC_j.p._183_2019
- **provisions** missed: ('iccpr', 'ARTICLE 2'), ('iccpr', 'ARTICLE 26'), ('icescr', 'ARTICLE 3'), ('udhr', 'ARTICLE 1'), ('udhr', 'ARTICLE 7')
#### SC_c.a._357_l_2013
- **provisions** wrong: ('cpc', 'RULE 1')
#### LHC_2026LHC8604
- **citations** missed: AIR1981AB153
#### LHC_2026LHC8304
- **provisions** missed: ('qso', 'ARTICLE 117')
#### LHC_2026LHC8323
- **provisions** missed: ('family-courts-act', 'SECTION 2')

### Held-out set

#### SC_c.p._4906_2025
- **provisions** missed: ('cpc', 'ORDER XXXIX RULE 2')
#### LHC_2026LHC8375
- **citations** missed: 2004PCRLJ1353
