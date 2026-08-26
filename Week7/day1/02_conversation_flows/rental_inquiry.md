
# Rental Inquiry (Conversation Flow)

## 1. Purpose

This flow handles customers who want to rent a residential property.

The agent should:

- Identify rental intent.
- Understand the customer's rental requirements.
- Collect only the missing information.
- Remember information already provided.
- Search verified rental inventory.
- Recommend suitable available properties.
- Handle price and requirement objections.
- Offer a property visit.
- Check Calendar availability.
- Book the visit only after successful Calendar confirmation.
- Trigger employee notification and CRM logging after booking.

---

# 2. Rental Requirements

The agent should gradually collect the following information:

| Information | Required | Example |
|---|---|---|
| Intent | Yes | Rental |
| City | Yes | Lahore |
| Location / Area | Preferred | DHA |
| Monthly Budget | Yes | 1.5 lakh |
| Property Type | Preferred | Apartment |
| Bedrooms | Preferred | 3 |
| Furnished Status | Optional | Furnished |
| Move-in Date | Preferred | September |
| Amenities | Optional | Parking, lift |
| Selected Property | Before visit | Property A |
| Visit Date | Before booking | Saturday |
| Visit Time | Before booking | 4 PM |

The agent should not ask every question at the beginning.

It should collect requirements naturally as the conversation develops.

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Greeting
      ↓
Detect Rental Intent
      ↓
Extract Existing Requirements
      ↓
Enough Information?
   ┌──────┴──────┐
  NO             YES
   ↓              ↓
Ask Most       Rental Search
Useful Missing     ↓
Information    Available?
   │          ┌────┴────┐
   │         NO         YES
   │          ↓          ↓
   │      Refine Search  Rank Options
   │          ↓          ↓
   └──────────┘       Present 1–3
                          ↓
                   Customer Interested?
                    ┌─────┴─────┐
                   NO           YES
                    ↓            ↓
              Refine Search   Offer Visit
                                  ↓
                            Date + Time
                                  ↓
                          Check Calendar
                             ┌────┴────┐
                          Available  Unavailable
                             ↓           ↓
                           Book      Alternatives
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

# 4. Stage 1: Greeting

The agent should start naturally.

Example:

> "Assalam-o-Alaikum sir! RealEstate Hub se baat ho rahi hai. Main aapki kis tarah help kar sakta hoon?"

If the customer immediately explains their requirement, do not repeat the greeting unnecessarily.

---

# 5. Stage 2: Detect Rental Intent

Example:

Customer:

> "Mujhe Lahore mein apartment rent par chahiye."

Extract:

```text
intent = rental
city = Lahore
property_type = apartment
```

The agent should understand variations such as:

```text
"flat rent par chahiye"
"rental apartment chahiye"
"ghar rent pe chahiye"
"lease ke liye property chahiye"
```

These should normally map to:

```text
intent = rental
```

---

# 6. Stage 3: Extract Requirements

Example:

Customer:

> "Lahore mein 1.5 lakh monthly budget hai, furnished apartment chahiye."

Extract:

```json
{
  "intent": "rental",
  "city": "Lahore",
  "monthly_budget": 150000,
  "property_type": "apartment",
  "furnished": true
}
```

If the customer later says:

> "Three bedrooms hona chahiye."

Update:

```text
bedrooms = 3
```

The agent should not ask again:

> "Kitne bedrooms chahiye?"

because the customer has already provided the information.

---

# 7. Stage 4: Missing Information

The agent should ask the most useful missing question.

Example:

Customer:

> "Lahore mein apartment rent pe chahiye."

Known:

```text
intent = rental
city = Lahore
property_type = apartment
```

Missing:

```text
monthly_budget
```

Agent:

> "Ji bilkul. Aapka monthly rental budget approximately kitna hai?"

---

## Another Example

Customer:

> "Mera budget 1.5 lakh hai."

Known:

