| model | AUC | accuracy | RMSE | train time (s) |
|---|---|---|---|---|
| DKT (dim=128) | 0.770 | 0.736 | 0.423 | 261 |
| SAKT (dim=128) | 0.747 | 0.722 | 0.432 | 462 |
| BKT (pyBKT, with forgetting) | 0.738 | 0.717 | 0.436 | 4602 |
| PFA (C=1.0, log counts) | 0.736 | 0.713 | 0.436 | 2 |
| baseline: student so far | 0.711 | 0.691 | 0.448 | 0 |
| baseline: skill mean | 0.624 | 0.658 | 0.467 | 0 |
| baseline: global mean | 0.500 | 0.646 | 0.478 | 0 |
