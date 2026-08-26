
# Conversation Flow of Investment Inquiry 

## 1. Purpose

This flow handles customers who are interested in real estate as an investment.

The customer may want to:

- Buy a property for capital appreciation.
- Buy a property for rental income.
- Invest in an under-development project.
- Buy a plot for future development.
- Purchase a commercial property as an investment.
- Compare multiple investment options.

The agent should understand the customer's investment objective, budget,
risk preference, preferred location, investment horizon, and property type.

The agent must provide only verified company information.

The agent must NEVER guarantee:

- Profit
- Appreciation
- Rental yield
- Future property price
- Return on investment

---

# 2. Investment Requirements

The agent should gradually collect:

| Information | Required | Example |
|---|---|---|
| Intent | Yes | Investment |
| City | Preferred | Lahore |
| Budget | Yes | 5 crore |
| Investment Type | Preferred | Rental income |
| Property Type | Preferred | Apartment |
| Location | Preferred | DHA / Bahria Town |
| Investment Horizon | Preferred | 3–5 years |
| Risk Preference | Optional | Moderate |
| Rental Income Goal | Optional | Yes |
| Development Status | Optional | Ready / Under Development |
| Commercial/Residential | Optional | Residential |
| Selected Property | Before visit | Property A |
| Visit Date | Before booking | Saturday |
| Visit Time | Before booking | 4 PM |

The agent should ask questions conversationally instead of turning the call
into a questionnaire.

---

# 3. High-Level Flow

```text
Incoming Call
      ↓
Greeting
      ↓
Detect Investment Intent
      ↓
Understand Investment Goal
      ↓
Collect Budget + Preferences
      ↓
Identify Investment Strategy
      ↓
Enough Information?
   ┌──────┴──────┐
  NO             YES
   ↓              ↓
Ask Missing    Investment Search
Information        ↓
              Matching Properties?
               ┌────┴────┐
              NO         YES
               ↓          ↓
        Refine Search   Rank Options
               ↓          ↓
             Search    Present Options
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

Example:

> "Assalam-o-Alaikum sir! RealEstate Hub se baat ho rahi hai. Main aapki kis tarah help kar sakta hoon?"

If the customer immediately says:

> "Mujhe property mein investment karni hai."

Move directly to investment discovery.

---

# 5. Stage 2: Detect Investment Intent

Example:

Customer:

> "Mere paas 5 crore hain aur main property mein invest karna chahta hoon."

Extract:

```text
intent = investment
budget = 5 crore
```

The agent should recognize natural variations:

```text
"property mein paisa lagana hai"
"real estate mein invest karna hai"
"investment ke liye property chahiye"
"rental income ke liye property chahiye"
"future appreciation ke liye property chahiye"
```

These should normally map to:

```text
intent = investment
```

---

# 6. Stage 3: Understand Investment Objective

This is one of the most important steps.

The agent should determine what the customer wants from the investment.

Example:

Agent:

> "Ji bilkul. Aapka main focus rental income hai, future appreciation, ya dono?"

Possible values:

```text
rental_income
capital_appreciation
both
unspecified
```

---

# 7. Rental Income Strategy

Customer:

> "Mujhe monthly rental income chahiye."

Extract:

```text
investment_goal = rental_income
```

The recommendation engine should prioritize verified information related to:

* Existing rental status
* Rental history, if available
* Current rental information
* Property type
* Location
* Tenant demand information, if available in company data

The agent must not invent rental yields.

---

# 8. Capital Appreciation Strategy

Customer:

> "Main long-term appreciation ke liye invest karna chahta hoon."

Extract:

```text
investment_goal = capital_appreciation
investment_horizon = long_term
```

The agent may use verified information such as:

* Development status
* Project location
* Developer
* Project infrastructure
* Historical company-provided market information

The agent must not say:

> "Is property ki value definitely double ho jayegi."

Correct:

> "Future appreciation ki guarantee nahi di ja sakti. Main aapko available verified project aur location information ke basis par options compare kar sakta hoon."

---

# 9. Stage 4: Budget

Example:

Customer:

> "Budget around 5 crore hai."

Extract:

```text
budget_min = optional
budget_max = 50000000
currency = PKR
```

If the customer says:

> "5 se 6 crore tak."

Store:

```text
budget_min = 50000000
budget_max = 60000000
```

---

# 10. Stage 5: Location Preference

Customer:

> "DHA ya Bahria Town mein options dekhein."

Store:

```json
{
  "locations": [
    "DHA",
    "Bahria Town"
  ]
}
```

The search should support multiple locations.

The agent should NOT force the customer to select only one location.

---

# 11. Stage 6: Property Type

Ask only when necessary.

Example:

> "Ji, aap apartment, plot ya commercial property mein interested hain?"

Customer:

> "Apartment."

Store:

```text
property_type = apartment
```

If the customer says:

> "Koi bhi achi investment ho."

Do not assume a property type.

Instead:

> "Ji, main residential aur commercial dono options check kar sakta hoon. Aap dono compare karna chahenge?"

---

# 12. Stage 7: Investment Horizon

The agent can ask:

> "Aap short-term investment dekh rahe hain ya 3–5 years ke liye hold karna chahenge?"

Possible values:

```text
short_term
medium_term
long_term
unknown
```

This helps the recommendation engine rank properties.

---

# 13. Stage 8: Risk Preference

This is optional.

Example:

> "Aap relatively stable option prefer karenge ya development-stage project bhi consider kar sakte hain?"

Possible values:

```text
lower_risk
moderate
development_stage
unknown
```

The agent must not present these as financial guarantees.

---

# 14. Stage 9: Investment Search

Example customer profile:

```text
intent = investment
budget_max = 50000000
locations = [
    "DHA",
    "Bahria Town"
]
property_type = apartment
investment_goal = both
investment_horizon = 3_to_5_years
```

Call:

```text
search_investment_properties(
    budget_max=50000000,
    locations=["DHA", "Bahria Town"],
    property_type="Apartment",
    investment_goal="both",
    investment_horizon="3_to_5_years",
    availability=true
)
```

---

# 15. Structured SQL Search

Example:

```sql
SELECT
    property_id,
    title,
    city,
    location,
    property_type,
    transaction_type,
    price,
    area_sqft,
    bedrooms,
    availability,
    developer,
    development_status,
    rental_status
