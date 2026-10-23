# Seed Conversations Guide for Zarya Digital Bank

## Purpose

This directory contains the foundational seed conversations used to drive synthetic data generation for the Zarya Digital Bank assistant. Batch 1 contains 30 verified seeds in seeds.jsonl. Batch 2 contains 16 verified seeds in seeds_batch2.jsonl, including grounded transfer interactions and 6 no document variants.

## Seed Row Structure

Each seed is formatted as a single line JSON object with these fields:

1. id: Unique string identifier such as seed_031.
2. category: Operational category enumeration (account, transfer, card, loan, complaint, fraud, out_of_scope).
3. intent: Specific intent enumeration matching the schema in src/schema.py.
4. language: Language mode (urdulish, roman_urdu, english, urdu_script).
5. is_multi_turn: Boolean flag (true if two or three customer turns, false if single turn).
6. context: Optional string containing short synthetic policy text, or the token koi document nahi mila, or null.
7. messages: List of message dictionaries with role and content.
8. ticket: Optional dictionary for conversations requiring structured ticket extraction.

## Essential Persona Rules for Assistant Replies

1. Always address the customer with respect using Ji and aap.
2. Keep responses brief and focused. Ask only one question at a time.
3. When answering queries about fees, limits, or turnaround times, ground every number directly in the provided context documents. The legacy token placeholder has been retired.
4. Never request or accept sensitive security credentials such as OTP, PIN, password, or CVV.
5. Never put JSON, curly braces, or markdown code blocks inside assistant chat messages. The assistant speaks strictly in natural conversational language.
6. When customer information is gathered, state that the complaint has been recorded along with the turnaround time from documents. Never invent a ticket reference number.
7. When documents state koi document nahi mila, state inability to confirm, record the request where relevant, and direct the customer to the bank helpline without inventing a telephone number or uttering digits.

## Ticket Metadata and Type B Generation

For seeds that involve complaints or fraud, specify the structured ticket as a separate top level ticket dictionary. The fields are: intent, category, priority, amount, time_mentioned, summary, customer_very_angry, escalate_to_human.

Deterministic escalation rules:
1. escalate_to_human evaluates to true if category is fraud.
2. escalate_to_human evaluates to true if amount is greater than or equal to the large amount threshold (placeholder 50000 rupees).
3. escalate_to_human evaluates to true if customer_very_angry is true.
4. In all other standard situations, escalate_to_human must evaluate to false.

After updating seeds, execute python src/build_json_tasks.py to generate Type B ticket extraction tasks in seeds_json_tasks.jsonl. Then run python src/seed_stats.py to verify distribution counts and confirm that both Type A and Type B pass all validation checks.
