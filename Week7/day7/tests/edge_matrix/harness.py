"""Execute public NLU/HTTP entry points; never replace production repairs or routes.

NLU omission probes supply an empty provider extraction, not the expected answer.
Route probes explicitly supply semantic NLU fixtures and exercise real turn(),
planner, policy, reference resolution, schemas and authenticated callbacks.
"""
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

OBSERVATIONS = []


@dataclass
class Case:
    category: str
    seed: str
    message: str
    state: str
    boundary: str
    expected: dict
    nlu: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    variant: str = "base"

    @property
    def id(self):
        return f"{self.seed}--{self.state}--{self.variant}"


def expand(category, specs, states=("new", "returning", "mid_new", "mid_returning"), boundary="repair"):
    """Each explicit spelling/mix variant is crossed with relevant state, never padded."""
    result = []
    for spec in specs:
        seed, phrases, expected, *options = spec
        opts = options[0] if options else {}
        for index, message in enumerate(phrases):
            for state in opts.get("states", states):
                result.append(Case(category, seed, message, state,
                                   opts.get("boundary", boundary), deepcopy(expected),
                                   deepcopy(opts.get("nlu", {})), deepcopy(opts.get("config", {})),
                                   f"phrase{index + 1}"))
    assert len({c.id for c in result}) == len(result)
    return result


def context_for(state):
    required = {}
    if state in ("returning", "mid_returning", "known", "booking"):
        required = {"city": "Lahore", "area": "DHA", "purpose": "Purchase", "budget": 20000000}
    return {"required": required, "preferred": {}, "excluded": {},
            "recent_turns": [{"intent": "greeting"}] if state.startswith("mid") else [],
            "pending_action": {"intent": "schedule_visit"} if state == "booking" else None,
            "timezone": "Asia/Karachi", "current_date": "2030-01-01T09:00:00+05:00"}


def run_nlu(case, monkeypatch):
    import sara_agent.understanding as module
    from sara_agent.understanding import UserUnderstandingService
    # Isolate from developer .env and never create a network client.
    monkeypatch.setattr(module, "load_dotenv", lambda *a, **kw: None)
    service = UserUnderstandingService(client=SimpleNamespace(), deterministic_first=case.boundary != "repair")
    service.max_message_length = 2000
    calls = []
    def provider(payload):
        calls.append(deepcopy(payload))
        if case.config.get("provider_failure"):
            raise RuntimeError("offline provider unavailable")
        return deepcopy(case.nlu or {"intent": "unknown"})
    monkeypatch.setattr(service, "_call_llm", provider)
    context = context_for(case.state)
    if case.config.get("malformed_context"):
        context = case.config["malformed_context"]
    try:
        parsed = service.understand(case.message, context=context)
        actual = asdict(parsed)
        actual["raw_length"] = len(parsed.raw_message)
        actual["raw_message"] = parsed.raw_message
    except Exception as exc:
        actual = {"exception": type(exc).__name__, "error": str(exc)}
    actual["provider_calls"] = len(calls)
    return actual, {"context": context, "provider_reply": case.nlu or {"intent": "unknown"},
                    "deterministic_first": service.deterministic_first}


