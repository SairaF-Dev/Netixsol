from datetime import datetime, timezone

from vapi_integration.learning import LearningRecordStore, build_learning_record


def test_learning_record_redacts_contact_details():
    record = build_learning_record(
        call_id="call-1",
        caller_phone="+923001234567",
        created_at=datetime.now(timezone.utc),
        turn_count=1,
        messages=[
            {"role": "user", "content": "Ali ka email ali@example.com hai"},
            {"role": "assistant", "content": "Phone +923001234567 note kar liya."},
        ],
        summary="Caller ali@example.com ne call ki.",
    )

    serialized = str(record)
    assert "ali@example.com" not in serialized
    assert "+923001234567" not in serialized
    assert "[EMAIL]" in serialized
    assert "[PHONE]" in serialized
    assert record["review_status"] == "unreviewed"


def test_learning_store_is_disabled_by_default(tmp_path):
    store = LearningRecordStore(str(tmp_path / "records.jsonl"), enabled=False)
    store.record(
        call_id="call-1",
        caller_phone="unknown",
        created_at=datetime.now(timezone.utc),
        turn_count=0,
        messages=[],
    )

    assert not (tmp_path / "records.jsonl").exists()
