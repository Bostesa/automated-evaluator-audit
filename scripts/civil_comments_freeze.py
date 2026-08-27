#!/usr/bin/env python
"""Civil Comments additional audit -- pre-scoring freeze (design stage).

Builds every pre-scoring artifact for the additional Civil Comments case
study of "What Else Do Automated Evaluators Measure?":

* ``results/civil_comments/primary_manifest.csv``      -- one comment per
  article, selected by a frozen A/Z/S-blind hash rule;
* ``results/civil_comments/negative_control_labels.csv`` -- one frozen
  random relabelling of each identity attribute within its exact-Z
  stratum of the primary sample (calibration sanity check);
* ``results/civil_comments/feasibility.json``          -- dataset facts,
  clustering diagnostics, and per-identity support counts under exact and
  binned Z, for the primary sample and the full census.

Everything here is computable without any evaluator score, and this
script never imports, downloads, or invokes Detoxify.  The frozen design
constants below are mirrored in ``config/civil_comments_additional_audit.json``
and prose-documented in ``docs/civil_comments_additional_audit_plan.md``.

Determinism: all randomness flows from ``numpy.random.SeedSequence`` with
the frozen entropy/spawn keys below; the sample selection itself uses
SHA-256 of a frozen seed string and is independent of any random state,
row order, comment text, label, or score.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from offcriterion.data import Strata  # noqa: E402
from offcriterion.permutation import permute_within_strata  # noqa: E402

# ---------------------------------------------------------------------------
# Frozen design constants (mirrored in config/civil_comments_additional_audit.json)
# ---------------------------------------------------------------------------

DATASET_CSV = REPO / "data" / "civil_comments" / "all_data_with_identities.csv"
DATASET_SHA256 = "403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f"
DATASET_ROWS = 448_000

RESULTS_DIR = REPO / "results" / "civil_comments"

#: Frozen seed string for the one-comment-per-article hash selection.
SELECTION_SEED_STRING = "civil-comments-additional-audit-v1"

#: Frozen base entropy for every SeedSequence in this study.
BASE_ENTROPY = 20260827

#: Frozen identity order.  Index i is the spawn-key slot for identity i in
#: every seeded procedure (permutation tests, negative control).
IDENTITIES = (
    "male",
    "female",
    "LGBTQ",
    "christian",
    "muslim",
    "other_religions",
    "black",
    "white",
)

#: Frozen spawn-key families: (analysis_slot, identity_index).
SPAWN_PRIMARY_EXACT = 1       # primary: one-per-article sample, exact Z
SPAWN_CENSUS_EXACT = 2        # sensitivity: full census, exact Z
SPAWN_PRIMARY_BINNED = 3      # sensitivity: one-per-article sample, binned Z
SPAWN_HIGH_CONFIDENCE = 4     # optional robustness: A>=0.8 vs A=0, exact Z
SPAWN_NEGATIVE_CONTROL_TEST = 5   # permutation test on the frozen synthetic labels
SPAWN_NEGATIVE_CONTROL_LABELS = 9  # generation of the frozen synthetic labels

#: The seven human-annotation columns forming Z, in frozen order.
Z_COLUMNS = (
    "toxicity",
    "severe_toxicity",
    "identity_attack",
    "insult",
    "threat",
    "obscene",
    "sexual_explicit",
)

ONE_HALF = Fraction(1, 2)


# ---------------------------------------------------------------------------
# Frozen rules
# ---------------------------------------------------------------------------

def selection_key(comment_id: str) -> str:
    """SHA-256 hex key for the one-comment-per-article selection.

    Depends only on the frozen seed string and the comment id as it
    appears in the source CSV; blind to A, Z, S, text, and row order.
    """
    payload = f"{SELECTION_SEED_STRING}:{comment_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_fraction(decimal_string: str) -> Fraction:
    """Exact rational value of a CSV decimal field.

    ``Fraction(str)`` parses a finite decimal literal exactly, so equal
    stored decimals map to equal rationals with no float round-trip.
    """
    return Fraction(decimal_string)


def z_key_exact(row: dict[str, str]) -> str:
    """Canonical exact-Z stratum key: reduced rationals, frozen order."""
    parts = []
    for col in Z_COLUMNS:
        f = canonical_fraction(row[col])
        parts.append(f"{f.numerator}/{f.denominator}")
    return "|".join(parts)


def bin_overall_toxicity(f: Fraction) -> int:
    """Frozen semantic bins for the overall toxicity fraction.

    0: == 0; 1: (0, 1/4]; 2: (1/4, 1/2); 3: [1/2, 3/4); 4: [3/4, 1].
    Exact rational comparisons; boundary membership as written.
    """
    if f == 0:
        return 0
    if f <= Fraction(1, 4):
        return 1
    if f < ONE_HALF:
        return 2
    if f < Fraction(3, 4):
        return 3
    return 4


def bin_subtype(f: Fraction) -> int:
    """Frozen semantic bins for each of the six subtype fractions.

    0: == 0; 1: (0, 1/2); 2: [1/2, 1].
    """
    if f == 0:
        return 0
    if f < ONE_HALF:
        return 1
    return 2


def z_key_binned(row: dict[str, str]) -> str:
    """Canonical binned-Z stratum key (Z sensitivity)."""
    parts = [str(bin_overall_toxicity(canonical_fraction(row["toxicity"])))]
    for col in Z_COLUMNS[1:]:
        parts.append(str(bin_subtype(canonical_fraction(row[col]))))
    return "|".join(parts)


def attribute_value(row: dict[str, str], identity: str) -> int:
    """A = 1 iff the stored identity column value is >= 1/2, exactly."""
    return 1 if canonical_fraction(row[identity]) >= ONE_HALF else 0


def discretize_scores(s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Frozen A-blind decile discretisation of a raw score vector.

    Included here (and unit-tested) so the rule is frozen in code before
    any score exists; it is NOT executed by this script's main path.

    1. boundaries = ``np.quantile(s, [k/10 for k in 1..9], method="linear")``
       computed on the pooled census scores (Hyndman-Fan type 7);
    2. exact-duplicate boundaries are collapsed with ``np.unique`` (the
       deterministic empty-category collapse);
    3. category(x) = #{boundaries <= x}, i.e.
       ``np.searchsorted(boundaries, x, side="right")``.

    Identical score values always land in the same category.
    """
    quantiles = np.array([k / 10 for k in range(1, 10)], dtype=np.float64)
    boundaries = np.unique(np.quantile(s, quantiles, method="linear"))
    return boundaries, np.searchsorted(boundaries, s, side="right").astype(np.int64)


