
import pytest

from grounded_response import generate_grounded_response


def test_only_supported_claims_are_included():
    claims = [
        {
            "claim_id": "C-001",
            "text": "The Earth orbits the Sun.",
            "verdict": "Supported",
        },
        {
            "claim_id": "C-002",
            "text": "The Sun orbits the Earth.",
            "verdict": "Contradicted",
        },
        {
            "claim_id": "C-003",
            "text": "An unknown planet orbits Earth.",
            "verdict": "Unverifiable",
        },
    ]

    result = generate_grounded_response(claims)

    assert result["enabled"] is True
    assert result["grounded_response"] == "The Earth orbits the Sun."
    assert result["included_claim_ids"] == ["C-001"]
    assert len(result["excluded_claims"]) == 2


def test_no_supported_claims_produces_safe_message():
    result = generate_grounded_response([
        {"claim_id": "C-001", "text": "Claim A", "verdict": "Uncertain"},
    ])

    assert result["included_claim_ids"] == []
    assert result["citations"] == []
    assert "cannot be provided" in result["grounded_response"]


def test_source_metadata_is_preserved_as_citation():
    result = generate_grounded_response([
        {
            "claim_id": "C-001",
            "text": "The Earth orbits the Sun.",
            "verdict": "Supported",
            "evidence": [
                {
                    "text": "Earth orbits the Sun.",
                    "source_id": "source-1",
                    "label": "Astronomy reference",
                }
            ],
        }
    ])

    assert result["citations"] == [
        {
            "source_id": "source-1",
            "label": "Astronomy reference",
        }
    ]


def test_duplicate_citations_are_removed():
    evidence = {
        "source_id": "source-1",
        "label": "Reference",
    }

    result = generate_grounded_response([
        {
            "claim_id": "C-001",
            "text": "Claim A",
            "verdict": "Supported",
            "evidence": [evidence],
        },
        {
            "claim_id": "C-002",
            "text": "Claim B",
            "verdict": "Supported",
            "evidence": [evidence],
        },
    ])

    assert len(result["citations"]) == 1


def test_disabled_mode_preserves_original_claim_text():
    result = generate_grounded_response(
        [
            {
                "claim_id": "C-001",
                "text": "Original statement.",
                "verdict": "Supported",
            }
        ],
        enabled=False,
    )

    assert result["enabled"] is False
    assert result["grounded_response"] == "Original statement."


def test_invalid_verdict_is_rejected():
    with pytest.raises(ValueError):
        generate_grounded_response([
            {"claim_id": "C-001", "text": "Claim", "verdict": "Maybe"}
        ])


def test_invalid_claim_is_rejected():
    with pytest.raises(TypeError):
        generate_grounded_response(["not a claim"])


def test_empty_claims_produce_safe_message():
    result = generate_grounded_response([])

    assert result["included_claim_ids"] == []
    assert result["excluded_claims"] == []
    assert "cannot be provided" in result["grounded_response"]


def test_blank_claim_text_is_rejected():
    with pytest.raises(ValueError):
        generate_grounded_response([
            {"claim_id": "C-001", "text": " ", "verdict": "Supported"}
        ])
