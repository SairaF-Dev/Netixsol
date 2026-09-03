from sara_agent.transcript_normalizer import normalize_transcript


def test_multilingual_deepgram_transcript_is_parser_ready():
    transcript = (
        "Lahore main property purchase high. "
        "Budget teen crore high."
    )

    assert normalize_transcript(transcript) == (
        "Lahore mein property purchase hai. "
        "Budget 3 crore hai."
    )


def test_roman_repairs_do_not_change_real_english_high_phrase():
    transcript = "High ROI chahiye aur budget char crore high."

    assert normalize_transcript(transcript) == (
        "High ROI chahiye aur budget 4 crore hai."
    )


def test_first_person_main_is_not_changed_globally():
    assert normalize_transcript("main rent ke liye dekh raha hoon") == (
        "main rent ke liye dekh raha hoon"
    )


def test_devanagari_deepgram_output_becomes_roman_urdulish():
    assert normalize_transcript(
        "यार मुझे DHA टेन सिक्स में प्रॉपर्टी चाहिए."
    ) == "yaar mujhe DHA Phase 6 mein property chahiye."


def test_unknown_devanagari_is_transliterated_not_sent_to_ui():
    normalized = normalize_transcript("जिला Hall में property चाहिए.")

    assert normalized == "jilaa Hall mein property chahiye."
    assert not any("\u0900" <= char <= "\u097f" for char in normalized)
