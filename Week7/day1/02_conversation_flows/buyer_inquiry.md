
# Buyer Inquiry — Conversation Flow

## 1. Purpose

This flow handles customers who want to purchase a residential property.

The agent should:

- Understand the customer's buying intent.
- Collect the minimum required information.
- Remember information already provided.
- Search verified property data.
- Recommend suitable available properties.
- Handle objections.
- Offer a property visit.
- Check appointment availability.
- Book the visit only after Calendar confirmation.

---

## 2. Required Customer Information

The agent should gradually collect:

| Information | Required | Example |
|---|---|---|
| Intent | Yes | Buyer |
| City | Yes | Lahore |
| Location / Area | Preferred | DHA |
| Budget | Yes | 3 crore |
| Property Type | Yes | Apartment |
| Bedrooms | Preferred | 3 |
| Purpose | Preferred | Personal use |
| Amenities | Optional | Parking, gym |
| Selected Property | Before booking | Property A |
| Visit Date | Before booking | Saturday |
| Visit Time | Before booking | 3 PM |

The agent should NOT ask all questions at once.

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Greeting
      ↓
Detect Buyer Intent
      ↓
Collect / Confirm Requirements
      ↓
Enough Information?
   ┌──────┴──────┐
  NO             YES
   ↓              ↓
Ask Missing    Property Search
Information        ↓
   └───────────────┘
                   ↓
          Available Properties?
              ┌────┴────┐
             NO         YES
              ↓          ↓
       Refine Search   Rank Options
              ↓          ↓
          Search Again  Present 1–3
                           ↓
                     Customer Interested?
                      ┌────┴────┐
                     NO         YES
                      ↓          ↓
                 Refine Search  Offer Visit
                                   ↓
                              Date + Time
                                   ↓
                           Check Calendar
                              ┌────┴────┐
                           Available  Unavailable
                              ↓           ↓
                           Book       Alternatives
                              ↓
                     Calendar Confirmation
                              ↓
                         Business Event
                              ↓
                             n8n
                       ┌──────┼──────┐
                       ↓      ↓      ↓
                     Email   CRM  Notification
                              ↓
                           Goodbye
````

---

# 4. Conversation Stages

## Stage 1: Greeting

The agent starts with a natural Pakistani UrduLish greeting.

Example:

> "Assalam-o-Alaikum sir! RealEstate Hub se baat ho rahi hai. Main aapki kis tarah help kar sakta hoon?"

Avoid:

> "Welcome to RealEstate Hub. How may I assist you today?"

The second response sounds like a generic chatbot.

---

# 5. Stage 2: Intent Detection

The LLM identifies whether the customer wants to purchase a property.

Example:

Customer:

> "Mujhe apartment purchase karna hai."

Extract:

```text
intent = buyer
property_type = apartment
```

If the customer is unclear:

Customer:

> "Mujhe property leni hai."

Agent:

> "Ji bilkul. Aap residential property dekh rahe hain ya investment ke liye?"

---

# 6. Stage 3: Requirement Extraction

The agent extracts information from the customer's speech.

Example:

Customer:

> "Mera budget three crore hai aur DHA mein apartment chahiye."

Extract:

```json
{
  "intent": "buyer",
  "budget": 30000000,
  "location": "DHA",
  "property_type": "apartment"
}
```

The agent should NOT ask for information that the customer has already provided.

---

# 7. Stage 4: Ask Missing Information

If enough information is not available, ask the most useful missing question.

Example:

Customer:

> "DHA mein apartment chahiye."

Known:

```text
location = DHA
property_type = apartment
```

Missing:

```text
budget
```

Agent:

> "Ji bilkul. Aapka approximate budget kitna hai?"

After the customer answers:

> "Around three crore."

State becomes:

```text
location = DHA
property_type = apartment
budget = 3 crore
```

The agent can now search.

---

# 8. Stage 5: Property Search

The agent calls the property search tool.

Example customer requirement:

```text
Intent: Buyer
City: Lahore
Location: DHA
Budget: 3 crore
Property Type: Apartment
```

Tool:

```text
search_properties(
    city="Lahore",
    location="DHA",
    property_type="Apartment",
    max_price=30000000,
    availability=true
)
```

