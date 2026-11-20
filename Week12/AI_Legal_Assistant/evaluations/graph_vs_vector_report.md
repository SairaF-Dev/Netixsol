# Vector vs Graph vs Hybrid on multi-hop questions (Day 3, Task 5)

Questions: `evaluations/multihop_eval_set.jsonl` (30, development: GraphRAG's rules were built on them) and `evaluations/multihop_heldout.jsonl` (10, held-out: written afterwards). Answers are sets; scores are averaged over questions. Script: `python -m evaluations.graph_vs_vector`.

Answers by `gemini-3.5-flash-lite`. **graph** answers come straight from the Cypher result (local / global search; text-to-Cypher for the one question it cannot plan: HO_02, which it answered correctly). **vector**: Gemini lists the answer from the top 10 passages. **hybrid**: Gemini gets the graph result and the passages. The hybrid prompt was changed once after the first run: with a generic 'answer only from the material' instruction Gemini discarded the graph list whenever the passages did not repeat it (F1 0.56 dev / 0.43 held-out); the final prompt says the graph result is a query over all judgments and should be copied. Even so it drops or splits items, so for list questions the graph result itself is the better answer, and the router sends these questions to the graph.

## dev set (30 questions)

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| vector | 49% | 40% | 0.40 |
| graph | 100% | 98% | 0.99 |
| hybrid | 77% | 74% | 0.72 |
| routed | 100% | 98% | 0.99 |

Router choices: {'graph': 30}.

| Question | Route | Graph path | Graph F1 | Vector coverage |
|---|---|---|---:|---:|
| MH_01: Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Pena | graph | local | 1.00 | 0% |
| MH_02: Kin judges ne un muqadmat ki samaat ki jin mein Qanun-e-Shahadat ke Article 129 ka hawala  | graph | local | 0.95 | 46% |
| MH_03: Which judges decided the judgments that discuss Section 164 of the Code of Criminal Proced | graph | local | 1.00 | 0% |
| MH_04: Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997? | graph | local | 1.00 | 78% |
| MH_05: Which judges dealt with cases where a plaint was to be returned under Order VII Rule 10 CP | graph | local | 1.00 | 0% |
| MH_06: Which Lahore High Court judgments refer to Article 189 of the Constitution (decisions of t | graph | local | 1.00 | 0% |
| MH_07: Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution? | graph | local | 1.00 | 40% |
| MH_08: Which judgments refer to Section 376 PPC, and which court decided each of them? | graph | local | 1.00 | 44% |
| MH_09: Which judgments refer to Article 84 of the Qanun-e-Shahadat Order (the court comparing sig | graph | local | 1.00 | 67% |
| MH_10: Which provisions of the Code of Civil Procedure were referred to in cases decided by Justi | graph | local | 1.00 | 40% |
| MH_11: Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad  | graph | local | 1.00 | 0% |
| MH_12: Which Articles of the Constitution were referred to in cases decided by Justice Jawad Hass | graph | local | 1.00 | 67% |
| MH_13: Justice Khalid Ishaq ke muqadmat mein Aain ke kaun se Articles ka zikr hua? | graph | local | 1.00 | 80% |
| MH_14: Which judges sat on the cases that cite 2017 SCMR 1218? | graph | local | 1.00 | 50% |
| MH_15: Which judgments in the corpus rely on or cite 2009 SCMR 230, and who were the judges? | graph | local | 1.00 | 75% |
| MH_16: Which courts decided the judgments citing 2010 SCMR 1630? | graph | local | 1.00 | 0% |
| MH_17: Which judges sat on the cases citing PLJ 2024 SC 114? | graph | local | 1.00 | 75% |
| MH_18: Which judgments cite both PLD 2019 SC 504 and PLD 1991 SC 197 (the cases on applications u | graph | local | 1.00 | 100% |
| MH_19: In judgments that refer to Section 324 PPC (attempt to murder), which other PPC sections a | graph | local | 1.00 | 71% |
| MH_20: Which precedents are cited in both the Supreme Court judgments C.A. 1410/2019 and C.R.P. 4 | graph | local | 1.00 | 0% |
| MH_21: Which precedents do the Lahore High Court judgments in W.P. No. 43022 of 2026 and Writ Pet | graph | local | 1.00 | 0% |
| MH_22: With which judges did Justice Malik Shahzad Ahmad Khan sit on a bench? | graph | local | 1.00 | 94% |
| MH_23: Which judges sat with Justice Amin-ud-Din Khan, and in which cases? | graph | local | 1.00 | 38% |
| MH_24: Which judgments decided by Justice Mirza Viqas Rauf refer to the Contract Act, 1872, and t | graph | local | 1.00 | 33% |
| MH_25: Which precedent (law-report citation) is cited by the largest number of judgments in the c | graph | global | 1.00 | 0% |
| MH_26: Which judge sat on the largest number of corpus cases that refer to Article 199 of the Con | graph | global | 0.67 | 0% |
| MH_27: Which provision of the Code of Civil Procedure is referred to by the most judgments in the | graph | global | 1.00 | 0% |
| MH_28: Which judge sat on the largest number of cases in the corpus? | graph | global | 1.00 | 0% |
| MH_29: Which Article of the Constitution is referred to by the most Lahore High Court judgments? | graph | global | 1.00 | 100% |
| MH_30: Which section of the Code of Criminal Procedure is referred to by the most Supreme Court j | graph | global | 1.00 | 100% |

## heldout set (10 questions)

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| vector | 48% | 47% | 0.43 |
| graph | 99% | 100% | 1.00 |
| hybrid | 78% | 73% | 0.73 |
| routed | 99% | 100% | 1.00 |

Router choices: {'graph': 10}.

| Question | Route | Graph path | Graph F1 | Vector coverage |
|---|---|---|---:|---:|
| HO_01: Which judges sat on the cases that refer to Section 9 of the Code of Civil Procedure? | graph | local | 1.00 | 0% |
| HO_02: How many judgments in the corpus cite PLD 2023 SC 588? | graph | text-to-cypher | 1.00 | 40% |
| HO_03: Which Lahore High Court cases refer to Section 22A of the CrPC? | graph | local | 1.00 | 100% |
| HO_04: Which precedents are cited by both C.A. 435-L/2012 and C.R.P. 410/2023? | graph | local | 1.00 | 0% |
| HO_05: Which judge has sat most often with Justice Musarrat Hilali? | graph | global | 1.00 | 100% |
| HO_06: Kaun se judges ne Section 302 PPC ke muqadmat sune? | graph | local | 1.00 | 46% |
| HO_07: Which Constitution Articles came up in the cases heard by Justice Qazi Faez Isa? | graph | local | 0.97 | 45% |
| HO_08: Which courts decided the judgments that cite PLD 2003 SC 315? | graph | local | 1.00 | 0% |
| HO_09: Which judgments cite both 2017 SCMR 1218 and 2019 SCMR 906? | graph | local | 1.00 | 100% |
| HO_10: Which section of the Code of Criminal Procedure appears in the most Lahore High Court judg | graph | global | 1.00 | 0% |
