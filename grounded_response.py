
"""Conservative evidence-grounded response generation.

This baseline uses verdicts and evidence supplied by the existing
verification pipeline. It does not independently establish factual truth
or generate unsupported replacement facts.
"""

from typing import Any


VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}


def generate_grounded_response(
    claims: list[dict[str, Any]],
    enabled: bool = True,
) -> dict[str, Any]:
    """Build a response using only claims marked Supported.

    Claims with other verdicts are reported separately rather than
    rewritten using facts that have not been established by evidence.
    """
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
            "message": "Grounded response generation is disabled.",
        }

    included_claims = []
    excluded_claims = []
    citations = []
    seen_citations = set()

    for index, claim in enumerate(claims, start=1):
        claim_id = claim.get("claim_id", f"C-{index:03d}")
        text = claim.get("normalized_text", claim.get("text")).strip()
        verdict = claim["verdict"]

        if verdict != "Supported":
            excluded_claims.append({
                "claim_id": claim_id,
                "text": text,
                "verdict": verdict,
                "reason": (
                    "Claim excluded because it is not marked Supported."
                ),
            })
            continue

        included_claims.append({
            "claim_id": claim_id,
            "text": text,
        })

        for item in claim.get("evidence", []):
            source_id = item.get("source_id")
            label = item.get("label")

            # Do not fabricate source references.
            if not source_id and not label:
                continue

            citation_key = (source_id, label)
            if citation_key in seen_citations:
                continue

            seen_citations.add(citation_key)
            citation = {}

            if source_id:
                citation["source_id"] = source_id
            if label:
                citation["label"] = label

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

    return {
        "enabled": True,
        "grounded_response": response_text,
        "included_claim_ids": [
            claim["claim_id"] for claim in included_claims
        ],
        "excluded_claims": excluded_claims,
        "citations": citations,
        "message": message,
    }
