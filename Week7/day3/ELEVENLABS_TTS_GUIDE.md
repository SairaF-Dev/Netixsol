# ElevenLabs TTS Integration Guide

This document describes how to use ElevenLabs for Text-to-Speech (TTS) in the Sara Real Estate Voice Agent.

## Overview

The system now supports **two TTS providers**:
- **Edge TTS** (Microsoft) — Free, default
- **ElevenLabs** — Premium, natural-sounding voices

You can switch between them using a single environment variable.

---

## Setup

### 1. Get ElevenLabs API Key

1. Visit [https://elevenlabs.io](https://elevenlabs.io)
2. Sign up for a free or paid account
3. Go to **Account → API Key**
4. Copy your API key

### 2. Configure Environment

Edit `.env`:

```env
# Switch to ElevenLabs
SARA_TTS_PROVIDER=elevenlabs

# Add your API key
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Customize voice and model
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_turbo_v2_5
ELEVENLABS_STABILITY=0.5
ELEVENLABS_SIMILARITY_BOOST=0.75
```

### 3. Install Package

Already included in `requirements.txt`. If needed:

```powershell
pip install elevenlabs
```

---

## Configuration Options

### `SARA_TTS_PROVIDER`

**Options:** `edge-tts` | `elevenlabs`  
**Default:** `edge-tts`

Controls which TTS backend is used.

```env
SARA_TTS_PROVIDER=elevenlabs
```

### `ELEVENLABS_API_KEY`

**Required for ElevenLabs**

Your API key from https://elevenlabs.io

```env
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### `ELEVENLABS_VOICE_ID`

**Default:** `EXAVITQu4vr4xnSDxMaL` (Rachel — Clear, expressive voice)

Voice ID to use. Options:
- `EXAVITQu4vr4xnSDxMaL` — Rachel (Recommended for UrduLish)
- `JBFqnCBsd6RMkjVY3eFS` — Bill
- `TxGEqnHWrfWFTfGW9XjX` — Grace
- Find more at https://elevenlabs.io/docs/voices

```env
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
```

### `ELEVENLABS_MODEL_ID`

**Default:** `eleven_turbo_v2_5`

Model to use. Options:
- `eleven_turbo_v2_5` — Fastest (recommended for real-time)
- `eleven_multilingual_v2` — Multilingual, natural
- `eleven_monolingual_v1` — English only, classic

```env
ELEVENLABS_MODEL_ID=eleven_turbo_v2_5
```

### `ELEVENLABS_STABILITY`

**Default:** `0.5` (range: 0.0–1.0)

Consistency of the voice. Lower = more variation, Higher = more consistent.

```env
ELEVENLABS_STABILITY=0.5
```

### `ELEVENLABS_SIMILARITY_BOOST`

**Default:** `0.75` (range: 0.0–1.0)

How closely the voice mimics the model. Higher = more accurate to training data.

```env
ELEVENLABS_SIMILARITY_BOOST=0.75
```

---

## Usage Examples

### Switch to ElevenLabs (Quick)

```powershell
# Edit .env
SARA_TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Start API
uvicorn api.main:app --reload
```

The system will automatically use ElevenLabs for all streaming voice sessions.

### Test with CLI

```python
from src.sara_agent.streaming_voice import build_tts_provider
import asyncio

async def test():
    tts = build_tts_provider()
    async for chunk in tts.stream("Assalam-o-Alaikum. How can I help you?"):
        print(f"Received {len(chunk)} bytes of audio")

asyncio.run(test())
```

### Test with WebSocket

```bash
# Terminal 1: Start API
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Open browser and connect to:
# ws://127.0.0.1:8000/ws/voice/test_session
```

The frontend will automatically stream with ElevenLabs TTS.

---

## Comparing TTS Providers

| Feature | Edge TTS | ElevenLabs |
|---------|----------|------------|
| **Cost** | Free | Paid ($0.03/10k chars) |
| **Naturalness** | Good | Excellent |
| **Latency** | <100ms | 200–300ms |
| **Languages** | 60+ | 29+ |
| **Urdu Support** | Native (ur-PK) | Via multilingual model |
| **Streaming** | ✅ Yes | ✅ Yes |
| **Voice Cloning** | ❌ No | ✅ Yes (paid) |
| **Customization** | Limited | Extensive |
| **Best For** | Dev/Testing | Production |

---

## Troubleshooting

### Error: "ELEVENLABS_API_KEY is not configured"

**Solution:** Add your API key to `.env`:
```env
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Error: "elevenlabs is not installed"

**Solution:** Install the package:
```powershell
pip install elevenlabs
```

### Slow TTS Response

**Solutions:**
1. Use `eleven_turbo_v2_5` model (fastest)
2. Reduce `SARA_TTS_MAX_CHARS` (default 1200)
3. Use Edge TTS for testing, ElevenLabs for production

### Poor Audio Quality

**Solutions:**
1. Increase `ELEVENLABS_SIMILARITY_BOOST` (0.75 → 0.9)
2. Increase `ELEVENLABS_STABILITY` (0.5 → 0.7)
3. Try different `ELEVENLABS_VOICE_ID`

### Urdu Pronunciation Issues

**Best Settings for UrduLish:**
```env
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_STABILITY=0.65
ELEVENLABS_SIMILARITY_BOOST=0.8
```

---

## Monitoring & Metrics

### Check TTS Provider at Runtime

The API logs which provider is active:
```
INFO  Using ElevenLabs for TTS
```

### Track Streaming Latency

Latency is automatically measured. Check the `StreamEvent` for:
- `stt_latency_ms`
- `llm_latency_ms`
- `tts_latency_ms`
- `total_latency_ms`

---

## Advanced: Custom Voice ID

To use a custom cloned voice from ElevenLabs:

1. Clone a voice in ElevenLabs dashboard
2. Note the Voice ID (looks like `EXAVITQu4vr4xnSDxMaL`)
3. Add to `.env`:

```env
ELEVENLABS_VOICE_ID=your_custom_voice_id_here
```

---

## Cost Estimation

### ElevenLabs Pricing (as of 2026)

- **Free tier:** 10,000 characters/month
- **Pay as you go:** $0.03 per 10,000 characters
- **Starter:** $5/month (100k chars)
- **Pro:** $99/month (1M chars)

### Estimating Usage

Average property inquiry conversation:
- ~50 turns (agent + user)
- ~100 chars per agent turn = 5,000 chars total
- Cost: **~$0.0015 per conversation**
- 100 calls/day = **$0.15/day** or **$4.50/month**

---

## Fallback Configuration

To gracefully fall back to Edge TTS if ElevenLabs fails:

```python
from src.sara_agent.streaming_voice import build_tts_provider

def get_tts_safe():
    try:
        return build_tts_provider()
    except Exception as e:
        logger.warning(f"ElevenLabs failed: {e}. Falling back to Edge TTS.")
        # Set fallback env var
        os.environ["SARA_TTS_PROVIDER"] = "edge-tts"
        return build_tts_provider()
```

---

## References

- ElevenLabs API Docs: https://elevenlabs.io/docs
- Available Voices: https://elevenlabs.io/docs/voices
- Streaming Guide: https://elevenlabs.io/docs/api-reference/stream
- Pricing: https://elevenlabs.io/pricing
