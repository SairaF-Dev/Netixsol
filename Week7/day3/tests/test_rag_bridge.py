from sara_agent.rag_bridge import RagBridge


def test_rag_bridge_fails_closed_without_service():
    assert RagBridge().answer("booking policy?") is None


def test_rag_bridge_uses_injected_verified_service():
    bridge = RagBridge(
        lambda question: "Verified policy answer"
    )

    assert bridge.answer("booking policy?") == "Verified policy answer"
