import asyncio

from sara_agent.streaming_voice import StreamingVoiceSession


class _Chatbot:
    def set_response_mode(self, _mode):
        return None


class _STT:
    async def close(self):
        return None


class _TTS:
    name = "test-tts"
    audio_mime_type = "audio/mpeg"

    async def stream(self, _text):
        yield b"greeting-audio"


def test_live_session_greets_and_streams_intro(monkeypatch):
    monkeypatch.setenv("SARA_VOICE_GREETING_ENABLED", "1")
    monkeypatch.delenv("SARA_VOICE_GREETING", raising=False)
    events = []

    async def collect(event):
        events.append(event)

    async def run():
        session = StreamingVoiceSession(
            chatbot=_Chatbot(),
            stt=_STT(),
            tts=_TTS(),
            event_sink=collect,
        )
        await session.greet()
        greeting_task = session._tts_task
        assert greeting_task is not None
        await greeting_task

    asyncio.run(run())

    assert events[0].type == "assistant_text"
    assert events[0].data["intro"] is True
    assert "real estate agent" in events[0].data["text"]
    assert any(event.type == "tts_start" for event in events)
    assert any(event.audio == b"greeting-audio" for event in events)
    assert any(event.type == "tts_end" for event in events)


def test_live_session_greeting_can_be_disabled(monkeypatch):
    monkeypatch.setenv("SARA_VOICE_GREETING_ENABLED", "0")
    events = []

    async def collect(event):
        events.append(event)

    async def run():
        session = StreamingVoiceSession(
            chatbot=_Chatbot(),
            stt=_STT(),
            tts=_TTS(),
            event_sink=collect,
        )
        await session.greet()

    asyncio.run(run())
    assert events == []
