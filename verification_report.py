
"""Build a structured verification report from existing pipeline results.

This module formats supplied claims, verdicts, scores, evidence, citations,
and warnings. It does not independently verify factual claims.
"""

from typing import Any

from evidence_citations import build_evidence_citations


VALID_VERDICTS = {
    "Supported",
    "Contradicted",
    "Uncertain",
    "Unverifiable",
}


def generate_verification_report(
    claims: list[dict[str, Any]],
    risk_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a report using the verdicts and evidence already supplied."""
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    if risk_summary is not None and not isinstance(risk_summary, dict):
        raise TypeError("risk_summary must be a dictionary or None")

    report_claims = []
    warnings = []
    evidence_items = []
    counts = {verdict: 0 for verdict in VALID_VERDICTS}

    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise TypeError("each claim must be a dictionary")

        claim_id = claim.get("claim_id", f"C-{index:03d}")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("claim_id must be a non-empty string")

        text = claim.get("normalized_text", claim.get("text"))
        if not isinstance(text, str) or not text.strip():
            raise ValueError("each claim must contain non-empty text")

        verdict = claim.get("verdict")
        if verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(VALID_VERDICTS)}"
            )

        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise TypeError("claim evidence must be a list")

        for item in evidence:
            if not isinstance(item, dict):
                raise TypeError("each evidence item must be a dictionary")
            evidence_items.append({
                "claim_id": claim_id,
                **item,
            })

        report_claim = dict(claim)
        report_claim["claim_id"] = claim_id
        report_claim["text"] = text.strip()
        report_claim["verdict"] = verdict
        report_claim["evidence"] = evidence
        report_claims.append(report_claim)
        counts[verdict] += 1

        if verdict != "Supported":
            warning_messages = {
                "Contradicted": "The claim is contradicted by the supplied assessment.",
                "Uncertain": "The supplied evidence does not establish a consistent verdict.",
                "Unverifiable": "The claim could not be verified from the supplied evidence.",
            }
            warnings.append({
                "claim_id": claim_id,
                "verdict": verdict,
                "message": warning_messages[verdict],
            })

    citation_groups = build_evidence_citations(report_claims)

    return {
        "report_type": "verification_report",
        "claim_count": len(report_claims),
        "verdict_summary": {
            "supported": counts["Supported"],
            "contradicted": counts["Contradicted"],
            "uncertain": counts["Uncertain"],
            "unverifiable": counts["Unverifiable"],
        },
        "claims": report_claims,
        "evidence": evidence_items,
        "citations": citation_groups,
        "warnings": warnings,
        "risk_summary": dict(risk_summary) if risk_summary is not None else None,
        "message": (
            "Report generated from supplied pipeline results; "
            "it does not independently establish factual truth."
        ),
    }
