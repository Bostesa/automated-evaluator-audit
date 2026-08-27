#!/usr/bin/env python
"""Civil Comments additional audit -- Stages 5-8: frozen confirmatory analysis.

Runs, exactly as frozen in ``config/civil_comments_additional_audit.json``
and ``docs/civil_comments_additional_audit_plan.md``:

* Stage 5: hash-verified joins of the frozen score stores to the frozen
  primary manifest, exact/binned Z, the eight WILDS identity attributes,
  and the frozen negative-control labels (STOP on any unexpected join
  failure);
* Stage 6: the primary confirmatory family -- eight conditional G2
  permutation tests (one per identity) on the one-comment-per-article
  sample under exact Z, B = 999, frozen seeds, Holm across the eight
  raw p-values; plus the frozen descriptive conditional mean gap on the
  raw Detoxify probability scale;
* Stage 7: the prespecified negative control (frozen labels, slot 5);
* Stage 8: the prespecified sensitivities -- binned Z (slot 3), full
  census (slot 2), and the optional high-confidence robustness check
  (slot 4, labeled robustness, never confirmatory).

Statistic: ``offcriterion.statistics.ConditionalG2`` via
``offcriterion.permutation.permutation_test`` (the identical frozen
machinery of the PERSUADE audit).  Seeds:
``SeedSequence(entropy=20260827, spawn_key=(slot, identity_index))``.

Run:  .venv/bin/python scripts/civil_comments_analysis.py
"""

from __future__ import annotations

import csv
import json
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from civil_comments_freeze import (  # noqa: E402
    BASE_ENTROPY,
    IDENTITIES,
    SPAWN_CENSUS_EXACT,
    SPAWN_HIGH_CONFIDENCE,
    SPAWN_NEGATIVE_CONTROL_TEST,
    SPAWN_PRIMARY_BINNED,
    SPAWN_PRIMARY_EXACT,
    attribute_value,
    canonical_fraction,
    read_rows,
    sha256_file,
    z_key_binned,
    z_key_exact,
)
from offcriterion.data import Sample, Strata  # noqa: E402
from offcriterion.permutation import permutation_test  # noqa: E402

RESULTS = REPO / "results" / "civil_comments"
MANIFEST = RESULTS / "primary_manifest.csv"
MANIFEST_SHA256 = "892245a7899401c1041f3cf7bc17528d80d9812efacefe994dbfd16fec97469e"
NC_LABELS = RESULTS / "negative_control_labels.csv"
NC_SHA256 = "c2215e561b71b41f4018d0a8ad500b30971b61a8d7a5b98ccbbed2341220f73c"

B = 999
ALPHA = 0.05
FOUR_FIFTHS = Fraction(4, 5)


def verify(path: Path, want: str, what: str) -> None:
    got = sha256_file(path)
    if got != want:
        raise SystemExit(f"STOP: {what} hash mismatch: {got}")