def run_chat(case, monkeypatch):
    from sara_agent.models import UserUnderstanding, ComparisonRequest
    from sara_agent.understanding import UnderstandingError
    from test_phase9_chat import chat, setup
    from test_web_api import CUSTOMER_ID
    from web_api.services import RecommendationSessionExpired
    web, svc, nlu = setup()
    cfg = case.config
    pref = svc.customers.preferences
    if case.state in ("new", "mid_new", "history_empty"):
        for key in ("city", "area", "purpose", "budget_max", "bedrooms", "property_type"):
            setattr(pref, key, None)
        pref.amenities = []
    if case.state in ("returning", "mid_returning", "pending", "scope") or case.state.startswith("history"):
        nlu.test_returning = True
    if cfg.get("cities"):
        svc.properties.list_available_cities = lambda: list(cfg["cities"])
    if cfg.get("split_areas"):
        svc.properties.rows[0]["area"] = "DHA"
        svc.properties.rows[1]["area"] = "Gulberg"
    if case.state == "single":
        svc.properties.rows = svc.properties.rows[:1]
    if case.state == "history_single":
        svc.interactions.events = [{"customer_id": CUSTOMER_ID, "property_id": svc.properties.rows[0]["property_id"], "action": "shown"}]
    elif case.state == "history_multiple":
        svc.interactions.events = [{"customer_id": CUSTOMER_ID, "property_id": row["property_id"], "action": "shown"} for row in svc.properties.rows]
    elif case.state == "history_incomplete":
        pref.budget_max = None
    elif case.state == "history_empty":
        svc.properties.rows = []
    for key, value in cfg.get("prefs", {}).items():
        setattr(pref, key, value)
    cid = None
    first = None
    if case.state in ("mid_new", "mid_returning", "pending", "scope"):
        nlu.result = UserUnderstanding(intent="greeting")
        first = chat(web, message="hi").json()
        cid = first["conversation_id"]
        if case.state == "mid_returning":
            nlu.result = UserUnderstanding(intent="unknown")
            chat(web, cid, "haan wahi chahiye")
        if case.state == "scope":
            nlu.result = UserUnderstanding(intent="unknown")
            chat(web, cid, "aur options dekhna chahungi")
    elif case.state in ("shown", "selected", "single", "filtered", "stale", "expired", "denied", "unavailable", "changed", "abandoned", "resumed", "older"):
        first = chat(web).json()
        assert "properties" in first, f"fixture search failed: {first}"
        cid = first["conversation_id"]
        saved = svc.chat.store.rows[cid][2]
        if case.state in ("selected", "unavailable"):
            saved["selected"] = first["properties"][0]["property_id"]
        if case.state == "unavailable":
            for row in svc.properties.rows:
                row["available"] = False
        if case.state == "stale":
            saved.pop("recommendation_session_id", None)
        if case.state == "expired":
            def expired(*a, **kw):
                raise RecommendationSessionExpired()
            svc.sessions.get = expired
        if case.state == "denied":
            svc.chat.store.expired.add(cid)
        if case.state == "changed":
            nlu.result = UserUnderstanding(intent="unknown", required={"budget": 40000000})
            chat(web, cid, "ab budget 4 crore hai")
        if case.state == "abandoned":
            saved["pending_action"] = {"intent": "schedule_visit", "property_id": first["properties"][0]["property_id"]}
        if case.state == "resumed":
            saved["recent_turns"] = [{"intent": "property_search"}] * 6
        if case.state == "older":
            svc.properties.rows = svc.properties.rows[:1]
            nlu.result = UserUnderstanding(intent="property_search")
            chat(web, cid, "naye options dikha dein")
        if case.state == "filtered":
            nlu.result = UserUnderstanding(intent="property_details")
            subset = chat(web, cid, "DHA mein kya options hain").json()
            assert len(subset.get("properties", [])) == 1, f"fixture subset failed: {subset}"
    # Inventory variants belong to the tested turn, after a valid shown-results setup.
    if cfg.get("areas") is not None:
        svc.properties.list_available_areas = lambda **kw: list(cfg["areas"])
    if cfg.get("empty_inventory"):
        svc.properties.rows = []
    if cfg.get("pending_booking") and cid:
        svc.chat.store.rows[cid][2]["pending_action"] = {"intent": "schedule_visit", "property_id": first["properties"][0]["property_id"]}
    pre_steps = []
    for step in cfg.get("pre_turns", []):
        nlu.result = UserUnderstanding(**step["nlu"])
        response = chat(web, cid, step["message"])
        assert response.status_code == 200, f"pre-turn setup failed: {response.text}"
        data = response.json()
        cid = data["conversation_id"]
        pre_steps.append({"input": step, "response": data})
    aid = str(uuid4())
    svc.auth.repository.owns_appointment = lambda user, appointment: str(appointment) == aid
    svc.auth.repository.own_appointment = lambda *a: None
    async def gateway(method, path, payload=None):
        svc.appointments.calls.append((method, path, payload))
        return (201 if method == "POST" else 200), {"appointment": {"appointment_id": aid, "status": "confirmed"}}
    svc.appointments.request = gateway
    semantic = deepcopy(case.nlu)
    if semantic.get("appointment_id") == "$owned":
        semantic["appointment_id"] = aid
    if semantic.get("interaction_property_id") == "$first" and first:
        semantic["interaction_property_id"] = first["properties"][0]["property_id"]
    if cfg.get("nlu_error"):
        nlu.result = UnderstandingError("unsupported_script")
    else:
        model_values = deepcopy(semantic)
        if isinstance(model_values.get("comparison"), dict):
            model_values["comparison"] = ComparisonRequest(**model_values["comparison"])
        nlu.result = UserUnderstanding(**model_values)
    before = deepcopy(svc.chat.store.rows[cid][2]) if cid else {}
    before_prefs = asdict(pref)
    event_start = len(svc.interactions.events)
    if case.boundary == "turn":
        async def forbidden(*a, **kw):
            raise AssertionError("empty input must not invoke callbacks")
        data = asyncio.run(svc.chat.turn(SimpleNamespace(customer_id=CUSTOMER_ID, user_id="ua"),
                          SimpleNamespace(conversation_id=cid, message=case.message),
                          forbidden, forbidden, forbidden, forbidden))
        status = 200
    else:
        response = chat(web, cid, case.message)
        status = response.status_code
        try:
            data = response.json()
        except ValueError:
            data = {"body": response.text}
    current_cid = data.get("conversation_id", cid)
    after = deepcopy(svc.chat.store.rows[current_cid][2]) if current_cid in svc.chat.store.rows else {}
    actual = {"status": status, "response": data, "saved": after, "prefs": asdict(pref),
              "events": deepcopy(svc.interactions.events[event_start:]),
              "appointments": deepcopy(svc.appointments.calls), "searches": deepcopy(svc.properties.search_calls),
              "before": before, "before_prefs": before_prefs, "pre_steps": pre_steps}
    if cfg.get("duplicate"):
        response2 = chat(web, current_cid, case.message)
        actual["duplicate_status"] = response2.status_code
    if cfg.get("follow_time"):
        nlu.result = UserUnderstanding(intent="schedule_visit", starts_at="2030-01-02T10:00:00+05:00")
        follow = chat(web, current_cid, "2 January 2030 subah 10 baje").json()
        actual["follow"] = follow
        actual["appointments"] = deepcopy(svc.appointments.calls)
    actual["event_ids"] = [e.get("property_id") for e in actual["events"] if e.get("action") != "shown"]
    actual["booked_ids"] = [c[2].get("property_id") for c in actual["appointments"] if c[0] == "POST" and c[2]]
    return actual, {"saved_before": before, "preferences_before": before_prefs, "semantic_fixture": semantic}


