
# Conversation Flow of Appointment Rescheduling  

## 1. Purpose

This flow handles customers who want to change an existing property visit
appointment.

The agent must:

- Identify the correct appointment.
- Understand the customer's preferred new date/time.
- Check real calendar availability.
- Offer alternatives when the requested slot is unavailable.
- Update the existing calendar event.
- Update CRM records.
- Trigger required notifications.
- Confirm the new appointment only after successful calendar update.

### Core Rule

> Never promise or confirm a rescheduled appointment before the Calendar
> update succeeds.

---

# 2. Required Information

| Information | Required | Example |
|---|---|---|
| Customer ID | Yes | CUST-1024 |
| Customer Name | Preferred | Ali Khan |
| Phone | Yes | +92XXXXXXXXXX |
| Existing Appointment | Yes | DHA Phase 6 — Saturday 4 PM |
| Property | Yes | DHA Phase 6 Apartment |
| New Date | Yes | Sunday |
| New Time | Yes | 3 PM |
| Assigned Employee | Preferred | Ahmed |
| Reason | Optional | Personal issue |
| Meeting Notes | Existing | Customer wants 3-bedroom apartment |

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Identify Customer
      ↓
Detect Rescheduling Intent
      ↓
Retrieve Active Appointments
      ↓
Appointment Found?
   ┌──────┴──────┐
  YES            NO
   ↓              ↓
One Appointment  Explain no active
   ↓             appointment
Multiple?
   ┌──────┴──────┐
  NO             YES
   ↓              ↓
Use Appointment  Ask Which
   ↓             Appointment
   └───────┬──────┘
           ↓
     Ask New Date/Time
           ↓
    Check Calendar
       ┌───┴────┐
  Available   Unavailable
       ↓           ↓
 Update Event   Offer Alternatives
       ↓           ↓
 Confirmation ← Customer Selects
       ↓
      CRM
       ↓
      n8n
   ┌───┼────┐
   ↓   ↓    ↓
 Email CRM Notification
       ↓
     Goodbye
````

---

# 4. Stage 1: Detect Rescheduling Intent

Customer examples:

```text
"Meri property visit ka time change karna hai."

"Saturday wali appointment Sunday kar dein."

"Jo visit book ki thi usko reschedule karna hai."

"4 PM possible nahi hai, 6 PM kar sakte hain?"

"Meri appointment ka time change ho sakta hai?"
```

Map to:

```text
intent = appointment_reschedule
```

---

# 5. Stage 2: Identify Customer

The telephony system provides the incoming phone number.

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

If the customer cannot be identified reliably:

> "Ji bilkul. Main aapki appointment check kar deta hoon. Aap apna naam
> confirm kar dein?"

Do not guess the customer identity.

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
> Aap isko reschedule karna chahte hain?"

Customer:

> "Ji."

Proceed.

---

# 8. Multiple Active Appointments

If multiple appointments exist, ask for clarification.

Agent:

> "Ji sir, aapki do visits scheduled hain — DHA Phase 6 Saturday 4 PM
> aur Bahria Town Sunday 3 PM. Aap kis wali appointment ko reschedule
> karna chahte hain?"

Customer:

> "DHA wali."

Now select:

```text
appointment_id = APT-1001
```

Never choose an appointment automatically when multiple matches exist.

---

# 9. Stage 4: Ask for New Date/Time

Agent:

> "Ji bilkul. Aap kis din aur kis time reschedule karna chahenge?"

Customer:

> "Sunday 4 PM."

Extract:

```text
new_date = Sunday
new_time = 16:00
```

---

# 10. Partial Information

Customer:

> "Sunday ko kar dein."

Missing:

```text
time
```

Agent:

> "Ji bilkul. Sunday ko kis time convenient rahega?"

---

Customer:

> "4 baje."

Missing:

```text
date
```

Agent:

> "Ji, 4 PM. Kis din aap prefer karenge?"

---

# 11. Natural Date Handling

Customer:

> "Next Saturday."

The system should resolve the date using the current date/time context.

Do not rely on the LLM alone for calendar date calculation.

Convert to a concrete value:

```text
date = YYYY-MM-DD
time = HH:MM
timezone = Asia/Karachi
```

---

# 12. Stage 5: Check Calendar Availability

Before modifying the appointment:

```text
check_calendar_availability(
    employee_id,
    new_date,
    new_time,
    duration
)
```

Example:

```text
Requested:
Sunday
4 PM

Result:
AVAILABLE
```

Only then proceed to update.

---

# 13. Available Slot

Agent:

> "Ji bilkul, Sunday 4 PM available hai. Main aapki appointment is slot
> par move kar deta hoon."

Call:

```text
reschedule_calendar_event(
    appointment_id="APT-1001",
    new_date="YYYY-MM-DD",
    new_time="16:00"
)
```

---

# 14. Calendar Update Successful

Result:

```json
{
  "success": true,
  "event_id": "google-event-123",
  "new_start": "2026-08-30T16:00:00+05:00",
  "new_end": "2026-08-30T17:00:00+05:00"
}
```