def load_frozen_scores() -> tuple[dict[str, float], dict[str, int], int, dict]:
    frozen = json.loads((RESULTS / "scores_FROZEN.json").read_text())
    for name, want in frozen["artifact_sha256"].items():
        verify(RESULTS / name, want, name)
    raw: dict[str, float] = {}
    with (RESULTS / "scores_raw.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["status"].startswith("ok"):
                raw[r["comment_id"]] = float(r["toxicity"])
    disc: dict[str, int] = {}
    with (RESULTS / "scores_discrete.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["status"].startswith("ok"):
                disc[r["comment_id"]] = int(r["s_category"])
    n_categories = int(frozen["discretization"]["n_categories"])
    return raw, disc, n_categories, frozen


def weighted_mean_gap(s_raw: np.ndarray, a: np.ndarray, z: np.ndarray) -> float | None:
    """Frozen descriptive companion: stratum-size-weighted conditional mean
    difference of the RAW toxicity probability over informative strata,
    sign = mean(S | A=1) - mean(S | A=0); same weighting rule as the
    paper's ``weighted_mean_difference``."""
    strata = Strata.from_codes(z)
    w_total = 0
    mean_d = 0.0
    for group in strata.groups:
        a_g = a[group]
        if group.size < 2 or a_g.min() == a_g.max():
            continue
        s_g = s_raw[group]
        w = group.size
        mean_d += w * (s_g[a_g == 1].mean() - s_g[a_g == 0].mean())
        w_total += w
    return float(mean_d / w_total) if w_total else None


def support(a: np.ndarray, z: np.ndarray) -> dict[str, int]:
    strata = Strata.from_codes(z)
    informative = retained = retained_a1 = 0
    for group in strata.groups:
        a_g = a[group]
        if group.size < 2 or a_g.min() == a_g.max():
            continue
        informative += 1
        retained += int(group.size)
        retained_a1 += int(a_g.sum())
    return {
        "n_total": int(a.size),
        "n_a1_total": int(a.sum()),
        "n_informative_strata": informative,
        "n_retained_informative": retained,
        "n_retained_a1": retained_a1,
    }


def run_family(
    rows: list[dict[str, str]],
    z_keys: list[str],
    s_raw_map: dict[str, float],
    s_bin_map: dict[str, int],
    n_categories: int,
    slot: int,
    label: str,
    a_of: dict[str, callable],
) -> dict[str, object]:
    """One eight-test family on a fixed (rows, Z) design."""
    ids = [row["id"] for row in rows]
    missing = [i for i in ids if i not in s_raw_map]
    if missing:
        raise SystemExit(f"STOP: {label}: {len(missing)} comments missing from frozen score store")
    s_raw = np.array([s_raw_map[i] for i in ids], dtype=np.float64)
    s_bin = np.array([s_bin_map[i] for i in ids], dtype=np.int64)
    code_of: dict[str, int] = {}
    z = np.array([code_of.setdefault(k, len(code_of)) for k in z_keys], dtype=np.int64)

    out: dict[str, object] = {"family": label, "analysis_slot": slot, "n_permutations": B, "tests": {}}
    for idx, identity in enumerate(IDENTITIES):
        a_all = a_of[identity](rows)          # np.int64 array with -1 = excluded
        keep = a_all >= 0
        a = a_all[keep].astype(np.int64)
        if keep.all():
            s_r, s_b, z_i = s_raw, s_bin, z
        else:
            s_r, s_b = s_raw[keep], s_bin[keep]
            sub_keys = [z_keys[j] for j in range(len(z_keys)) if keep[j]]
            sub_code: dict[str, int] = {}
            z_i = np.array([sub_code.setdefault(k, len(sub_code)) for k in sub_keys], dtype=np.int64)
        sample = Sample(
            s_raw=s_r, s_bin=s_b, a=a, z=z_i,
            n_s_bins=n_categories, n_a=2, n_z=int(z_i.max()) + 1,
        )
        rng = np.random.default_rng(
            np.random.SeedSequence(entropy=BASE_ENTROPY, spawn_key=(slot, idx))
        )
        res = permutation_test(sample, ("conditional_g2",), B, rng)["conditional_g2"]
        out["tests"][identity] = {
            "identity_index": idx,
            "seed_spawn_key": [slot, idx],
            **support(a, z_i),
            "observed_conditional_g2": res.observed,
            "n_permutations": res.n_permutations,
            "permutation_exceedance_count": res.n_at_least_observed,
            "p_raw": res.p_value,
            "weighted_mean_gap_raw_probability": weighted_mean_gap(s_r, a, z_i),
        }
        print(f"  {label} / {identity}: G2={res.observed:.3f} p={res.p_value:.3f}", flush=True)

    # Holm step-down across the eight raw p-values
    ps = {k: v["p_raw"] for k, v in out["tests"].items()}
    order = sorted(ps, key=lambda k: ps[k])
    m = len(order)
    adj = {}
    running = 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * ps[k]))
        adj[k] = running
    for k in out["tests"]:
        out["tests"][k]["p_holm"] = adj[k]
        out["tests"][k]["reject_holm_at_0.05"] = adj[k] <= ALPHA
    return out


def real_attr(identity: str):
    def f(rows):
        return np.array([attribute_value(r, identity) for r in rows], dtype=np.int64)
    return f


