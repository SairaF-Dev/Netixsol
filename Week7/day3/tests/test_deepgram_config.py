import json
import urllib.parse
import asyncio

from sara_agent.deepgram_config import DEFAULT_DEEPGRAM_KEYTERMS
from sara_agent.streaming_voice import DeepgramLiveSTT
from sara_agent.voice import DeepgramSTTProvider


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(
            {
                "results": {
                    "channels": [
                        {
                            "alternatives": [
                                {"transcript": "teen crore"}
                            ]
                        }
                    ]
                }
            }
        ).encode("utf-8")


def test_prerecorded_deepgram_defaults_to_urdulish_multi(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.delenv("DEEPGRAM_LANGUAGE", raising=False)
    monkeypatch.delenv("DEEPGRAM_KEYTERMS", raising=False)
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(
        "sara_agent.voice.urllib.request.urlopen",
        fake_urlopen,
    )
    provider = DeepgramSTTProvider()

    assert provider.transcribe(b"audio", "caller.mp3") == "teen crore"

    query = urllib.parse.parse_qs(
        urllib.parse.urlsplit(captured["url"]).query
    )
    assert query["model"] == ["nova-3"]
    assert query["language"] == ["multi"]
    assert query["keyterm"] == list(DEFAULT_DEEPGRAM_KEYTERMS)
    assert "teen crore" in query["keyterm"]
    assert "property purchase" in query["keyterm"]


def test_streaming_deepgram_uses_same_urdulish_config(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.delenv("DEEPGRAM_LANGUAGE", raising=False)
    monkeypatch.delenv("DEEPGRAM_KEYTERMS", raising=False)

    provider = DeepgramLiveSTT()

    assert provider.language == "multi"
    assert provider.keyterms == list(DEFAULT_DEEPGRAM_KEYTERMS)


def test_deepgram_language_and_keyterms_remain_configurable(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    monkeypatch.setenv("DEEPGRAM_LANGUAGE", "ur")
    monkeypatch.setenv("DEEPGRAM_KEYTERMS", "DHA Phase 6,three crore")

    provider = DeepgramSTTProvider()

    assert provider.language == "ur"
    assert provider.keyterms == ["DHA Phase 6", "three crore"]


def test_streaming_deepgram_reconnects_and_retries_audio(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    provider = DeepgramLiveSTT()
    sent = []

    class DroppedSocket:
        async def send(self, _audio):
            raise ConnectionResetError("socket dropped")

    class RestoredSocket:
        async def send(self, audio):
            sent.append(audio)

    provider._closed = False
    provider._ws = DroppedSocket()

    async def reconnect(_exc):
        provider._ws = RestoredSocket()

    provider._reconnect_after_drop = reconnect

    asyncio.run(provider.send_audio(b"pcm"))

    assert sent == [b"pcm"]
