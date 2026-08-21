# AFL Assistant Monitoring Checklist

## Track
- Response latency
- Tool error rate
- API error rate
- Off-topic leak rate
- Prompt-injection failure rate
- Grounding failures
- Prediction accuracy after real results arrive
- Prediction calibration / probability drift
- Model/data freshness

## Suggested alerts
- P95 latency > 5 seconds: investigate
- Tool error rate > 5%: alert
- Off-topic leak rate > 1%: alert
- Prompt-injection failures > 0: immediate review
- Grounding failures > 1%: review retrieval/routing
- Material prediction accuracy/calibration drift: trigger model review

## Cadence
- Daily: inspect API/tool errors and latency
- Weekly: run the 25+ evaluation suite
- After every completed AFL round: append real outcomes and calculate prediction metrics
- Weekly/biweekly: refresh feature tables
- Retrain when drift or sustained performance degradation justifies it
- Before deployment: run guardrail + regression suite

## Weekly refresh loop
1. Add the newest completed match results.
2. Rebuild team/player feature snapshots without future leakage.
3. Score the existing model on newly observed matches.
4. Compare against the ladder-position baseline.
5. If performance is acceptable, keep the model.
6. If drift/degradation is material, retrain and re-evaluate.
7. Deploy only after regression and guardrail tests pass.