FROM properties
WHERE price <= 50000000
  AND location IN ('DHA', 'Bahria Town')
  AND property_type = 'Apartment'
  AND availability = TRUE
ORDER BY price ASC;
```

The exact recommendation logic should be implemented separately from
the database query.

SQL retrieves verified candidates.

The recommendation engine ranks them.

---

# 16. Recommendation Ranking

Example ranking factors:

```text
Location Match
        ↓
Budget Fit
        ↓
Investment Goal Match
        ↓
Property Type Match
        ↓
Investment Horizon Match
        ↓
Development Status
        ↓
Verified Rental Information
        ↓
Customer Preferences
```

Example scoring concept:

```text
Location Match         30%
Budget Fit             25%
Investment Goal        20%
Property Type          10%
Investment Horizon     10%
Other Preferences       5%
```

These weights are configurable.

They should not be presented to the customer unless needed.

---

# 17. Present Investment Options

Suppose the system finds:

```text
Property A
DHA Phase 6
Apartment
Price: 4.8 crore
Ready
Verified rental information available

Property B
Bahria Town
Apartment
Price: 4.5 crore
Under Development
Payment plan available

Property C
DHA Phase 5
Apartment
Price: 5 crore
Ready
```

Agent:

> "Ji, aapke 5 crore ke budget mein mujhe DHA aur Bahria Town mein teen relevant options mil rahe hain. DHA Phase 6 ka ek ready apartment 4 crore 80 lakh ka hai, aur Bahria Town mein ek 4 crore 50 lakh ka under-development option hai. Agar aap rental income aur long-term holding dono consider kar rahe hain to main in options ka verified comparison bata deta hoon."

---

# 18. Investment Comparison

Customer:

> "In dono mein better investment kaunsi hai?"

The agent should NOT make an unsupported financial recommendation.

Better response:

> "Ye aapke investment goal par depend karega. DHA wala option ready hai, jabke Bahria Town wala under-development hai. Agar aap chahein to main dono ke verified price, development status, rental information aur payment plan compare kar deta hoon."

Then present evidence.

---

# 19. ROI / Rental Yield Questions

Customer:

> "Iska ROI kitna hoga?"

If verified data exists:

> "Company ke available data ke mutabiq estimated rental information ye hai..."

If no verified data:

> "Is property ka verified ROI mere paas available nahi hai, isliye main percentage guess nahi karunga."

Never fabricate:

```text
"ROI guaranteed 20%"
"Price 30% increase hogi"
"Rental yield definitely 8%"
```

---

# 20. Payment Plan Questions

Customer:

> "Payment plan kya hai?"

If stored in structured data:

```text
PostgreSQL
```

If present in brochure:

```text
RAG
```

Example:

> "Ji, verified payment plan ke mutabiq initial payment ke baad installments available hain. Main aapko exact installment schedule bata deta hoon."

If the payment plan is unavailable:

> "Is project ka current payment plan meri verified knowledge mein available nahi hai. Main representative se confirm karwa sakta hoon."

---

# 21. Development Status

Customer:

> "Project ready hai?"

Use verified property data.

Example:

> "Ji, company records ke mutabiq ye project ready hai."

OR:

> "Ye project currently under development hai."

Never infer development status from an old document without checking
the current structured record.

---

# 22. Investment Objection Handling

## "Price High Hai"

Customer:

> "5 crore bohat zyada hai."

Agent:

> "Ji, samajh sakta hoon. Agar aap chahein to main isi locations mein 4 crore ya us se neeche ke investment options check kar leta hoon."

---

## "Risky Lag Raha Hai"

Customer:

> "Under-development project risky lag raha hai."

Agent:

> "Ji, ye valid concern hai. Main aapko project ka verified development status, developer information aur available payment details bata sakta hoon. Agar aap prefer karein to ready properties bhi compare kar lete hain."

---

## "Future Price Guarantee"

Customer:

> "Ye 2 saal mein kitne ka ho jayega?"

Agent:

> "Future price ki guarantee dena possible nahi hai. Main current verified pricing aur available project information ke basis par comparison kar sakta hoon."

---

# 23. Stage 10: Property Visit

When customer shows interest:

Customer:

> "DHA wala option dekhna hai."

Agent:

> "Ji bilkul. Property visit schedule kar dete hain. Aap kis din convenient hain?"

---

# 24. Stage 11: Calendar Availability

Customer:

> "Saturday 4 PM."

Agent:

> "Ji, Saturday 4 PM. Main availability check karta hoon."

Call:

```text
check_calendar_availability(
    date="Saturday",
    time="16:00"
)
```

---

## Available

Continue.

## Unavailable

Agent:

> "Saturday 4 PM available nahi hai. Saturday 5 PM ya Sunday 4 PM available hai. Aapke liye konsa convenient rahega?"

Never pretend that an unavailable slot was booked.

---

# 25. Stage 12: Appointment Booking

After selecting an available slot:

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

Example notes:

```text
Investment Goal:
Rental income + appreciation