```text
monthly_budget = 150000
```

Still missing:

```text
location
```

Agent:

> "Ji, Lahore mein kis area ko prefer karenge?"

---

# 8. Stage 5: Move-in Date

Move-in date can be important for rental availability.

Example:

Customer:

> "September mein shift hona hai."

Extract:

```text
move_in_date = September
```

Agent should not unnecessarily ask for an exact date immediately unless it is required for the search.

If exact date becomes necessary:

> "Ji, September mein approximately kis date ke around move karna hai?"

---

# 9. Stage 6: Rental Search

Once enough information is available, call the property search tool.

Example:

```text
intent = rental
city = Lahore
monthly_budget = 150000
property_type = apartment
bedrooms = 3
furnished = true
move_in_date = September
```

Tool:

```text
search_rental_properties(
    city="Lahore",
    max_monthly_rent=150000,
    property_type="Apartment",
    bedrooms=3,
    furnished=true,
    move_in_date="September",
    availability=true
)
```

---

# 10. Structured Database Search

Rental inventory should be stored in PostgreSQL.

Example query:

```sql
SELECT
    property_id,
    title,
    city,
    location,
    property_type,
    bedrooms,
    bathrooms,
    area,
    monthly_rent,
    furnished,
    availability,
    available_from
FROM rental_properties
WHERE city = 'Lahore'
  AND property_type = 'Apartment'
  AND monthly_rent <= 150000
  AND bedrooms = 3
  AND furnished = TRUE
  AND availability = TRUE
ORDER BY monthly_rent ASC;
```

The database result is the source of truth for:

* Rental price
* Availability
* Bedrooms
* Property type
* Location
* Furnished status
* Available-from date

---

# 11. No Exact Match

If there is no exact match, the agent should not invent an option.

Example:

Customer:

> "1.5 lakh mein DHA mein furnished three-bedroom apartment chahiye."

Database:

```text
No exact match
```

Agent:

> "Ji, 1.5 lakh mein DHA mein furnished three-bedroom ka exact match abhi nahi mil raha. Agar aap chahein to main unfurnished options ya nearby areas mein furnished options check kar leta hoon."

Possible alternatives:

```text
1. Increase monthly budget
2. Reduce bedrooms
3. Choose unfurnished
4. Change location
5. Search nearby areas
```

---

# 12. Budget Flexibility

The customer may ask:

> "Thora budget increase kar sakte hain?"

The agent should confirm before changing the search.

Example:

> "Ji bilkul. Maximum kitna monthly budget rakhna chahenge?"

Customer:

> "1.7 lakh."

Update:

```text
monthly_budget = 170000
```

Then search again.

---

# 13. Lower-Budget Request

Customer:

> "Is se sasta koi option hai?"

The agent should preserve other requirements and only change the relevant constraint.

Current state:

```text
city = Lahore
location = DHA
property_type = apartment
bedrooms = 3
furnished = true
monthly_budget = 150000
```

Agent:

> "Ji bilkul. Main isi requirement ke saath lower-rent options check karta hoon."

The system should search for lower-priced matches.

---

# 14. Stage 7: Present Rental Options

Suppose the search returns:

```text
Property A
DHA Phase 6
3 Bedrooms
Furnished
Rent: 145,000/month
Available

Property B
DHA Phase 5
3 Bedrooms
Furnished
Rent: 150,000/month
Available

Property C
DHA Phase 8
2 Bedrooms
Furnished
Rent: 130,000/month
Available
```

The agent should summarize the strongest options.

Example:

> "Ji, aapke budget mein do suitable three-bedroom furnished options mil rahe hain. DHA Phase 6 mein ek 1 lakh 45 hazar monthly hai, aur Phase 5 mein 1 lakh 50 hazar. Agar aap chahein to main dono ki details compare kar deta hoon."

Do not read every database field.

---

# 15. Stage 8: Rental Property Details

Customer:

