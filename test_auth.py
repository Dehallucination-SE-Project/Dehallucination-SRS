
import pytest
from fastapi.testclient import TestClient

from main import app


TEST_TOKEN = "local-test-token-not-for-production"

client = TestClient(app)


@pytest.fixture(autouse=True)
def configure_test_token(monkeypatch):
    """Configure a temporary token for each test."""
    monkeypatch.setenv(
        "DEHALLUCINATION_API_TOKEN",
        TEST_TOKEN,
    )


def test_public_root_without_token():
    response = client.get("/")

    assert response.status_code == 200


def test_public_health_without_token():
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_protected_endpoint_without_token():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "The Earth revolves around the Sun."},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_with_invalid_token():
    response = client.post(
        "/api/v1/verify",
        headers={"Authorization": "Bearer incorrect-token"},
        json={"input_text": "The Earth revolves around the Sun."},
    )

    assert response.status_code == 401


def test_protected_endpoint_with_valid_token():
    response = client.post(
        "/api/v1/verify",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={"input_text": "The Earth revolves around the Sun."},
    )

    assert response.status_code == 202
    assert "request_id" in response.json()


def test_service_status_requires_authentication():
    response = client.get("/api/v1/status")

    assert response.status_code == 401


def test_report_retrieval_requires_authentication():
    response = client.get("/api/v1/reports/example-request-id")

    assert response.status_code == 401


def test_review_queue_requires_authentication():
    response = client.get("/api/v1/reviews/pending")

    assert response.status_code == 401


def test_missing_authentication_configuration(monkeypatch):
    monkeypatch.delenv(
        "DEHALLUCINATION_API_TOKEN",
        raising=False,
    )

    response = client.post(
        "/api/v1/verify",
        json={"input_text": "Example factual claim."},
    )

    assert response.status_code == 503