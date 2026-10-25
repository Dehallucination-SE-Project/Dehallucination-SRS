
"""Adapters for retrieving evidence from configured sources.

The local adapter is suitable for development and testing. It searches
a supplied collection of evidence items; it does not access the internet
or an external knowledge graph.

Retrieved evidence includes source_id, label, and retrieved_at metadata.
"""

from datetime import datetime, timezone
from typing import Any, Protocol


EvidenceItem = dict[str, Any]


class EvidenceSourceUnavailableError(RuntimeError):
    """Raised when an evidence source cannot be used."""


class EvidenceSource(Protocol):
    """Interface that evidence sources must implement."""

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Return evidence relevant to the supplied query."""
        ...


def _validate_query(query: str) -> None:
    """Reject queries that are not usable."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    if not query.strip():
        raise ValueError("query must not be blank")


def _add_evidence_metadata(
    item: EvidenceItem,
    source_id: str,
    label: str,
    retrieved_at: datetime,
) -> EvidenceItem:
    """Return a copy of an evidence item with retrieval metadata."""
    result = dict(item)
    result["source_id"] = source_id
    result["label"] = label
    result["retrieved_at"] = retrieved_at.isoformat()
    return result


class LocalEvidenceAdapter:
    """Retrieve matching evidence from a local collection."""

    def __init__(
        self,
        evidence_items: list[EvidenceItem],
        source_id: str = "local",
        label: str = "Local evidence",
    ) -> None:
        if not isinstance(evidence_items, list):
            raise TypeError("evidence_items must be a list")

        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(label, str) or not label.strip():
            raise ValueError("label must be a non-empty string")

        for item in evidence_items:
            if not isinstance(item, dict):
                raise TypeError("each evidence item must be a dictionary")

            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    "each evidence item must contain non-empty text"
                )

        # Copy items so external changes do not modify stored evidence.
        self._evidence_items = [dict(item) for item in evidence_items]
        self.source_id = source_id.strip()
        self.label = label.strip()

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Return matching items with source and retrieval metadata."""
        _validate_query(query)

        query_words = set(query.casefold().split())
        matches = []

        for item in self._evidence_items:
            evidence_words = set(item["text"].casefold().split())

            if query_words.intersection(evidence_words):
                matches.append(item)

        # Use one UTC timestamp for this retrieval operation.
        retrieved_at = datetime.now(timezone.utc)

        return [
            _add_evidence_metadata(
                item,
                source_id=self.source_id,
                label=self.label,
                retrieved_at=retrieved_at,
            )
            for item in matches
        ]


class UnavailableEvidenceAdapter:
    """Represent a source that has not been configured or is unavailable."""

    def __init__(self, source_name: str = "evidence source") -> None:
        self.source_name = source_name

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Raise an explicit error instead of pretending retrieval worked."""
        _validate_query(query)

        raise EvidenceSourceUnavailableError(
            f"{self.source_name} is not configured or is unavailable"
        )