def high_conf_attr(identity: str):
    col = identity

    def f(rows):
        out = np.empty(len(rows), dtype=np.int64)
        for j, r in enumerate(rows):
            frac = canonical_fraction(r[col])
            if frac >= FOUR_FIFTHS:
                out[j] = 1
            elif frac == 0:
                out[j] = 0
            else:
                out[j] = -1  # excluded (intermediate fraction)
        return out
    return f


def main() -> None:
    # Stage 5: hash-verified loads
    verify(MANIFEST, MANIFEST_SHA256, "primary manifest")
    verify(NC_LABELS, NC_SHA256, "negative-control labels")
    s_raw_map, s_bin_map, n_categories, frozen_meta = load_frozen_scores()
    rows = read_rows()  # verifies dataset hash
    by_id = {r["id"]: r for r in rows}

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_ids = [r["comment_id"] for r in csv.DictReader(f)]
    missing = [i for i in manifest_ids if i not in by_id]
    if missing:
        raise SystemExit(f"STOP: {len(missing)} manifest ids missing from dataset")
    primary = sorted((by_id[i] for i in manifest_ids), key=lambda r: int(r["id"]))

    with NC_LABELS.open(newline="", encoding="utf-8") as f:
        nc_rows = {r["comment_id"]: r for r in csv.DictReader(f)}
    if set(nc_rows) != set(manifest_ids):
        raise SystemExit("STOP: negative-control ids do not match the primary manifest")

    census_sorted = sorted(rows, key=lambda r: int(r["id"]))

    z_exact_primary = [z_key_exact(r) for r in primary]
    z_binned_primary = [z_key_binned(r) for r in primary]
    z_exact_census = [z_key_exact(r) for r in census_sorted]

    real = {i: real_attr(i) for i in IDENTITIES}

    def nc_attr(identity: str):
        def f(rows_):
            return np.array([int(nc_rows[r["id"]][f"nc_{identity}"]) for r in rows_], dtype=np.int64)
        return f

    nc = {i: nc_attr(i) for i in IDENTITIES}
    hc = {i: high_conf_attr(i) for i in IDENTITIES}

    results: dict[str, object] = {
        "study": "civil_comments_additional_audit",
        "frozen_inputs": {
            "score_store": frozen_meta["artifact_sha256"],
            "primary_manifest_sha256": MANIFEST_SHA256,
            "negative_control_labels_sha256": NC_SHA256,
            "n_categories": n_categories,
        },
    }

    print("Stage 6: primary confirmatory family", flush=True)
    results["primary_family"] = run_family(
        primary, z_exact_primary, s_raw_map, s_bin_map, n_categories,
        SPAWN_PRIMARY_EXACT, "primary: one-per-article, exact Z", real)

    print("Stage 7: negative control", flush=True)
    results["negative_control"] = run_family(
        primary, z_exact_primary, s_raw_map, s_bin_map, n_categories,
        SPAWN_NEGATIVE_CONTROL_TEST, "negative control: frozen synthetic labels", nc)
    results["negative_control"]["status"] = "calibration sanity check, NOT confirmatory"

    print("Stage 8A: binned-Z sensitivity", flush=True)
    results["sensitivity_binned_z"] = run_family(
        primary, z_binned_primary, s_raw_map, s_bin_map, n_categories,
        SPAWN_PRIMARY_BINNED, "sensitivity: one-per-article, binned Z", real)

    print("Stage 8C: high-confidence robustness (optional, prespecified)", flush=True)
    results["robustness_high_confidence"] = run_family(
        primary, z_exact_primary, s_raw_map, s_bin_map, n_categories,
        SPAWN_HIGH_CONFIDENCE, "robustness: A>=4/5 vs A=0, exact Z", hc)
    results["robustness_high_confidence"]["status"] = (
        "optional prespecified robustness check; never confirmatory evidence")

    print("Stage 8B: full-census dependence sensitivity", flush=True)
    results["sensitivity_census"] = run_family(
        census_sorted, z_exact_census, s_raw_map, s_bin_map, n_categories,
        SPAWN_CENSUS_EXACT, "sensitivity: full census, exact Z", real)
    results["sensitivity_census"]["caveat"] = (
        "article-level dependence; never replaces the one-per-article primary")

    out = RESULTS / "audit_results.json"
    out.write_text(json.dumps(results, indent=2) + "\n")
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