def value_at(actual, path):
    value = actual
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def violations(case, actual):
    failures = []
    for path, expected in case.expected.get("eq", {}).items():
        value = value_at(actual, path)
        if value != expected:
            failures.append(f"{path}: expected {expected!r}, actual {value!r}")
    for path, tokens in case.expected.get("contains", {}).items():
        value = value_at(actual, path)
        for token in tokens:
            if str(token).casefold() not in str(value).casefold():
                failures.append(f"{path}: missing {token!r}; actual {value!r}")
    for path, tokens in case.expected.get("excludes", {}).items():
        value = value_at(actual, path)
        for token in tokens:
            if str(token).casefold() in str(value).casefold():
                failures.append(f"{path}: must not contain {token!r}; actual {value!r}")
    for path in case.expected.get("truthy", []):
        if not value_at(actual, path):
            failures.append(f"{path}: expected nonempty, actual {value_at(actual, path)!r}")
    for path in case.expected.get("empty", []):
        if value_at(actual, path):
            failures.append(f"{path}: expected empty, actual {value_at(actual, path)!r}")
    for path, choices in case.expected.get("one_of", {}).items():
        if value_at(actual, path) not in choices:
            failures.append(f"{path}: expected one of {choices!r}, actual {value_at(actual, path)!r}")
    if case.expected.get("preserve_prefs") and actual.get("prefs") != actual.get("before_prefs"):
        failures.append("preferences changed during unrelated/pending interaction")
    return failures


