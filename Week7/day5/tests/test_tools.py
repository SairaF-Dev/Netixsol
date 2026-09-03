from __future__ import annotations

import pytest

from day5_langgraph.tools import ToolExecutor


class Repository:
    def search(self, **kwargs):
        self.search_args = kwargs
        return [{"property_id": "P-1", "property_name": "Pearl", "city": "Lahore"}]

    def get_property(self, property_id):
        return {"property_id": property_id, "property_name": "Pearl"}


class RAG:
    def answer(self, question):
        return {"answer": "Verified brochure answer", "results": [{"source": "brochure"}]}


@pytest.mark.asyncio
async def test_search_uses_day2_repository():
    repo = Repository()
    tools = ToolExecutor("http://day4", property_repository=repo)
    result = await tools.search_properties(location="Lahore", max_price=30_000_000)
    assert result["count"] == 1
    assert repo.search_args["city"] == "Lahore"
    assert repo.search_args["budget"] == 30_000_000


@pytest.mark.asyncio
async def test_property_details_are_not_hard_coded():
    tools = ToolExecutor("http://day4", property_repository=Repository())
    result = await tools.get_property_details(property_id="P-1")
    assert result == {"property_id": "P-1", "property_name": "Pearl"}


@pytest.mark.asyncio
async def test_rag_uses_day2_pipeline():
    tools = ToolExecutor("http://day4", rag_pipeline=RAG())
    result = await tools.search_rag("What is the payment plan?")
    assert result["answer"] == "Verified brochure answer"
