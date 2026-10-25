
import pytest

from contradiction_detection import detect_contradictions


def make_claim(claim_id, text):
    return {
        "claim_id": claim_id,
        "text": text,
        "normalized_text": text,
    }


def test_detects_explicit_negation_conflict():
    claims = [
        make_claim("C1", "The Earth is round."),
        make_claim("C2", "The Earth is not round."),
    ]

    conflicts = detect_contradictions(claims)

    assert len(conflicts) == 1
    assert conflicts[0]["reason"] == "opposite_explicit_negation"


def test_detects_conflicting_numeric_values():
    claims = [
        make_claim("C1", "The population is 10 million."),
        make_claim("C2", "The population is 12 million."),
    ]

    conflicts = detect_contradictions(claims)

    assert len(conflicts) == 1
    assert conflicts[0]["reason"] == "conflicting_numeric_values"


def test_preserves_both_claims_in_conflict():
    claims = [
        make_claim("C1", "The Earth is round."),
        make_claim("C2", "The Earth is not round."),
    ]

    conflict = detect_contradictions(claims)[0]

    assert conflict["claim_a_id"] == "C1"
    assert conflict["claim_b_id"] == "C2"
    assert conflict["claim_a_text"] == claims[0]["text"]
    assert conflict["claim_b_text"] == claims[1]["text"]


def test_identical_claims_are_not_a_conflict():
    claims = [
        make_claim("C1", "The Earth orbits the Sun."),
        make_claim("C2", "The Earth orbits the Sun."),
    ]

    assert detect_contradictions(claims) == []


def test_unrelated_claims_are_not_a_conflict():
    claims = [
        make_claim("C1", "The Earth orbits the Sun."),
        make_claim("C2", "Water freezes at 0 degrees."),
    ]

    assert detect_contradictions(claims) == []


def test_empty_list_returns_no_conflicts():
    assert detect_contradictions([]) == []


def test_rejects_non_list_input():
    with pytest.raises(TypeError):
        detect_contradictions("not a list")


def test_rejects_invalid_claim():
    with pytest.raises(ValueError):
        detect_contradictions([{"claim_id": "C1", "text": "  "}])


def test_rejects_non_dictionary_claim():
    with pytest.raises(TypeError):
        detect_contradictions(["not a claim"])
