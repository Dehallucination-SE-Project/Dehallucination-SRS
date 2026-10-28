
import pytest

from response_risk import calculate_response_risk


def test_empty_claims_return_zero_risk():
    result = calculate_response_risk([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["claim_count"] == 0


def test_contradicted_claim_has_higher_risk_than_supported_claim():
    supported = calculate_response_risk([
        {"verdict": "Supported"}
    ])
    contradicted = calculate_response_risk([
        {"verdict": "Contradicted"}
    ])

    assert contradicted["risk_score"] > supported["risk_score"]


def test_high_impact_contradiction_has_higher_risk():
    low_impact = calculate_response_risk([
        {"verdict": "Contradicted", "impact_level": "low"}
    ])
    high_impact = calculate_response_risk([
        {"verdict": "Contradicted", "impact_level": "high"}
    ])

    assert high_impact["risk_score"] > low_impact["risk_score"]


def test_risk_score_is_bounded():
    result = calculate_response_risk([
        {"verdict": "Contradicted", "impact_level": "high"},
        {"verdict": "Supported", "impact_level": "low"},
    ])

    assert 0.0 <= result["risk_score"] <= 1.0


def test_mixed_claims_return_counts():
    result = calculate_response_risk([
        {"verdict": "Supported"},
        {"verdict": "Contradicted"},
        {"verdict": "Uncertain"},
        {"verdict": "Unverifiable"},
    ])

    assert result["claim_count"] == 4
    assert result["contradicted_count"] == 1
    assert result["uncertain_count"] == 1
    assert result["unverifiable_count"] == 1


def test_invalid_verdict_is_rejected():
    with pytest.raises(ValueError):
        calculate_response_risk([{"verdict": "Maybe"}])


def test_invalid_impact_level_is_rejected():
    with pytest.raises(ValueError):
        calculate_response_risk([
            {"verdict": "Contradicted", "impact_level": "extreme"}
        ])


def test_non_list_input_is_rejected():
    with pytest.raises(TypeError):
        calculate_response_risk("not a list")


def test_non_dictionary_claim_is_rejected():
    with pytest.raises(TypeError):
        calculate_response_risk(["not a claim"])
