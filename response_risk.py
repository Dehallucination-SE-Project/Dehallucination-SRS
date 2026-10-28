
from typing import Any


VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}

VERDICT_RISK = {
    "Supported": 0.10,
    "Contradicted": 1.00,
    "Uncertain": 0.60,
    "Unverifiable": 0.45,
}

IMPACT_WEIGHTS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.0,
}


def calculate_response_risk(
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate a deterministic, impact-sensitive response risk score."""
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    if not claims:
        return {
            "risk_score": 0.0,
            "risk_level": "low",
            "claim_count": 0,
            "contradicted_count": 0,
            "uncertain_count": 0,
            "unverifiable_count": 0,
        }

    total_risk = 0.0
    total_weight = 0.0
    counts = {
        "Supported": 0,
        "Contradicted": 0,
        "Uncertain": 0,
        "Unverifiable": 0,
    }

    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("each claim must be a dictionary")

        verdict = claim.get("verdict")
        if verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(VALID_VERDICTS)}"
            )

        impact = claim.get("impact_level", "medium")
        if not isinstance(impact, str):
            raise ValueError("impact_level must be a string")

        impact = impact.lower()
        if impact not in IMPACT_WEIGHTS:
            raise ValueError(
                f"impact_level must be one of {sorted(IMPACT_WEIGHTS)}"
            )

        
        weight = IMPACT_WEIGHTS[impact]

        # Normalize impact so high-impact claims contribute more risk.
        total_risk += VERDICT_RISK[verdict] * (weight / 2.0)
        total_weight += 1.0
        counts[verdict] += 1

    score = round(total_risk / total_weight, 3)


    if score >= 0.70:
        level = "high"
    elif score >= 0.35:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": score,
        "risk_level": level,
        "claim_count": len(claims),
        "contradicted_count": counts["Contradicted"],
        "uncertain_count": counts["Uncertain"],
        "unverifiable_count": counts["Unverifiable"],
    }
