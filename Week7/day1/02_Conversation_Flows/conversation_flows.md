# Task 2 — Conversation Flow Design

Each flow below follows the same skeleton — **Greet → Identify Intent → Qualify → Deliver Value → Handle Objection → Drive to Action → Confirm → Close/Log** — but branches differently once intent is known.

## 2.1 Buyer Inquiry

```mermaid
flowchart TD
    A[Greeting] --> B{New or returning caller?}
    B -->|New| C[Ask: buy/rent/invest/commercial]
    B -->|Returning| C2[Pull history, greet by name]
    C --> D[Qualify: budget, location, size, timeline]
    C2 --> D
    D --> E[RAG: search matching properties]
    E --> F[Present 2-3 options with key highlights]
    F --> G{Interested?}
    G -->|Yes| H[Offer site visit slots]
    G -->|Objection: price/location/etc| I[Objection handling]
    I --> F
    H --> J[Book visit via Calendar API]
    J --> K[Send confirmation email]
    K --> L[Log conversation + close warmly]
```

## 2.2 Rental Inquiry

```mermaid
flowchart TD
    A[Greeting] --> B[Ask: area, budget/month, bedrooms, move-in date]
    B --> C[RAG: search rental listings]
    C --> D[Present matches: rent, deposit, furnishing]
    D --> E{Interested?}
    E -->|Yes| F[Explain lease terms & documents needed]
    E -->|Price too high| G[Offer nearby/lower-tier alternatives]
    G --> D
    F --> H[Book viewing]
    H --> I[Confirm + email + log]
```

## 2.3 Commercial Property Inquiry

```mermaid
flowchart TD
    A[Greeting] --> B[Identify: office/retail/warehouse, sq ft, purpose]
    B --> C[Qualify: business type, footfall needs, budget, lease vs buy]
    C --> D[RAG: commercial listings + zoning/compliance notes]
    D --> E[Present options with commercial specifics: parking, floor plan, utilities]
    E --> F{Needs decision-maker approval?}
    F -->|Yes| G[Offer to send detailed proposal by email]
    F -->|No| H[Book site visit]
    G --> I[Schedule follow-up call]
    H --> J[Confirm + log]
    I --> J
```

## 2.4 Investment Inquiry

```mermaid
flowchart TD
    A[Greeting] --> B[Qualify: investment goal - rental yield vs capital gain]
    B --> C[Ask budget range and risk appetite]
    C --> D[RAG: high-ROI listings, historical appreciation data]
    D --> E[Present options with ROI/rental yield figures]
    E --> F{Objection: risk/market conditions}
    F -->|Yes| G[Address with data-backed reassurance]
    G --> E
    F -->|No, convinced| H[Offer investor site visit + payment plan details]
    H --> I[Book visit, send investment brochure by email]
    I --> J[Log + close]
```

## 2.5 Returning Customer

```mermaid
flowchart TD
    A[Caller ID matched in DB] --> B[Pull past inquiries/visits from memory]
    B --> C[Personalized greeting referencing history]
    C --> D{Purpose of call}
    D -->|Follow-up on same property| E[Give status update]
    D -->|New request| F[Route to relevant flow 2.1-2.4]
    E --> G{Ready to proceed?}
    G -->|Yes| H[Book visit / next step]
    G -->|Still deciding| I[Offer to send more info, schedule follow-up]
    H --> J[Confirm + log]
    I --> J
```

## 2.6 Appointment Rescheduling

```mermaid
flowchart TD
    A[Caller requests reschedule] --> B[Look up existing booking via phone/ID]
    B --> C{Booking found?}
    C -->|No| D[Politely clarify details / offer new booking]
    C -->|Yes| E[Confirm which appointment]
    E --> F[Ask preferred new date/time]
    F --> G[Check Calendar availability]
    G --> H{Slot available?}
    H -->|Yes| I[Update Calendar event]
    H -->|No| J[Offer nearest alternative slots]
    J --> F
    I --> K[Send updated confirmation email]
    K --> L[Log change + close]
```

## 2.7 Appointment Cancellation

```mermaid
flowchart TD
    A[Caller requests cancellation] --> B[Look up booking]
    B --> C{Found?}
    C -->|No| D[Clarify details]
    C -->|Yes| E[Confirm details back to caller]
    E --> F[Ask reason - optional, for CRM insight]
    F --> G{Open to rescheduling instead?}
    G -->|Yes| H[Route to 2.6 Reschedule flow]
    G -->|No, cancel| I[Cancel Calendar event]
    I --> J[Send cancellation confirmation email]
    J --> K[Log cancellation + polite door-open close]
```
