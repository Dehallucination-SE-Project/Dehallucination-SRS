
import pytest

from evidence_citations import build_evidence_citations


def test_builds_citation_from_available_metadata():
    claims = [
        {
            "claim_id": "C-001",
            "evidence": [
                {
                    "source_id": "source-1",
                    "label": "Astronomy reference",
                }
            ],
        }
    ]

    result = build_evidence_citations(claims)

    assert result == [
        {
            "claim_id": "C-001",
            "citations": [
                {
                    "source_id": "source-1",
                    "label": "Astronomy reference",
                }
            ],
        }
    ]


def test_preserves_all_supported_citation_fields():
    evidence = {
        "source_id": "source-1",
        "label": "Astronomy reference",
        "url": "https://example.com/astronomy",
        "title": "Astronomy Guide",
        "retrieved_at": "2026-10-28T10:00:00+00:00",
        "text": "Earth orbits the Sun.",
    }

    result = build_evidence_citations([
        {"claim_id": "C-001", "evidence": [evidence]}
    ])

    assert result[0]["citations"] == [
        {
            "source_id": "source-1",
            "label": "Astronomy reference",
            "url": "https://example.com/astronomy",
            "title": "Astronomy Guide",
            "retrieved_at": "2026-10-28T10:00:00+00:00",
        }
    ]

    # Evidence text is not citation metadata.
    assert "text" not in result[0]["citations"][0]


def test_does_not_invent_citation_metadata():
    result = build_evidence_citations([
        {
            "claim_id": "C-001",
            "evidence": [{"text": "Some evidence"}],
        }
    ])

    assert result == [
        {"claim_id": "C-001", "citations": []}
    ]


def test_ignores_empty_metadata_fields():
    result = build_evidence_citations([
        {
            "claim_id": "C-001",
            "evidence": [
                {
                    "source_id": "",
                    "label": None,
                    "title": "Useful title",
                }
            ],
        }
    ])

    assert result[0]["citations"] == [
        {"title": "Useful title"}
    ]


def test_duplicate_citations_are_removed_within_claim():
    citation = {
        "source_id": "source-1",
        "label": "Reference",
    }

    result = build_evidence_citations([
        {
            "claim_id": "C-001",
            "evidence": [citation, citation.copy()],
        }
    ])

    assert len(result[0]["citations"]) == 1


def test_citations_are_grouped_by_claim():
    result = build_evidence_citations([
        {
            "claim_id": "C-001",
            "evidence": [{"source_id": "source-1"}],
        },
        {
            "claim_id": "C-002",
            "evidence": [{"source_id": "source-2"}],
        },
    ])

    assert result[0]["claim_id"] == "C-001"
    assert result[0]["citations"] == [
        {"source_id": "source-1"}
    ]

    assert result[1]["claim_id"] == "C-002"
    assert result[1]["citations"] == [
        {"source_id": "source-2"}
    ]


def test_missing_claim_id_gets_fallback_id():
    result = build_evidence_citations([
        {"evidence": [{"label": "Reference"}]}
    ])

    assert result[0]["claim_id"] == "C-001"


def test_non_list_claims_are_rejected():
    with pytest.raises(TypeError):
        build_evidence_citations("not a list")


def test_non_dictionary_claim_is_rejected():
    with pytest.raises(TypeError):
        build_evidence_citations(["not a claim"])


def test_blank_claim_id_is_rejected():
    with pytest.raises(ValueError):
        build_evidence_citations([
            {"claim_id": " ", "evidence": []}
        ])


def test_non_list_claim_evidence_is_rejected():
    with pytest.raises(TypeError):
        build_evidence_citations([
            {"claim_id": "C-001", "evidence": "not a list"}
        ])


def test_non_dictionary_evidence_item_is_rejected():
    with pytest.raises(TypeError):
        build_evidence_citations([
            {"claim_id": "C-001", "evidence": ["not a dictionary"]}
        ])


def test_missing_evidence_defaults_to_empty_list():
    result = build_evidence_citations([
        {"claim_id": "C-001"}
    ])

    assert result == [
        {"claim_id": "C-001", "citations": []}
    ]
