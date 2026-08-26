# Appointment Cancellation — Conversation Flow

## 1. Purpose

This flow handles customers who want to cancel an existing property visit
appointment.

The agent must:

- Identify the customer.
- Retrieve active appointments.
- Identify the correct appointment.
- Confirm the cancellation when necessary.
- Cancel the Calendar event.
- Update CRM records.
- Trigger employee/customer notifications.
- Preserve appointment history.
- Confirm cancellation only after the Calendar operation succeeds.

### Core Rule

> Never tell the customer that an appointment has been cancelled until the
> cancellation has actually succeeded.

---

# 2. Required Information

| Information | Required | Example |
|---|---|---|
| Customer ID | Yes | CUST-1024 |
| Customer Name | Preferred | Ali Khan |
| Phone | Yes | +92XXXXXXXXXX |
| Appointment ID | Yes | APT-1001 |
| Property | Yes | DHA Phase 6 Apartment |
| Appointment Date | Yes | Saturday |
| Appointment Time | Yes | 4 PM |
| Cancellation Reason | Optional | Personal issue |
| Assigned Employee | Preferred | Ahmed |

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Identify Customer
      ↓
Detect Cancellation Intent
      ↓
Retrieve Active Appointments
      ↓
Appointments Found?
   ┌──────┴──────┐
  YES            NO
   ↓              ↓
One Appointment  Inform Customer
   ↓              ↓
Multiple?      Human Escalation
   ┌──────┴──────┐
  NO             YES
   ↓              ↓
Select          Ask Which
Appointment     Appointment
   └──────┬──────┘
          ↓
   Confirm Cancellation
          ↓
   Cancel Calendar Event
          ↓
     Success?
     ┌────┴────┐
    YES        NO
     ↓          ↓
  Update CRM   Error Handling
     ↓
   n8n Event
     ↓
 ┌───┼─────────┐
 ↓   ↓         ↓
Email CRM Notification
     ↓
Confirmation
     ↓
   Goodbye
````

---

# 4. Stage 1: Detect Cancellation Intent

Natural customer examples:

```text
"Meri property visit cancel kar dein."

"Saturday wali appointment cancel karni hai."

"Main visit par nahi aa sakta."

"Jo appointment book hui thi woh cancel kar dein."

"Meri DHA wali visit cancel kar dein."

"Mujhe appointment cancel karwani hai."
```

Map to:

```text
intent = appointment_cancellation
```

---

# 5. Stage 2: Identify Customer

The telephony layer provides the incoming phone number.

```text
incoming_phone
      ↓
get_customer_by_phone()
      ↓
customer_id
```

Example:

```json
{
  "customer_id": "CUST-1024",
  "name": "Ali Khan",
  "phone": "+92XXXXXXXXXX"
}
```

If the customer cannot be identified:

> "Ji bilkul, main aapki appointment check kar deta hoon. Aap apna naam
> confirm kar dein?"

Do not cancel an appointment based only on an unverified name.

---

# 6. Stage 3: Retrieve Active Appointments

Call:

```text
get_customer_appointments(
    customer_id="CUST-1024",
    status="confirmed"
)
```

Example:

```text
Appointment 1
Property: DHA Phase 6 Apartment
Date: Saturday
Time: 4 PM
Status: Confirmed

Appointment 2
Property: Bahria Town Apartment
Date: Sunday
Time: 3 PM
Status: Confirmed
```

---

# 7. One Active Appointment

If only one appointment exists:

Agent:

> "Ji sir, aapki DHA Phase 6 wali visit Saturday 4 PM par scheduled hai.
> Aap isi appointment ko cancel karna chahte hain?"

Customer:

> "Ji."

Proceed with cancellation.

---

# 8. Multiple Active Appointments

If multiple appointments exist:

Agent:

> "Ji sir, aapki do visits scheduled hain — DHA Phase 6 Saturday 4 PM
> aur Bahria Town Sunday 3 PM. Aap kis wali appointment ko cancel
> karna chahte hain?"

Customer:

> "DHA wali."

Now select:

```text
appointment_id = APT-1001
```

Never guess.

---

# 9. Stage 4: Confirmation

For cancellation, the agent should clearly identify the appointment before
performing the destructive action.

Example:

> "Ji sir, confirm kar doon ke aap DHA Phase 6 ki Saturday 4 PM wali
> property visit cancel karna chahte hain?"

Customer:

> "Ji, cancel kar dein."

Now proceed.

---

# 10. Customer Changes Mind

Customer:

> "Nahi, rehne dein."

Do not call the cancellation tool.

Update:

```text
cancellation_status = not_confirmed
```

Agent:

> "Ji bilkul, appointment as it is rehne dete hain."

---

# 11. Stage 5: Cancel Calendar Event

Call:

```text
cancel_calendar_event(
    appointment_id="APT-1001"
)
```

Or, depending on the implementation:

```text
cancel_calendar_event(
    calendar_event_id="google-event-123"
)
```

