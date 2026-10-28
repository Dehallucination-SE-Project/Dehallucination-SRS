
import json
import sqlite3

import pytest

from audit_trail import AuditTrail


def test_accepted_request_event_is_persisted(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    event = trail.record_request_accepted(
        "request-123",
        {"input_length": 25},
    )

    events = trail.get_events("request-123")

    assert len(events) == 1
    assert events[0]["event_id"] == event["event_id"]
    assert events[0]["request_id"] == "request-123"
    assert events[0]["action"] == "request_accepted"
    assert events[0]["actor"] == "system"
    assert events[0]["details"] == {"input_length": 25}
    assert events[0]["timestamp"].endswith("+00:00")


def test_final_result_event_is_persisted(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    result = {
        "status": "completed",
        "verdict": "Supported",
    }

    event = trail.record_final_result("request-123", result)

    assert event["action"] == "verification_completed"
    assert event["details"] == {"result": result}
    assert trail.get_events("request-123")[0]["details"]["result"] == result


def test_events_are_persisted_across_instances(tmp_path):
    db_path = tmp_path / "audit.db"

    first = AuditTrail(db_path)
    first.record_request_accepted("request-456")

    second = AuditTrail(db_path)

    assert len(second.get_events("request-456")) == 1


def test_events_are_separated_by_request_id(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    trail.record_request_accepted("request-A")
    trail.record_request_accepted("request-B")

    assert len(trail.get_events("request-A")) == 1
    assert len(trail.get_events("request-B")) == 1
    assert trail.get_events("missing-request") == []


def test_event_has_unique_id(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    first = trail.record_request_accepted("request-123")
    second = trail.record_request_accepted("request-123")

    assert first["event_id"] != second["event_id"]


@pytest.mark.parametrize(
    "request_id",
    ["", "   ", None, 123],
)
def test_invalid_request_id_is_rejected(tmp_path, request_id):
    trail = AuditTrail(tmp_path / "audit.db")

    with pytest.raises(ValueError):
        trail.record_request_accepted(request_id)


@pytest.mark.parametrize("action", ["", "   ", None])
def test_invalid_action_is_rejected(tmp_path, action):
    trail = AuditTrail(tmp_path / "audit.db")

    with pytest.raises(ValueError):
        trail.record_event("request-123", action=action)


def test_non_dictionary_details_are_rejected(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    with pytest.raises(TypeError):
        trail.record_event(
            "request-123",
            action="request_accepted",
            details=["not", "a", "dictionary"],
        )


def test_non_json_serializable_details_are_rejected(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    with pytest.raises(ValueError):
        trail.record_event(
            "request-123",
            action="request_accepted",
            details={"invalid": object()},
        )


def test_event_is_stored_as_a_database_record(tmp_path):
    db_path = tmp_path / "audit.db"
    trail = AuditTrail(db_path)
    trail.record_request_accepted("request-123")

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT request_id, action, details
            FROM audit_events
            WHERE request_id = ?
            """,
            ("request-123",),
        ).fetchone()

    assert row is not None
    assert row[0] == "request-123"
    assert row[1] == "request_accepted"
    assert json.loads(row[2]) == {}


def test_final_result_must_be_a_dictionary(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")

    with pytest.raises(TypeError):
        trail.record_final_result("request-123", ["invalid"])