> "Phase 6 wale apartment mein parking hai?"

If parking is a structured property field:

```text
PostgreSQL
```

If the answer is in a brochure/document:

```text
RAG
```

Example:

> "Ji, verified property details ke mutabiq covered parking available hai."

If unavailable:

> "Is property ki parking ki verified information mere paas abhi available nahi hai, isliye main guess nahi karunga."

---

# 16. Stage 9: Furnished / Unfurnished

Customer:

> "Furnished nahi chahiye, unfurnished option dikhao."

Update:

```text
furnished = false
```

Agent:

> "Ji bilkul. Main isi budget aur location mein unfurnished apartments check karta hoon."

The system should preserve:

```text
city
location
budget
bedrooms
property_type
move_in_date
```

and only update:

```text
furnished = false
```

---

# 17. Stage 10: Objection Handling

## Rent Too High

Customer:

> "1.5 lakh zyada hai."

Agent:

> "Ji, samajh sakta hoon. Agar aap chahein to main isi area mein lower-rent options check kar leta hoon."

---

## Location Concern

Customer:

> "DHA mein nahi chahiye, thora central area ho."

Agent:

> "Ji bilkul. Aapki preference ko update karke nearby central areas mein options check karta hoon."

---

## Property Condition

Customer:

> "Apartment ki condition kaisi hai?"

The agent must only use verified information.

If the condition is documented:

> "Ji, available property description ke mutabiq apartment recently renovated hai."

If not:

> "Iski current condition ki verified detail mere paas nahi hai. Visit ke time aap personally inspect kar sakte hain, ya main representative se confirm karwa deta hoon."

---

# 18. Stage 11: Offer Property Visit

When the customer shows interest:

Customer:

> "Haan, Phase 6 wala dekhna hai."

Agent:

> "Ji bilkul. Property visit schedule kar dete hain. Aap kis din convenient hain?"

---

# 19. Stage 12: Appointment Details

Before booking, collect:

```text
customer_name
phone
selected_property
preferred_date
preferred_time
assigned_employee
```

Example:

> "Ji, Phase 6 wala furnished apartment. Saturday ko kis time convenient rahega?"

Customer:

> "4 PM."

Agent:

> "Ji, Saturday 4 PM. Main calendar availability check karta hoon."

---

# 20. Stage 13: Calendar Availability

Call:

```text
check_calendar_availability(
    date="Saturday",
    time="16:00"
)
```

---

## Available

Proceed to booking.

---

## Unavailable

Agent:

> "Sir, Saturday 4 PM available nahi hai. Saturday 5 PM ya Sunday 4 PM available hai. Aapke liye konsa better rahega?"

Never claim the original slot was booked.

---

# 21. Stage 14: Booking

After customer selects an available slot:

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

Only after successful response:

```text
booking_status = confirmed
```

Agent:

> "Ji bilkul, aapka property visit Saturday 5 PM ke liye confirm ho gaya hai."

---

# 22. Stage 15: n8n Business Event

Successful booking creates:

```text
AppointmentBooked
```

Then:

```text
AppointmentBooked
        ↓
       n8n
    ┌───┼────┐
    ↓   ↓    ↓
 Email CRM Notification
```

Employee email can contain:

```text
Customer: Ali Khan
Phone: +92XXXXXXXXXX
Property: DHA Phase 6 Apartment
Monthly Rent: 145,000
Visit: Saturday, 5 PM
Requirements:
- 3 bedrooms
- Furnished
- Lahore
- Budget up to 150,000/month
- Move-in: September
```

---

# 23. Stage 16: Goodbye

Example:

> "Perfect sir, aapka visit Saturday 5 PM ke liye confirm hai. Thank you, Allah Hafiz."

Keep the closing short and natural.

---

# 24. Complete Example

### Customer

> "Assalam-o-Alaikum, mujhe Lahore mein rental apartment chahiye."

### Agent

