# Live voice-call validation — 2026-08-31

## Successful call

The production HTTP voice path completed with real cloud services and returned
HTTP 200 plus non-empty MP3 response audio.

- Caller utterance: `Assalam-o-Alaikum, mujhe Lahore mein teen crore tak ghar khareedna hai.`
- Caller audio: Edge neural Urdu TTS, 17,568 bytes
- STT: Deepgram
- Normalized transcript: `Lahoreمین 10 کریور ٹیک ہائی`
- Agent response: `Aap rent ke liye dekh rahi hain ya purchase ke liye?`
- Spoken response: `Acha. Aap rent ke liye dekh rahi hain ya purchase ke liye?`
- Response audio: MP3, 27,072 bytes
- Observed request round trip: 10,709 ms
- PostgreSQL readiness: ready
- RAG readiness: ready

## Acceptance result

- End-to-end speech → STT → agent → TTS: **pass**
- Non-empty playable response audio: **pass**
- Safe recovery from uncertain transcription: **pass**
- Accurate UrduLish transcription: **fail** — purchase intent was lost and the
  budget was misheard.
- Under-two-second target: **fail** — observed round trip was 10.7 seconds.

## ElevenLabs validation

The ElevenLabs integration was updated for the current SDK and authenticated
with the supplied API key. The provider rejected synthesis with HTTP 402 because
the account plan does not permit the configured/library voices through the API.
No API key is stored in this report or in repository configuration.

To complete an ElevenLabs-output call, enable API TTS for the account or provide
a voice ID permitted by its subscription. The Edge fallback remains operational.
