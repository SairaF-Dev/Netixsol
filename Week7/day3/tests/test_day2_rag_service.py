from sara_agent.day2_rag_service import (
    Day2RAGService,
    FALLBACK_ANSWER,
)


class FakePipeline:
    def __init__(
        self,
        **kwargs,
    ):
        self.kwargs = kwargs
        self.calls = []

    def answer(
        self,
        question,
    ):
        self.calls.append(
            question
        )

        if "price" in question.casefold():
            return {
                "answer": FALLBACK_ANSWER,
                "reason": "structured_fact_requires_postgresql",
            }

        return {
            "answer": "Verified semantic answer",
            "reason": "grounded_context",
        }


def test_day2_rag_service_is_lazy_and_uses_real_pipeline_contract(
    tmp_path,
):
    rag = tmp_path / "02_rag"
    docs = rag / "documents"
    docs.mkdir(
        parents=True
    )

    created = []

    def factory(
        **kwargs,
    ):
        pipeline = FakePipeline(
            **kwargs
        )
        created.append(
            pipeline
        )
        return pipeline

    service = Day2RAGService(
        day2_root=tmp_path,
        pipeline_factory=factory,
    )

    assert created == []
    assert service.status()["initialized"] is False

    assert (
        service.answer(
            "Tell me about the project"
        )
        == "Verified semantic answer"
    )

    assert len(created) == 1
    assert service.status()["initialized"] is True

    assert (
        service.answer(
            "What is the price?"
        )
        is None
    )


def test_day2_rag_service_converts_exact_fallback_to_none(
    tmp_path,
):
    rag = tmp_path / "02_rag"
    (rag / "documents").mkdir(
        parents=True
    )

    class Pipeline:
        def __init__(
            self,
            **kwargs,
        ):
            pass

        def answer(
            self,
            question,
        ):
            return {
                "answer": FALLBACK_ANSWER,
                "reason": "grounded_context",
            }

    service = Day2RAGService(
        day2_root=tmp_path,
        pipeline_factory=Pipeline,
    )

    assert service.answer(
        "unknown"
    ) is None
