"""Strict parsing of judge responses.

An invalid response is an *exclusion event*, never repaired: no retries with
relaxed regexes, no clamping, no imputation.  The preregistered exclusion
rule (pre-scoring amendment v3, structured output) is exactly: keep iff the
whole response parses as a JSON object with the single key ``score`` and an
integer value in 1..6.
"""

from __future__ import annotations

import json


class ParseError(ValueError):
    """Raised when a judge response does not match the frozen format."""


def parse_score(raw_response: str) -> int:
    try:
        obj = json.loads(raw_response.strip())
    except json.JSONDecodeError as err:
        raise ParseError(
            f"response is not valid JSON: {raw_response[:80]!r}"
        ) from err
    if not isinstance(obj, dict) or set(obj) != {"score"}:
        raise ParseError(
            f"response is not an object with the single key \'score\': "
            f"{raw_response[:80]!r}"
        )
    score = obj["score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 6:
        raise ParseError(f"score is not an integer in 1..6: {score!r}")
    return score
