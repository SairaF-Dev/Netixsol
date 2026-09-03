# Latency Targets

Day 3 target: perceived turn latency under 2 seconds where provider/network conditions allow it.

Measure separately:
- STT
- semantic/LLM + retrieval
- TTS
- total wall time

Do not claim the system guarantees <2 seconds. External provider/network latency varies.

Production tactics:
1. websocket/streaming transport;
2. short NLU prompt;
3. deterministic PostgreSQL tools;
4. stream first TTS sentence while later text is prepared;
5. interruption cancels current TTS and opens microphone;
6. warm clients/connections;
7. log p50/p95/p99.
