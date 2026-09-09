# UrduLish conversational matrix — observed results

Executed 1270 cases: {'pass': 1002, 'fail': 268}. pytest exit status: 1.

Offline scope: `repair` runs public understand() with a neutral omitted-field provider response; `deterministic` enables the real fast path with the same offline fallback. Neither measures live LLM accuracy. `http` supplies explicit semantic NLU fixtures and exercises ChatAdapter.turn() through the authenticated API. `turn` bypasses HTTP validation only to test the adapter's empty-input behavior.

Failures are observed contract mismatches, not automatically approved fixes. Repair failures describe resilience to provider omissions; live semantic interpretation may differ. No production changes are part of this pass.

| Category | Cases | Pass | Fail | Harness errors |
|---|---:|---:|---:|---:|
| 01_greetings | 52 | 30 | 22 | 0 |
| 02_new_user | 54 | 54 | 0 | 0 |
| 03_returning_user | 72 | 70 | 2 | 0 |
| 04_search | 117 | 90 | 27 | 0 |
| 05_location | 108 | 76 | 32 | 0 |
| 06_budget | 73 | 62 | 11 | 0 |
| 07_attributes | 60 | 52 | 8 | 0 |
| 08_feedback | 46 | 37 | 9 | 0 |
| 09_booking | 108 | 102 | 6 | 0 |
| 10_details | 80 | 50 | 30 | 0 |
| 11_off_topic | 40 | 24 | 16 | 0 |
| 12_unclear | 50 | 38 | 12 | 0 |
| 13_multi_intent | 45 | 33 | 12 | 0 |
| 14_language | 48 | 39 | 9 | 0 |
| 15_system_input | 48 | 48 | 0 | 0 |
| 16_session_context | 40 | 36 | 4 | 0 |
| 17_negation | 46 | 4 | 42 | 0 |
| 18_frustration | 40 | 40 | 0 | 0 |
| 19_references | 57 | 42 | 15 | 0 |
| 20_cross_cutting | 86 | 75 | 11 | 0 |

## Failure families

Each family groups one seed and test boundary; full individual inputs, effective state, expected checks, actual responses, mutations and side effects are in results.json and failures.md.

