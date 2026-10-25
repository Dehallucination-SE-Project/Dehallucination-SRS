
import pytest

from verdict_engine import assign_verdict, evaluate_claim


def test_empty_evidence_is_unverifiable():
    assert assign_verdict([]) == "Unverifiable"


def test_supporting_evidence_is_supported():
    evidence = [{"assessment": "supports"}]
    assert assign_verdict(evidence) == "Supported"


def test_contradicting_evidence_is_contradicted():
    evidence = [{"assessment": "contradicts"}]
    assert assign_verdict(evidence) == "Contradicted"


def test_mixed_evidence_is_uncertain():
    evidence = [
        {"assessment": "supports"},
        {"assessment": "contradicts"},
    ]
    assert assign_verdict(evidence) == "Uncertain"


def test_insufficient_evidence_is_unverifiable():
    evidence = [{"assessment": "insufficient"}]
    assert assign_verdict(evidence) == "Unverifiable"


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
    assert "verdict" not in claim


def test_evaluate_claim_rejects_empty_text():
    with pytest.raises(ValueError):
        evaluate_claim({"claim_id": "C-001", "text": " "}, [])
