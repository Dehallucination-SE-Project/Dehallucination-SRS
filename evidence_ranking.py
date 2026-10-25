
"""Rank evidence using configurable relevance and source-credibility signals."""

import re
from typing import Any, Mapping, Sequence


EvidenceItem = dict[str, Any]


def _tokens(text: str) -> set[str]:
    """Return lowercase alphanumeric tokens from text."""
    return set(re.findall(r"\b\w+\b", text.casefold()))


def rank_evidence(
    query: str,
    evidence_items: Sequence[EvidenceItem],
    source_credibility: Mapping[str, float] | None = None,
    *,
    relevance_weight: float = 0.7,
    credibility_weight: float = 0.3,
) -> list[EvidenceItem]:
    """Return evidence ranked by weighted relevance and source credibility.

    Relevance is the fraction of distinct query tokens present in evidence.
    Credibility is a configured score from 0.0 to 1.0, looked up by source_id.
    Evidence fields and metadata are preserved in the returned copies.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        raise ValueError("query must not be blank")

    if not isinstance(evidence_items, (list, tuple)):
        raise TypeError("evidence_items must be a list or tuple")

    if not 0 <= relevance_weight <= 1:
        raise ValueError("relevance_weight must be between 0 and 1")
    if not 0 <= credibility_weight <= 1:
        raise ValueError("credibility_weight must be between 0 and 1")
    if relevance_weight + credibility_weight <= 0:
        raise ValueError("at least one ranking weight must be positive")

    if source_credibility is None:
        source_credibility = {}
    if not isinstance(source_credibility, Mapping):
        raise TypeError("source_credibility must be a mapping")

    for source_id, score in source_credibility.items():
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source IDs must be non-empty strings")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise TypeError("credibility scores must be numeric")
        if not 0 <= score <= 1:
            raise ValueError("credibility scores must be between 0 and 1")

    query_tokens = _tokens(query)
    if not query_tokens:
        raise ValueError("query must contain at least one searchable token")

    total_weight = relevance_weight + credibility_weight
    ranked: list[tuple[float, int, EvidenceItem]] = []

    for index, item in enumerate(evidence_items):
        if not isinstance(item, dict):
            raise TypeError("each evidence item must be a dictionary")

        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("each evidence item must contain non-empty text")

        evidence_tokens = _tokens(text)
        relevance = len(query_tokens & evidence_tokens) / len(query_tokens)

        source_id = item.get("source_id", "")
        credibility = source_credibility.get(source_id, 0.0)

        score = (
            relevance_weight * relevance
            + credibility_weight * credibility
        ) / total_weight

        result = dict(item)
        result["relevance_score"] = relevance
        result["credibility_score"] = credibility
        result["ranking_score"] = score

        # Original index provides stable ordering for tied scores.
        ranked.append((score, index, result))

    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item for _, _, item in ranked]