The tool should return a clear success/failure result.

---

# 12. Calendar Cancellation Successful

Example:

```json
{
  "success": true,
  "appointment_id": "APT-1001",
  "status": "cancelled"
}
```

Only after this result should the system update the appointment status.

---

# 13. Update CRM

Store:

```json
{
  "appointment_id": "APT-1001",
  "customer_id": "CUST-1024",
  "status": "cancelled",
  "cancelled_at": "2026-08-26T23:10:00+05:00",
  "cancellation_reason": "Personal issue"
}
```

Do not delete the appointment.

The history should remain:

```text
Booked
  ↓
Confirmed
  ↓
Cancelled
```

This is important for CRM analytics and customer history.

---

# 14. Cancellation Reason

The reason is useful but should not become a mandatory interrogation.

Agent:

> "Agar aap mind karein to main cancellation reason note kar doon?"

Customer:

> "Personal issue hai."

Store:

```text
cancellation_reason = personal_issue
```

If the customer does not want to provide a reason:

```text
cancellation_reason = not_provided
```

Do not pressure the customer.

---

# 15. Stage 6: n8n Workflow

After successful Calendar cancellation:

```text
AppointmentCancelled
        ↓
       n8n
    ┌───┼────────┐
    ↓   ↓        ↓
 Email CRM   Notification
```

The event payload may contain:

```json
{
  "event": "AppointmentCancelled",
  "customer_id": "CUST-1024",
  "appointment_id": "APT-1001",
  "property_id": "DHA-P6-102",
  "employee_id": "EMP-12",
  "appointment_datetime": "2026-08-29T16:00:00+05:00",
  "reason": "Personal issue"
}
```

---

# 16. Employee Notification

Example:

```text
Subject:
Property Visit Cancelled — Ali Khan — DHA Phase 6

Customer:
Ali Khan

Phone:
+92XXXXXXXXXX

Property:
DHA Phase 6 Apartment

Original Visit:
Saturday, 4 PM

Status:
Cancelled

Reason:
Personal issue
```

---

# 17. Customer Confirmation

After successful cancellation:

> "Ji bilkul sir, aapki DHA Phase 6 wali Saturday 4 PM ki property visit
> cancel ho gayi hai."

Optional:

> "Agar aap baad mein visit reschedule karna chahein to main aapki help
> kar sakta hoon."

Do not pressure the customer into rebooking.

---

# 18. Calendar Cancellation Failure

Example:

```text
cancel_calendar_event()
        ↓
FAILED
```

The agent must NOT say:

> "Ji, appointment cancel ho gayi hai."

Instead:

> "Sorry sir, appointment cancel karte waqt technical issue aa gaya hai.
> Main isko dobara try karta hoon."

If retry also fails:

> "Sir, main abhi appointment successfully cancel nahi kar pa raha.
> Main is request ko representative ko forward kar deta hoon."

Store:

```text
cancellation_status = failed
human_escalation = true
```

---

# 19. CRM Update Rule

If Calendar cancellation fails:

```text
Calendar = FAILED
CRM appointment status = NOT CANCELLED
```

Do not mark:

```text
status = cancelled
```

until the actual cancellation succeeds.

---

# 20. Email Failure

Possible result:

```text
Calendar = SUCCESS
CRM = SUCCESS
Email = FAILED
```

The appointment is still cancelled.

The customer should not be told that cancellation failed.

Instead:

> "Ji sir, appointment successfully cancel ho gayi hai. Notification
> email mein issue aa raha hai, lekin Calendar mein cancellation complete
> ho chuki hai."

Store:

```text
email_status = failed
retry_required = true
```

n8n should retry the email.

---

# 21. Notification Failure

If Calendar and CRM succeed but notification fails:

```text
Calendar = SUCCESS
CRM = SUCCESS
Notification = FAILED
```

The cancellation remains valid.

Log the failure and retry asynchronously.

---

# 22. Appointment Already Cancelled

Customer:

> "Meri appointment cancel kar dein."

CRM:

```text
status = cancelled
```

Agent:

> "Ji sir, ye appointment pehle hi cancel ho chuki hai."

Do not call the cancellation tool again.

---

# 23. Appointment Already Completed

If:

```text
status = completed
```

The appointment cannot be cancelled.

Agent:

> "Ji sir, ye visit already complete ho chuki hai, isliye isko cancel
> karne ki zaroorat nahi hai."

If the customer actually wants another appointment cancelled, retrieve
active appointments and clarify.

---

# 24. Appointment Not Found

If there is no matching active appointment:

> "Ji sir, mujhe aapke account par currently koi confirmed property visit
> nazar nahi aa rahi. Agar aap chahein to main representative se confirm
> karwa deta hoon."

Do not invent an appointment.

---

# 25. Multiple Matching Appointments

Example:

```text
DHA Phase 6
Saturday 4 PM

DHA Phase 5
Sunday 5 PM

Bahria Town
Monday 3 PM
```

