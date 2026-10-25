
from fastapi.testclient import TestClient

import main
from evidence_adapters import (
    LocalEvidenceAdapter,
    UnavailableEvidenceAdapter,
)


client = TestClient(main.app)


def test_retrieve_endpoint_returns_matching_evidence():
    main.evidence_source = LocalEvidenceAdapter([
        {
            "text": "The Earth orbits the Sun.",
            "source": "local-test",
        },
        {
            "text": "Water freezes at zero degrees Celsius.",
            "source": "local-test",
        },
    ])

    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "Earth orbits"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Earth orbits"
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["source"] == "local-test"


def test_retrieve_endpoint_returns_empty_results():
    main.evidence_source = LocalEvidenceAdapter([
        {"text": "The Earth orbits the Sun."},
    ])

    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "volcanoes"},
    )

    assert response.status_code == 200
    assert response.json()["evidence"] == []


def test_retrieve_endpoint_rejects_missing_query():
    response = client.post("/api/v1/evidence/retrieve", json={})

    assert response.status_code == 422


def test_retrieve_endpoint_rejects_blank_query():
    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "   "},
    )

    assert response.status_code == 422


def test_retrieve_endpoint_reports_unavailable_source():
    main.evidence_source = UnavailableEvidenceAdapter("Test source")

    response = client.post(
        "/api/v1/evidence/retrieve",
        json={"query": "The Earth orbits the Sun."},
    )

    assert response.status_code == 503
    assert "Test source" in response.json()["detail"]


def test_health_still_reports_external_sources_unconfigured():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert (
        response.json()["dependencies"]["evidence_sources"]
        == "not_configured"
    )


def test_verify_endpoint_still_accepts_requests():
    response = client.post(
        "/api/v1/verify",
        json={"input_text": "The Earth orbits the Sun."},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
