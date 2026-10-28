
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

def test_uncertain_claim_produces_warning():
    result = generate_grounded_response([
        {
            "claim_id": "C-001",
            "text": "The treatment may work.",
            "verdict": "Uncertain",
        }
    ])

    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["claim_id"] == "C-001"
    assert result["warnings"][0]["verdict"] == "Uncertain"
    assert "uncertain" in result["warnings"][0]["warning"].lower()
    assert result["included_claim_ids"] == []


def test_unverifiable_claim_produces_warning():
    result = generate_grounded_response([
        {
            "claim_id": "C-002",
            "text": "An unknown planet orbits Earth.",
            "verdict": "Unverifiable",
        }
    ])

    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["verdict"] == "Unverifiable"
    assert "could not be verified" in result["warnings"][0]["warning"]


def test_contradicted_claim_produces_warning():
    result = generate_grounded_response([
        {
            "claim_id": "C-003",
            "text": "The Sun orbits the Earth.",
            "verdict": "Contradicted",
        }
    ])

    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["verdict"] == "Contradicted"
    assert "contradicts" in result["warnings"][0]["warning"].lower()


def test_supported_claim_has_no_uncertainty_warning():
    result = generate_grounded_response([
        {
            "claim_id": "C-004",
            "text": "The Earth orbits the Sun.",
            "verdict": "Supported",
        }
    ])

    assert result["warnings"] == []
    assert result["included_claim_ids"] == ["C-004"]


def test_mixed_claims_warn_only_for_excluded_claims():
    result = generate_grounded_response([
        {
            "claim_id": "C-001",
            "text": "The Earth orbits the Sun.",
            "verdict": "Supported",
        },
        {
            "claim_id": "C-002",
            "text": "An unverified claim.",
            "verdict": "Unverifiable",
        },
        {
            "claim_id": "C-003",
            "text": "A conflicting claim.",
            "verdict": "Uncertain",
        },
    ])

    assert result["included_claim_ids"] == ["C-001"]
    assert len(result["warnings"]) == 2
    assert {
        warning["claim_id"] for warning in result["warnings"]
    } == {"C-002", "C-003"}


def test_disabled_mode_returns_no_warnings():
    result = generate_grounded_response(
        [
            {
                "claim_id": "C-001",
                "text": "An unverified claim.",
                "verdict": "Unverifiable",
            }
        ],
        enabled=False,
    )

    assert result["enabled"] is False
    assert result["warnings"] == []
