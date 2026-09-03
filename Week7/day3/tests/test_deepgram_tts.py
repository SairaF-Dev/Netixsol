import json
import urllib.parse

from sara_agent.deepgram_tts import DeepgramTTSConfig
from sara_agent.streaming_voice import (
    DeepgramTTSStreamer,
    FallbackTTSStreamer,
    build_tts_provider,
)
from sara_agent.voice import (
    DeepgramTTSProvider,
    FallbackTTSProvider,
    build_voice_provider,
)


def test_deepgram_tts_config_builds_flux_mp3_request(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.delenv("DEEPGRAM_TTS_MODEL", raising=False)
    monkeypatch.delenv("DEEPGRAM_TTS_ENCODING", raising=False)

    config = DeepgramTTSConfig.from_env()
    query = urllib.parse.parse_qs(
        urllib.parse.urlsplit(config.request_url).query
    )

    assert config.endpoint == "https://api.deepgram.com/v2/speak"
    assert config.headers()["Authorization"] == "Token test-key"
    assert config.audio_mime_type == "audio/mpeg"
    assert query["model"] == ["flux-priya-en"]
    assert query["encoding"] == ["mp3"]
    assert config.payload(" Ji bilkul. ") == {"text": "Ji bilkul."}


def test_turn_based_deepgram_tts_returns_audio(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"mp3-audio"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "sara_agent.voice.urllib.request.urlopen",
        fake_urlopen,
    )
    provider = DeepgramTTSProvider()

    assert provider.synthesize("Assalam-o-Alaikum") == b"mp3-audio"
    assert captured["payload"] == {"text": "Assalam-o-Alaikum"}
    assert "/v2/speak?" in captured["url"]


def test_provider_factories_select_deepgram_tts(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.setenv("SARA_TTS_PROVIDER", "deepgram")
    monkeypatch.setenv("VOICE_TTS_PROVIDER", "deepgram")
    monkeypatch.setenv("VOICE_STT_PROVIDER", "deepgram")
    monkeypatch.setenv("SARA_TTS_FALLBACK_PROVIDER", "edge-tts")

    streaming = build_tts_provider()
    turn_based = build_voice_provider().tts

    assert isinstance(streaming, FallbackTTSStreamer)
    assert isinstance(streaming.primary, DeepgramTTSStreamer)
    assert isinstance(turn_based, FallbackTTSProvider)
    assert isinstance(turn_based.primary, DeepgramTTSProvider)
