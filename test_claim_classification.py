
import pytest

from claim_classification import classify_claim, classify_claims


def make_claim(text, claim_id="C-001"):
    return {
        "claim_id": claim_id,
        "text": text,
        "normalized_text": text,
    }


def test_classifies_causal_claim():
    result = classify_claim(
        make_claim("Heavy rain caused flooding.")
    )
    assert result["claim_type"] == "causal"


def test_classifies_comparative_claim():
    result = classify_claim(
        make_claim("Product A is faster than Product B.")
    )
    assert result["claim_type"] == "comparative"


def test_classifies_temporal_claim():
    result = classify_claim(
        make_claim("The event occurred yesterday.")
    )
    assert result["claim_type"] == "temporal"


def test_classifies_numerical_claim():
    result = classify_claim(
        make_claim("The price increased by 15%.")
    )
    assert result["claim_type"] == "numerical"


def test_uses_general_factual_fallback():
    result = classify_claim(
        make_claim("The Earth orbits the Sun.")
    )
    assert result["claim_type"] == "general_factual"


def test_preserves_claim_id_and_text():
    claim = make_claim("The price increased by 15%.")
    result = classify_claim(claim)

    assert result["claim_id"] == claim["claim_id"]
    assert result["text"] == claim["text"]
    assert result["normalized_text"] == claim["normalized_text"]


def test_classifies_multiple_claims():
    claims = [
        make_claim("Heavy rain caused flooding.", "C-001"),
        make_claim("The price increased by 15%.", "C-002"),
    ]

    results = classify_claims(claims)

    assert len(results) == 2
    assert results[0]["claim_type"] == "causal"
    assert results[1]["claim_type"] == "numerical"
    assert results[0]["claim_id"] == "C-001"
    assert results[1]["claim_id"] == "C-002"


def test_rejects_empty_claim_text():
    with pytest.raises(ValueError):
        classify_claim({"claim_id": "C-001", "text": "  "})


def test_rejects_non_dictionary_claim():
    with pytest.raises(TypeError):
        classify_claim("Not a claim")


def test_rejects_non_list_input():
    with pytest.raises(TypeError):
        classify_claims("Not a list")
