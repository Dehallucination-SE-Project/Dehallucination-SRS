import pytest
from verification_report import generate_verification_report

def test_report_contains_claims_verdicts_and_summary():
    report = generate_verification_report([
        {"claim_id": "C-001", "text": "Earth orbits the Sun.", "verdict": "Supported"},
        {"claim_id": "C-002", "text": "The Sun orbits Earth.", "verdict": "Contradicted"},
    ])

    assert report["report_type"] == "verification_report"
    assert report["claim_count"] == 2
    assert report["verdict_summary"]["supported"] == 1
    assert report["verdict_summary"]["contradicted"] == 1
    assert len(report["claims"]) == 2


def test_report_includes_evidence_and_citations():
    report = generate_verification_report([
        {
            "claim_id": "C-001",
            "text": "Earth orbits the Sun.",
            "verdict": "Supported",
            "confidence_score": 0.9,
            "evidence": [
                {
                    "text": "Earth orbits the Sun.",
                    "source_id": "source-1",
                    "label": "Astronomy reference",
                }
            ],
        }
    ])

    assert report["claims"][0]["confidence_score"] == 0.9
    assert report["evidence"][0]["source_id"] == "source-1"
    assert report["citations"][0]["claim_id"] == "C-001"
    assert report["citations"][0]["citations"][0]["label"] == "Astronomy reference"


def test_report_creates_warnings_for_non_supported_claims():
    report = generate_verification_report([
        {"claim_id": "C-001", "text": "Claim A", "verdict": "Supported"},
        {"claim_id": "C-002", "text": "Claim B", "verdict": "Contradicted"},
        {"claim_id": "C-003", "text": "Claim C", "verdict": "Uncertain"},
        {"claim_id": "C-004", "text": "Claim D", "verdict": "Unverifiable"},
    ])

    assert len(report["warnings"]) == 3
    assert {warning["claim_id"] for warning in report["warnings"]} == {
        "C-002", "C-003", "C-004"
    }


def test_report_preserves_risk_summary():
    risk = {"risk_score": 0.75, "risk_level": "high"}

    report = generate_verification_report([], risk)

    assert report["risk_summary"] == risk
    assert report["claim_count"] == 0
    assert report["warnings"] == []


def test_empty_report_is_valid():
    report = generate_verification_report([])

    assert report["claim_count"] == 0
    assert report["claims"] == []
    assert report["evidence"] == []
    assert report["citations"] == []
    assert report["warnings"] == []


def test_non_list_claims_are_rejected():
    with pytest.raises(TypeError):
        generate_verification_report("not a list")


def test_non_dictionary_claim_is_rejected():
    with pytest.raises(TypeError):
        generate_verification_report(["not a claim"])


def test_invalid_verdict_is_rejected():
    with pytest.raises(ValueError):
        generate_verification_report([
            {"claim_id": "C-001", "text": "Claim", "verdict": "Maybe"}
        ])


def test_blank_claim_text_is_rejected():
    with pytest.raises(ValueError):
        generate_verification_report([
            {"claim_id": "C-001", "text": " ", "verdict": "Supported"}
        ])


def test_invalid_risk_summary_is_rejected():
    with pytest.raises(TypeError):
        generate_verification_report([], ["not a dictionary"])
