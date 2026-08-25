"""Deterministic, attribute-free sample selection from the usable strata.

Design (preregistered):

* Population: essays with non-missing prompt, human holistic score, and ELL
  status, lying in a USABLE ``(prompt, human_score)`` stratum -- one with at
  least two essays and both ELL categories observed.  The usable-stratum
  definition is the ONLY place the attribute is consulted, and it is consulted
  at the population level (feasibility stage, before sampling), not per essay:
  the same 61 strata are usable for every seed and every n.
* Allocation: proportional to stratum size by the largest-remainder
  (Hamilton) method, so stratum shares in the sample match the population as
  closely as integer counts allow.
* Within-stratum: simple random sampling WITHOUT replacement, using an
  independent, position-addressed seed per stratum
  (``SeedSequence(entropy=seed, spawn_key=(stratum_index,))``), so the draw
  for one stratum does not depend on iteration order or on other strata.

Attribute-freeness: individual essays are never selected on ``ell_status``.
The test suite verifies that permuting the ``ell_status`` column of the input
leaves the selected essay-ID set unchanged.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SampleManifest:
    """The scoring manifest: which essays to score, and nothing else.

    Deliberately excludes ELL status and the human holistic score -- the
    scoring stage has no need for either, and excluding them here means a
    leak would require actively re-joining the data.
    """

    essay_ids: tuple[str, ...]
    prompt_names: tuple[str, ...]
    tasks: tuple[str, ...]
    seed: int
    n_requested: int

    def write_csv(self, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["essay_id_comp", "prompt_name", "task"])
            for row in zip(self.essay_ids, self.prompt_names, self.tasks):
                writer.writerow(row)


def _complete(row: dict[str, str]) -> bool:
    return bool(
        row["ell_status"].strip()
        and row["prompt_name"].strip()
        and row["holistic_essay_score"].strip()
    )


def usable_strata(
    rows: list[dict[str, str]], task: str | None = None
) -> dict[tuple[str, str], list[int]]:
    """Map each usable ``(prompt, human_score)`` stratum to member row indices.

    Usable: >= 2 essays and both ELL categories present.  This is the same
    definition used by the feasibility analysis and by ``Strata.n_usable``.
    ``task`` restricts the population to one writing task (the revised
    primary design uses ``"Independent"`` -- see docs/preregistration.md §3).
    """
    members: dict[tuple[str, str], list[int]] = defaultdict(list)
    ell_yes: Counter[tuple[str, str]] = Counter()
    for i, row in enumerate(rows):
        if not _complete(row):
            continue
        if task is not None and row["task"] != task:
            continue
        key = (row["prompt_name"], row["holistic_essay_score"])
        members[key].append(i)
        if row["ell_status"] == "Yes":
            ell_yes[key] += 1
    return {
        key: idx
        for key, idx in members.items()
        if len(idx) >= 2 and 0 < ell_yes[key] < len(idx)
    }


def _largest_remainder(sizes: list[int], n: int) -> list[int]:
    """Proportional integer allocation of ``n`` by largest remainder."""
    total = sum(sizes)
    exact = [n * s / total for s in sizes]
    counts = [int(e) for e in exact]
    counts = [min(c, s) for c, s in zip(counts, sizes)]
    shortfall = n - sum(counts)
    remainders = sorted(
        range(len(sizes)),
        key=lambda i: (exact[i] - int(exact[i]), i),
        reverse=True,
    )
    for i in remainders:
        if shortfall == 0:
            break
        if counts[i] < sizes[i]:
            counts[i] += 1
            shortfall -= 1
    if shortfall:  # pragma: no cover - n <= population guaranteed by caller
        raise ValueError("allocation failed; n exceeds population")
    return counts


def draw_primary_sample(
    essay_level_csv: Path, n: int, seed: int, task: str | None = None
) -> SampleManifest:
    """Draw the preregistered primary sample.  Deterministic given ``seed``.

    With ``n`` equal to the full usable-pool size the draw is a census: the
    allocation gives every stratum its full membership and the within-stratum
    draw selects everyone, independent of ``seed``.
    """
    with essay_level_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    strata = usable_strata(rows, task=task)
    keys = sorted(strata)  # deterministic stratum order and index
    sizes = [len(strata[k]) for k in keys]
    if not 0 < n <= sum(sizes):
        raise ValueError(f"n must be in (0, {sum(sizes)}], got {n}")
    counts = _largest_remainder(sizes, n)

    chosen: list[int] = []
    for stratum_index, (key, count) in enumerate(zip(keys, counts)):
        if count == 0:
            continue
        # Sort member ids so the draw depends only on stratum content, never
        # on input row order.
        member_ids = sorted(rows[i]["essay_id_comp"] for i in strata[key])
        rng = np.random.default_rng(
            np.random.SeedSequence(entropy=seed, spawn_key=(stratum_index,))
        )
        picked = rng.choice(len(member_ids), size=count, replace=False)
        by_id = {rows[i]["essay_id_comp"]: i for i in strata[key]}
        chosen.extend(by_id[member_ids[j]] for j in sorted(picked))

    chosen.sort(key=lambda i: rows[i]["essay_id_comp"])
    return SampleManifest(
        essay_ids=tuple(rows[i]["essay_id_comp"] for i in chosen),
        prompt_names=tuple(rows[i]["prompt_name"] for i in chosen),
        tasks=tuple(rows[i]["task"] for i in chosen),
        seed=seed,
        n_requested=n,
    )
