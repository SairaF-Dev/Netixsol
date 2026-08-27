# Recommendation Examples

## Example 1 — Buyer

Input:

```text
Budget: 3 crore
City: Lahore
Area: DHA
Bedrooms: 3
Purpose: Purchase
```

The engine should filter available properties and rank the best matches.

## Example 2 — Cheaper option

If the customer says:

> "Is se sasti koi option hai?"

The agent should preserve the previous requirements and lower the price
constraint instead of restarting the conversation.

## Example 3 — Rental

```text
Budget: 150,000 PKR/month
City: Lahore
Property type: Apartment
Bedrooms: 3
Purpose: Rental
```

The recommendation engine should return available rental properties
within the budget.

## Important

Recommendations are generated only from available records in the
structured knowledge base. The engine must not invent a property.
