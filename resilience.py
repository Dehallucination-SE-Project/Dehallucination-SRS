"""Resilience helpers for evidence-source calls.

A timed-out synchronous call may continue running in its worker thread. The
bounded executor prevents unbounded thread creation; network-backed adapters
should also configure their own connect/read timeouts so the underlying I/O
can terminate promptly.
"""

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import math
from typing import Any, Sequence

from evidence_adapters import EvidenceSource, EvidenceSourceUnavailableError


class EvidenceRetrievalTimeoutError(TimeoutError):
    """Raised when evidence retrieval exceeds the configured wait time."""


# A bounded, shared pool avoids creating a new thread pool for every request.
# Eight workers is a conservative default for this student-project prototype.
_EVIDENCE_EXECUTOR = ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="evidence-retrieval",
)


def _validate_timeout(timeout_seconds: float) -> None:
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a finite positive number")


def retrieve_with_timeout(
    source: EvidenceSource,
    query: str,
    *,
    timeout_seconds: float = 2.0,
) -> list[dict[str, Any]]:
    """Retrieve evidence while bounding how long the caller waits.

    The source's own exceptions are propagated unchanged. A timeout is mapped
    to EvidenceRetrievalTimeoutError so API code can distinguish it from an
    unavailable source or an ordinary source failure.
    """
    _validate_timeout(timeout_seconds)
    future: Future[list[dict[str, Any]]] = _EVIDENCE_EXECUTOR.submit(
        source.retrieve, query
    )
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        # This cancels work that has not started. Python cannot forcibly stop a
        # synchronous function that is already running, so adapters should also
        # set native network timeouts when they are implemented.
        future.cancel()
        raise EvidenceRetrievalTimeoutError(
            f"Evidence retrieval timed out after {timeout_seconds:g} seconds"
        ) from exc


def retrieve_queries_independently(
    source: EvidenceSource,
    queries: Sequence[str],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    """Retrieve evidence for each query independently and retain partial results.

    One timed-out or failed query does not prevent later queries from being
    attempted. Each result contains its index, query, status, evidence, and an
    optional safe warning. Possible statuses are completed, no_evidence,
    timeout, unavailable, and failed.
    """
    _validate_timeout(timeout_seconds)
    if isinstance(queries, (str, bytes)) or not isinstance(queries, Sequence):
        raise TypeError("queries must be a sequence of strings")
    if not queries:
        raise ValueError("queries must contain at least one query")

    results: list[dict[str, Any]] = []
    for index, query in enumerate(queries):
        try:
            evidence = retrieve_with_timeout(
                source, query, timeout_seconds=timeout_seconds
            )
        except EvidenceRetrievalTimeoutError as exc:
            result = {
                "index": index,
                "query": query,
                "status": "timeout",
                "evidence": [],
                "warning": str(exc),
            }
        except EvidenceSourceUnavailableError as exc:
            result = {
                "index": index,
                "query": query,
                "status": "unavailable",
                "evidence": [],
                "warning": str(exc),
            }
        except Exception:
            # Isolate ordinary per-query source failures while avoiding leaking
            # internal exception details through the API response.
            result = {
                "index": index,
                "query": query,
                "status": "failed",
                "evidence": [],
                "warning": "Evidence retrieval failed for this query.",
            }
        else:
            result = {
                "index": index,
                "query": query,
                "status": "completed" if evidence else "no_evidence",
                "evidence": evidence,
            }
        results.append(result)

    failed_statuses = {"timeout", "unavailable", "failed"}
    failed = sum(item["status"] in failed_statuses for item in results)
    completed = len(results) - failed
    with_evidence = sum(bool(item["evidence"]) for item in results)
    warnings = [
        {"index": item["index"], "query": item["query"], "warning": item["warning"]}
        for item in results
        if "warning" in item
    ]

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "completed": completed,
            "failed": failed,
            "with_evidence": with_evidence,
        },
        "partial": 0 < failed < len(results),
        "warnings": warnings,
    }