> "Wa-Alaikum-Assalam sir. Ji bilkul. Aapka monthly budget approximately kitna hai?"

### Customer

> "1.5 lakh."

### Agent

> "Ji, 1.5 lakh monthly. Aapko kis area mein chahiye?"

### Customer

> "DHA."

### Agent

> "Ji bilkul. Aapko kitne bedrooms chahiye?"

### Customer

> "Three bedroom."

### Agent

> "Furnished chahiye ya unfurnished?"

### Customer

> "Furnished."

### Agent

> "Ji, aur move-in kab karna hai?"

### Customer

> "September mein."

### Agent

> "Perfect. Main DHA mein three-bedroom furnished apartments 1.5 lakh tak, September availability ke saath check karta hoon."

### Tool

```text
search_rental_properties(
    city="Lahore",
    location="DHA",
    max_monthly_rent=150000,
    property_type="Apartment",
    bedrooms=3,
    furnished=true,
    move_in_date="September",
    availability=true
)
```

### Tool Result

```text
Property A
DHA Phase 6
3 Bedrooms
Furnished
145,000/month
Available

Property B
DHA Phase 5
3 Bedrooms
Furnished
150,000/month
Available
```

### Agent

> "Ji, do suitable options available hain. DHA Phase 6 mein three-bedroom furnished apartment 1 lakh 45 hazar monthly hai, aur Phase 5 mein 1 lakh 50 hazar. Aap kis option ki details dekhna chahenge?"

### Customer

> "Phase 6 wala."

### Agent

> "Ji bilkul. Agar aap chahein to iska visit schedule kar dete hain. Aap kis din convenient hain?"

### Customer

> "Saturday 4 PM."

### Agent

> "Ji, Saturday 4 PM. Main availability check karta hoon."

### Calendar

```text
Available
```

### Agent

> "Ji bilkul, main visit book kar deta hoon."

### Calendar

```text
Booking Successful
```

### Agent

> "Perfect sir, aapka Phase 6 apartment ka visit Saturday 4 PM ke liye confirm ho gaya hai."

### Business Event

```text
AppointmentBooked
        ↓
       n8n
    ┌───┼────┐
    ↓   ↓    ↓
 Email CRM Notification
```

---

# 25. Context Memory Example

Customer:

> "Mera budget 1.5 lakh hai."

State:

```text
monthly_budget = 150000
```

Customer:

> "DHA mein kuch hai?"

State:

```text
monthly_budget = 150000
location = DHA
```

Customer:

> "Three bedroom chahiye."

State:

```text
monthly_budget = 150000
location = DHA
bedrooms = 3
```

Customer:

> "Furnished hona chahiye."

State:

```text
monthly_budget = 150000
location = DHA
bedrooms = 3
furnished = true
```

The agent should now search without asking the customer to repeat these
requirements.

---

# 26. Guardrails

The rental flow MUST enforce:

```text
 Never invent rental prices
 Never invent availability
 Never invent property condition
 Never invent amenities
 Never guarantee property suitability
 Never book unavailable appointments
 Never claim booking success before Calendar confirmation
 Never repeatedly ask for known information
 Never expose internal system information
```

---

# 27. Success Criteria

A rental conversation is successful when the agent can:

* Detect rental intent.
* Extract monthly budget.
* Understand location requirements.
* Understand bedroom requirements.
* Handle furnished/unfurnished preference.
* Understand move-in date.
* Search verified rental inventory.
* Recommend available properties.
* Refine search when requirements change.
* Maintain context.
* Handle common rental objections.
* Schedule a property visit.
* Check actual Calendar availability.
* Confirm booking only after successful Calendar creation.
* Trigger employee notification and CRM logging.

---

# 28. Core Principle

> **Listen → Extract → Remember → Search → Verify → Recommend → Schedule → Confirm**

For rental inquiries, the agent should behave like a real rental consultant,
not a form-filling chatbot.

