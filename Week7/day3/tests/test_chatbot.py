from sara_agent.chatbot import SaraChatbot
from sara_agent.models import UserUnderstanding
from sara_agent.understanding import UserUnderstandingService


class U:
    def __init__(self, values):
        self.values = iter(values)

    def understand(self, *args, **kwargs):
        return next(self.values)


class K:
    def execute_plan(self, plan, **kwargs):
        return [
            {
                "property_id": "1",
                "property_name": "First",
                "area": "A",
                "city": "Lahore",
                "bedrooms": 2,
                "purpose": "Rental",
                "price": 100000,
                "currency": "PKR",
            },
            {
                "property_id": "2",
                "property_name": "Second",
                "area": "A",
                "city": "Lahore",
                "bedrooms": 2,
                "purpose": "Rental",
                "price": 120000,
                "currency": "PKR",
            },
        ]

    def list_areas(self, city, filters=None):
        return ["A"]

    def list_cities(self, filters=None):
        return ["Lahore"]

    def resolve_locations(self, text, city_hint=None):
        value = text.casefold()
        out = {}

        if "lahore" in value or value.strip() == "search":
            out["city"] = "Lahore"

        if value.strip() in {"a", "search"}:
            out["area"] = "A"
            out["city"] = "Lahore"

        return out


def test_off_topic_request_is_blocked_before_tools_and_state_changes():
    class GuardedKnowledge(K):
        def __init__(self):
            self.executed = False

        def execute_plan(self, plan, **kwargs):
            self.executed = True
            raise AssertionError("off-topic request must not reach search")

    knowledge = GuardedKnowledge()
    bot = SaraChatbot(
        knowledge,
        U([UserUnderstanding(intent="off_topic")]),
    )
    bot.memory.required = {"city": "Lahore", "budget": 150000}

    response = bot.handle_message("Mujhe biryani ki recipe batao")

    assert "sirf real estate" in response
    assert knowledge.executed is False
    assert bot.memory.required == {"city": "Lahore", "budget": 150000}


def test_search_select_details_with_complete_required_flow():
    u = U(
        [
            UserUnderstanding(
                intent="property_search",
                required={
                    "city": "Lahore",
                    "area": "A",
                    "budget": 150000,
                    "bedrooms": 2,
                    "purpose": "Rental",
                },
            ),
            UserUnderstanding(
                intent="property_selection",
                selected_index=1,
                reference_type="second_result",
            ),
            UserUnderstanding(
                intent="property_details",
                reference_type="selected_property",
            ),
        ]
    )

    bot = SaraChatbot(K(), u)

    assert "First" in bot.handle_message("search")
    assert "Second" in bot.handle_message("dusri")
    assert "verified details" in bot.handle_message("details")


class RealWorldK:
    def __init__(self):
        self.last_plan = None

    def resolve_locations(self, text, city_hint=None):
        value = " ".join(text.casefold().split())
        out = {}

        if "lahore" in value:
            out["city"] = "Lahore"

        # Only exact verified spelling here. Fuzzy typo recovery should be
        # performed against verified choices by the chatbot edge layer.
        if "bahria town" in value:
            out["area"] = "Bahria Town"
            out["city"] = "Lahore"

        if "dha phase6" in value or "dha phase 6" in value:
            out["area"] = "DHA Phase 6"
            out["city"] = "Lahore"

        return out

    def list_cities(self, filters=None):
        return ["Lahore"]

    def list_areas(self, city, filters=None):
        return [
            "Bahria Town",
            "DHA Phase 6",
            "DHA Phase 8",
            "Gulberg III",
        ]

    def execute_plan(self, plan, **kwargs):
        self.last_plan = plan
        return [
            {
                "property_id": "BT-1",
                "property_name": "Verified Option",
                "area": plan.required.get("area"),
                "city": plan.required.get("city"),
                "property_type": plan.required.get("property_type"),
                "purpose": plan.required.get("purpose"),
                "price": 25000000,
                "currency": "PKR",
            }
        ]


def _deterministic_service():
    # Deterministic turns do not call this dummy object.
    return UserUnderstandingService(client=object())


def test_real_world_order_preserves_apartment_and_asks_budget_before_area():
    knowledge = RealWorldK()
    bot = SaraChatbot(
        knowledge,
        _deterministic_service(),
    )

    first = bot.handle_message(
        "Lahore mein apartment chahiye."
    )

    assert bot.memory.required["city"] == "Lahore"
    assert bot.memory.required["property_type"] == "Apartment"
    assert "rent" in first.casefold()
    assert "purchase" in first.casefold()

    second = bot.handle_message("purchase")
    assert "budget" in second.casefold()

    third = bot.handle_message("3 crore")
    assert "Bahria Town" in third
    assert "area" in third.casefold()


def test_fuzzy_verified_area_typo_is_recovered_without_hardcoded_mapping():
    knowledge = RealWorldK()
    bot = SaraChatbot(
        knowledge,
        _deterministic_service(),
    )

    bot.handle_message("Lahore mein apartment chahiye.")
    bot.handle_message("purchase")
    bot.handle_message("3 crore")

    response = bot.handle_message("Bagria Town")

    assert bot.memory.required["area"] == "Bahria Town"
    assert "Verified Option" in response


def test_phase_digit_is_not_misread_as_option_number():
    knowledge = RealWorldK()
    bot = SaraChatbot(
        knowledge,
        _deterministic_service(),
    )

    bot.handle_message("Lahore mein apartment chahiye.")
    bot.handle_message("purchase")
    bot.handle_message("3 crore")

    response = bot.handle_message("DHA phase6")

    assert bot.memory.required["area"] == "DHA Phase 6"
    assert "current verified list mein nahi" not in response.casefold()


def test_numeric_area_choice_still_works():
    knowledge = RealWorldK()
    bot = SaraChatbot(
        knowledge,
        _deterministic_service(),
    )

    bot.handle_message("Lahore mein apartment chahiye.")
    bot.handle_message("purchase")
    bot.handle_message("3 crore")

    bot.handle_message("2")
    assert bot.memory.required["area"] == "DHA Phase 6"


class UnsupportedLocationK:
    def resolve_locations(self, text, city_hint=None):
        return {}

    def list_cities(self, filters=None):
        return ["Lahore", "Islamabad"]

    def list_areas(self, city, filters=None):
        return []

    def execute_plan(self, plan, **kwargs):
        raise AssertionError("unsupported location must not reach property search")


def test_unverified_llm_location_is_not_committed():
    u = U(
        [
            UserUnderstanding(
                intent="property_search",
                required={"city": "Peshawar"},
            )
        ]
    )

    bot = SaraChatbot(
        UnsupportedLocationK(),
        u,
    )

    response = bot.handle_message(
        "Peshawar mein property chahiye"
    )

    assert "city" not in bot.memory.required
    assert "verified" in response.casefold()