Now update CRM:

```text
appointment_status = rescheduled
old_date = Saturday
old_time = 16:00
new_date = Sunday
new_time = 16:00
```

Agent:

> "Ji bilkul, aapki DHA Phase 6 property visit Sunday 4 PM ke liye
> reschedule ho gayi hai."

---

# 15. Requested Slot Unavailable

Calendar:

```text
Sunday 4 PM
UNAVAILABLE
```

The agent must NOT say:

> "Ji ho gayi hai."

Instead:

> "Ji, Sunday 4 PM available nahi hai. Sunday 5 PM available hai,
> ya Monday 4 PM. Aapke liye konsa convenient rahega?"

---

# 16. Offer Alternatives

The system should retrieve nearby available slots.

```text
find_available_slots(
    employee_id,
    preferred_date,
    preferred_time,
    window=120
)
```

Example result:

```text
Sunday 5 PM
Sunday 6 PM
Monday 4 PM
```

Present a small number of choices.

Do not overwhelm the customer with ten options.

---

# 17. Customer Selects Alternative

Customer:

> "Sunday 5 PM kar dein."

Check again:

```text
check_calendar_availability(
    date="Sunday",
    time="17:00"
)
```

If available:

```text
reschedule_calendar_event(...)
```

Then confirm.

---

# 18. Race Condition Protection

Availability can change between checking and updating.

Example:

```text
10:00
↓
Check 5 PM
↓
AVAILABLE

10:01
↓
Another appointment takes 5 PM
↓
Update fails
```

The system must handle this.

If update fails:

> "Ji, 5 PM abhi book ho gaya hai. Main doosra available slot check
> kar leta hoon."

Then search alternatives.

Never assume that an earlier availability check guarantees successful booking.

---

# 19. Stage 6: Update Existing Calendar Event

Prefer updating the existing event rather than creating a duplicate.

```text
OLD EVENT
DHA Phase 6
Saturday 4 PM
        ↓
UPDATE
        ↓
NEW EVENT
DHA Phase 6
Sunday 5 PM
```

Avoid:

```text
Create new event
+
Leave old event active
```

because this can create duplicate appointments.

---

# 20. Stage 7: Update CRM

Store both old and new appointment information.

Example:

```json
{
  "appointment_id": "APT-1001",
  "status": "rescheduled",
  "old_datetime": "2026-08-29T16:00:00+05:00",
  "new_datetime": "2026-08-30T17:00:00+05:00",
  "property_id": "DHA-P6-102",
  "customer_id": "CUST-1024"
}
```

Do not delete the original appointment history.

---

# 21. Stage 8: Workflow Event

After successful Calendar update:

```text
AppointmentRescheduled
          ↓
         n8n
      ┌───┼────┐
      ↓   ↓    ↓
   Email CRM Notification
```

---

# 22. Employee Email

Example:

```text
Subject:
Appointment Rescheduled — Ali Khan — DHA Phase 6

Customer:
Ali Khan

Phone:
+92XXXXXXXXXX

Property:
DHA Phase 6 Apartment

Previous Appointment:
Saturday, 4 PM

New Appointment:
Sunday, 5 PM

Customer Requirements:
3-bedroom apartment
Budget: 3.5 crore

Reason:
Personal schedule conflict
```

The email should only be sent after successful rescheduling.

---

# 23. Customer Confirmation

After all critical operations succeed:

> "Ji bilkul sir, aapki DHA Phase 6 wali visit Saturday 4 PM se Sunday
> 5 PM ke liye successfully reschedule ho gayi hai."

Optional:

> "Aapko updated appointment details email ke through bhi mil jayengi."

Do not claim email delivery if the email operation failed.

---

# 24. Email Failure

Calendar update succeeds:

```text
Calendar = SUCCESS
Email = FAILED
```

The appointment is still rescheduled.

Agent:

> "Ji sir, aapki appointment successfully reschedule ho gayi hai.
> Email notification mein issue aa raha hai, lekin appointment Calendar mein
> update ho chuki hai."

Log:

```text
email_status = failed
retry_required = true
```

n8n should retry the email.

---

# 25. Calendar Failure

If Calendar update fails:

```text
Calendar = FAILED
```

Do NOT update the appointment as successfully rescheduled.

Agent:

> "Sorry sir, appointment update karte waqt issue aa gaya hai. Main
> aapko available alternative slot de deta hoon."

Log:

```text
reschedule_status = failed
calendar_error = true
```

---

# 26. Customer Changes Mind

Customer:

> "Actually Sunday bhi nahi, Monday kar dein."

If the original appointment has not yet been changed:

Simply search Monday.

If the new appointment was already successfully moved to Sunday and the
customer calls again:

Treat it as a new rescheduling request.

Do not create another appointment.

---

# 27. Customer Gives Relative Time

Customer:

> "Kal shaam ko kar dein."

The system should resolve:

```text
kal = tomorrow
shaam = configured evening window
```

But "shaam" may be ambiguous.

