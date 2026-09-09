"""Focused multi-turn and preservation probes supplement the category expansion."""
from .catalog import reply, route, nlu
from .harness import expand


def extra_cases(name):
    if name == "returning_user":
        return expand("03_returning_user", [
            ("different_city", ["Karachi mein apartment chahiye", "ab Karachi dekhna hai", "show Karachi apartments"], reply("Pichli dafa", "Karachi", "purchase", empty=["response.properties"]), route("property_search", required={"city": "Karachi", "property_type": "Apartment"})),
            ("different_purpose", ["ab rent par chahiye", "rental ke options chahiye", "rent this time please"], reply("Pichli dafa", "city", empty=["response.properties"]), route("property_search", required={"purpose": "Rental"})),
        ], states=("returning",))
    if name == "search":
        out = []
        for field, phrases in [("budget", ["is se sasta", "cheaper than this", "kam price wala"]),
                               ("bedrooms", ["zyada bedrooms wala", "more bedrooms please", "is se zyada rooms"] )]:
            out += expand("04_search", [("compare_" + field, phrases, reply("comparison", empty=["response.properties"]), route("property_search", comparison={"field": field, "operator": "lt" if field == "budget" else "gt", "reference": "selected_property"}))], states=("shown", "selected"))
        out += expand("04_search", [("no_invention", ["kuch dikhao", "options bata dein", "show me something"], {"empty": ["required", "preferred", "excluded"]})], states=("new", "known", "mid_returning"), boundary="deterministic")
        out += expand("04_search", [("provider_omission_flexible_fastpath", ["budget flexible hai", "budget koi masla nahi", "no budget limit"], {"contains": {"relax": ["budget"]}})], states=("new", "known"), boundary="deterministic")
        return out
    if name == "location":
        out = expand("05_location", [("pagination_same_area", ["DHA mein aur options", "dha mein aor options", "more options in DHA"], reply("DHA", "aur koi", truthy=["saved.pending_expand_area"], preserve_prefs=True), {**route("property_search", required={"area": "DHA"}), "config": {"areas": ["DHA", "Gulberg"]}})], states=("shown",))
        out += expand("05_location", [("exact_phase", ["DHA Phase 6 mein", "DHA Phase 6 options", "show DHA Phase 6"], {"eq": {"status": 200, "prefs.area": "DHA Phase 6"}, "truthy": ["response.properties"]}, {**route("property_search", required={"area": "DHA Phase 6"}), "config": {"areas": ["DHA Phase 5", "DHA Phase 6", "DHA Phase 6 Extension"]}})], states=("known", "shown"))
        return out
    if name == "booking":
        pre = [{"message": "dha mein", "nlu": {"intent": "property_search", "required": {"area": "DHA"}}},
               {"message": "DHA Phase 6 mein", "nlu": {"intent": "property_search", "required": {"area": "DHA Phase 6"}}}]
        return expand("09_booking", [
            ("after_phase_resolution", ["pehli ki visit book kar dein", "first option visit please", "option 1 visit karni hai"], reply("date", "time", truthy=["saved.pending_action"]), {**route("schedule_visit", selected_index=0), "config": {"areas": ["DHA Phase 5", "DHA Phase 6"], "pre_turns": pre}}),
            ("invalid_id", ["appointment abc cancel kar do", "cancel booking abc", "visit abc cancel please"], reply("Appointment ID dobara", empty=["appointments"]), route("cancel_visit", appointment_id="abc")),
            ("reschedule_missing_time", ["meri appointment reschedule kar dein", "reschedule my visit", "visit ka time badalna hai"], reply("Nayi date", "time", empty=["appointments"]), route("reschedule_visit", appointment_id="$owned")),
        ], states=("known", "shown"))
    if name == "negation":
        out = []
        for field, value, phrases in [
            ("area", "DHA", ["DHA nahi chahiye", "nahi DHA nahi chahiye ab"]),
            ("purpose", "Rental", ["rent nahi chahiye", "rental nahi"]),
            ("amenities", "Gym", ["gym nahi chahiye", "no gym please"]),
            ("property_type", "Apartment", ["apartment nahi chahiye", "flat nahi chahiye"]),
        ]:
            out += expand("17_negation", [("preserve_exclusion_" + field, phrases,
                          {"contains": {f"excluded.{field}": [value]}, "excludes": {f"required.{field}": [value], f"preferred.{field}": [value]}},
                          {"nlu": {"intent": "property_search", "excluded": {field: [value]}}})], states=("new", "mid_returning"))
        return out
    if name == "frustration":
        return expand("18_frustration", [("no_results_next_step", ["phir koi result nahi, budget wahi hai", "yaar kuch mil bhi raha hai ya nahi", "same requirements, still no options", "bohat time waste ho gaya", "koi acha option dikha do"], reply("budget", "area", truthy=["saved.last_asked_broaden"], empty=["appointments", "response.properties"]), {**route("property_search"), "config": {"empty_inventory": True}})], states=("known", "shown"))
    if name == "language":
        pre = [{"message": "I want to buy in Lahore", "nlu": {"intent": "property_search", "required": {"purpose": "Purchase", "city": "Lahore"}}},
               {"message": "DHA mein 2 crore tak apartment chahiye", "nlu": {"intent": "property_search", "required": {"area": "DHA", "budget": 20000000, "property_type": "Apartment"}}}]
        return expand("14_language", [("english_urdu_english_flow", ["What is the price of the first option?", "How much is the first property?", "Please tell me the first property's price"], {"eq": {"status": 200}, "contains": {"response.message": ["PKR"]}, "excludes": {"response.message": ["ki price", "hai.", "batayein"]}}, {**route("property_details", selected_index=0), "config": {"pre_turns": pre}})], states=("new", "returning"))
    if name == "cross_cutting":
        return expand("20_cross_cutting", [("area_reorder_then_first", ["pehli pasand hai", "first option like please", "option 1 shortlist"], {"eq": {"status": 200, "event_ids": ["P-1"]}}, {**route(interaction_action="liked", selected_index=0), "config": {"split_areas": True, "pre_turns": [{"message": "DHA ke qareeb, area flexible hai", "nlu": {"intent": "property_search", "relax": ["area"]}}]}})], states=("known", "shown"))
    return []
