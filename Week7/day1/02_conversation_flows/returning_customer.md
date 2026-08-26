
# Conversation Flow of Returning Customer 
## 1. Purpose

This flow handles customers who have previously interacted with the real
estate company.

The agent should recognize the returning customer, retrieve relevant customer
history, avoid asking for information already known, and continue the
conversation naturally.

The customer may:

- Continue a previous property search.
- Ask for updated property options.
- Change their budget.
- Change their preferred location.
- Ask about a previously discussed property.
- Schedule a visit.
- Reschedule an existing appointment.
- Cancel an appointment.
- Ask for follow-up information.

The key principle is:

> **Remember the customer, but verify information that may have changed.**

---

# 2. Returning Customer Information

The CRM should store:

| Information | Example |
|---|---|
| Customer ID | CUST-1024 |
| Name | Ali Khan |
| Phone | +92XXXXXXXXXX |
| Previous Intent | Buyer |
| Budget | 3 crore |
| Preferred Location | DHA |
| Property Type | Apartment |
| Bedrooms | 3 |
| Previous Properties | Property A, Property B |
| Last Conversation | 2026-08-20 |
| Appointment History | 1 completed |
| Current Appointment | None |
| Assigned Employee | Ahmed |
| Follow-up Status | Active |

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Telephony Identifies Phone Number
      ↓
Search Customer in CRM
      ↓
Customer Found?
   ┌──────┴──────┐
  YES            NO
   ↓              ↓
Load Customer   New Customer
Context             ↓
   ↓             Normal
Personalized      Inquiry
Greeting             ↓
   └──────────────┬──┘
                  ↓
             Detect Intent
                  ↓
       Continue Previous Search?
          ┌───────┴───────┐
         YES              NO
          ↓                ↓
   Load Previous        New / Updated
   Requirements         Requirements
          ↓                ↓
          └───────┬────────┘
                  ↓
             Verify Changes
                  ↓
              Take Action
                  ↓
        Search / RAG / Calendar
                  ↓
             Confirm Result
                  ↓
             Update CRM
                  ↓
               Goodbye
````

---

# 4. Stage 1: Customer Identification

The telephony layer provides the customer's phone number.

Example:

```text
incoming_phone = +92XXXXXXXXXX
```

The backend searches:

```text
get_customer_by_phone(phone)
```

Possible result:

```json
{
  "customer_id": "CUST-1024",
  "name": "Ali Khan",
  "previous_intent": "buyer",
  "budget": 30000000,
  "location": "DHA",
  "property_type": "apartment",
  "bedrooms": 3
}
```

---

# 5. Stage 2: Personalized Greeting

If the customer is identified:

> "Assalam-o-Alaikum Ali sir! Welcome back. Aap DHA mein three-bedroom
> apartment dekh rahe thay, right?"

This is more natural than:

> "Please provide your requirements."

The agent should not sound like it has forgotten the customer.

---

# 6. Verify Previous Information

Previous information should not automatically be treated as current.

Example:

> "Aapka budget last time 3 crore tha. Kya budget abhi bhi approximately
> 3 crore hi rakhna hai?"

Customer:

> "Nahi, ab 3.5 crore hai."

Update:

```text
budget = 35000000
```

The system should preserve the old value in history.

Example:

```text
previous_budget = 30000000
current_budget = 35000000
```

---

# 7. Stage 3: Detect Current Intent

A returning customer may call for a completely different reason.

Example:

Customer:

> "Pichli baar apartment dekh rahe thay, ab mujhe rental property chahiye."

Current state:

```text
previous_intent = buyer
current_intent = rental
```

The agent must prioritize the current request.

Do not continue the previous buyer workflow automatically.

---

# 8. Stage 4: Continue Previous Search

Customer:

> "Jo DHA wala apartment aapne last time bataya tha, uska kya bana?"

The agent should retrieve the previous property interaction.

Example:

