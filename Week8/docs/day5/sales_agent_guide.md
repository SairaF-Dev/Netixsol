# Sales-agent quick guide

## Starting the service

Start the Week 8 API using the project README or the deployment instructions in [operations.md](./operations.md). Open the connected Week 7 dashboard and confirm the Week 8 API is available. If it is unavailable, report the issue to the administrator instead of treating sample results as customer records.

## Property valuation

1. Open the ML valuation page and select Sale or Rent.
2. Enter the supported city, locality, property type, area, bedrooms and bathrooms.
3. Review the estimate, price range and listed-price verdict together.
4. Read the SHAP drivers as model contributions on the **log-price scale**. They are not individual PKR adjustments and do not prove a cause.
5. Compare the estimate with current local comparables and inspect the property before advising a client.

The result is an estimate, not an appraisal or a guaranteed sale/rental price. Do not use it as the sole basis for a financial or contractual decision.

## Lead prioritization

1. Open the lead scoring page and review each lead's tier, score and explanation.
2. Use Hot/Warm/Cold as suggested follow-up priority, not as a promise that a lead will or will not convert.
3. Check the source label. “Week 8 Simulated Leads” and “Sample Leads” are demonstration data, not verified CRM customers.
4. Until the lead model is validated against real, consented CRM outcomes, use scores for demonstration and human-reviewed prioritization only.

## Assistant and escalation

Ask the assistant for a valuation, a lead score, comparable listings or market statistics. Its numeric answers should come from the corresponding model or data tool. Verify important results in the dashboard or with a sales manager. Escalate missing fields, unsupported cities, rejected out-of-distribution inputs, and unavailable API responses; do not invent replacement numbers.

## Feedback and responsible use

Never enter credentials or unnecessary personal information in assistant prompts. Do not promise a price, approve a lead automatically, or use synthetic/sample identities as real customers. Report incorrect data, implausible estimates, or repeated errors by city/property segment to the model owner for review.