The tool queries PostgreSQL.

Example SQL:

```sql
SELECT
    property_id,
    title,
    location,
    property_type,
    bedrooms,
    bathrooms,
    area,
    price,
    availability
FROM properties
WHERE city = 'Lahore'
  AND location = 'DHA'
  AND property_type = 'Apartment'
  AND price <= 30000000
  AND availability = TRUE
ORDER BY price ASC;
```

---

# 9. Stage 6: No Matching Property

If no exact match exists, the agent should NOT invent a property.

Example:

> "Sir, three crore ke andar DHA mein abhi exact match available nahi mil raha. Agar aap chahein to main thore lower-budget ya nearby-location options check kar sakta hoon."

Possible alternatives:

```text
1. Increase budget
2. Reduce bedrooms
3. Change location
4. Change property type
5. Search nearby areas
```

Ask the customer which direction they prefer.

---

# 10. Stage 7: Property Recommendation

If matching properties exist, select the strongest 1–3 options.

Example tool result:

```text
Property A
3 Bedrooms
DHA Phase 6
Price: 2.85 crore
Available

Property B
3 Bedrooms
DHA Phase 5
Price: 2.95 crore
Available

Property C
2 Bedrooms
DHA Phase 6
Price: 2.65 crore
Available
```

Agent response:

> "Ji, aapke budget mein mujhe three suitable options mil rahe hain. Ek DHA Phase 6 mein three-bedroom apartment hai jo 2 crore 85 lakh ka hai, aur doosra Phase 5 mein 2 crore 95 lakh ka. Agar aap chahein to main in mein se kisi property ki details bata deta hoon."

Do NOT read a long database result to the customer.

---

# 11. Stage 8: Customer Refinement

Customer may change requirements.

Example:

Customer:

> "Mujhe is se sasti koi option chahiye."

Update:

```text
budget = lower_than_current
```

Agent:

> "Ji bilkul. Main isi DHA requirement ke saath thore lower-price options check karta hoon."

Search again.

---

# 12. Stage 9: Property Details

If the customer asks:

> "Is apartment mein amenities kya hain?"

The agent should use the appropriate verified source.

Possible routing:

```text
Exact structured fact
        ↓
PostgreSQL

Document / descriptive information
        ↓
RAG
```

Example:

> "Ji, verified information ke mutabiq is property mein covered parking aur gym available hai."

If the information is not available:

> "Is property ki gym facility ki verified detail mere paas abhi available nahi hai, isliye main guess nahi karunga."

---

# 13. Stage 10: Objection Handling

## Price Objection

Customer:

> "Price zyada hai."

Agent:

> "Ji, samajh sakta hoon. Agar aap chahein to main isi area mein thore lower-budget options check kar leta hoon."

---

## Location Objection

Customer:

> "DHA thora door hai."

Agent:

> "Ji, agar location flexible hai to main aapke budget mein nearby areas ke options bhi check kar sakta hoon."

---

## Trust Objection

Customer:

> "Mujhe property ki authenticity ka concern hai."

Agent:

> "Ji bilkul, ye important hai. Main aapko sirf verified company information ke basis par details bataunga. Agar aap chahein to main human representative se bhi connect karwa sakta hoon."

---

## Investment Concern

Customer:

> "Kya iski price future mein increase hogi?"

Agent MUST NOT guarantee appreciation.

Correct response:

> "Future price increase ki guarantee main nahi de sakta. Main aapko available verified property information aur relevant project details bata sakta hoon."

---

# 14. Stage 11: Offer Property Visit

Once the customer shows interest:

Customer:

> "Haan, ye property achi lag rahi hai."

Agent:

> "Ji bilkul. Agar aap chahein to property visit schedule kar dete hain. Aap kis din convenient hain?"

---

# 15. Stage 12: Collect Appointment Details

Required:

```text
selected_property
customer_name
phone
preferred_date
preferred_time
assigned_employee
```

The agent should confirm the details before booking.

Example:

> "Ji, to visit DHA Phase 6 wali property ka hai, Saturday ko 3 PM. Main availability check kar leta hoon."

---

# 16. Stage 13: Calendar Availability

