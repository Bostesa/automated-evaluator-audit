"""Strict parsing of judge responses.

An invalid response is an *exclusion event*, never repaired: no retries with
relaxed regexes, no clamping, no imputation.  The preregistered exclusion rule
is exactly: keep iff the whole response (after stripping whitespace) is
``SCORE: k`` with k an integer 1..6.
"""

from __future__ import annotations

import re

_PATTERN = re.compile(r"\ASCORE:\s*([1-6])\Z")


class ParseError(ValueError):
    """Raised when a judge response does not match the frozen format."""


def parse_score(raw_response: str) -> int:
    match = _PATTERN.match(raw_response.strip())
    if match is None:
        raise ParseError(f"response does not match 'SCORE: <1-6>': {raw_response[:80]!r}")
    return int(match.group(1))