Ask:

> "Ji bilkul. Kal evening mein 5 PM ya 6 PM mein se koi time convenient
> rahega?"

Do not invent an exact time.

---

# 28. Timezone

All appointment operations should use:

```text
timezone = Asia/Karachi
```

Store timestamps consistently.

Example:

```text
2026-08-30T17:00:00+05:00
```

Never silently mix UTC and Pakistan local time.

---

# 29. Rescheduling Example

### Customer

> "Assalam-o-Alaikum, meri DHA wali visit Saturday 4 PM ki hai,
> isko Sunday karna hai."

### Agent

> "Wa-Alaikum-Assalam sir. Ji bilkul, main aapki appointment check
> kar leta hoon."

### CRM

```text
Customer:
Ali Khan

Appointment:
DHA Phase 6
Saturday 4 PM
```

### Agent

> "Ji sir, DHA Phase 6 wali visit Saturday 4 PM par confirmed hai.
> Sunday ko kis time convenient rahega?"

### Customer

> "4 PM."

### Calendar

```text
Sunday 4 PM
UNAVAILABLE
```

### Agent

> "Ji, Sunday 4 PM available nahi hai. Sunday 5 PM available hai,
> ya Monday 4 PM. Aapke liye konsa better rahega?"

### Customer

> "Sunday 5 PM."

### Calendar

```text
Sunday 5 PM
AVAILABLE
```

### Update

```text
reschedule_calendar_event()
```

### Result

```text
SUCCESS
```

### CRM

```text
old = Saturday 4 PM
new = Sunday 5 PM
status = rescheduled
```

### n8n

```text
AppointmentRescheduled
        ↓
       n8n
    ┌───┼────┐
    ↓   ↓    ↓
 Email CRM Notification
```

### Agent

> "Perfect sir, aapki DHA Phase 6 wali visit Sunday 5 PM ke liye
> reschedule ho gayi hai."

---

# 30. Guardrails

The rescheduling flow MUST enforce:

```text
 Never reschedule an unidentified appointment.
 Never guess which appointment the customer means.
 Never book an unavailable slot.
 Never confirm before Calendar success.
 Never create duplicate appointments.
 Never leave the old Calendar event active.
 Never update CRM before the actual appointment change succeeds.
 Never claim email delivery if email failed.
 Never silently change timezone.
 Never overwrite appointment history.
 Never invent available times.
```

---

# 31. Error Handling

## Customer Not Found

```text
Customer
   ↓
Not Found
   ↓
Ask identifying information
   ↓
Search again
   ↓
Still Not Found
   ↓
Human Escalation
```

---

## Appointment Not Found

Agent:

> "Ji, mujhe aapke number par currently koi confirmed appointment
> nazar nahi aa rahi. Agar aap chahein to main representative se confirm
> karwa deta hoon."

---

## Multiple Appointments

Ask which appointment.

---

## Calendar API Failure

Do not confirm.

Create an internal failure event/log.

---

## Email API Failure

Appointment remains valid if Calendar succeeded.

Retry notification asynchronously.

---

# 32. State Example

```python
state = {
    "customer_id": "CUST-1024",

    "intent": "appointment_reschedule",

    "appointment_id": "APT-1001",

    "property_id": "DHA-P6-102",

    "old_datetime": "2026-08-29T16:00:00+05:00",

    "requested_datetime": "2026-08-30T17:00:00+05:00",

    "availability": True,

    "reschedule_status": "confirmed",

    "calendar_event_id": "google-event-123",

    "email_status": "pending",

    "crm_status": "updated"
}
```

---

# 33. LangGraph Routing

```text
START
  ↓
detect_intent
  ↓
appointment_reschedule
  ↓
load_customer
  ↓
load_appointments
  ↓
select_appointment
  ↓
collect_new_datetime
  ↓
check_availability
  ↓
 ┌──────────────┴──────────────┐
 ↓                             ↓
available                    unavailable
 ↓                             ↓
reschedule_event          suggest_slots
 ↓                             ↓
verify_update             customer_choice
 ↓                             ↓
update_crm                check_availability
 ↓
trigger_n8n
 ↓
send_notification
 ↓
confirm
 ↓
END
```

---

# 34. Success Criteria

The rescheduling flow is successful when the agent can:

* Detect rescheduling intent.
* Identify the correct customer.
* Retrieve active appointments.
* Handle multiple appointments.
* Collect a new date and time.
* Resolve relative dates correctly.
* Handle ambiguous times.
* Check real Calendar availability.
* Offer alternatives.
* Handle race-condition failures.
* Update the existing Calendar event.
* Preserve appointment history.
* Update CRM.
* Trigger n8n.
* Notify the employee.
* Handle email failures.
* Confirm only after successful rescheduling.
* Escalate unresolved problems.

---

# 35. Core Principle

> **Identify → Retrieve → Clarify → Check → Reschedule → Verify → Update CRM → Notify → Confirm**

The most important rule:

> **No Calendar success = No rescheduling confirmation.**