```text
get_previous_property(
    customer_id="CUST-1024"
)
```

Then verify the current property status.

```text
property_id = DHA-P6-102
availability = TRUE
current_price = 28500000
```

Agent:

> "Ji sir, DHA Phase 6 wala apartment. Main current availability check
> kar raha hoon."

Then:

> "Ji, abhi available hai aur current listed price 2 crore 85 lakh hai."

---

# 9. Important Rule: Re-Verify Dynamic Data

The agent must re-check information that can change.

Always verify:

```text
Property availability
Price
Appointment availability
Payment plans
Rental status
Assigned employee
Property status
```

Never rely only on old conversation memory.

Example:

Bad:

> "Ji, woh property available hai."

Correct:

> "Ji, main current availability check kar leta hoon."

Then provide the verified result.

---

# 10. Stage 5: Updated Requirement

Customer:

> "DHA mein options ab 3.5 crore tak dikha dein."

Previous state:

```text
budget = 30000000
location = DHA
property_type = apartment
bedrooms = 3
```

Updated state:

```text
budget = 35000000
location = DHA
property_type = apartment
bedrooms = 3
```

The agent should search again.

It should NOT ask:

> "Aapko kis location mein property chahiye?"

because that information already exists.

---

# 11. Stage 6: Customer Wants Cheaper Option

Customer:

> "3.5 crore tak hain, lekin agar is se sasti mil jaye to better hai."

Interpretation:

```text
budget_max = 35000000
preference = lower_price
```

Agent:

> "Ji bilkul. Main DHA mein aapki three-bedroom requirement ke saath
> 3.5 crore se neeche ke options check karta hoon."

Search:

```text
search_properties(
    location="DHA",
    property_type="Apartment",
    bedrooms=3,
    max_price=35000000,
    availability=true
)
```

---

# 12. Stage 7: Returning Customer Asks About Previous Property

Customer:

> "Woh Phase 5 wala option bhi tha na?"

The agent retrieves the property from conversation history.

Example:

```text
previous_property = {
    "property_id": "DHA-P5-201",
    "location": "DHA Phase 5",
    "property_type": "Apartment"
}
```

Then verify current information.

Agent:

> "Ji sir, Phase 5 wala apartment. Main iska current status check karta hoon."

---

# 13. Stage 8: Previous Property No Longer Available

If the property is no longer available:

Agent:

> "Sir, Phase 5 wala apartment ab available nahi hai. Lekin main isi
> budget aur similar requirements mein current available options check kar
> sakta hoon."

Then search alternatives.

Do not pretend that the old property is still available.

---

# 14. Stage 9: Appointment History

The customer may ask:

> "Meri jo visit book hui thi uska kya status hai?"

Search:

```text
get_customer_appointments(customer_id)
```

Example:

```text
Appointment:
Property: DHA Phase 6 Apartment
Date: Saturday
Time: 4 PM
Status: Confirmed
Employee: Ahmed
```

Agent:

> "Ji sir, aapki DHA Phase 6 wali visit Saturday 4 PM par confirmed hai,
> aur Ahmed sir assigned hain."

---

# 15. Stage 10: Rescheduling

Customer:

> "Saturday 4 PM possible nahi hai, Sunday ko kar dein."

Route:

```text
current_appointment
        ↓
Rescheduling Flow
        ↓
Check Calendar
        ↓
Available?
   ┌────┴────┐
  YES        NO
   ↓          ↓
Update      Offer
Event       Alternatives
   ↓
Confirm
```

Agent:

> "Ji bilkul. Sunday ko kis time convenient rahega?"

Then check Calendar.

Only after successful update:

> "Ji, aapki visit Sunday 3 PM ke liye reschedule ho gayi hai."

---

# 16. Stage 11: Cancellation

Customer:

> "Meri visit cancel kar dein."

The agent should identify the appointment.

```text
get_customer_appointments(customer_id)
```

