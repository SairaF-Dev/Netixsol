
# Voice Evaluation (Fish Audio vs ElevenLabs)

## 1. Purpose

The real estate voice agent must sound natural during Pakistani
UrduLish conversations.

The selected TTS voice should support:

- Natural Urdu pronunciation
- Natural English pronunciation
- Urdu-English code-switching
- Conversational tone
- Appropriate pauses
- Emotional variation
- Low latency
- Streaming
- Consistent voice quality

For this project:

- **Agent identity:** Sara
- **Selected voice:** Sia
- **Voice provider:** Fish Audio
- **Alternative provider:** ElevenLabs

Important distinction:

> Sara is the agent's identity. Sia is the TTS voice used to speak Sara's
> responses.

---

# 2. Evaluation Criteria

We evaluate both providers on:

1. Latency
2. Naturalness
3. Emotion
4. Streaming
5. Voice cloning
6. Pricing
7. Multilingual support
8. Urdu pronunciation
9. Urdu-English switching
10. Suitability for a real-time sales agent

---

# 3. Test Sentences

The same test sentences should be used for both providers.

## Test 1: UrduLish Greeting

> "Assalam-o-Alaikum sir! RealEstate Hub se Sara baat kar rahi hoon.
> Main aapki kis tarah help kar sakti hoon?"

### Evaluate

- Urdu pronunciation
- Warmth
- Natural greeting
- Professional tone

---

## Test 2: Property Search

> "Ji bilkul, main aapke budget mein DHA ke available apartments check
> kar leti hoon."

### Evaluate

- Urdu-English switching
- Natural sentence rhythm
- Pronunciation of "budget", "DHA", and "apartments"

---

## Test 3: Numbers

> "Is apartment ki price do crore 85 lakh hai."

### Evaluate

- Number pronunciation
- Natural Urdu pronunciation
- Pace

---

## Test 4: English Real Estate Terms

> "Ye three-bedroom furnished apartment hai, aur is mein dedicated
> parking bhi available hai."

### Evaluate

- "three-bedroom"
- "furnished"
- "apartment"
- "dedicated parking"
- Urdu-English switching

---

## Test 5: Objection Handling

> "Ji, samajh sakti hoon. Agar aap chahein to main isi area mein
> lower-price options bhi check kar leti hoon."

### Evaluate

- Empathy
- Emotional variation
- Persuasiveness
- Conversational naturalness

---

## Test 6: Thinking Phrase

> "Hmm... ek second sir, main availability check karti hoon."

### Evaluate

- Pause
- Natural hesitation
- Human-like delivery

---

# 4. Scoring System

Each category is scored from **1 to 5**.

| Score | Meaning |
|---|---|
| 1 | Very poor |
| 2 | Poor |
| 3 | Acceptable |
| 4 | Good |
| 5 | Excellent |

---

# 5. Evaluation Matrix

| Category | Fish Audio | ElevenLabs |
|---|---:|---:|
| Urdu pronunciation |  |  |
| English pronunciation |  |  |
| Urdu-English switching |  |  |
| Naturalness |  |  |
| Emotional expression |  |  |
| Conversational tone |  |  |
| Streaming |  |  |
| Latency |  |  |
| Voice consistency |  |  |
| Voice cloning |  |  |
| Multilingual support |  |  |
| Pricing |  |  |
| Overall suitability |  |  |

Scores should be based on actual testing rather than assumptions.

---

# 6. Actual Initial Voice Test

## ElevenLabs — Sia

The selected ElevenLabs voice:

**Sia — Sweet & Smart Sales Professional**

Observed results during initial testing:

| Category | Score |
|---|---:|
| Urdu pronunciation | 5/5 |
| English pronunciation | 5/5 |
| Naturalness | 5/5 |

### Observation

Sia performed well on Urdu and English pronunciation and sounded natural
during the initial tests.

The voice is suitable for a professional sales conversation.

---

# 7. Fish Audio Voice Testing

Several Fish Audio voices were tested.

## Test Voice 1

Description:

> "A young female voice with an energetic and friendly tone, ideal for
> social media content or product advertisements."

### Result

**Rejected**

Reason:

> The voice sounded too robotic for a natural real estate phone
> conversation.

---

## Test Voice 2

Description:

> "A calm and professional female voice, perfect for explaining
> processes and discussing options with clarity and a measured pace."

### Result

**Rejected**

Reason:

> The voice did not sound sufficiently natural for the intended
> conversational experience.

---

## Test Voice 3 — Warm Storytelling Voice

Description:

> "A clear and warm female voice, perfect for engaging storytelling and
> narrative content."

### Result

**Rejected**

Reason:

> The voice did not match the desired real estate sales-agent
> personality closely enough.

---

## Test Voice 4

Description:

> "A cheerful and professional young female voice, ideal for customer
> service and promotional calls."

### Result

**Rejected**

Reason:

> The voice did not sound sufficiently natural for the target
> conversation.

---

# 8. Selected Voice

For the current implementation, the project uses:

