
import pytest

from verdict_engine import (
    assign_verdict,
    calculate_confidence_score,
    evaluate_claim,
)


def test_empty_evidence_is_unverifiable():
    assert assign_verdict([]) == "Unverifiable"


def test_supporting_evidence_is_supported():
    assert assign_verdict([{"assessment": "supports"}]) == "Supported"


def test_contradicting_evidence_is_contradicted():
    assert assign_verdict([{"assessment": "contradicts"}]) == "Contradicted"


def test_mixed_evidence_is_uncertain():
    evidence = [
        {"assessment": "supports"},
        {"assessment": "contradicts"},
    ]
    assert assign_verdict(evidence) == "Uncertain"


def test_insufficient_evidence_is_unverifiable():
    assert assign_verdict([{"assessment": "insufficient"}]) == "Unverifiable"


def test_insufficient_evidence_does_not_override_support():
    evidence = [
        {"assessment": "supports"},
        {"assessment": "insufficient"},
    ]
    assert assign_verdict(evidence) == "Supported"


def test_invalid_assessment_is_rejected():
    with pytest.raises(ValueError):
        assign_verdict([{"assessment": "maybe"}])


def test_non_list_evidence_is_rejected():
    with pytest.raises(TypeError):
        assign_verdict("not a list")


def test_non_dictionary_evidence_is_rejected():
    with pytest.raises(TypeError):
        assign_verdict(["supports"])


def test_evaluate_claim_preserves_claim_fields():
    claim = {
        "claim_id": "C-001",
        "text": "The Earth orbits the Sun.",
        "normalized_text": "The Earth orbits the Sun.",
    }

    result = evaluate_claim(claim, [{"assessment": "supports"}])

    assert result["claim_id"] == "C-001"
    assert result["text"] == claim["text"]
    assert result["verdict"] == "Supported"
    assert 0.0 <= result["confidence_score"] <= 1.0
    assert "verdict" not in claim
    assert "confidence_score" not in claim


def test_evaluate_claim_rejects_empty_text():
    with pytest.raises(ValueError):
        evaluate_claim({"claim_id": "C-001", "text": " "}, [])


# DH-040 confidence score tests


def test_no_evidence_has_zero_confidence():
    assert calculate_confidence_score([]) == 0.0


def test_insufficient_evidence_has_zero_confidence():
    evidence = [
        {"assessment": "insufficient"},
        {"assessment": "insufficient"},
    ]
    assert calculate_confidence_score(evidence) == 0.0


def test_more_consistent_supporting_evidence_increases_confidence():
    one_item = [{"assessment": "supports"}]
    two_items = [
        {"assessment": "supports"},
        {"assessment": "supports"},
    ]
    three_items = [
        {"assessment": "supports"},
        {"assessment": "supports"},
        {"assessment": "supports"},
    ]

    assert calculate_confidence_score(one_item) == pytest.approx(1 / 3, abs=0.001)
    assert calculate_confidence_score(two_items) == pytest.approx(2 / 3, abs=0.001)
    assert calculate_confidence_score(three_items) == 1.0


def test_consistent_contradicting_evidence_can_have_high_confidence():
    evidence = [
        {"assessment": "contradicts"},
        {"assessment": "contradicts"},
        {"assessment": "contradicts"},
    ]

    assert calculate_confidence_score(evidence) == 1.0
    assert assign_verdict(evidence) == "Contradicted"


def test_mixed_evidence_has_lower_confidence_than_consistent_evidence():
    mixed = [
        {"assessment": "supports"},
        {"assessment": "contradicts"},
    ]
    consistent = [
        {"assessment": "supports"},
        {"assessment": "supports"},
    ]

    assert calculate_confidence_score(mixed) < calculate_confidence_score(
        consistent
    )
    assert assign_verdict(mixed) == "Uncertain"


def test_confidence_score_is_bounded_between_zero_and_one():
    evidence = [
        {"assessment": "supports"},
        {"assessment": "supports"},
        {"assessment": "contradicts"},
        {"assessment": "insufficient"},
    ]

    score = calculate_confidence_score(evidence)
    assert 0.0 <= score <= 1.0


def test_invalid_evidence_is_rejected_by_confidence_calculation():
    with pytest.raises(ValueError):
        calculate_confidence_score([{"assessment": "unknown"}])


def test_evaluate_claim_returns_confidence_score():
    claim = {"claim_id": "C-002", "text": "Water freezes at 0°C."}
    evidence = [
        {"assessment": "supports"},
        {"assessment": "supports"},
        {"assessment": "supports"},
    ]

    result = evaluate_claim(claim, evidence)

    assert result["verdict"] == "Supported"
    assert result["confidence_score"] == 1.0