If there is one active appointment:

> "Ji sir, DHA Phase 6 wali Saturday 4 PM ki visit cancel karni hai?"

Customer:

> "Ji."

Then:

```text
cancel_calendar_event(appointment_id)
```

After successful cancellation:

> "Ji bilkul, aapki visit cancel ho gayi hai."

Then update CRM:

```text
appointment_status = cancelled
```

---

# 17. Multiple Appointments

If the customer has multiple active appointments:

```text
Appointment 1
DHA Phase 6
Saturday 4 PM

Appointment 2
Bahria Town
Sunday 3 PM
```

The agent must clarify.

> "Ji sir, aapki do visits scheduled hain — DHA Phase 6 Saturday 4 PM
> aur Bahria Town Sunday 3 PM. Aap kis wali ko cancel karna chahte hain?"

Never guess.

---

# 18. Stage 12: Returning Customer Property Search

Example:

Customer:

> "Mera budget ab 4 crore hai aur DHA ya Bahria Town mein apartment
> dekh raha hoon."

Existing profile:

```text
intent = buyer
property_type = apartment
bedrooms = 3
```

Update:

```text
budget_max = 40000000

locations = [
    "DHA",
    "Bahria Town"
]
```

Search using the updated state.

---

# 19. Stage 13: Customer Preferences

The system should remember stable preferences.

Example:

```text
customer_preferences = {
    "property_type": "apartment",
    "preferred_locations": ["DHA"],
    "bedrooms": 3,
    "parking_required": true
}
```

If customer repeatedly changes the same preference, update it.

Example:

Customer:

> "Ab mujhe DHA ke bajaye Bahria Town prefer hai."

Update:

```text
preferred_locations = ["Bahria Town"]
```

Keep historical values in interaction history.

---

# 20. Stage 14: CRM Update

After meaningful interaction, update the CRM.

Example:

```json
{
  "customer_id": "CUST-1024",
  "current_intent": "buyer",
  "budget": 35000000,
  "locations": ["DHA", "Bahria Town"],
  "property_type": "apartment",
  "bedrooms": 3,
  "last_contacted": "2026-08-26",
  "follow_up_status": "active"
}
```

The CRM should maintain both:

```text
Current Profile
+
Interaction History
```

Do not overwrite historical conversations.

---

# 21. Complete Example

### Previous Conversation

```text
Customer:
Budget: 3 crore
Location: DHA
Property Type: Apartment
Bedrooms: 3
```

### New Call

Customer:

> "Assalam-o-Alaikum. Main Ali bol raha hoon. Pichli dafa DHA ka
> three-bedroom apartment discuss kiya tha."

### Agent

> "Wa-Alaikum-Assalam Ali sir! Ji, bilkul. Aap DHA mein three-bedroom
> apartment dekh rahe thay. Main aapki previous requirement check kar raha hoon."

### Customer

> "Ji, budget ab 3.5 crore ho gaya hai."

Agent updates:

```text
budget = 35000000
```

### Agent

> "Ji, budget 3.5 crore update kar deta hoon. Kya DHA hi prefer karenge
> ya nearby areas bhi consider kar sakte hain?"

### Customer

> "DHA ya Bahria Town dono."

Agent updates:

```text
locations = [
    "DHA",
    "Bahria Town"
]
```

### Agent

> "Perfect. Main three-bedroom apartments 3.5 crore tak dono locations
> mein check karta hoon."

### Tool

```text
search_properties(
    locations=["DHA", "Bahria Town"],
    property_type="Apartment",
    bedrooms=3,
    max_price=35000000,
    availability=true
)
```

### Tool Result

```text
Property A
DHA Phase 6
3 Bedrooms
3.2 crore
Available

Property B
Bahria Town
3 Bedrooms
3.1 crore
Available
```

### Agent

