# Long-context vs RAG for contract review (Day 4, Task 5)

10 CUAD test contracts (3,412-14,158 words), 10 clause types each = 100 questions; 44 of them are present according to the CUAD lawyers. Model: gemini-3.5-flash-lite. Script: `python -m evaluations.long_context_vs_rag`.

| | Long-context (whole contract) | RAG (3 chunks per clause type) |
|---|---:|---:|
| Accuracy (present / absent) | 90/100 (90%) | 88/100 (88%) |
| Missed clauses (present, answered absent) | 3/44 | 7/44 |
| False alarms (absent, answered present) | 7 | 5 |
| Quote real and on the right clause | 40/44 | 36/44 |
| Input per contract (~tokens, average) | 14,348 | 10,122 |
| Time per contract (average) | 18.2 s | 5.8 s |

Cost on a paid plan scales with input tokens; the free tier used here costs nothing but limits requests per day. Time includes the client's 4-second pacing between requests (the same for both).

| Contract | Words | Long-context correct | RAG correct |
|---|---:|---:|---:|
| ACCURAYINC_09_01_2010-EX-10.31-DISTRIBUTOR AGREEMENT | 13,349 | 8/10 | 9/10 |
| BEYONDCOMCORP_08_03_2000-EX-10.2-CO-HOSTING AGREEMENT | 7,991 | 9/10 | 9/10 |
| BellringBrandsInc_20190920_S-1_EX-10.12_11817081_EX-10.12_Manufacturin | 6,565 | 9/10 | 9/10 |
| DIVERSINETCORP_03_01_2012-EX-4-RESELLER AGREEMENT | 11,296 | 9/10 | 9/10 |
| ElPolloLocoHoldingsInc_20200306_10-K_EX-10.16_12041700_EX-10.16_Develo | 9,315 | 10/10 | 9/10 |
| GSVINC_05_15_1998-EX-10-SPONSORSHIP AGREEMENT | 5,880 | 7/10 | 7/10 |
| LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_8473102_EX-10.26_Conten | 7,198 | 9/10 | 7/10 |
| NOVOINTEGRATEDSCIENCES,INC_12_23_2019-EX-10.1-JOINT VENTURE AGREEMENT | 3,412 | 10/10 | 10/10 |
| SUMMAFOURINC_06_19_1998-EX-10.3-SOFTWARE LICENSE AND MAINTENANCE AGREE | 14,158 | 9/10 | 9/10 |
| URSCORPNEW_03_17_2014-EX-99-COOPERATION AGREEMENT | 6,004 | 10/10 | 10/10 |
