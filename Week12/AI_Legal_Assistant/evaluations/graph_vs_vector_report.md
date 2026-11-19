# Vector vs Graph vs Hybrid on multi-hop questions (Day 3, Task 5)

Questions: `evaluations/multihop_eval_set.jsonl` (30, development: GraphRAG's rules were built on them) and `evaluations/multihop_heldout.jsonl` (10, held-out: written afterwards). Answers are sets; scores are averaged over questions. Script: `python -m evaluations.graph_vs_vector`.

Mode `--no-llm` (no Gemini calls): **graph** is scored as an answer (precision / recall / F1 of the items its Cypher query returns; the 1 question that needs text-to-Cypher counts as unanswered). **vector** and **hybrid** are scored by *answer coverage*: the share of the answer key present anywhere in the retrieved context (vector: top 10 passages; hybrid: graph result + those passages). Coverage is an upper bound on what an LLM could list, not an answer score.

## dev set (30 questions)

| Method | Answer score (P / R / F1) | Answer coverage in context |
|---|---:|---:|
| vector (top 10 passages) | needs Gemini | 53% |
| graph (Cypher, no LLM) | 100% / 98% / 0.99 | 98% |
| hybrid (graph + passages) | needs Gemini | 100% |
| routed | | 98% |

Router choices: {'graph': 30}.

| Question | Route | Graph path | Graph F1 | Vector coverage |
|---|---|---|---:|---:|
| MH_01: Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Pena | graph | local | 1.00 | 12% |
| MH_02: Kin judges ne un muqadmat ki samaat ki jin mein Qanun-e-Shahadat ke Article 129 ka hawala  | graph | local | 0.95 | 40% |
| MH_03: Which judges decided the judgments that discuss Section 164 of the Code of Criminal Proced | graph | local | 1.00 | 0% |
| MH_04: Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997? | graph | local | 1.00 | 90% |
| MH_05: Which judges dealt with cases where a plaint was to be returned under Order VII Rule 10 CP | graph | local | 1.00 | 0% |
| MH_06: Which Lahore High Court judgments refer to Article 189 of the Constitution (decisions of t | graph | local | 1.00 | 0% |
| MH_07: Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution? | graph | local | 1.00 | 25% |
| MH_08: Which judgments refer to Section 376 PPC, and which court decided each of them? | graph | local | 1.00 | 20% |
| MH_09: Which judgments refer to Article 84 of the Qanun-e-Shahadat Order (the court comparing sig | graph | local | 1.00 | 80% |
| MH_10: Which provisions of the Code of Civil Procedure were referred to in cases decided by Justi | graph | local | 1.00 | 38% |
| MH_11: Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad  | graph | local | 1.00 | 33% |
| MH_12: Which Articles of the Constitution were referred to in cases decided by Justice Jawad Hass | graph | local | 1.00 | 25% |
| MH_13: Justice Khalid Ishaq ke muqadmat mein Aain ke kaun se Articles ka zikr hua? | graph | local | 1.00 | 100% |
| MH_14: Which judges sat on the cases that cite 2017 SCMR 1218? | graph | local | 1.00 | 33% |
| MH_15: Which judgments in the corpus rely on or cite 2009 SCMR 230, and who were the judges? | graph | local | 1.00 | 75% |
| MH_16: Which courts decided the judgments citing 2010 SCMR 1630? | graph | local | 1.00 | 100% |
| MH_17: Which judges sat on the cases citing PLJ 2024 SC 114? | graph | local | 1.00 | 60% |
| MH_18: Which judgments cite both PLD 2019 SC 504 and PLD 1991 SC 197 (the cases on applications u | graph | local | 1.00 | 100% |
| MH_19: In judgments that refer to Section 324 PPC (attempt to murder), which other PPC sections a | graph | local | 1.00 | 78% |
| MH_20: Which precedents are cited in both the Supreme Court judgments C.A. 1410/2019 and C.R.P. 4 | graph | local | 1.00 | 0% |
| MH_21: Which precedents do the Lahore High Court judgments in W.P. No. 43022 of 2026 and Writ Pet | graph | local | 1.00 | 0% |
| MH_22: With which judges did Justice Malik Shahzad Ahmad Khan sit on a bench? | graph | local | 1.00 | 100% |
| MH_23: Which judges sat with Justice Amin-ud-Din Khan, and in which cases? | graph | local | 1.00 | 83% |
| MH_24: Which judgments decided by Justice Mirza Viqas Rauf refer to the Contract Act, 1872, and t | graph | local | 1.00 | 100% |
| MH_25: Which precedent (law-report citation) is cited by the largest number of judgments in the c | graph | global | 1.00 | 0% |
| MH_26: Which judge sat on the largest number of corpus cases that refer to Article 199 of the Con | graph | global | 0.67 | 100% |
| MH_27: Which provision of the Code of Civil Procedure is referred to by the most judgments in the | graph | global | 1.00 | 0% |
| MH_28: Which judge sat on the largest number of cases in the corpus? | graph | global | 1.00 | 100% |
| MH_29: Which Article of the Constitution is referred to by the most Lahore High Court judgments? | graph | global | 1.00 | 100% |
| MH_30: Which section of the Code of Criminal Procedure is referred to by the most Supreme Court j | graph | global | 1.00 | 100% |

## heldout set (10 questions)

| Method | Answer score (P / R / F1) | Answer coverage in context |
|---|---:|---:|
| vector (top 10 passages) | needs Gemini | 56% |
| graph (Cypher, no LLM) | 89% / 90% / 0.90 | 90% |
| hybrid (graph + passages) | needs Gemini | 90% |
| routed | | 90% |

Router choices: {'graph': 10}.

| Question | Route | Graph path | Graph F1 | Vector coverage |
|---|---|---|---:|---:|
| HO_01: Which judges sat on the cases that refer to Section 9 of the Code of Civil Procedure? | graph | local | 1.00 | 0% |
| HO_02: How many judgments in the corpus cite PLD 2023 SC 588? | graph | text-to-cypher | 0.00 | 0% |
| HO_03: Which Lahore High Court cases refer to Section 22A of the CrPC? | graph | local | 1.00 | 100% |
| HO_04: Which precedents are cited by both C.A. 435-L/2012 and C.R.P. 410/2023? | graph | local | 1.00 | 80% |
| HO_05: Which judge has sat most often with Justice Musarrat Hilali? | graph | global | 1.00 | 100% |
| HO_06: Kaun se judges ne Section 302 PPC ke muqadmat sune? | graph | local | 1.00 | 25% |
| HO_07: Which Constitution Articles came up in the cases heard by Justice Qazi Faez Isa? | graph | local | 0.97 | 50% |
| HO_08: Which courts decided the judgments that cite PLD 2003 SC 315? | graph | local | 1.00 | 100% |
| HO_09: Which judgments cite both 2017 SCMR 1218 and 2019 SCMR 906? | graph | local | 1.00 | 100% |
| HO_10: Which section of the Code of Criminal Procedure appears in the most Lahore High Court judg | graph | global | 1.00 | 0% |