# ---------------------------------------------------------------------------
# Artifact construction
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows() -> list[dict[str, str]]:
    """Read the frozen source CSV as verbatim strings (no float parsing)."""
    if sha256_file(DATASET_CSV) != DATASET_SHA256:
        raise RuntimeError(f"dataset hash mismatch for {DATASET_CSV}; refusing to proceed")
    with DATASET_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != DATASET_ROWS:
        raise RuntimeError(f"expected {DATASET_ROWS} rows, read {len(rows)}")
    return rows


def select_primary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """One comment per article by lexicographically smallest selection key.

    A row with a missing/empty ``article_id`` (none exist in the frozen
    source, but the rule is prespecified) forms its own singleton
    pseudo-article keyed by ``"__missing__:" + comment id`` and is retained.
    """
    best: dict[str, tuple[str, dict[str, str]]] = {}
    for row in rows:
        article = row["article_id"] or f"__missing__:{row['id']}"
        key = selection_key(row["id"])
        cur = best.get(article)
        if cur is None or key < cur[0]:
            best[article] = (key, row)
    chosen = [row for _, row in best.values()]
    chosen.sort(key=lambda r: int(r["id"]))
    return chosen


def support_counts(rows: list[dict[str, str]], z_keys: list[str]) -> dict[str, dict[str, int]]:
    """Per-identity informative-strata support under a given Z keying.

    A stratum is informative iff it holds >= 2 comments and both A values;
    pure-A and singleton strata contribute nothing to the conditional test.
    """
    out: dict[str, dict[str, int]] = {}
    strata_of: dict[str, list[int]] = {}
    for i, zk in enumerate(z_keys):
        strata_of.setdefault(zk, []).append(i)
    for identity in IDENTITIES:
        a = [attribute_value(rows[i], identity) for i in range(len(rows))]
        retained = retained_a1 = informative = 0
        for members in strata_of.values():
            if len(members) < 2:
                continue
            ones = sum(a[i] for i in members)
            if ones == 0 or ones == len(members):
                continue
            informative += 1
            retained += len(members)
            retained_a1 += ones
        out[identity] = {
            "n": len(rows),
            "n_a1": sum(a),
            "n_informative_strata": informative,
            "n_retained": retained,
            "n_retained_a1": retained_a1,
        }
    return out