Budget:
Up to 5 crore

Preferred Locations:
DHA, Bahria Town

Property Type:
Apartment

Investment Horizon:
3–5 years
```

After successful Calendar confirmation:

> "Ji bilkul, aapka property visit Saturday 5 PM ke liye confirm ho gaya hai."

---

# 26. Stage 13: Business Event

Create:

```text
AppointmentBooked
```

Send to n8n:

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

Intent:
Investment

Budget:
Up to 5 crore

Preferred Locations:
DHA, Bahria Town

Investment Goal:
Rental income + appreciation

Property Type:
Apartment

Investment Horizon:
3–5 years

Selected Property:
DHA Phase 6 Apartment

Visit:
Saturday, 5 PM
```

---

# 27. Complete Example

### Customer

> "Mere paas 5 crore hain aur mujhe property mein investment karni hai."

### Agent

> "Ji bilkul. Aapka main focus rental income hai, future appreciation, ya dono?"

### Customer

> "Dono."

### Agent

> "Perfect. Koi preferred location hai?"

### Customer

> "DHA ya Bahria Town."

### Agent

> "Ji. Apartment, plot ya commercial property mein preference hai?"

### Customer

> "Apartment."

### Agent

> "Aur aap short-term investment dekh rahe hain ya kuch years ke liye hold karna chahenge?"

### Customer

> "3–5 years."

### Agent