- **01_greetings/recognition** (deterministic; 22 cases): `hi` — intent: expected 'greeting', actual 'unknown'
- **03_returning_user/same_city** (http; 2 cases): `lahor mein hi` — response.message: missing 'DHA'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'
- **04_search/bedrooms_flexible** (repair; 9 cases): `bedrooms flexible hain` — relax: missing 'bedrooms'; actual ['area']
- **04_search/budget_flexible** (repair; 9 cases): `budget koi masla nahi` — relax: missing 'budget'; actual []
- **04_search/type_flexible** (repair; 9 cases): `property type koi bhi` — relax: missing 'property_type'; actual ['area']
- **05_location/city_typo** (repair; 9 cases): `lahor` — required.city: expected 'Lahore', actual None
- **05_location/correction** (repair; 6 cases): `Bahria mein sorry DHA mein` — required.area: expected 'DHA', actual 'Bahria'
- **05_location/full_phase** (repair; 9 cases): `DHA Phase 5` — required.area: expected 'DHA Phase 5', actual 'DHA'
- **05_location/multiple** (http; 2 cases): `DHA mein dikhao` — response.requires_clarification: expected True, actual False
- **05_location/phase_without_parent** (repair; 6 cases): `Phase 5` — needs_clarification: expected True, actual False
- **06_budget/booking_budget** (http; 6 cases): `budget flexible hai` — response.requires_clarification: expected True, actual False
- **06_budget/decimal_1** (repair; 3 cases): `budget 3.5m` — required.budget: expected 3500000, actual None
- **06_budget/unknown_purpose** (repair; 2 cases): `3.5m` — needs_clarification: expected True, actual False
- **07_attributes/house** (repair; 2 cases): `ghar chahiye` — required.property_type: expected 'House', actual None
- **07_attributes/negative_amenity** (repair; 6 cases): `gym nahi chahiye` — preferred.amenities: must not contain 'Gym'; actual ['Gym']
- **08_feedback/liked** (http; 3 cases): `pehli pasand hai` — event_ids: expected ['P-1'], actual ['P-2']
- **08_feedback/rejected** (http; 3 cases): `pehli reject kar dein` — event_ids: expected ['P-1'], actual ['P-2']
- **08_feedback/shortlisted** (http; 3 cases): `pehli shortlist kar dein` — event_ids: expected ['P-1'], actual ['P-2']
- **09_booking/full** (http; 3 cases): `pehli ki visit 2 January 2030 subah 10 baje` — booked_ids: expected ['P-1'], actual ['P-2']
- **09_booking/single_time** (http; 3 cases): `2 January 2030 subah 10 baje visit` — response.appointment: expected nonempty, actual None
- **10_details/amenities** (http; 2 cases): `amenities kya hain` — response.message: missing 'Parking'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/area_attribute** (http; 3 cases): `DHA mein price kya hai` — response.message: missing 'Home P-1'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/bathrooms** (http; 6 cases): `bathrooms kitne hain` — response.message: missing '2'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/bedrooms** (http; 2 cases): `bedrooms kitne hain` — response.message: missing '3'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/developer** (http; 2 cases): `developer kaun hai` — response.message: missing 'developer'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/location** (http; 2 cases): `location kahan hai` — response.message: missing 'Lahore'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/multiple** (http; 2 cases): `price kya hai aur bathrooms kitne hain` — response.message: missing 'bathrooms'; actual 'Ji, Home P-2 mein 3 bedrooms hain. Mazeed details ya visit schedule karne ke liye batayein.'
- **10_details/price** (http; 2 cases): `price kya hai` — response.message: missing 'price'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/purpose** (http; 2 cases): `purpose kya hai` — response.message: missing 'purchase'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/size** (http; 2 cases): `size kya hai` — response.message: missing 'Home'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/status** (http; 2 cases): `status kya hai` — response.message: missing 'Ready'; actual 'Kis option ki baat kar rahe hain? Option number bata dein.'
- **10_details/unavailable** (http; 3 cases): `price kya hai` — response.message: missing 'available nahi'; actual 'Kis option ki details chahiye? Option number bata dein.'
- **11_off_topic/redirect** (http; 16 cases): `Pakistan ka capital kya hai` — response.message: missing 'property'; actual 'Ji, please batayein — Lahore mein hi doosre areas dekhne hain ya kisi aur city mein?'
- **12_unclear/ambiguous_property_type** (http; 6 cases): `apartment ya house` — response.message: missing 'type'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'
- **12_unclear/ambiguous_purpose** (http; 6 cases): `rent ya buy` — response.message: missing 'rent'; actual 'Ji, apartment, Lahore mein aur 2 crore tak budget samajh gayi. Bas ye thora sa clear kar dein kis area mein dekhna hai ya kitney bedrooms, phir main best options suggest krskti hoon?'
- **13_multi_intent/details_booking** (http; 6 cases): `price kya hai aur pehli ki visit book kar dein` — response.message: missing 'date'; actual 'Ji, Home P-2 ki price 1.20 Crore PKR hai. Mazeed details ya visit schedule karne ke liye batayein.'
- **13_multi_intent/feedback_criteria** (http; 6 cases): `pehli pasand hai lekin ab budget 3 crore` — event_ids: expected nonempty, actual []
- **14_language/urdu_script** (deterministic; 9 cases): `مجھے مکان چاہیے` — exception: expected 'UnderstandingError', actual None
- **16_session_context/booking** (http; 2 cases): `pehli ki visit book kar dein` — status: expected 200, actual 503
- **16_session_context/details** (http; 2 cases): `pehli ki details` — status: expected 200, actual 503
- **17_negation/amenity** (repair; 6 cases): `gym nahi chahiye` — excluded.amenities: missing 'Gym'; actual None
- **17_negation/area** (repair; 6 cases): `DHA nahi chahiye` — excluded.area: missing 'DHA'; actual None
- **17_negation/double** (repair; 6 cases): `nahi DHA nahi chahiye ab` — excluded.area: missing 'DHA'; actual None
- **17_negation/preserve_exclusion_amenities** (repair; 4 cases): `gym nahi chahiye` — preferred.amenities: must not contain 'Gym'; actual ['Gym']
- **17_negation/preserve_exclusion_area** (repair; 4 cases): `DHA nahi chahiye` — required.area: must not contain 'DHA'; actual 'DHA'
- **17_negation/preserve_exclusion_purpose** (repair; 4 cases): `rent nahi chahiye` — required.purpose: must not contain 'Rental'; actual 'Rental'
- **17_negation/purpose** (repair; 6 cases): `rent nahi chahiye` — excluded.purpose: missing 'Rental'; actual None
- **17_negation/type** (repair; 6 cases): `apartment nahi chahiye` — excluded.property_type: missing 'Apartment'; actual None
- **19_references/first_index** (http; 3 cases): `1` — event_ids: expected ['P-1'], actual ['P-2']
- **19_references/first_word** (http; 3 cases): `pehli wali` — event_ids: expected ['P-1'], actual ['P-2']
- **19_references/pronoun** (http; 3 cases): `yeh wala` — event_ids: expected ['P-1'], actual []
- **19_references/second_index** (http; 3 cases): `2` — response.requires_clarification: expected True, actual False
- **19_references/second_word** (http; 3 cases): `doosri wali` — response.requires_clarification: expected True, actual False
- **20_cross_cutting/filtered_booking** (http; 5 cases): `pehli ki visit book kar dein` — booked_ids: expected ['P-1'], actual ['P-2']
- **20_cross_cutting/offtopic_booking** (http; 5 cases): `weather kaisa hai, khair visit book karni hai` — response.message: missing 'property'; actual 'Saved requirement continue karni hai ya koi preference change karni hai?'
- **20_cross_cutting/phase_typo_booking** (http; 1 cases): `DHA mein dikhao, visit bhi karni hai` — response.requires_clarification: expected True, actual False

## Production file fingerprints

- `day7/web_api/chat.py`: `f90d4d1ac06f5799547da2db174cf9acafe3d69131e3c9b537d4778722ac5cda`
- `day3/src/sara_agent/understanding.py`: `6c9230b9a61e8e976c11cce4c0db70c176e5db32c50620434f2ccaa77c0151b7`
