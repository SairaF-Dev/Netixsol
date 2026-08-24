# Task 4 — Fish Audio vs ElevenLabs Evaluation

| Criterion | Fish Audio | ElevenLabs |
|---|---|---|
| Latency | Streams audio at roughly 100ms latency, positioned for real-time conversational agents | Flash/Turbo models are tuned specifically for ultra-low-latency conversational agents; generally has the latency edge for live phone-style agents |
| Naturalness | S2 Pro beat ElevenLabs 60/40 in blind A/B tests across 71,000+ paired comparisons | Strong, especially for long-form consistency; scores higher for consistency across long-form, production-ready output |
| Emotion / expressiveness | Leans into inline emotion tags, word-level prosody control, with thousands of emotion tags | Rich but more studio/production oriented |
| Streaming | Supports streaming APIs suited to live token streaming and real-time agents | Real-time streaming API at sub-300ms latency; mature streaming infra for conversational agents |
| Voice cloning | Voice cloning from short samples; open-source self-hosting option | Instant and professional voice cloning, from as little as 30 seconds, more polished studio tooling |
| Pricing | TTS at $15 per million UTF-8 bytes (~180,000 English words / 12 hours of speech) — significantly cheaper per-character than ElevenLabs | Roughly $0.18–$0.30 per 1,000 characters depending on model tier — 4–11x more expensive per character for comparable text |
| Multilingual support | Community voice library holds more than 2,000,000 shared voices across 30+ languages | 70+ languages; broader documented enterprise multilingual/dubbing support |
| Urdu pronunciation / code-switching | Not a headline-documented language on either platform — real-world testing required | Same caveat applies — neither vendor publishes Urdu-specific benchmarks; both need hands-on pronunciation testing with real UrduLish scripts |
| Ecosystem / reliability | Newer platform; hasn't faced similar public legal challenges around training data as some competitors, but ElevenLabs has the larger, more established ecosystem | Differentiates through Scribe v2 transcription and ElevenAgents, a mature platform for converting chat agents into voice agents |

## Conclusion

For this project, **Fish Audio is the better default choice**, primarily on cost and latency: at roughly $15/million characters versus ElevenLabs' $0.18–$0.30 per 1,000 characters, Fish Audio is dramatically cheaper for a high-call-volume real estate line, and its ~100ms streaming latency fits a sub-1.2s response budget. The main open risk is **Urdu/UrduLish pronunciation quality**, which neither vendor documents in detail — this needs to be validated empirically by cloning or selecting a voice and running it against real UrduLish sales scripts (code-switched sentences, Urdu numerals, English real-estate jargon like "down payment," "possession," "installment plan"). If Fish Audio's Urdu output proves weak, ElevenLabs is the fallback given its broader documented language coverage and studio-grade cloning — at a materially higher per-minute cost that should be budgeted for at scale.

*Sources: Fish Audio and ElevenLabs public comparison/pricing pages, referenced August 2026.*
