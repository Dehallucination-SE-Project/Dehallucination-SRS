
import re
from typing import Any


NEGATION_WORDS = {
    "not", "never", "no", "neither", "nor", "without",
    "cannot", "can't", "dont", "don't", "doesnt", "doesn't",
    "didnt", "didn't", "isnt", "isn't", "arent", "aren't",
    "wasnt", "wasn't", "werent", "weren't", "wont", "won't",
    "shouldnt", "shouldn't", "wouldnt", "wouldn't",
}

CONTRACTION_EXPANSIONS = {
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "doesn't": "does not",
    "don't": "do not",
    "didn't": "did not",
    "can't": "can not",
    "cannot": "can not",
    "won't": "will not",
    "shouldn't": "should not",
    "wouldn't": "would not",
}


def _tokens(text: str) -> list[str]:
    """Create lowercase word/number tokens with common contractions expanded."""
    text = text.casefold()

    for contraction, expansion in CONTRACTION_EXPANSIONS.items():
        text = re.sub(
            rf"\b{re.escape(contraction)}\b",
            expansion,
            text,
        )

    return re.findall(r"\b[\w]+(?:\.[\w]+)?\b", text)


def _negation_count(tokens: list[str]) -> int:
    """Count explicit negation cues in a claim."""
    return sum(token in NEGATION_WORDS for token in tokens)


def _content_tokens(tokens: list[str]) -> list[str]:
    """Remove explicit negation cues to compare the remaining wording."""
    return [token for token in tokens if token not in NEGATION_WORDS]


def _numeric_values(tokens: list[str]) -> list[str]:
    """Return number-like tokens in their original order."""
    return [
        token for token in tokens
        if re.fullmatch(r"\d+(?:\.\d+)?", token)
    ]




def _is_clear_contradiction(text_a: str, text_b: str) -> str | None:
    """Detect explicit negation and conflicting numeric values."""
    tokens_a = _tokens(text_a)
    tokens_b = _tokens(text_b)

    if not tokens_a or not tokens_b:
        return None

    content_a = _content_tokens(tokens_a)
    content_b = _content_tokens(tokens_b)

    # Opposite explicit negation, with otherwise matching content.
    if content_a == content_b:
        negated_a = _negation_count(tokens_a) % 2 == 1
        negated_b = _negation_count(tokens_b) % 2 == 1

        if negated_a != negated_b:
            return "opposite_explicit_negation"

    # Conflicting numeric values when the surrounding wording matches.
    numbers_a = _numeric_values(tokens_a)
    numbers_b = _numeric_values(tokens_b)

    if (
        numbers_a
        and numbers_b
        and len(numbers_a) == len(numbers_b)
        and numbers_a != numbers_b
    ):
        words_a = [token for token in tokens_a if not token.replace(".", "", 1).isdigit()]
        words_b = [token for token in tokens_b if not token.replace(".", "", 1).isdigit()]

        if words_a == words_b:
            return "conflicting_numeric_values"

    return None



def detect_contradictions(
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Return pairs of claims that match the baseline contradiction rules.

    Each claim must contain non-empty text or normalized_text.
    Both original statements and their IDs are preserved in each conflict.
    """
    if not isinstance(claims, list):
        raise TypeError("claims must be a list")

    prepared = []

    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("each claim must be a dictionary")

        text = claim.get("normalized_text", claim.get("text"))

        if not isinstance(text, str) or not text.strip():
            raise ValueError("each claim must contain non-empty text")

        prepared.append({
            "claim_id": claim.get("claim_id"),
            "text": claim.get("text", text),
            "comparison_text": text,
        })

    conflicts = []

    for i, first in enumerate(prepared):
        for second in prepared[i + 1:]:
            reason = _is_clear_contradiction(
                first["comparison_text"],
                second["comparison_text"],
            )

            if reason is not None:
                conflicts.append({
                    "claim_a_id": first["claim_id"],
                    "claim_a_text": first["text"],
                    "claim_b_id": second["claim_id"],
                    "claim_b_text": second["text"],
                    "reason": reason,
                })

    return conflicts
