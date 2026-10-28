
from typing import Any


VALID_ASSESSMENTS = {"supports", "contradicts", "insufficient"}
VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}

# Number of consistent, usable evidence items needed to reach
# the maximum baseline confidence score.
CONFIDENCE_EVIDENCE_TARGET = 3


def _validate_evidence(evidence: list[dict[str, Any]]) -> list[str]:
    """Validate evidence items and return their assessments."""
    if not isinstance(evidence, list):
        raise TypeError("evidence must be a list")

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

    return assessments


def assign_verdict(evidence: list[dict[str, Any]]) -> str:
    """
    Assign a verdict from explicit evidence assessments.

    Evidence marked insufficient does not count as support or
    contradiction. Conflicting usable evidence produces Uncertain.
    """
    assessments = _validate_evidence(evidence)

    if not assessments:
        return "Unverifiable"

    has_support = "supports" in assessments
    has_contradiction = "contradicts" in assessments

    if has_support and has_contradiction:
        return "Uncertain"

    if has_support:
        return "Supported"

    if has_contradiction:
        return "Contradicted"

    return "Unverifiable"


def calculate_confidence_score(
    evidence: list[dict[str, Any]],
) -> float:
    """
    Calculate a deterministic baseline confidence score from 0.0 to 1.0.

    The score reflects the amount and consistency of usable evidence.
    It is not a calibrated probability that a claim is true.

    - No usable evidence: 0.0
    - More consistent usable evidence: higher score
    - Mixed supporting and contradicting evidence: lower score
    - Insufficient evidence does not increase the score
    """
    assessments = _validate_evidence(evidence)

    supports = assessments.count("supports")
    contradicts = assessments.count("contradicts")
    usable_count = supports + contradicts

    if usable_count == 0:
        return 0.0

    consistency = max(supports, contradicts) / usable_count
    evidence_coverage = min(
        usable_count / CONFIDENCE_EVIDENCE_TARGET,
        1.0,
    )

    score = consistency * evidence_coverage
    return round(score, 3)


def evaluate_claim(
    claim: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a claim with its verdict and confidence score attached."""
    if not isinstance(claim, dict):
        raise TypeError("claim must be a dictionary")

    claim_text = claim.get("normalized_text", claim.get("text"))

    if not isinstance(claim_text, str) or not claim_text.strip():
        raise ValueError("claim must contain non-empty text")

    # Validate once before producing the result.
    assessments = _validate_evidence(evidence)

    result = dict(claim)
    result["verdict"] = assign_verdict(evidence)
    result["confidence_score"] = calculate_confidence_score(
        [{"assessment": assessment} for assessment in assessments]
    )

    return result
