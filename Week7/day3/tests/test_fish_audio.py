import json

from sara_agent.fish_audio import FishAudioConfig
from sara_agent.streaming_voice import (
    FallbackTTSStreamer,
    FishAudioStreamer,
    build_tts_provider,
)
from sara_agent.voice import (
    FallbackTTSProvider,
    FishAudioTTSProvider,
    build_voice_provider,
)


def test_fish_config_builds_official_tts_request(monkeypatch):
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "voice-id")
    monkeypatch.delenv("FISH_AUDIO_FORMAT", raising=False)
    monkeypatch.delenv("FISH_AUDIO_OUTPUT_FORMAT", raising=False)
    monkeypatch.delenv("FISH_AUDIO_MODEL", raising=False)
    monkeypatch.delenv("FISH_AUDIO_TTS_URL", raising=False)
    monkeypatch.delenv("FISH_AUDIO_API_URL", raising=False)

    config = FishAudioConfig.from_env()
    payload = config.payload(" Ji bilkul. ")

    assert config.endpoint == "https://api.fish.audio/v1/tts"
    assert config.headers()["Authorization"] == "Bearer test-key"
    assert config.headers()["model"] == "s2-pro"
    assert payload["text"] == "Ji bilkul."
    assert payload["reference_id"] == "voice-id"
    assert payload["format"] == "mp3"
    assert payload["latency"] == "balanced"


def test_turn_based_fish_provider_returns_audio(monkeypatch):
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_FORMAT", "mp3")
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"audio"

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "sara_agent.voice.urllib.request.urlopen",
        fake_urlopen,
    )
    provider = FishAudioTTSProvider()

    assert provider.synthesize("Assalam-o-Alaikum") == b"audio"
    assert captured["payload"]["text"] == "Assalam-o-Alaikum"
    assert provider.audio_mime_type == "audio/mpeg"


def test_fish_config_accepts_voice_and_output_aliases(monkeypatch):
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.delenv("FISH_AUDIO_REFERENCE_ID", raising=False)
    monkeypatch.setenv("FISH_AUDIO_VOICE_ID", "saved-voice-id")
    monkeypatch.delenv("FISH_AUDIO_FORMAT", raising=False)
    monkeypatch.setenv("FISH_AUDIO_OUTPUT_FORMAT", "pcm")
    monkeypatch.setenv("FISH_AUDIO_SAMPLE_RATE", "24000")

    config = FishAudioConfig.from_env()
    payload = config.payload("Ji bilkul.")

    assert config.reference_id == "saved-voice-id"
    assert config.audio_mime_type == "audio/pcm"
    assert config.sample_rate == 24000
    assert payload["format"] == "pcm"
    assert payload["sample_rate"] == 24000


def test_provider_factories_select_fish_audio(monkeypatch):
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("SARA_TTS_PROVIDER", "fish-audio")
    monkeypatch.setenv("VOICE_TTS_PROVIDER", "fish-audio")
    monkeypatch.setenv("VOICE_STT_PROVIDER", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "deepgram-key")

    streaming = build_tts_provider()
    turn_based = build_voice_provider().tts

    assert isinstance(streaming, FallbackTTSStreamer)
    assert isinstance(streaming.primary, FishAudioStreamer)
    assert isinstance(turn_based, FallbackTTSProvider)
    assert isinstance(turn_based.primary, FishAudioTTSProvider)


def test_streaming_falls_back_before_any_primary_audio():
    import asyncio

    class Failed:
        name = "failed"
        audio_mime_type = "audio/mpeg"

        async def stream(self, _text):
            if False:
                yield b""
            raise RuntimeError("provider unavailable")

    class Working:
        name = "working"
        audio_mime_type = "audio/mpeg"

        async def stream(self, _text):
            yield b"fallback-audio"

    async def collect():
        provider = FallbackTTSStreamer(Failed(), Working())
        chunks = [chunk async for chunk in provider.stream("hello")]
        return provider, chunks

    provider, chunks = asyncio.run(collect())

    assert chunks == [b"fallback-audio"]
    assert provider.active_provider_name == "working"
