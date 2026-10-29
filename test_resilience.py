import time

import pytest

from evidence_adapters import EvidenceSourceUnavailableError
from resilience import (
    EvidenceRetrievalTimeoutError,
    retrieve_queries_independently,
    retrieve_with_timeout,
)


class StubEvidenceSource:
    """Predictable source used to simulate success and dependency failures."""

    def retrieve(self, query: str) -> list[dict]:
        if query == "slow":
            time.sleep(0.08)
            return [{"text": "finished late"}]
        if query == "unavailable":
            raise EvidenceSourceUnavailableError("source unavailable")
        if query == "broken":
            raise RuntimeError("simulated dependency failure")
        if query == "none":
            return []
        return [{"text": f"evidence for {query}"}]


def test_retrieve_with_timeout_raises_specific_timeout_error():
    with pytest.raises(EvidenceRetrievalTimeoutError, match="timed out"):
        retrieve_with_timeout(
            StubEvidenceSource(), "slow", timeout_seconds=0.005
        )


def test_retrieve_with_timeout_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="finite positive number"):
        retrieve_with_timeout(StubEvidenceSource(), "ok", timeout_seconds=0)


def test_batch_retrieval_preserves_successes_when_one_query_fails():
    result = retrieve_queries_independently(
        StubEvidenceSource(),
        ["first", "broken", "last"],
        timeout_seconds=0.5,
    )

    assert [item["status"] for item in result["results"]] == [
        "completed", "failed", "completed"
    ]
    assert result["results"][0]["evidence"] == [{"text": "evidence for first"}]
    assert result["results"][2]["evidence"] == [{"text": "evidence for last"}]
    assert result["summary"] == {
        "total": 3,
        "completed": 2,
        "failed": 1,
        "with_evidence": 2,
    }
    assert result["partial"] is True
    assert len(result["warnings"]) == 1


def test_batch_retrieval_isolates_timeout_and_continues_processing():
    result = retrieve_queries_independently(
        StubEvidenceSource(),
        ["first", "slow", "last"],
        timeout_seconds=0.005,
    )

    statuses = [item["status"] for item in result["results"]]
    assert statuses == ["completed", "timeout", "completed"]
    assert result["summary"]["completed"] == 2
    assert result["summary"]["failed"] == 1
    assert result["partial"] is True
    assert result["results"][2]["evidence"] == [{"text": "evidence for last"}]


def test_batch_retrieval_distinguishes_no_evidence_from_failure():
    result = retrieve_queries_independently(
        StubEvidenceSource(), ["none", "unavailable"], timeout_seconds=0.5
    )

    assert [item["status"] for item in result["results"]] == [
        "no_evidence", "unavailable"
    ]
    assert result["summary"]["completed"] == 1
    assert result["summary"]["failed"] == 1


def test_batch_retrieval_rejects_empty_query_list():
    with pytest.raises(ValueError, match="at least one query"):
        retrieve_queries_independently(StubEvidenceSource(), [], timeout_seconds=0.5)
