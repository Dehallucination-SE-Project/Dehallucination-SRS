
import pytest

from claim_extraction import extract_claims, normalize_claim


def test_extracts_two_sentences():
    result = extract_claims(
        "The Earth orbits the Sun. Water freezes at 0°C."
    )

    assert len(result) == 2
    assert result[0]["text"] == "The Earth orbits the Sun."
    assert result[1]["text"] == "Water freezes at 0°C."


def test_assigns_unique_claim_ids():
    result = extract_claims("First claim. Second claim.")

    ids = [claim["claim_id"] for claim in result]
    assert len(ids) == len(set(ids))
    assert all(ids)


def test_single_sentence():
    result = extract_claims("The Earth orbits the Sun.")

    assert len(result) == 1


def test_blank_text_returns_no_claims():
    assert extract_claims("   ") == []


def test_unicode_text():
    result = extract_claims("Café prices rose by 5%.")

    assert len(result) == 1
    assert result[0]["text"] == "Café prices rose by 5%."


def test_non_string_input_raises_type_error():
    with pytest.raises(TypeError):
        extract_claims(None)


def test_normalize_claim_collapses_whitespace():
    assert normalize_claim("  The   Earth   orbits the Sun.  ") == (
        "The Earth orbits the Sun."
    )


def test_original_text_is_preserved():
    original = "The   Earth   orbits the Sun."
    result = extract_claims(original)

    assert result[0]["text"] == original
    assert result[0]["normalized_text"] == "The Earth orbits the Sun."


def test_normalization_preserves_punctuation():
    assert normalize_claim("Is it true?  Yes!") == "Is it true? Yes!"


def test_normalize_claim_rejects_non_string():
    with pytest.raises(TypeError):
        normalize_claim(None)
