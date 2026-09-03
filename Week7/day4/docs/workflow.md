# Day 4 workflow

```mermaid
flowchart LR
  A[Day 3 pending action] --> B{Complete details?}
  B -- no --> C[Ask caller for missing field]
  B -- yes --> D[Check employee calendar]
  D -- busy --> E[Request another slot]
  D -- free --> F[Create or update event]
  F --> G[Persist appointment and audit event]
  G --> H[Email assigned employee]
  H --> I[Publish n8n event]
  I --> J[Return confirmation plus warnings]
```

Reschedule and cancellation accept the internal appointment UUID. The Google
event ID is loaded from CRM so a caller cannot inject an arbitrary event ID.
Notification failures remain visible as warnings and do not create duplicate
calendar events.
