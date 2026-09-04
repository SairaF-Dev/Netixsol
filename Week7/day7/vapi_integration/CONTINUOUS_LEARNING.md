# Continuous Learning For Sara

Sara should not update her production behavior directly from raw calls. Use a
reviewed offline loop:

```text
VAPI call
  -> redacted JSONL record (optional)
  -> human review and label
  -> evaluation set and approved fine-tuning examples
  -> offline evaluation
  -> staged deployment
```

## 1. Collect records

The VAPI `end-of-call-report` path can write redacted records when enabled:

```env
SARA_LEARNING_ENABLED=1
SARA_LEARNING_DATA_PATH=data/learning/conversations.jsonl
SARA_CUSTOMER_HASH_SALT=generate-a-long-random-secret
DATABASE_URL=postgresql://...
```

The collector is disabled by default. It removes email addresses and phone
numbers and marks every record `review_status: unreviewed`. Keep this data out
of git and follow consent, retention, and applicable privacy requirements.

Add a human label after review, for example:

- `successful`: Sara answered correctly and the customer reached the intended next step
- `needs_correction`: the response was wrong, unclear, or poorly grounded
- `escalate`: a human should handle the case

Also record a correction or ideal response. Do not train on an unreviewed
transcript, a hallucinated property fact, or a private customer detail.

For preference learning, approved records may include a `features` object with
`city`, `area`, `budget`, `bedrooms`, `property_type`, `purpose`, `amenities`,
`viewed_property_ids`, `rejected_property_ids`, and `booked_property_ids`.
These annotations are aggregated per salted `customer_key`.

Initialize the profile table once:

```powershell
psql $env:DATABASE_URL -f day7/vapi_integration/learning_schema.sql
```

## 2. Improve the right layer

Use the failure type to choose the intervention:

| Failure | Correct intervention |
|---|---|
| Old or missing property fact | Update Day 2 PostgreSQL/RAG knowledge base |
| Wrong intent or constraint extraction | Add a reviewed evaluation case; improve the parser/prompt |
| Weak UrduLish wording | Add approved response examples or tune the speech policy |
| Repeated task failure | Fix the workflow/tool contract and add a regression test |
| Tone or policy problem | Update guardrails and test the refusal/redirect |

Most real-estate improvements should be retrieval, validation, prompts, and
regression tests first. Fine-tuning is useful only after collecting a stable,
representative, reviewed dataset.

## 3. Build preference profiles

Run the offline aggregation after reviewers set `review_status` to
`approved`:

```powershell
cd day7/vapi_integration
python scripts/train_preferences.py data/learning/conversations.jsonl
```

This stores only customer preference profiles in PostgreSQL. It does not alter
the property tables and does not fine-tune an LLM.

At runtime, Sara first asks `PostgresPropertyRepository` for verified,
available candidates using the requested filters. If a profile is available,
`ExplainablePreferenceRanker` reorders those rows using city, area, budget,
bedrooms, type, purpose, amenities, and prior property outcomes. The response
still contains only facts from the PostgreSQL candidate rows. Without a profile,
salt, database, or model result, the original repository order is preserved.

## 4. Build training data

Convert only approved records into your provider's format. For supervised
fine-tuning, each example should contain the conversation and the desired
assistant answer, for example:

```json
{"messages":[{"role":"system","content":"Sara policy and UrduLish instructions"},{"role":"user","content":"DHA mein 3 bedroom flat chahiye"},{"role":"assistant","content":"Zaroor. Aap ka budget aur preferred area kya hai?"}]}
```

Keep a separate holdout set that is never used for training. Include real
failure cases, UrduLish code-switching, prompt injection, unsupported property
claims, and appointment edge cases.

## 5. Measure before deployment

Track grounded-answer accuracy, intent accuracy, constraint extraction,
appointment success, escalation rate, refusal correctness, latency, and cost.
Compare the candidate model against the current version on the same holdout
set. Deploy gradually and retain rollback capability.

This is continuous improvement, not autonomous self-training: a reviewer and an
evaluation gate decide what reaches production.
