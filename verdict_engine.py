
from typing import Any


VALID_ASSESSMENTS = {"supports", "contradicts", "insufficient"}
VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}


def assign_verdict(evidence: list[dict[str, Any]]) -> str:
    """
    Assign a verdict from explicit evidence assessments.

    Each evidence item must contain an assessment:
      - supports
      - contradicts
      - insufficient

    Evidence marked insufficient does not count as support or contradiction.
    No usable evidence results in Unverifiable.
    """
    if not isinstance(evidence, list):
        raise TypeError("evidence must be a list")

    if not evidence:
        return "Unverifiable"

    assessments = []

    for item in evidence:
        if not isinstance(item, dict):
            raise TypeError("each evidence item must be a dictionary")

        assessment = item.get("assessment")

        if assessment not in VALID_ASSESSMENTS:
            raise ValueError(
                f"assessment must be one of {sorted(VALID_ASSESSMENTS)}"
            )

        assessments.append(assessment)

    has_support = "supports" in assessments
    has_contradiction = "contradicts" in assessments

    if has_support and has_contradiction:
        return "Uncertain"

    if has_support:
        return "Supported"

    if has_contradiction:
        return "Contradicted"

    return "Unverifiable"


def evaluate_claim(
    claim: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a claim with its evidence-based verdict attached."""
    if not isinstance(claim, dict):
        raise TypeError("claim must be a dictionary")

    claim_text = claim.get("normalized_text", claim.get("text"))

    if not isinstance(claim_text, str) or not claim_text.strip():
        raise ValueError("claim must contain non-empty text")

    result = dict(claim)
    result["verdict"] = assign_verdict(evidence)
    return result
