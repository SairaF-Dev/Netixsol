from sara_agent.chatbot import SaraChatbot
from sara_agent.models import UserUnderstanding
from sara_agent.rag_bridge import RagBridge


class SequenceUnderstanding:
    def __init__(
        self,
        *values,
    ):
        self.values = iter(
            values
        )

    def understand(
        self,
        *args,
        **kwargs,
    ):
        return next(
            self.values
        )


class MinimalKnowledge:
    def resolve_locations(
        self,
        text,
        city_hint=None,
    ):
        return {}

    def list_cities(
        self,
        filters=None,
    ):
        return []

    def list_areas(
        self,
        city,
        filters=None,
    ):
        return []

    def execute_plan(
        self,
        plan,
        **kwargs,
    ):
        return []


def test_property_overview_without_selection_can_use_verified_rag():
    u = SequenceUnderstanding(
        UserUnderstanding(
            intent="property_details"
        )
    )

    bot = SaraChatbot(
        MinimalKnowledge(),
        u,
        rag_bridge=RagBridge(
            lambda question:
            "Verified project overview"
        ),
    )

    assert (
        bot.handle_message(
            "Tell me about Horizon Heights Apartment"
        )
        == "Verified project overview"
    )


def test_availability_is_refreshed_from_exact_property_record():
    class Knowledge(
        MinimalKnowledge
    ):
        def get_property(
            self,
            property_id,
        ):
            return {
                "property_id": property_id,
                "property_name": "Demo",
                "available": False,
            }

    u = SequenceUnderstanding(
        UserUnderstanding(
            intent="availability"
        )
    )

    bot = SaraChatbot(
        Knowledge(),
        u,
    )

    bot.memory.selected_property = {
        "property_id": "P-1",
        "property_name": "Demo",
        "available": True,
    }

    response = bot.handle_message(
        "Is it available?"
    )

    assert "available nahi" in response.casefold()
    assert (
        bot.memory
        .selected_property[
            "available"
        ]
        is False
    )


def test_payment_plan_is_read_from_structured_source_before_nlu():
    class Knowledge(
        MinimalKnowledge
    ):
        def get_property(
            self,
            property_id,
        ):
            return {
                "property_id": property_id,
                "property_name": "Demo",
            }

        def get_payment_plans(
            self,
            property_id,
        ):
            return [
                {
                    "plan_name": "Standard",
                    "summary": "20% down payment",
                    "status": "Active",
                }
            ]

    class MustNotRun:
        def understand(
            self,
            *args,
            **kwargs,
        ):
            raise AssertionError(
                "deterministic structured fact path should run first"
            )

    bot = SaraChatbot(
        Knowledge(),
        MustNotRun(),
    )

    bot.memory.selected_property = {
        "property_id": "P-1",
        "property_name": "Demo",
    }

    response = bot.handle_message(
        "payment plan kya hai?"
    )

    assert "Standard" in response
    assert "20% down payment" in response



def test_same_bot_serializes_concurrent_turns():
    import threading
    import time

    class TrackingUnderstanding:
        def __init__(self):
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()

        def understand(
            self,
            *args,
            **kwargs,
        ):
            with self.lock:
                self.active += 1
                self.max_active = max(
                    self.max_active,
                    self.active,
                )

            time.sleep(
                0.03
            )

            with self.lock:
                self.active -= 1

            return UserUnderstanding(
                intent="unknown"
            )

    service = TrackingUnderstanding()
    bot = SaraChatbot(
        MinimalKnowledge(),
        service,
    )

    threads = [
        threading.Thread(
            target=bot.handle_message,
            args=(
                f"complex unrelated request {index}",
            ),
        )
        for index in range(2)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert service.max_active == 1
