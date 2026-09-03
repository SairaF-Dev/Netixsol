from pathlib import Path


def test_live_voice_ui_contains_two_way_controls_and_no_legacy_copy():
    page = (
        Path(__file__).resolve().parents[1]
        / "streaming_voice_client.html"
    ).read_text(encoding="utf-8")

    assert "Two-way audio is live" in page
    assert "Roman UrduLish transcript" in page
    assert "Speak anytime to interrupt" in page
    assert 'id="speakerBtn"' in page
    assert 'id="audioRecovery"' in page
    assert 'id="audioTest"' in page
    assert "Sara speaker test" in page
    assert "speechSynthesis" in page
    assert "stt_reconnecting" in page
    assert "responsePending && !playbackStarted" in page
    assert "streaming Edge TTS" not in page
    assert "ðŸ" not in page
