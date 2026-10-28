
"""Conservative evidence-grounded response generation.

Only claims marked Supported are included in the grounded response.
Other claims receive explicit warnings and are not presented as verified.
"""

from typing import Any

from evidence_citations import build_evidence_citations


VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}

UNCERTAINTY_WARNINGS = {
    "Contradicted": "Warning: evidence contradicts this claim.",
    "Uncertain": "Warning: evidence is conflicting; this claim is uncertain.",
    "Unverifiable": "Warning: this claim could not be verified from available evidence.",
}


def generate_grounded_response(
    claims: list[dict[str, Any]],
    enabled: bool = True,
) -> dict[str, Any]:
    """Build a response from supported claims and warn about other claims."""
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    if not isinstance(enabled, bool):
        raise TypeError("enabled must be a boolean")

    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("each claim must be a dictionary")

        verdict = claim.get("verdict")
        if verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(VALID_VERDICTS)}"
            )

        text = claim.get("normalized_text", claim.get("text"))
        if not isinstance(text, str) or not text.strip():
            raise ValueError("each claim must contain non-empty text")

        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise TypeError("claim evidence must be a list")

        for item in evidence:
            if not isinstance(item, dict):
                raise TypeError(
                    "each evidence item must be a dictionary"
                )

    if not enabled:
        original_claims = [
            claim.get("text", claim.get("normalized_text"))
            for claim in claims
        ]
        return {
            "enabled": False,
            "grounded_response": " ".join(original_claims),
            "included_claim_ids": [
                claim.get("claim_id") for claim in claims
            ],
            "excluded_claims": [],
            "citations": [],
            "warnings": [],
            "message": "Grounded response generation is disabled.",
        }

    included_claims = []
    excluded_claims = []
    supported_claims_for_citations = []
    warnings = []

    for index, claim in enumerate(claims, start=1):
        claim_id = claim.get("claim_id", f"C-{index:03d}")
        text = claim.get(
            "normalized_text",
            claim.get("text"),
        ).strip()
        verdict = claim["verdict"]

        if verdict != "Supported":
            warning = UNCERTAINTY_WARNINGS[verdict]

            excluded_claims.append({
                "claim_id": claim_id,
                "text": text,
                "verdict": verdict,
                "reason": warning,
            })

            warnings.append({
                "claim_id": claim_id,
                "verdict": verdict,
                "text": text,
                "warning": warning,
            })
            continue

        included_claims.append({
            "claim_id": claim_id,
            "text": text,
        })

        supported_claim = dict(claim)
        supported_claim["claim_id"] = claim_id
        supported_claims_for_citations.append(supported_claim)

    grouped_citations = build_evidence_citations(
        supported_claims_for_citations
    )

    # Preserve the existing flat citation response format.
    citations = []
    seen_citations = set()

    for group in grouped_citations:
        for citation in group["citations"]:
            key = tuple(
                (field, repr(citation[field]))
                for field in sorted(citation)
            )

            if key in seen_citations:
                continue

            seen_citations.add(key)
            citations.append(citation)

    if included_claims:
        response_text = " ".join(
            claim["text"] for claim in included_claims
        )
        message = (
            "Response contains only claims marked Supported by the "
            "verification pipeline. This verdict is only as reliable "
            "as the evidence assessment supplied to the pipeline."
        )
    else:
        response_text = (
            "A grounded response cannot be provided because no claims "
            "were marked Supported by the verification pipeline."
        )
        message = (
            "No supported claims were available. No replacement facts "
            "were invented."
        )

    if warnings:
        message += (
            f" {len(warnings)} claim(s) require caution because they "
            "were contradicted, uncertain, or unverifiable."
        )

    return {
        "enabled": True,
        "grounded_response": response_text,
        "included_claim_ids": [
            claim["claim_id"] for claim in included_claims
        ],
        "excluded_claims": excluded_claims,
        "citations": citations,
        "warnings": warnings,
        "message": message,
    }
