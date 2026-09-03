from api import main as api_main


def test_liveness_does_not_construct_runtime(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "_runtime",
        None,
    )
    monkeypatch.setenv(
        "SARA_RAG_ENABLED",
        "1",
    )

    result = api_main.health()

    assert result["status"] == "ok"
    assert result["rag"]["enabled"] is True
    assert result["rag"]["initialized"] is False



def test_readiness_uses_dependency_checks(
    monkeypatch,
):
    class Runtime:
        def readiness(
            self,
        ):
            return {
                "database": {
                    "ready": True,
                    "error_type": None,
                },
                "rag": {
                    "enabled": True,
                    "ready": True,
                },
            }

    monkeypatch.setattr(
        api_main,
        "get_runtime",
        lambda: Runtime(),
    )
    monkeypatch.setenv(
        "SARA_RAG_REQUIRED",
        "1",
    )

    result = api_main.ready()

    assert result["status"] == "ready"
    assert result["database"]["ready"] is True