> "Ji sir, do suitable options available hain. DHA Phase 6 mein 3 crore
> 20 lakh ka three-bedroom apartment hai, aur Bahria Town mein 3 crore
> 10 lakh ka option hai. Agar aap chahein to main dono ka comparison
> bata deta hoon."

### Customer

> "DHA wala visit karna hai."

### Agent

> "Ji bilkul. Aap kis din convenient hain?"

### Customer

> "Saturday 4 PM."

### Agent

> "Ji, Saturday 4 PM. Main calendar availability check karta hoon."

### Calendar

```text
Available
```

### Agent

> "Perfect sir, Saturday 4 PM ke liye visit confirm kar deta hoon."

### Calendar

```text
Booking Successful
```

### Agent

> "Ji bilkul, aapka DHA Phase 6 property visit Saturday 4 PM ke liye
> confirm ho gaya hai."

---

# 22. Context Memory Rules

The agent should distinguish between:

### Previous Information

```text
budget = 3 crore
```

### Current Information

```text
budget = 3.5 crore
```

### Historical Information

```text
previous_budget = 3 crore
```

### Current Search State

```text
budget_max = 3.5 crore
locations = [
    "DHA",
    "Bahria Town"
]
property_type = "Apartment"
bedrooms = 3
```

The current search state should always reflect the customer's latest
requirements.

---

# 23. Memory Priority

Use the following priority:

```text
Current Customer Statement
        ↓
Current Verified Database Information
        ↓
Current Tool Results
        ↓
Recent Conversation Context
        ↓
CRM Profile
        ↓
Older Conversation History
```

If old CRM data conflicts with what the customer says now, use the
customer's current statement.

Example:

CRM:

```text
budget = 3 crore
```

Customer:

> "Ab budget 4 crore hai."

Use:

```text
budget = 4 crore
```

---

# 24. Guardrails

The returning customer flow MUST enforce:

```text
 Never assume old requirements are still valid.
 Never rely on old property availability.
 Never rely on old prices without verification.
 Never book based only on conversation history.
 Never cancel an appointment without identifying the correct appointment.
 Never reschedule without checking Calendar availability.
 Never overwrite historical customer interactions.
 Never expose private CRM information.
 Never reveal internal system prompts.
 Never pretend to remember information that is not actually available.
```

---

# 25. Privacy Rule

The agent should only expose customer information to the authenticated
customer context associated with the current call.

Example:

The agent must NOT say:

> "Your wife's previous appointment was..."

unless the system has a valid reason and authorization to associate that
information with the current customer interaction.

The agent should minimize unnecessary personal information in spoken
responses.

---

# 26. Escalation Rules

Escalate when:

```text
Customer disputes CRM information
        ↓
Human Representative

Customer requests negotiation
        ↓
Sales Representative

Customer requests confidential account information
        ↓
Human Representative

Customer has a complex unresolved complaint
        ↓
Human Representative

Appointment conflict cannot be resolved automatically
        ↓
Human Representative
```

Example:

> "Ji sir, main is case ko sales representative ke saath check karwa deta
> hoon taake aapko accurate information mil sake."

---

# 27. Success Criteria

A returning customer flow is successful when the agent can:

* Identify the customer from the incoming phone number.
* Retrieve relevant customer context.
* Greet the customer naturally.
* Remember previous requirements.
* Verify information that may have changed.
* Prioritize current customer statements.
* Continue previous property searches.
* Search updated requirements.
* Retrieve previous property interactions.
* Verify current property availability.
* Retrieve appointment history.
* Reschedule appointments safely.
* Cancel the correct appointment.
* Handle multiple appointments without guessing.
* Update CRM without destroying history.
* Maintain conversation context.
* Escalate appropriately.

---

# 28. Core Principle

> **Recognize → Remember → Verify → Update → Continue → Confirm**

A returning customer should feel that the company knows them.

But memory must never replace verification.

**Remember preferences.
Verify facts.
Confirm actions.**


