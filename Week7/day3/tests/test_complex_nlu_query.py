import os
import pytest
from sara_agent.understanding import UnderstandingError, UserUnderstandingService


@pytest.fixture
def deterministic_service(monkeypatch):
    service = UserUnderstandingService(client=object())

    def unexpected_llm(payload):
        pytest.fail("deterministic input must not call the LLM")

    monkeypatch.setattr(service, "_call_llm", unexpected_llm)
    return service


@pytest.mark.parametrize("message", [
    "hi", "hii", "hiii", "hello", "helo", "hallo", "hey", "heyy", "yo",
    "salam", "salaam", "assalam o alaikum", "asalam alaikum",
    "assalamualaikum", "aoa", "a.o.a", "good morning", "good evening",
    "good afternoon", "  HELLO!!!  ", "Good   Morning!", "A.O.A.",
])
def test_greeting_only_skips_llm(deterministic_service, message):
    result = deterministic_service.understand(message)
    assert result.intent == "greeting"
    assert result.raw_message == message.strip()
    assert result.required == {}
    assert result.preferred == {}


def test_greeting_with_search_preserves_slots(deterministic_service, monkeypatch):
    calls = []

    def search_llm(payload):
        calls.append(payload)
        return {
            "intent": "property_search",
            "required": {"property_type": "Apartment", "bedrooms": 3, "area": "DHA"},
            "preferred": {},
        }

    monkeypatch.setattr(deterministic_service, "_call_llm", search_llm)
    result = deterministic_service.understand(
        "hi mujhe 3 bed apartment chahiye DHA mein"
    )
    baseline = deterministic_service.understand(
        "mujhe 3 bed apartment chahiye DHA mein"
    )
    assert result.intent != "greeting"
    assert result.required == baseline.required
    assert result.preferred == baseline.preferred
    extracted = {**result.preferred, **result.required}
    assert extracted["property_type"] == "Apartment"
    assert extracted["bedrooms"] == 3
    assert "DHA" in extracted["area"]
    assert calls[0]["current_message"] == "hi mujhe 3 bed apartment chahiye DHA mein"


def test_repeated_greeting_is_context_independent(deterministic_service):
    first = deterministic_service.understand("salam", context={"turn_count": 0})
    later = deterministic_service.understand("salam", context={
        "turn_count": 8,
        "required": {"city": "Lahore", "property_type": "Apartment"},
    })
    assert first.intent == "greeting"
    assert later == first


@pytest.mark.parametrize("message, relax", [
    ("haan", []), ("theek hai", []), ("budget flexible", ["budget"]),
    ("sab areas", ["area"]), ("flexible hai", ["area"]),
])
def test_existing_exact_branches_preserved(deterministic_service, message, relax):
    result = deterministic_service._deterministic_understanding(message, context={})
    assert result.intent == "property_search"
    assert result.relax == relax
    assert deterministic_service.understand(message).intent == "property_search"


@pytest.mark.parametrize("message", [
    "مجھے مکان چاہیے", "你好世界", "Здравствуйте",
])
@pytest.mark.parametrize("deterministic_first", [True, False])
def test_unsupported_script_rejected(deterministic_service, message, deterministic_first):
    deterministic_service.deterministic_first = deterministic_first
    with pytest.raises(UnderstandingError, match="^unsupported_script$"):
        deterministic_service.understand(message)


def test_unsupported_script_preserves_deterministic_result(deterministic_service):
    result = deterministic_service.understand("你好世界你好世界你好世界 flexible hai")
    assert result.intent == "property_search"
    assert result.relax == ["area"]


@pytest.mark.parametrize("message", [
    "你好世界 123", "你好世界 ۱۲۳", "你好世界你好 budget", "你好 hi there",
])
def test_script_guard_preserves_llm_route(deterministic_service, monkeypatch, message):
    calls = []

    def fake_llm(payload):
        calls.append(payload)
        return {"intent": "unknown"}

    monkeypatch.setattr(deterministic_service, "_call_llm", fake_llm)
    monkeypatch.setattr(deterministic_service, "_deterministic_understanding", lambda **kwargs: None)
    deterministic_service.understand(message)
    assert len(calls) == 1


def test_complex_multi_field_query_nlu_extraction():
    """
    Task 5 Regression Test: Verify complex multi-field query extracts accurately
    without falling back to deterministic parsing or raising JSON errors.
    """
    service = UserUnderstandingService()
    assert service.model == os.getenv("SARA_LLM_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))

    context = {
        "city": "Islamabad",
        "bedrooms": 3,
        "property_type": "Plot",
        "purpose": "purchase",
        "budget": 40000000,
    }

    message = (
        "Mujhe DHA ya Bahria Town Islamabad mein 4 bedroom ghar chahiye, "
        "budget 50-60 million, saath mein swimming pool aur servant quarter bhi ho, "
        "purpose investment hai"
    )

    res = service.understand(message, context=context)
    assert res is not None
    assert res.intent in ("property_search", "recommendation")
    assert res.needs_clarification is False

    # Verify extracted slots from required/preferred
    extracted = {**res.preferred, **res.required}
    assert extracted.get("city") == "Islamabad"
    assert extracted.get("bedrooms") == 4
    assert extracted.get("property_type") in ("House", "Villa", None)
    assert extracted.get("budget") in (50000000, 60000000, "50-60 million", 50000000.0, 60000000.0)

    # Area (DHA or Bahria Town)
    extracted_area = str(extracted.get("area", ""))
    assert "DHA" in extracted_area or "Bahria" in extracted_area

    # Amenities (swimming pool / servant quarter)
    amenities = extracted.get("amenities", [])
    if isinstance(amenities, list):
        amenities_str = " ".join([str(a).lower() for a in amenities])
        assert "swimming" in amenities_str or "pool" in amenities_str or "servant" in amenities_str
