
import re
from uuid import uuid4


def extract_claims(input_text: str) -> list[dict[str, str]]:
    """
    Split input text into candidate factual claims and assign claim IDs.

    This is a lightweight baseline, not a full natural-language
    understanding or fact-checking system.
    """
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a string")

    if not input_text.strip():
        return []

    # Split on sentence-ending punctuation when followed by whitespace
    # or the end of the input. Keep common abbreviations from splitting
    # where practical; advanced language processing can be added later.
    parts = re.split(r"(?<=[.!?])\s+", input_text.strip())

    claims = []
    for part in parts:
        text = part.strip()
        if not text:
            continue

        claims.append({
            "claim_id": f"C-{uuid4().hex[:12]}",
            "text": text,
        })

    return claims
