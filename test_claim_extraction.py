
from claim_extraction import extract_claims


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
    try:
        extract_claims(None)
        assert False, "Expected TypeError"
    except TypeError:
        pass
