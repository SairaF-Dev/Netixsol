# Knowledge graph extraction (regex, Day 3)

Built by `src/graph/regex_extract.py` from the structured corpus; schema in `docs/graph_schema.md`.
CSV files for Neo4j in `data/graph/`. Relationship types come from cue words in the citing
sentence; those marked "needs check" (OVERRULES, DISTINGUISHES, INTERPRETS) are candidates for the
LLM step and have not been verified. Precision / recall have not been measured yet.

## Nodes

| Label | Count |
|---|---:|
| Act | 138 |
| Case | 1649 |
| Clause | 1186 |
| Contract | 73 |
| Court | 2 |
| Judge | 52 |
| Party | 339 |
| Section | 3214 |

## Relationships

| Type | Count | Needs check |
|---|---:|---:|
| CITES | 1248 | 0 |
| DECIDED_BY | 221 | 0 |
| DISTINGUISHES | 4 | 0 |
| FOLLOWS | 108 | 0 |
| HAS_PARTY | 356 | 0 |
| INTERPRETS | 67 | 1 |
| OVERRULES | 2 | 0 |
| PART_OF | 4400 | 0 |
| REFERS_TO | 2149 | 0 |
| RELATED_MATTER | 401 | 0 |
| SAT_ON | 490 | 0 |

Precedent links (reporter / neutral citations): 1362, of which 1 point to another
judgment in the corpus. Same-litigation links (bare case numbers): 401
(0 appeal history).
(most cited cases are reported judgments outside the corpus and become `in_corpus=false` nodes).
Statute references not linked to a corpus section: {'act not in corpus': 1458, 'law not named or not found': 1211, 'section not in corpus act': 237}.

## Most cited precedents

| Case | Cited by (paragraphs) |
|---|---:|
| 2017 SCMR 1218 | 5 |
| PLD 2007 SC 302 | 5 |
| 2017 PTD 1756 | 5 |
| PLJ 2024 SC 114 | 4 |
| 2009 SCMR 230 | 4 |
| 2022 SCMR 1231 | 4 |
| 2010 SCMR 1630 | 4 |
| 2017 SCMR 1427 | 4 |

## Most referenced provisions

| Act | Provision | References |
|---|---|---:|
| Code of Civil Procedure, 1908 | Section 12 | 58 |
| Constitution of the Islamic Republic of Pakistan, 1973 (as amended up to the 27th Amendment, 2025) | Article 199 | 40 |
| Pakistan Penal Code, 1860 | Section 302 | 40 |
| Constitution of the Islamic Republic of Pakistan, 1973 (as amended up to the 27th Amendment, 2025) | Article 10A | 28 |
| Constitution of the Islamic Republic of Pakistan, 1973 (as amended up to the 27th Amendment, 2025) | Article 25 | 27 |
| Code of Civil Procedure, 1908 | Order VII Rule 11 | 26 |
| Code of Criminal Procedure | Section 382B | 21 |
| Code of Civil Procedure, 1908 | Section 115 | 20 |
| Constitution of the Islamic Republic of Pakistan, 1973 (as amended up to the 27th Amendment, 2025) | Article 175 | 20 |
| Constitution of the Islamic Republic of Pakistan, 1973 (as amended up to the 27th Amendment, 2025) | Article 185 | 20 |

## OVERRULES candidates (to be checked)

| Citing case | Cited case | Sentence |
|---|---|---|
| CRL.P. 1121/2021 | PLD 2016 SC 769 | We agree with the learned counsel for the petitioner that the High Court could not have placed reliance on the judgments in the cases of Habib Ullah (supra) and |
| Civil Revision No.504 of 2015 | PLD 1997 KAR 62 | Both judgments were expressly approved, whereas the contrary interpretation adopted in Abdul Rahim and others v. United Bank Ltd. (PLD 1997 Karachi 62) was disa |
