"""Judge interface and the fake deterministic judge used for the dry run.

No real API client is implemented here yet -- by design.  A real judge adapter
will be added only after the preregistration is approved, and must satisfy the
same ``Judge`` protocol: it receives the rendered prompt and an opaque call
key, and returns the raw response text verbatim.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class Judge(Protocol):
    name: str

    def score(self, prompt: str, call_key: str) -> str:
        """Return the raw response text for one rendered prompt."""
        ...


@dataclass(frozen=True)
class FakeDeterministicJudge:
    """Deterministic local pseudo-judge for end-to-end dry runs.

    The returned score is a pure function of (name, prompt text): a SHA-256
    of both selects a category in 1..6.  It sees exactly what a real judge
    would see -- the rendered prompt -- and nothing else, so a dry run
    exercises the same information flow as the real experiment.

    ``invalid_every``: if > 0, every k-th call (by hash, deterministic)
    returns a malformed response, to exercise the exclusion path.
    """

    name: str = "fake-deterministic-v1"
    invalid_every: int = 0

    def score(self, prompt: str, call_key: str) -> str:
        digest = hashlib.sha256(
            (self.name + "\x00" + prompt).encode("utf-8")
        ).digest()
        if self.invalid_every > 0:
            gate = int.from_bytes(digest[8:12], "big") % self.invalid_every
            if gate == 0:
                return "I think this essay deserves a 4 out of 6."
        return f'{{"score": {1 + digest[0] % 6}}}'

