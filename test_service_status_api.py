from fastapi.testclient import TestClient
import pytest

import main
from audit_trail import AuditTrail
from report_store import ReportStore
from review_queue import ReviewQueue
from evidence_adapters import UnavailableEvidenceAdapter


@pytest.fixture

def client_with_test_stores(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "report_store", ReportStore(tmp_path / "reports.db"))
    monkeypatch.setattr(main, "audit_trail", AuditTrail(tmp_path / "audit.db"))
    monkeypatch.setattr(main, "review_queue", ReviewQueue(tmp_path / "reviews.db"))
    monkeypatch.setattr(main, "evidence_source", UnavailableEvidenceAdapter())
    return TestClient(main.app)


def test_health_reports_core_dependencies_and_degraded_evidence(client_with_test_stores):
    response = client_with_test_stores.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["overall_status"] == "degraded"
    assert data["components"]["report_store"]["status"] == "healthy"
    assert data["components"]["audit_store"]["status"] == "healthy"
    assert data["components"]["review_queue"]["status"] == "healthy"
    assert data["components"]["evidence_sources"]["status"] == "not_configured"


def test_status_alias_matches_health(client_with_test_stores):
    health = client_with_test_stores.get("/api/v1/health").json()
    status = client_with_test_stores.get("/api/v1/status").json()

    assert status["overall_status"] == health["overall_status"]
    assert status["components"].keys() == health["components"].keys()


def test_review_required_mode_is_flagged_and_audited(client_with_test_stores):
    response = client_with_test_stores.post(
        "/api/v1/verify",
        json={"input_text": "A high-impact claim.", "verification_mode": "review-required"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["review_required"] is True
    event = main.audit_trail.get_events(data["request_id"])[0]
    assert event["details"]["review_required"] is True


def test_report_review_lifecycle_and_audit(client_with_test_stores):
    created = client_with_test_stores.post(
        "/api/v1/reports/request-review-1",
        json={
            "claims": [{"text": "A claim for review.", "verdict": "Uncertain"}],
            "review_required": True,
        },
    )
    assert created.status_code == 201
    assert created.json()["review"]["status"] == "pending"

    pending = client_with_test_stores.get("/api/v1/reviews/pending").json()
    assert pending["count"] == 1
    assert pending["items"][0]["request_id"] == "request-review-1"
    assert pending["items"][0]["report"] is not None

    decision = client_with_test_stores.post(
        "/api/v1/reviews/request-review-1",
        json={"decision": "approved", "reviewer": "qa-reviewer", "comment": "Checked"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    report = client_with_test_stores.get("/api/v1/reports/request-review-1").json()
    assert report["review"]["reviewer"] == "qa-reviewer"
    actions = [e["action"] for e in main.audit_trail.get_events("request-review-1")]
    assert "review_requested" in actions
    assert "review_decision" in actions

    duplicate = client_with_test_stores.post(
        "/api/v1/reviews/request-review-1",
        json={"decision": "rejected", "reviewer": "second-reviewer"},
    )
    assert duplicate.status_code == 409