def execute(case, monkeypatch):
    try:
        actual, context = run_nlu(case, monkeypatch) if case.boundary in ("repair", "deterministic") else run_chat(case, monkeypatch)
        failures = violations(case, actual)
    except Exception as exc:
        actual, context = {"harness_exception": type(exc).__name__, "error": str(exc)}, {}
        failures = [f"harness error (not a confirmed product gap): {type(exc).__name__}: {exc}"]
    OBSERVATIONS.append({**asdict(case), "id": case.id, "effective_context": context,
                         "actual": actual, "violations": failures,
                         "outcome": "harness_error" if "harness_exception" in actual else "fail" if failures else "pass"})
    assert not failures, json.dumps({"input": case.message, "state": case.state, "boundary": case.boundary,
                                    "violations": failures}, ensure_ascii=False, indent=2)


def write_report(target, exitstatus):
    target.mkdir(parents=True, exist_ok=True)
    rows = sorted(OBSERVATIONS, key=lambda row: (row["category"], row["id"]))
    (target / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    matrix = [{k: v for k, v in row.items() if k not in ("actual", "violations", "outcome")} for row in rows]
    (target / "matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    counts = Counter(r["outcome"] for r in rows)
    lines = ["# UrduLish conversational matrix — observed results", "",
             f"Executed {len(rows)} cases: {dict(counts)}. pytest exit status: {exitstatus}.", "",
             "Offline scope: `repair` runs public understand() with a neutral omitted-field provider response; "
             "`deterministic` enables the real fast path with the same offline fallback. Neither measures live LLM accuracy. "
             "`http` supplies explicit semantic NLU fixtures and exercises ChatAdapter.turn() through the authenticated API. "
             "`turn` bypasses HTTP validation only to test the adapter's empty-input behavior.", "",
             "Failures are observed contract mismatches, not automatically approved fixes. Repair failures describe resilience "
             "to provider omissions; live semantic interpretation may differ. No production changes are part of this pass.", "",
             "| Category | Cases | Pass | Fail | Harness errors |", "|---|---:|---:|---:|---:|"]
    for category in sorted({r["category"] for r in rows}):
        group = [r for r in rows if r["category"] == category]
        c = Counter(r["outcome"] for r in group)
        lines.append(f"| {category} | {len(group)} | {c['pass']} | {c['fail']} | {c['harness_error']} |")
    lines += ["", "## Failure families", "", "Each family groups one seed and test boundary; full individual inputs, effective state, "
              "expected checks, actual responses, mutations and side effects are in results.json and failures.md.", ""]
    groups = {}
    for row in rows:
        if row["outcome"] != "pass":
            groups.setdefault((row["category"], row["seed"], row["boundary"]), []).append(row)
    for (category, seed, boundary), group in groups.items():
        sample = group[0]
        lines += [f"- **{category}/{seed}** ({boundary}; {len(group)} cases): `{sample['message'][:160]}` — "
                  + sample["violations"][0].replace("\n", " ")[:600]]
    root = Path(__file__).resolve().parents[3]
    lines += ["", "## Production file fingerprints", ""]
    for relative in ("day7/web_api/chat.py", "day3/src/sara_agent/understanding.py"):
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        lines.append(f"- `{relative}`: `{digest}`")
    (target / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    details = ["# Individual failing cases", ""]
    for row in rows:
        if row["outcome"] == "pass":
            continue
        details += [f"## {row['category']}/{row['id']}", "", f"Boundary: {row['boundary']}; state: {row['state']}", "",
                    "```json", json.dumps({k: row[k] for k in ("message", "effective_context", "expected", "actual", "violations")},
                                          ensure_ascii=False, indent=2, default=str), "```", ""]
    (target / "failures.md").write_text("\n".join(details), encoding="utf-8")
