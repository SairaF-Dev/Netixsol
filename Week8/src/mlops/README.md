# MLOps command reference

Run commands from the Week 8 repository root with the project virtual environment active.

```powershell
# Compare the reference training population with current labeled properties.
.\.venv\Scripts\python.exe -m src.mlops.monitoring

# Exercise the drift alarms with a simulated 15% target-price increase.
.\.venv\Scripts\python.exe -m src.mlops.monitoring --simulate-price-increase 0.15 --output reports\day5\simulated_drift_report.json

# Train and validation-score a candidate. Active files change only if MAPE improves.
.\.venv\Scripts\python.exe -m src.mlops.retrain --purpose sale
.\.venv\Scripts\python.exe -m src.mlops.retrain --purpose rent

# Restore one model family from the rollback directory printed by retraining.
.\.venv\Scripts\python.exe -m src.mlops.retrain --purpose sale --rollback models\rollback\<timestamp>
```

Drift reports include per-column PSI, a 0.10 warning threshold, a 0.25 critical threshold, and MAPE alerts above 15% when current rows have verified labels. Candidate selection uses the validation split only; the locked test split is not used to select or promote a model.
