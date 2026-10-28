
from response_risk import explain_response_risk


def test_explanation_includes_risk_summary():
    result = explain_response_risk([
        {
            "claim_id": "C-001",
            "text": "Example claim",
            "verdict": "Contradicted",
            "impact_level": "high",
        }
    ])

    assert result["risk_level"] == "high"
    assert result["risk_score"] == 1.0
    assert "Contradicted" in result["explanation"]
    assert len(result["claim_explanations"]) == 1


def test_explanation_identifies_claim_and_impact():
    result = explain_response_risk([
        {
            "claim_id": "C-010",
            "text": "Example claim",
            "verdict": "Unverifiable",
            "impact_level": "high",
        }
    ])

    claim_result = result["claim_explanations"][0]

    assert claim_result["claim_id"] == "C-010"
    assert claim_result["verdict"] == "Unverifiable"
    assert claim_result["impact_level"] == "high"
    assert "high impact" in claim_result["explanation"]


def test_explanation_handles_empty_claims():
    result = explain_response_risk([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["claim_explanations"] == []
    assert "No claims" in result["explanation"]


def test_explanation_preserves_existing_risk_counts():
    claims = [
        {"verdict": "Supported"},
        {"verdict": "Contradicted", "impact_level": "high"},
        {"verdict": "Uncertain"},
        {"verdict": "Unverifiable"},
    ]

    result = explain_response_risk(claims)

    assert result["claim_count"] == 4
    assert result["contradicted_count"] == 1
    assert result["uncertain_count"] == 1
    assert result["unverifiable_count"] == 1
    assert len(result["claim_explanations"]) == 4


def test_explanation_rejects_invalid_verdict():
    import pytest

    with pytest.raises(ValueError):
        explain_response_risk([
            {"verdict": "Maybe"}
        ])