> "Ji bilkul. Main DHA aur Bahria Town mein 5 crore tak ke apartments check karta hoon jo aapke investment goal ke saath match karte hon."

### Tool

```text
search_investment_properties(
    budget_max=50000000,
    locations=["DHA", "Bahria Town"],
    property_type="Apartment",
    investment_goal="both",
    investment_horizon="3_to_5_years",
    availability=true
)
```

### Tool Result

```text
Property A
DHA Phase 6
Apartment
4.8 crore
Ready

Property B
Bahria Town
Apartment
4.5 crore
Under Development
Payment Plan Available
```

### Agent

> "Ji, do strong options available hain. DHA Phase 6 mein 4 crore 80 lakh ka ready apartment hai, aur Bahria Town mein 4 crore 50 lakh ka under-development option hai. Agar aap chahein to main dono ka verified comparison bata deta hoon."

### Customer

> "DHA wala dekhna hai."

### Agent

> "Ji bilkul. Aap Saturday ko visit kar sakte hain?"

### Customer

> "Haan, 4 PM."

### Agent

> "Ji, Saturday 4 PM. Main availability check karta hoon."

### Calendar

```text
Available
```

### Agent

> "Perfect sir, visit Saturday 4 PM ke liye confirm kar deta hoon."

### Calendar

```text
Booking Successful
```

### Agent

> "Ji bilkul, aapka DHA Phase 6 property visit Saturday 4 PM ke liye confirm ho gaya hai."

### n8n

```text
AppointmentBooked
        ↓
       n8n
    ┌───┼────┐
    ↓   ↓    ↓
 Email CRM Notification
```

---

# 28. Context Memory Example

Customer:

> "Budget 5 crore hai."

State:

```text
budget_max = 50000000
```

Customer:

> "DHA ya Bahria Town."

State:

```text
locations = [
    "DHA",
    "Bahria Town"
]
```

Customer:

> "Apartment."

State:

```text
property_type = apartment
```

Customer:

> "Rental income bhi chahiye."

State:

```text
investment_goal = rental_income
```

Customer:

> "Aur 3–5 years hold karunga."

State:

```text
investment_horizon = 3_to_5_years
```

The final search should use the complete accumulated context.

---

# 29. Guardrails

The investment flow MUST enforce:

```text
 Never guarantee profit.
 Never guarantee appreciation.
 Never guarantee rental yield.
 Never provide fabricated ROI.
 Never fabricate market statistics.
 Never present speculation as fact.
 Never invent property prices.
 Never invent availability.
 Never invent payment plans.
 Never recommend an unavailable property.
 Never book an unavailable appointment.
 Never claim booking success before Calendar confirmation.
 Never provide personalized financial advice beyond verified property information.
 Never hide material property information to force a sale.
 Never use fake urgency or pressure tactics.
```

---

# 30. Escalation Rules

Escalate to a human representative when:

```text
Customer requests detailed financial advice
        ↓
Human Investment Specialist

Customer asks for legal/tax advice
        ↓
Human / Qualified Professional

Customer requests negotiation
        ↓
Human Sales Representative

Customer asks for unavailable internal information
        ↓
Human Representative

Customer has a complex investment portfolio
        ↓
Human Investment Specialist
```

Example:

> "Ji, is specific financial decision ke liye main aapko qualified investment
> specialist se connect karwa deta hoon."

---

# 31. Success Criteria

An investment conversation is successful when the agent can:

* Detect investment intent.
* Identify the investment objective.
* Understand budget.
* Handle multiple preferred locations.
* Understand property type.
* Understand investment horizon.
* Understand basic risk preference.
* Search verified investment properties.
* Rank properties according to customer requirements.
* Compare options using factual evidence.
* Answer ROI and rental questions without hallucinating.
* Handle investment objections responsibly.
* Maintain context.
* Offer a property visit.
* Check actual Calendar availability.
* Book only available slots.
* Trigger employee notification.
* Log investment requirements in CRM.

---

# 32. Core Principle

> **Understand Goal → Collect Constraints → Search → Verify → Compare → Explain → Schedule → Confirm**

For investment inquiries, the agent's job is not to promise the customer
a profitable investment.

Its job is to provide **accurate, verified property information**, understand
the customer's investment objective, present relevant options, and move the
customer toward an informed next step.

