"""Regression tests for UTF-8 and multilingual text round-trips."""

import pytest
from fastapi.testclient import TestClient

import main
from audit_trail import AuditTrail
from report_store import ReportStore
from review_queue import ReviewQueue


MULTILINGUAL_TEXT = "Café — नमस्ते — こんにちは — مرحبًا — 你好 — 😀"


@pytest.fixture
def unicode_client(tmp_path, monkeypatch):
    """Isolate SQLite stores so Unicode tests do not touch application data."""
    monkeypatch.setattr(
        main,
        "report_store",
        ReportStore(tmp_path / "unicode-reports.db"),
    )
    monkeypatch.setattr(
        main,
        "audit_trail",
        AuditTrail(tmp_path / "unicode-audit.db"),
    )
    monkeypatch.setattr(
        main,
        "review_queue",
        ReviewQueue(tmp_path / "unicode-reviews.db"),
    )
    return TestClient(main.app)


def test_verify_api_round_trips_multilingual_input(unicode_client):
    response = unicode_client.post(
        "/api/v1/verify",
        json={"input_text": MULTILINGUAL_TEXT},
    )

    assert response.status_code == 202
    assert response.content.decode("utf-8")
    assert MULTILINGUAL_TEXT.encode("utf-8") in response.content
    assert response.json()["input_text"] == MULTILINGUAL_TEXT


def test_report_api_round_trips_multilingual_content_through_sqlite(
    unicode_client,
):
    request_id = "unicode-report-001"
    payload = {
        "claims": [
            {
                "claim_id": "claim-unicode-001",
                "text": MULTILINGUAL_TEXT,
                "verdict": "Supported",
                "evidence": [
                    {
                        "source_id": "source-unicode-001",
                        "label": MULTILINGUAL_TEXT,
                        "title": MULTILINGUAL_TEXT,
                    }
                ],
            }
        ],
        "risk_summary": {"explanation": MULTILINGUAL_TEXT},
    }

    created = unicode_client.post(
        f"/api/v1/reports/{request_id}",
        json=payload,
    )
    retrieved = unicode_client.get(f"/api/v1/reports/{request_id}")

    assert created.status_code == 201
    assert retrieved.status_code == 200
    report = created.json()["report"]
    assert report["claims"][0]["text"] == MULTILINGUAL_TEXT
    assert report["claims"][0]["evidence"][0]["label"] == MULTILINGUAL_TEXT
    assert report["citations"][0]["citations"][0]["title"] == MULTILINGUAL_TEXT
    assert report["risk_summary"]["explanation"] == MULTILINGUAL_TEXT
    assert retrieved.json() == created.json()


def test_audit_trail_persists_multilingual_event_details(tmp_path):
    database_path = tmp_path / "unicode-audit.db"
    first_instance = AuditTrail(database_path)

    first_instance.record_event(
        request_id="unicode-request-001",
        action="unicode_round_trip",
        details={"message": MULTILINGUAL_TEXT},
    )

    second_instance = AuditTrail(database_path)
    events = second_instance.get_events("unicode-request-001")

    assert events[0]["details"]["message"] == MULTILINGUAL_TEXT
