from sara_agent.voice import ElevenLabsTTSProvider


class _TextToSpeech:
    def __init__(self):
        self.request = None

    def convert(self, **kwargs):
        self.request = kwargs
        return iter((b"first", b"second"))


class _Client:
    def __init__(self):
        self.text_to_speech = _TextToSpeech()


def test_elevenlabs_turn_provider_uses_current_sdk(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-1")
    monkeypatch.setenv("ELEVENLABS_MODEL_ID", "model-1")
    monkeypatch.setenv(
        "ELEVENLABS_OUTPUT_FORMAT",
        "mp3_44100_128",
    )
    client = _Client()

    provider = ElevenLabsTTSProvider(client=client)

    assert provider.synthesize(" Ji bilkul. ") == b"firstsecond"
    assert client.text_to_speech.request == {
        "text": "Ji bilkul.",
        "voice_id": "voice-1",
        "model_id": "model-1",
        "output_format": "mp3_44100_128",
    }


def test_elevenlabs_turn_provider_rejects_empty_text():
    provider = ElevenLabsTTSProvider(client=_Client())

    try:
        provider.synthesize("  ")
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:
        raise AssertionError("empty text should be rejected")
