
import pytest

from evidence_ranking import rank_evidence


def test_relevant_evidence_ranks_first():
    evidence = [
        {"text": "Water freezes at zero degrees.", "source_id": "source-a"},
        {"text": "Earth orbits the Sun.", "source_id": "source-b"},
    ]

    ranked = rank_evidence("Earth orbits Sun", evidence)

    assert ranked[0]["source_id"] == "source-b"
    assert ranked[0]["relevance_score"] == 1.0


def test_configured_credibility_changes_ranking():
    evidence = [
        {"text": "Earth orbits the Sun.", "source_id": "less-trusted"},
        {"text": "Earth orbits the Sun.", "source_id": "more-trusted"},
    ]

    ranked = rank_evidence(
        "Earth orbits Sun",
        evidence,
        source_credibility={
            "less-trusted": 0.2,
            "more-trusted": 0.9,
        },
    )

    assert ranked[0]["source_id"] == "more-trusted"
    assert ranked[0]["credibility_score"] == 0.9


def test_weights_control_ranking():
    evidence = [
        {"text": "Earth orbits Sun.", "source_id": "low"},
        {"text": "Earth orbits Sun and Moon.", "source_id": "high"},
    ]
    credibility = {"low": 1.0, "high": 0.0}

    ranked = rank_evidence(
        "Earth orbits Sun Moon",
        evidence,
        credibility,
        relevance_weight=0.1,
        credibility_weight=0.9,
    )

    assert ranked[0]["source_id"] == "low"


def test_ranking_preserves_metadata_without_mutating_input():
    original = {
        "text": "Earth orbits the Sun.",
        "source_id": "source-a",
        "label": "Astronomy",
        "retrieved_at": "2026-10-25T10:00:00+00:00",
    }

    ranked = rank_evidence("Earth", [original])

    assert ranked[0]["label"] == "Astronomy"
    assert ranked[0]["retrieved_at"] == original["retrieved_at"]
    assert "ranking_score" not in original
    assert ranked[0] is not original


def test_empty_evidence_returns_empty_list():
    assert rank_evidence("Earth orbits", []) == []


@pytest.mark.parametrize("query", ["", "   ", "!!!"])
def test_invalid_query_is_rejected(query):
    with pytest.raises(ValueError):
        rank_evidence(query, [])


def test_non_string_query_is_rejected():
    with pytest.raises(TypeError, match="query must be a string"):
        rank_evidence(123, [])


def test_invalid_credibility_score_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        rank_evidence(
            "Earth",
            [],
            source_credibility={"source-a": 1.5},
        )


def test_invalid_weight_is_rejected():
    with pytest.raises(ValueError, match="relevance_weight"):
        rank_evidence("Earth", [], relevance_weight=-0.1)


def test_tied_scores_keep_original_order():
    evidence = [
        {"text": "Earth orbits Sun.", "source_id": "a"},
        {"text": "Earth orbits Sun.", "source_id": "b"},
    ]

    ranked = rank_evidence("Earth", evidence)

    assert [item["source_id"] for item in ranked] == ["a", "b"]
