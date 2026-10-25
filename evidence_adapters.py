
"""Adapters for retrieving evidence from configured sources.

The local adapter is suitable for development and testing. It searches
a supplied collection of evidence items; it does not access the internet
or an external knowledge graph.
"""

from typing import Any, Protocol


EvidenceItem = dict[str, Any]


class EvidenceSourceUnavailableError(RuntimeError):
    """Raised when an evidence source cannot be used."""


class EvidenceSource(Protocol):
    """Interface that evidence sources must implement."""

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Return evidence relevant to the supplied query."""
        ...


class LocalEvidenceAdapter:
    """Retrieve matching evidence from a local collection."""

    def __init__(self, evidence_items: list[EvidenceItem]) -> None:
        if not isinstance(evidence_items, list):
            raise TypeError("evidence_items must be a list")

        for item in evidence_items:
            if not isinstance(item, dict):
                raise TypeError("each evidence item must be a dictionary")

            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    "each evidence item must contain non-empty text"
                )

        # Keep copies so external changes do not modify stored evidence.
        self._evidence_items = [dict(item) for item in evidence_items]

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Return items whose text shares a word with the query."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        if not query.strip():
            raise ValueError("query must not be blank")

        query_words = set(query.casefold().split())
        matches = []

        for item in self._evidence_items:
            evidence_words = set(item["text"].casefold().split())

            if query_words.intersection(evidence_words):
                matches.append(dict(item))

        return matches


class UnavailableEvidenceAdapter:
    """Represent a source that has not been configured or is unavailable."""

    def __init__(self, source_name: str = "evidence source") -> None:
        self.source_name = source_name

    def retrieve(self, query: str) -> list[EvidenceItem]:
        """Raise an explicit error instead of pretending retrieval worked."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        if not query.strip():
            raise ValueError("query must not be blank")

        raise EvidenceSourceUnavailableError(
            f"{self.source_name} is not configured or is unavailable"
        )
