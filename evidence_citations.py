
"""Build traceable, claim-level citations from retrieved evidence.

Only metadata actually present on evidence items is included. This module
does not invent URLs, source identifiers, or bibliographic details.
"""

from typing import Any


CITATION_FIELDS = (
    "source_id",
    "label",
    "url",
    "title",
    "retrieved_at",
)


def build_evidence_citations(
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return citations grouped by claim, preserving available source metadata."""
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    results = []

    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise TypeError("each claim must be a dictionary")

        claim_id = claim.get("claim_id", f"C-{index:03d}")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("claim_id must be a non-empty string")

        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise TypeError("claim evidence must be a list")

        citations = []
        seen = set()

        for item in evidence:
            if not isinstance(item, dict):
                raise TypeError("each evidence item must be a dictionary")

            citation = {
                field: item[field]
                for field in CITATION_FIELDS
                if field in item
                and item[field] is not None
                and item[field] != ""
            }

            if not citation:
                continue

            # Use a stable representation to handle unusual metadata values.
            key = tuple(
                (field, repr(citation[field]) if field in citation else None)
                for field in CITATION_FIELDS
            )

            if key in seen:
                continue

            seen.add(key)
            citations.append(citation)

        results.append({
            "claim_id": claim_id,
            "citations": citations,
        })

    return results
