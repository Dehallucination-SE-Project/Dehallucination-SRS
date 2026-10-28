
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


def explain_response_risk(
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Explain the response risk score and the contribution of each claim.

    This provides deterministic, rule-based explanations. It does not
    independently verify whether the claims are factually correct.
    """
    risk = calculate_response_risk(claims)

    if not claims:
        return {
            **risk,
            "explanation": (
                "No claims were provided, so there is no claim-based "
                "risk to assess."
            ),
            "claim_explanations": [],
        }

    claim_explanations = []

    for index, claim in enumerate(claims, start=1):
        verdict = claim["verdict"]
        impact = claim.get("impact_level", "medium").lower()

        claim_text = claim.get(
            "normalized_text",
            claim.get("text", f"Claim {index}"),
        )

        if not isinstance(claim_text, str) or not claim_text.strip():
            claim_text = f"Claim {index}"

        if verdict == "Supported":
            reason = (
                "The claim is marked Supported, so it contributes "
                "relatively little risk."
            )
        elif verdict == "Contradicted":
            reason = (
                "The claim is marked Contradicted, so it contributes "
                "the highest base risk."
            )
        elif verdict == "Uncertain":
            reason = (
                "The claim has an Uncertain verdict, indicating mixed "
                "evidence and elevated risk."
            )
        else:
            reason = (
                "The claim is Unverifiable, meaning the available "
                "evidence does not establish its validity."
            )

        if impact == "high":
            reason += " Its high impact increases its risk contribution."
        elif impact == "low":
            reason += " Its low impact reduces its risk contribution."
        else:
            reason += " Its medium impact uses the standard impact weight."

        claim_explanations.append({
            "claim_id": claim.get("claim_id", f"C-{index:03d}"),
            "claim_text": claim_text,
            "verdict": verdict,
            "impact_level": impact,
            "base_risk": VERDICT_RISK[verdict],
            "impact_weight": IMPACT_WEIGHTS[impact],
            "explanation": reason,
        })

    contradicted = risk["contradicted_count"]
    uncertain = risk["uncertain_count"]
    unverifiable = risk["unverifiable_count"]

    summary_parts = []

    if contradicted:
        summary_parts.append(
            f"{contradicted} Contradicted claim(s)"
        )
    if uncertain:
        summary_parts.append(
            f"{uncertain} uncertain claim(s)"
        )
    if unverifiable:
        summary_parts.append(
            f"{unverifiable} unverifiable claim(s)"
        )

    if summary_parts:
        contributing_claims = ", ".join(summary_parts)
        explanation = (
            f"The response has a {risk['risk_level']} risk level "
            f"(score: {risk['risk_score']:.3f}). "
            f"Risk is influenced by {contributing_claims}. "
            "Claim impact levels adjust their risk contributions."
        )
    else:
        explanation = (
            f"The response has a {risk['risk_level']} risk level "
            f"(score: {risk['risk_score']:.3f}). "
            "All claims are marked Supported, which contributes "
            "relatively little risk under the current scoring rules."
        )

    return {
        **risk,
        "explanation": explanation,
        "claim_explanations": claim_explanations,
    }
