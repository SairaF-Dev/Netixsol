# Trace 2 — Retrieval

Query:
> What were Richmond's last five results?

State trace:

1. `router`
   - intent = `retrieval`

2. `retrieval`
   - resolve Richmond -> exact dataset team
   - call structured pandas lookup

3. `validation`
   - result exists
   - no error

4. `format`
   - returns the dataset-backed result

5. `END`

Why this is safer:
The Day 3 design deliberately uses structured lookup for exact AFL statistics
rather than semantic similarity. The Day 4 graph keeps that controlled path.
