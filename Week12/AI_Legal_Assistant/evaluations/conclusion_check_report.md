# Conclusion check: does the answer's conclusion follow from its sources?

The citation verifier proves each quote exists; this check asks whether the conclusion drawn from it is right (same legal issue, no retrieved passage contradicting or limiting it, not overstated). Run on the 79 answered questions of the Day 2 query-rewriting run, with the same passages and answers (one extra Gemini call each). Script: `python -m evaluations.conclusion_check_eval`.

| Verdict | Answers |
|---|---:|
| supported | 75 |
| partly | 2 |
| not_supported | 2 |

Every flagged answer was read by hand against the expected answer and the passages (read by Claude (an AI model) against the expected answer and the retrieved passages, not by a lawyer): **4 of 4 flags point to a real problem**, 0 are false alarms.

A sample of 10 answers the check passed was read the same way: 0 had a problem the check missed.

| Question | Type | Verdict | The check's reason | Hand review |
|---|---|---|---|---|
| STAT_010: If multiple people act as sureties for the same debt, how should they divide the liability among themselves if | statute | partly | The answer is incomplete as it fails to address the scenario where co-sureties are bound in different sums, which is governed by Section 147 (Passage 2). | right: minor: equal shares is correct, but the answer leaves out the rule in the next passage (Section 147) for co-sureties bound in different sums |
| STAT_039: Agar main apni job ke dauran kisi shakhs par terrorism ka shaq karoon, to kya mujhe police ko batana lazmi hai | statute | partly | The answer states that it is mandatory (qanoonan majboor) to report suspicion, but the provided passages describe the procedure for reporting and the protections for doing so, without explicitly establishing a mandatory legal duty to report. | right: the conclusion (reporting is mandatory) matches the expected answer, but the cited passage is about cooperating with the police, not the duty to disclose; the shown source does not back the claim |
| CASE_028: لاہور ہائی کورٹ نے ایل ایل بی کے امتحانات کو ٹکڑوں میں پاس کرنے اور پہلی کوشش میں ناکامی کے حوالے سے کیا رائے  | case_law | not_supported | The passages describe the appellant's history as a matter of fact in a specific case, but the court does not express a general legal opinion or ruling on the practice of passing exams in parts or failing first attempts; in fact, the court explicitly states this fact is not important for the decision. | right: the answer reports the appellant's piecemeal exams as the court's view but leaves out that the court said this fact was not important for the decision |
| NOANS_010: Partnership Act, 1932 ke tehat ek partner ka dusre partner ke khilaf account ka dawa kaise daira kiya jata hai | no_answer | not_supported | The answer relies on the Code of Civil Procedure, 1908, but fails to address the Partnership Act, 1932, as requested by the user. | right: a question the corpus cannot answer (Partnership Act, 1932 is not in it); the answer used the Code of Civil Procedure instead of saying no source was found |

Example caught outside this set (Day 2 demo, Urdu): asked whether a court can award *more* than the penalty amount fixed in a contract, the model answered yes, citing a real Specific Relief Act passage about enforcing the contract itself. The check rejected it ("the passages discuss specific performance despite a penalty clause, but do not address damages exceeding the amount"); the redraft answered "No sufficient source found", which is right for the passages retrieved.
