
import re
from typing import Any


def classify_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """
    Assign a preliminary claim type using transparent rule-based cues.

    This is a baseline classifier, not an AI model and not a fact checker.
    It preserves the input fields and adds the claim_type field.
    """
    if not isinstance(claim, dict):
        raise TypeError("claim must be a dictionary")

    if not isinstance(claim.get("text"), str) or not claim["text"].strip():
        raise ValueError("claim must contain non-empty text")

    text = claim.get("normalized_text", claim["text"]).strip()
    lowered = text.casefold()

    # Classification is based on surface cues, so rule order matters.
    if re.search(r"\b(because|causes?|caused|causing|leads? to|results? in|due to)\b", lowered):
        claim_type = "causal"

    elif re.search(r"\b(more than|less than|greater than|higher than|lower than|compared with|compared to|faster than|slower than)\b", lowered):
        claim_type = "comparative"

    elif re.search(r"\b(yesterday|today|tomorrow|last year|next year|in \d{4}|during \d{4})\b", lowered):
        claim_type = "temporal"

    elif re.search(
        r"\b\d+(?:\.\d+)?\s*(?:%|percent\b|km\b|miles?\b|meters?\b|"
        r"metres?\b|kg\b|grams?\b|°c\b|°f\b|years?\b|months?\b|days?\b)",
        lowered,
    ):
        claim_type = "numerical"

    else:
        claim_type = "general_factual"

    result = dict(claim)
    result["claim_type"] = claim_type
    return result


def classify_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify multiple claims while preserving their IDs and other fields."""
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    return [classify_claim(claim) for claim in claims]
