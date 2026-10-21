
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