Customer:

> "DHA wali cancel kar dein."

There are two DHA appointments.

The agent must clarify:

> "Ji sir, DHA Phase 6 wali Saturday 4 PM ya DHA Phase 5 wali Sunday
> 5 PM?"

Customer selects one.

Proceed with that appointment only.

---

# 26. Natural UrduLish Responses

Avoid robotic:

> "Please specify the appointment ID you wish to cancel."

Use:

> "Ji bilkul. Aapki kaunsi visit cancel karni hai?"

Avoid:

> "Cancellation request received."

Use:

> "Ji, main aapki visit cancel kar deta hoon."

Avoid:

> "Cancellation operation successful."

Use:

> "Ji bilkul, appointment cancel ho gayi hai."

---

# 27. Complete Example

### Customer

> "Assalam-o-Alaikum, meri DHA wali visit cancel karni hai."

### Agent

> "Wa-Alaikum-Assalam sir. Ji bilkul, main aapki appointment check
> kar leta hoon."

### CRM

```text
Customer:
Ali Khan

Appointments:

1. DHA Phase 6
   Saturday 4 PM
   Confirmed

2. Bahria Town
   Sunday 3 PM
   Confirmed
```

### Agent

> "Ji sir, aapki do visits hain. DHA Phase 6 wali Saturday 4 PM aur
> Bahria Town wali Sunday 3 PM. Aap DHA Phase 6 wali cancel karna
> chahte hain?"

### Customer

> "Ji."

### Agent

> "Ji bilkul. Confirm kar doon ke Saturday 4 PM wali DHA Phase 6
> visit cancel karni hai?"

### Customer

> "Yes."

### Tool

```text
cancel_calendar_event(
    appointment_id="APT-1001"
)
```

### Result

```text
SUCCESS
```

### CRM

```text
appointment_status = cancelled
```

### n8n

```text
AppointmentCancelled
        ↓
       n8n
    ┌───┼────┐
    ↓   ↓    ↓
 Email CRM Notification
```

### Agent

> "Ji bilkul sir, aapki DHA Phase 6 wali Saturday 4 PM ki visit
> cancel ho gayi hai."

---

# 28. LangGraph Routing

```text
START
  ↓
detect_intent
  ↓
appointment_cancellation
  ↓
load_customer
  ↓
load_appointments
  ↓
select_appointment
  ↓
confirm_cancellation
  ↓
cancel_calendar_event
  ↓
 ┌──────────────┴──────────────┐
 ↓                             ↓
success                       failure
 ↓                             ↓
update_crm                retry / escalate
 ↓
trigger_n8n
 ↓
send_notifications
 ↓
confirm_customer
 ↓
END
```

---

# 29. State Example

```python
state = {
    "customer_id": "CUST-1024",

    "intent": "appointment_cancellation",

    "appointment_id": "APT-1001",

    "property_id": "DHA-P6-102",

    "appointment_datetime": "2026-08-29T16:00:00+05:00",

    "cancellation_confirmed": True,

    "cancellation_status": "confirmed",

    "calendar_status": "success",

    "crm_status": "updated",

    "email_status": "pending",

    "notification_status": "pending"
}
```

---

# 30. Guardrails

The cancellation flow MUST enforce:

```text
 Never cancel an appointment without identifying the customer.
 Never guess when multiple appointments exist.
 Never cancel without confirmation.
 Never claim cancellation before Calendar success.
 Never mark CRM as cancelled if Calendar cancellation failed.
 Never delete appointment history.
 Never create a new appointment during cancellation.
 Never expose internal Calendar event IDs to customers.
 Never claim an email was sent if email failed.
 Never invent an appointment.
 Never repeatedly cancel an already cancelled appointment.
```

---

# 31. Security Considerations

Cancellation is a destructive business action.

Therefore:

```text
Customer Identification
        ↓
Appointment Identification
        ↓
Explicit Confirmation
        ↓
Calendar Mutation
        ↓
CRM Update
```

The LLM should not directly modify appointment records.

Instead:

```text
LLM
 ↓
Structured Tool Call
 ↓
Validation Layer
 ↓
Calendar API
 ↓
CRM
```

This prevents accidental or hallucinated cancellations.

---

# 32. Success Criteria

The cancellation flow is successful when the agent can:

* Detect cancellation intent.
* Identify the customer.
* Retrieve active appointments.
* Handle multiple appointments.
* Identify the correct appointment.
* Ask for confirmation.
* Cancel the actual Calendar event.
* Handle Calendar failures.
* Update CRM correctly.
* Preserve appointment history.
* Trigger n8n.
* Notify the assigned employee.
* Handle email/notification failures.
* Confirm cancellation only after success.
* Escalate unresolved cases.

---

# 33. Core Principle

> **Identify → Retrieve → Clarify → Confirm → Cancel → Verify → Update CRM → Notify → Confirm**

Most important rule:

> **No successful Calendar cancellation = No cancellation confirmation.**