def negative_control(primary: list[dict[str, str]], z_keys: list[str]) -> dict[str, list[int]]:
    """One frozen random relabelling of each A within exact-Z strata.

    Stratum-level A counts are preserved exactly (within-stratum
    permutation); singleton strata are necessarily unchanged.  Seeds are
    frozen per identity and are never regenerated.
    """
    code_of: dict[str, int] = {}
    z = np.array([code_of.setdefault(k, len(code_of)) for k in z_keys], dtype=np.int64)
    strata = Strata.from_codes(z)
    out: dict[str, list[int]] = {}
    for i, identity in enumerate(IDENTITIES):
        a = np.array([attribute_value(row, identity) for row in primary], dtype=np.int64)
        rng = np.random.default_rng(
            np.random.SeedSequence(
                entropy=BASE_ENTROPY, spawn_key=(SPAWN_NEGATIVE_CONTROL_LABELS, i)
            )
        )
        out[identity] = permute_within_strata(a, strata, rng).tolist()
    return out


def clustering_diagnostics(rows: list[dict[str, str]]) -> dict[str, object]:
    per_article = Counter(row["article_id"] for row in rows)
    sizes = np.array(sorted(per_article.values()), dtype=np.int64)
    shared = int(sum(c for c in per_article.values() if c > 1))
    return {
        "n_articles": len(per_article),
        "comments_per_article": {
            "median": float(np.median(sizes)),
            "mean": round(float(sizes.mean()), 3),
            "q90": int(np.quantile(sizes, 0.9)),
            "max": int(sizes.max()),
        },
        "pct_comments_sharing_article": round(100.0 * shared / len(rows), 1),
    }


def main() -> None:
    rows = read_rows()

    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError("comment ids are not unique")

    n_empty_text = sum(1 for row in rows if row["comment_text"] == "")
    n_missing_article = sum(1 for row in rows if not row["article_id"])

    primary = select_primary(rows)
    z_exact_primary = [z_key_exact(row) for row in primary]
    z_binned_primary = [z_key_binned(row) for row in primary]
    z_exact_census = [z_key_exact(row) for row in rows]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = RESULTS_DIR / "primary_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["comment_id", "article_id"])
        for row in primary:
            writer.writerow([row["id"], row["article_id"]])

    nc = negative_control(primary, z_exact_primary)
    nc_path = RESULTS_DIR / "negative_control_labels.csv"
    with nc_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["comment_id"] + [f"nc_{identity}" for identity in IDENTITIES])
        for j, row in enumerate(primary):
            writer.writerow([row["id"]] + [nc[identity][j] for identity in IDENTITIES])

    feasibility = {
        "study": "civil_comments_additional_audit",
        "frozen_design": {
            "selection_seed_string": SELECTION_SEED_STRING,
            "base_entropy": BASE_ENTROPY,
            "identity_order": list(IDENTITIES),
            "z_columns": list(Z_COLUMNS),
        },
        "dataset": {
            "file": str(DATASET_CSV.relative_to(REPO)),
            "sha256": DATASET_SHA256,
            "n_rows": len(rows),
            "n_unique_comment_ids": len(set(ids)),
            "n_empty_comment_text": n_empty_text,
            "n_missing_article_id": n_missing_article,
        },
        "clustering": clustering_diagnostics(rows),
        "primary_sample": {
            "n": len(primary),
            "n_exact_z_strata": len(set(z_exact_primary)),
            "n_binned_z_strata": len(set(z_binned_primary)),
            "support_exact_z": support_counts(primary, z_exact_primary),
            "support_binned_z": support_counts(primary, z_binned_primary),
        },
        "census": {
            "n": len(rows),
            "n_exact_z_strata": len(set(z_exact_census)),
            "support_exact_z": support_counts(rows, z_exact_census),
        },
        "artifact_sha256": {
            "primary_manifest.csv": sha256_file(manifest_path),
            "negative_control_labels.csv": sha256_file(nc_path),
        },
    }
    (RESULTS_DIR / "feasibility.json").write_text(
        json.dumps(feasibility, indent=2, sort_keys=False) + "\n"
    )
    print(json.dumps(feasibility["primary_sample"]["support_exact_z"], indent=2))
    print("manifest sha256:", feasibility["artifact_sha256"]["primary_manifest.csv"])
    print("negative control sha256:", feasibility["artifact_sha256"]["negative_control_labels.csv"])


if __name__ == "__main__":
    main()
