
import re
from uuid import uuid4


def normalize_claim(text: str) -> str:
    """Normalize whitespace while preserving the original claim separately."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    # Collapse repeated whitespace and remove surrounding whitespace.
    return re.sub(r"\s+", " ", text).strip()


def extract_claims(input_text: str) -> list[dict[str, str]]:
    """
    Split input text into candidate claims and assign unique claim IDs.

    This is a lightweight baseline. It does not determine whether claims
    are factual or whether they are true.
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a string")

    if not input_text.strip():
        return []

    parts = re.split(r"(?<=[.!?])\s+", input_text.strip())

    claims = []
    for part in parts:
        original_text = part.strip()
        if not original_text:
            continue

        claims.append({
            "claim_id": f"C-{uuid4().hex[:12]}",
            "text": original_text,
            "normalized_text": normalize_claim(original_text),
        })

    return claims
