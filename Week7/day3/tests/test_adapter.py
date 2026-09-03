from sara_agent.day2_adapter import Day2Adapter
from sara_agent.models import QueryPlan

class Repo:
    def search(self,**kwargs):
        return [
            {"property_name":"A","area":"Alpha Phase 1","city":"Lahore","price":100},
            {"property_name":"B","area":"Beta Town","city":"Lahore","price":120},
            {"property_name":"C","area":"Gamma","city":"Lahore","price":140},
        ]
    def get_cheaper_alternatives(self,**kwargs): return self.search()
class Rec:
    def recommend(self,**kwargs): return []

def test_generic_exclusion_has_no_business_name_dependency():
    a=Day2Adapter(Repo(),Rec())
    p=QueryPlan(required={"city":"Lahore"},excluded={"area":["Alpha","Beta"]})
    names=[x["property_name"] for x in a.execute_plan(p)]
    assert names==["C"]

def test_numeric_comparison_gt():
    a=Day2Adapter(Repo(),Rec())
    p=QueryPlan(required={"city":"Lahore"},comparison_field="price",comparison_operator="gt",comparison_value=110)
    assert [x["property_name"] for x in a.execute_plan(p)]==["B","C"]


class LocationRepo:
    def search(self, **kwargs):
        return [
            {"property_name": "A", "area": "Bahria Town", "city": "Lahore", "price": 100},
            {"property_name": "B", "area": "DHA Phase 6", "city": "Lahore", "price": 120},
            {"property_name": "C", "area": "F-10", "city": "Islamabad", "price": 140},
        ]


def test_verified_location_resolver_handles_safe_typos():
    adapter = Day2Adapter(LocationRepo(), Rec())

    assert adapter.resolve_locations("Lahor mein")["city"] == "Lahore"

    resolved = adapter.resolve_locations(
        "Bagria Town",
        city_hint="Lahore",
    )
    assert resolved["area"] == "Bahria Town"


def test_verified_location_resolver_does_not_guess_ambiguous_prefix():
    adapter = Day2Adapter(LocationRepo(), Rec())

    resolved = adapter.resolve_locations(
        "DHA",
        city_hint="Lahore",
    )

    # "DHA" should not be expanded to a phase by guesswork.
    assert resolved.get("area") is None
