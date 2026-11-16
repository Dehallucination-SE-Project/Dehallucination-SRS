"""Authentication and role-permission tests using real Bearer credentials."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import main
from audit_trail import AuditTrail
from evidence_adapters import UnavailableEvidenceAdapter
from report_store import ReportStore
from review_queue import ReviewQueue
from test_support import auth_headers


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "report_store", ReportStore(tmp_path / "reports.db"))
    monkeypatch.setattr(main, "audit_trail", AuditTrail(tmp_path / "audit.db"))
    monkeypatch.setattr(main, "review_queue", ReviewQueue(tmp_path / "reviews.db"))
    monkeypatch.setattr(main, "evidence_source", UnavailableEvidenceAdapter())
    return TestClient(main.app)


def test_public_root_and_health_do_not_require_credentials(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-token"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
    ],
)
def test_missing_or_invalid_credentials_return_401(client, headers):
    response = client.post(
        "/api/v1/verify",
        headers=headers,
        json={"input_text": "A verification request."},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "configuration",
    [
        "not-json",
        "{}",
        json.dumps([{"token": "token", "subject": "user", "role": "owner"}]),
        json.dumps([
            {"token": "duplicate", "subject": "user-a", "role": "end_user"},
            {"token": "duplicate", "subject": "user-b", "role": "reviewer"},
        ]),
    ],
)
def test_invalid_authentication_configuration_returns_503(
    client,
    monkeypatch,
    configuration,
):
    monkeypatch.setenv("DEHALLUCINATION_API_CREDENTIALS", configuration)

    response = client.post(
        "/api/v1/verify",
        headers=auth_headers("application_developer"),
        json={"input_text": "A verification request."},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication is not configured correctly"


def test_missing_authentication_configuration_returns_503(
    client,
    monkeypatch,
):
    monkeypatch.delenv("DEHALLUCINATION_API_CREDENTIALS", raising=False)

    response = client.post(
        "/api/v1/verify",
        json={"input_text": "A verification request."},
    )

    assert response.status_code == 503


def test_role_permissions_protect_status_and_evidence_endpoints(client):
    assert client.get(
        "/api/v1/status",
        headers=auth_headers("application_developer"),
    ).status_code == 403
    assert client.get(
        "/api/v1/status",
        headers=auth_headers("administrator"),
    ).status_code == 200

    assert client.post(
        "/api/v1/evidence/retrieve",
        headers=auth_headers("end_user"),
        json={"query": "a fact"},
    ).status_code == 403
    assert client.post(
        "/api/v1/evidence/retrieve",
        headers=auth_headers("application_developer"),
        json={"query": "a fact"},
    ).status_code == 503
    assert client.post(
        "/api/v1/evidence/retrieve/batch",
        headers=auth_headers("application_developer"),
        json={"queries": ["a fact"]},
    ).status_code == 200


def test_reports_are_limited_by_role_and_request_owner(client):
    end_user_request = client.post(
        "/api/v1/verify",
        headers=auth_headers("end_user"),
        json={"input_text": "A user's claim."},
    ).json()["request_id"]
    main.report_store.save_report(
        end_user_request,
        {"claim_count": 0},
        owner_subject="end-user-1",
    )

    assert client.get(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("end_user"),
    ).status_code == 200
    assert client.get(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("application_developer"),
    ).status_code == 404
    assert client.get(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("reviewer"),
    ).status_code == 200
    assert client.get(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("administrator"),
    ).status_code == 403

    developer_request = client.post(
        "/api/v1/verify",
        headers=auth_headers("application_developer"),
        json={"input_text": "An integration's claim."},
    ).json()["request_id"]
    create = client.post(
        f"/api/v1/reports/{developer_request}",
        headers=auth_headers("application_developer"),
        json={"claims": []},
    )
    assert create.status_code == 201
    assert client.get(
        f"/api/v1/reports/{developer_request}",
        headers=auth_headers("application_developer"),
    ).status_code == 200
    # Ownership remains available even after the audit-retention policy removes
    # the request-accepted event that originally established the owner.
    main.audit_trail.purge_expired_events(
        retention_days=1,
        now=datetime(2100, 1, 1, tzinfo=timezone.utc),
    )
    assert main.report_store.get_report_owner(developer_request) == "application-1"
    assert client.get(
        f"/api/v1/reports/{developer_request}",
        headers=auth_headers("application_developer"),
    ).status_code == 200

    assert client.post(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("application_developer"),
        json={"claims": []},
    ).status_code == 404
    assert client.post(
        f"/api/v1/reports/{end_user_request}",
        headers=auth_headers("end_user"),
        json={"claims": []},
    ).status_code == 403


def test_review_endpoints_require_reviewer_and_audit_verified_actor(client):
    request_id = client.post(
        "/api/v1/verify",
        headers=auth_headers("application_developer"),
        json={"input_text": "A claim for review."},
    ).json()["request_id"]
    created = client.post(
        f"/api/v1/reports/{request_id}",
        headers=auth_headers("application_developer"),
        json={
            "claims": [{"text": "A claim for review.", "verdict": "Uncertain"}],
            "review_required": True,
        },
    )
    assert created.status_code == 201

    assert client.get(
        "/api/v1/reviews/pending",
        headers=auth_headers("application_developer"),
    ).status_code == 403
    assert client.get(
        "/api/v1/reviews/pending",
        headers=auth_headers("reviewer"),
    ).status_code == 200
    assert client.get(
        f"/api/v1/reviews/{request_id}",
        headers=auth_headers("reviewer"),
    ).status_code == 200

    spoofed = client.post(
        f"/api/v1/reviews/{request_id}",
        headers=auth_headers("reviewer"),
        json={"decision": "approved", "reviewer": "somebody-else"},
    )
    assert spoofed.status_code == 403

    decision = client.post(
        f"/api/v1/reviews/{request_id}",
        headers=auth_headers("reviewer"),
        json={"decision": "approved", "reviewer": "qa-reviewer"},
    )
    assert decision.status_code == 200
    event = next(
        item
        for item in main.audit_trail.get_events(request_id)
        if item["action"] == "review_decision"
    )
    assert event["actor"] == "qa-reviewer"
    assert event["details"]["outcome"] == "success"

    assert client.post(
        f"/api/v1/reviews/{request_id}",
        headers=auth_headers("end_user"),
        json={"decision": "rejected", "reviewer": "end-user-1"},
    ).status_code == 403
