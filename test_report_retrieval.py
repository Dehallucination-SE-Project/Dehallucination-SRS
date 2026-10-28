
import pytest
from fastapi.testclient import TestClient

import main
from report_store import ReportStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use a temporary database so tests do not alter real report data."""
    monkeypatch.setattr(
        main,
        "report_store",
        ReportStore(tmp_path / "test_reports.db"),
    )
    return TestClient(main.app)


def test_report_can_be_created_and_retrieved(client):
    request_id = "request-report-001"

    payload = {
        "claims": [
            {
                "claim_id": "C-001",
                "text": "The Earth orbits the Sun.",
                "verdict": "Supported",
                "evidence": [
                    {
                        "source_id": "source-1",
                        "label": "Astronomy reference",
                    }
                ],
            },
            {
                "claim_id": "C-002",
                "text": "An unknown claim.",
                "verdict": "Unverifiable",
                "evidence": [],
            },
        ],
        "risk_summary": {
            "risk_score": 0.45,
            "risk_level": "medium",
        },
    }

    create_response = client.post(
        f"/api/v1/reports/{request_id}",
        json=payload,
    )

    assert create_response.status_code == 201

    saved = create_response.json()
    assert saved["request_id"] == request_id
    assert saved["report"]["claim_count"] == 2

    retrieve_response = client.get(
        f"/api/v1/reports/{request_id}"
    )

    assert retrieve_response.status_code == 200
    retrieved = retrieve_response.json()

    assert retrieved["request_id"] == request_id
    assert retrieved["report"] == saved["report"]
    assert retrieved["report"]["risk_summary"] == payload["risk_summary"]


def test_missing_report_returns_404(client):
    response = client.get("/api/v1/reports/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Verification report not found"


def test_duplicate_report_creation_is_rejected(client):
    request_id = "request-report-002"
    payload = {
        "claims": [],
        "risk_summary": None,
    }

    first = client.post(
        f"/api/v1/reports/{request_id}",
        json=payload,
    )
    second = client.post(
        f"/api/v1/reports/{request_id}",
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 400


def test_invalid_verdict_is_rejected(client):
    response = client.post(
        "/api/v1/reports/request-report-003",
        json={
            "claims": [
                {
                    "claim_id": "C-001",
                    "text": "Example claim",
                    "verdict": "Maybe",
                }
            ]
        },
    )

    assert response.status_code == 400


def test_empty_report_can_be_retrieved(client):
    request_id = "request-report-004"

    create_response = client.post(
        f"/api/v1/reports/{request_id}",
        json={"claims": []},
    )

    assert create_response.status_code == 201

    retrieve_response = client.get(
        f"/api/v1/reports/{request_id}"
    )

    assert retrieve_response.status_code == 200
    assert retrieve_response.json()["report"]["claim_count"] == 0
    assert retrieve_response.json()["report"]["claims"] == []
