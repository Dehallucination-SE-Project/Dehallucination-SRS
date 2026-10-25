
from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_valid_request_is_accepted():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "The Earth orbits the Sun."},
    )

    assert response.status_code == 202

    data = response.json()
    assert data["request_id"]
    assert data["created_at"]
    assert data["status"] == "accepted"
    assert data["input_text"] == "The Earth orbits the Sun."


def test_request_id_is_valid_uuid():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "Test statement."},
    )

    assert response.status_code == 202
    request_id = response.json()["request_id"]

    # Raises ValueError if the ID is not a valid UUID.
    parsed_id = UUID(request_id)
    assert str(parsed_id) == request_id


def test_created_at_is_utc():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "Test statement."},
    )

    assert response.status_code == 202
    created_at = datetime.fromisoformat(response.json()["created_at"])

    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timezone.utc.utcoffset(created_at)


def test_missing_input_text_is_rejected():
    response = client.post("/api/v1/verify", json={})

    assert response.status_code == 422


def test_blank_input_text_is_rejected():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "   "},
    )

    assert response.status_code == 422


def test_each_request_gets_a_unique_id():
    first = client.post(
        "/api/v1/verify",
        json={"input_text": "First statement."},
    )
    second = client.post(
        "/api/v1/verify",
        json={"input_text": "Second statement."},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["request_id"] != second.json()["request_id"]


def test_health_endpoint_returns_service_status():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "dehallucination-api"
    assert data["version"] == "0.1.0"


def test_health_endpoint_reports_dependency_status():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    dependencies = response.json()["dependencies"]
    assert "evidence_sources" in dependencies
    assert dependencies["evidence_sources"] == "not_configured"


def test_evidence_retrieval_returns_503_when_source_unavailable():
    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "What is the capital of France?"},
    )

    assert response.status_code == 503




def test_evidence_retrieval_explains_unavailable_source():
    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "What is the capital of France?"},
    )

    assert response.status_code == 503
    assert "not configured or is unavailable" in response.json()["detail"]

