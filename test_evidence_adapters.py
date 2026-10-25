
import pytest

from evidence_adapters import (
    LocalEvidenceAdapter,
    UnavailableEvidenceAdapter,
)


def test_local_adapter_returns_matching_evidence():
    evidence = [
        {"text": "The Earth orbits the Sun.", "source": "local-test"},
        {"text": "Water freezes at zero degrees Celsius.", "source": "local-test"},
    ]
    adapter = LocalEvidenceAdapter(evidence)

    results = adapter.retrieve("Earth orbits")

    assert len(results) == 1
    assert results[0]["text"] == "The Earth orbits the Sun."
    assert results[0]["source"] == "local-test"


def test_local_adapter_returns_empty_list_when_no_evidence_matches():
    adapter = LocalEvidenceAdapter([
        {"text": "The Earth orbits the Sun."},
    ])

    assert adapter.retrieve("volcanoes and mountains") == []


def test_local_adapter_rejects_non_string_query():
    adapter = LocalEvidenceAdapter([])

    with pytest.raises(TypeError, match="query must be a string"):
        adapter.retrieve(123)


def test_local_adapter_rejects_blank_query():
    adapter = LocalEvidenceAdapter([])

    with pytest.raises(ValueError, match="query must not be blank"):
        adapter.retrieve("   ")


def test_local_adapter_rejects_invalid_evidence_collection():
    with pytest.raises(TypeError, match="evidence_items must be a list"):
        LocalEvidenceAdapter("not a list")


def test_local_adapter_rejects_evidence_without_text():
    with pytest.raises(ValueError, match="non-empty text"):
        LocalEvidenceAdapter([{"source": "local-test"}])


def test_unavailable_source_reports_failure():
    adapter = UnavailableEvidenceAdapter("Test knowledge graph")

    with pytest.raises(
        RuntimeError,
        match="Test knowledge graph is not configured or is unavailable",
    ):
        adapter.retrieve("Earth orbits the Sun.")


def test_unavailable_source_rejects_blank_query():
    adapter = UnavailableEvidenceAdapter()

    with pytest.raises(ValueError, match="query must not be blank"):
        adapter.retrieve(" ")