```text
Agent Name: Sara
TTS Voice: Sia
````

The selected Sia voice is preferred because the initial testing showed:

```text
Urdu pronunciation: 5/5
English pronunciation: 5/5
Naturalness: 5/5
```

The voice should continue to be tested using complete UrduLish
conversations before final production deployment.

---

# 9. Urdu-English Switching Test

The agent must naturally switch between Urdu and English.

### Example

> "Ji sir, aapka budget three crore hai aur aap DHA mein
> three-bedroom apartment prefer kar rahe hain."

A good voice should not make the English terms sound disconnected from
the Urdu sentence.

### Required behaviour

```text
Urdu → English → Urdu → English
```

should sound like one natural conversation.

---

# 10. Number Pronunciation Test

Real estate conversations contain many numbers.

Test:

> "Price do crore 85 lakh hai."

Test:

> "Monthly rent aek lakh pachaas hazar hai."

Test:

> "Three-bedroom apartment available hai."

The voice should preserve the intended language of each term.

---

# 11. Latency Evaluation

For a real-time voice agent, latency is critical.

Measure:

```text
Customer stops speaking
        ↓
Speech-to-Text complete
        ↓
LLM response generated
        ↓
TTS starts
```

### Target

```text
End-to-first-audio latency < 2 seconds
```

The target should be measured in the complete pipeline rather than
measuring TTS alone.

---

# 12. Streaming Evaluation

Streaming is important because the agent should begin speaking before
the entire response is generated.

### Desired pipeline

```text
Customer Speech
      ↓
Streaming STT
      ↓
LLM
      ↓
Streaming TTS
      ↓
Audio Output
```

### Good behaviour

The customer should hear the beginning of the response quickly rather
than waiting for the complete response to be generated.

---

# 13. Emotion Evaluation

Test the voice with different situations.

### Normal

> "Ji bilkul, main available options check karti hoon."

### Empathy

> "Ji, samajh sakti hoon. Price aapke budget se thori high hai."

### Excitement

> "Ji, mujhe aapke criteria ke according ek acha option mila hai."

### Confirmation

> "Ji bilkul, aapki appointment confirm ho gayi hai."

### Apology

> "Sorry sir, aapko inconvenience hui."

The voice should change its delivery naturally.

---

# 14. Voice Cloning Evaluation

Voice cloning can be useful for creating a consistent brand identity.

Evaluate:

* Voice similarity
* Pronunciation quality
* Urdu performance
* English performance
* Emotional consistency
* Stability across long conversations

Voice cloning should only be used with appropriate authorization and
consent.

---

# 15. Naturalness Evaluation

A voice should not simply pronounce words correctly.

Evaluate:

```text
Prosody
Pauses
Rhythm
Pitch variation
Sentence endings
Emphasis
Emotional delivery
```

A voice can have perfect pronunciation and still sound robotic.

Therefore:

> **Naturalness is more important than pronunciation alone.**

---

# 16. Real Estate Conversation Test

The final test should simulate a complete call.

### Customer

> "Assalam-o-Alaikum, mujhe DHA mein apartment chahiye."

### Sara

> "Wa-Alaikum-Assalam sir! Ji bilkul. Aap purchase ke liye dekh rahe
> hain ya rental ke liye?"

### Customer

> "Purchase. Budget around 3 crore hai."

### Sara

> "Acha ji, 3 crore. Bedrooms kitne chahiye?"

### Customer

> "Three bedroom."

### Sara

> "Theek hai sir. Main DHA mein three-bedroom apartments aapke budget
> ke according check karti hoon."

The voice should sound like a continuous human conversation.

---

# 17. Evaluation Findings

Based on the initial manual tests:

### ElevenLabs Sia

Strengths observed:

* Excellent Urdu pronunciation
* Excellent English pronunciation
* High naturalness
* Suitable professional female voice
* Good fit for the sales persona

Initial score:

```text
Urdu pronunciation: 5/5
English pronunciation: 5/5
Naturalness: 5/5
```

### Fish Audio

Initial tested voices did not match the desired conversational
personality closely enough.

Several voices sounded:

* Robotic
* Too promotional
* Too narration-oriented
* Less suitable for the intended sales conversation

Therefore, Fish Audio should not be selected simply because it is
recommended in the project specification.

---

# 18. Current Decision

## Selected TTS Voice

**Sia — ElevenLabs**

## Agent Identity

**Sara**

### Decision

For the current prototype, **ElevenLabs Sia is the preferred voice**
because the actual initial testing produced stronger results for:

* Urdu pronunciation
* English pronunciation
* Naturalness
* Real estate sales persona

Fish Audio remains a valid alternative and can be re-evaluated if a more
suitable voice is found.

---

# 19. Important Engineering Principle

Do not choose a TTS provider based only on marketing claims.

The final decision should be based on:

```text
Actual UrduLish Test
        ↓
Latency Measurement
        ↓
Naturalness Evaluation
        ↓
Conversation Test
        ↓
User Evaluation
        ↓
Production Cost
        ↓
Final Decision
```

---

# 20. Future Benchmark

Before production deployment, record at least:

```text
10 UrduLish test sentences
5 property-search conversations
5 objection-handling conversations
5 appointment conversations
5 interruption tests
5 number/pricing tests
```

Then calculate:

```text
Average Naturalness
Average Urdu Pronunciation
Average English Pronunciation
Average Code-Switching Quality
Average Latency
```

The final voice should be selected using these measurements rather than
personal preference alone.

---

# 21. Final Recommendation

For the current project:

```text
                    TTS
                     │
             ┌───────┴────────┐
             ↓                ↓
        ElevenLabs        Fish Audio
             │
             ↓
       Sia Voice
             │
             ↓
       Sara's Voice
```

**Current choice: ElevenLabs Sia**

Reason:

> Actual testing showed 5/5 for Urdu pronunciation, 5/5 for English
> pronunciation, and 5/5 for naturalness, making it the stronger
> choice for the current UrduLish real estate voice agent prototype.