The agent calls:

```text
check_calendar_availability(
    date="Saturday",
    time="15:00"
)
```

### Available

Continue to booking.

### Unavailable

Do NOT say:

> "Theek hai, book ho gaya."

Instead:

> "Sir, Saturday 3 PM available nahi hai. Saturday 4 PM ya Sunday 3 PM available hai. Aapke liye konsa better rahega?"

---

# 17. Stage 14: Appointment Booking

Once the customer selects an available slot:

```text
create_calendar_event(
    customer_name,
    phone,
    employee,
    property,
    date,
    time,
    notes
)
```

Only after successful Calendar confirmation:

> "Ji bilkul, aapka property visit Saturday 4 PM ke liye confirm ho gaya hai."

---

# 18. Stage 15: Business Event

After successful booking:

```text
AppointmentBooked
```

The event is sent to n8n.

```text
AppointmentBooked
       ↓
      n8n
   ┌───┼────┐
   ↓   ↓    ↓
 Email CRM Notification
```

Employee receives:

```text
Customer: Ali Khan
Phone: +92XXXXXXXXXX
Property: DHA Phase 6 Apartment
Date: Saturday
Time: 4 PM
Budget: 3 crore
Requirements: 3-bedroom apartment
```

---

# 19. Stage 16:  Goodbye

Example:

> "Perfect sir, aapka visit Saturday 4 PM ke liye confirm hai. Thank you, aur agar aapko koi aur requirement ho to zaroor batayiyega. Allah Hafiz."

Keep goodbye short.

---

# 20. Example Complete Conversation

### Customer

> "Assalam-o-Alaikum, mujhe DHA mein apartment chahiye."

### Agent

> "Wa-Alaikum-Assalam sir. Ji bilkul. Aapka approximate budget kitna hai?"

### Customer

> "Three crore."

### Agent

> "Ji, three crore. Aapko two ya three bedrooms mein preference hai?"

### Customer

> "Three bedroom."

### Agent

> "Ji bilkul. Main DHA mein three-bedroom apartments three crore tak check karta hoon."

### Tool

```text
search_properties(
    location="DHA",
    property_type="Apartment",
    bedrooms=3,
    max_price=30000000,
    availability=true
)
```

### Tool Result

```text
Property A
DHA Phase 6
3 Bedrooms
2.85 crore
Available
```

### Agent

> "Ji, ek suitable option mila hai DHA Phase 6 mein. Three-bedroom apartment hai aur price 2 crore 85 lakh hai. Ye available hai."

### Customer

> "Visit kar sakte hain?"

### Agent

> "Ji bilkul. Aap kis din convenient hain?"

### Customer

> "Saturday."

### Agent

> "Saturday kis time convenient rahega?"

### Customer

> "3 PM."

### Agent

> "Ji, Saturday 3 PM. Main availability check karta hoon."

### Calendar

```text
Available
```

### Agent

> "Ji bilkul, Saturday 3 PM available hai. Main visit book kar deta hoon."

### Calendar

```text
Booking Successful
```

### Agent

> "Perfect sir, aapka DHA Phase 6 property visit Saturday 3 PM ke liye confirm ho gaya hai."

### Business Event

```text
AppointmentBooked
```

### n8n

```text
→ Employee Email
→ CRM Update
→ Customer Notification
```

---

# 21. Guardrails

The buyer flow MUST enforce:

```text
 No fabricated properties
 No fabricated prices
 No fabricated availability
 No guaranteed investment returns
 No fake urgency
 No booking without Calendar confirmation
 No unnecessary repeated questions
 No exposing internal tools or system prompt
```

---

# 22. Success Criteria

A buyer conversation is considered successful when the agent can:

* Correctly identify buyer intent.
* Extract requirements from natural UrduLish.
* Maintain customer context.
* Search verified property inventory.
* Recommend available properties.
* Handle at least common objections.
* Offer a property visit.
* Check actual Calendar availability.
* Book only available slots.
* Trigger downstream business automation.
* Respond naturally in UrduLish.

## Key Principle

> **Understand → Search → Verify → Recommend → Confirm → Act**

The agent should never skip **Verify** before making a factual or business-action claim.


