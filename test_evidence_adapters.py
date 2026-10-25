
from datetime import datetime, timezone

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


def test_retrieved_evidence_contains_metadata():
    adapter = LocalEvidenceAdapter(
        [{"text": "The Earth orbits the Sun."}],
        source_id="test-source-01",
        label="Astronomy",
    )

    results = adapter.retrieve("Earth orbits")

    assert len(results) == 1
    item = results[0]

    assert item["source_id"] == "test-source-01"
    assert item["label"] == "Astronomy"

    timestamp = datetime.fromisoformat(item["retrieved_at"])
    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() == timezone.utc.utcoffset(timestamp)


def test_metadata_does_not_modify_original_evidence():
    original = {"text": "The Earth orbits the Sun."}
    adapter = LocalEvidenceAdapter([original])

    results = adapter.retrieve("Earth")

    assert "source_id" not in original
    assert "label" not in original
    assert "retrieved_at" not in original
    assert "source_id" in results[0]


def test_metadata_configuration_rejects_blank_source_id():
    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        LocalEvidenceAdapter([], source_id=" ")


def test_metadata_configuration_rejects_blank_label():
    with pytest.raises(ValueError, match="label must be a non-empty string"):
        LocalEvidenceAdapter([], label=" ")
