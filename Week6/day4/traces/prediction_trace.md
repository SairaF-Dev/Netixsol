# Trace 1 — Match Prediction

Query:
> Will the Pies beat the Cats?

Expected state trace:

1. `router`
   - intent = `prediction`
   - reason = future match outcome

2. `prediction`
   - Pies -> dataset team name
   - Cats -> dataset team name
   - explicit date required by the current Day 2 API

3. If date is available:
   - `match_winner_prediction`
   - result contains predicted winner + home win probability + as-of date

4. `validation`
   - confirms a non-error result

5. `format`
   - converts probability to winner probability
   - mentions grounding inputs
   - explicitly states that the result is probabilistic, not certain

6. `END`

Important:
The supplied Day 2 `predict_match_winner()` requires an explicit date. The
provided historical artifacts do not constitute a live fixture feed, so the
implementation asks for a date instead of guessing a "this week" fixture.
