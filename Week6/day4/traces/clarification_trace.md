# Trace 3 — Ambiguous Prediction

Query:
> Who will win Tigers?

State trace:

1. `router`
   - intent = `prediction`

2. `prediction`
   - Tigers -> Richmond
   - opponent is missing

3. `validation`
   - `needs_clarification`

4. `clarification`
   - asks for the missing opponent/date rather than guessing

5. `END`

Safety property:
No prediction tool is called with an invented opponent.
