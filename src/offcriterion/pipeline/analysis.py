"""Primary analysis from a frozen raw-score store.

Demographics enter the pipeline HERE and nowhere earlier, and only after
``RawScoreStore.verify_frozen()`` has passed.  Everything this module
computes -- test, baselines, diagnostics -- is preregistered in
``docs/preregistration.md``; the descriptive decomposition is fixed in
advance so it cannot be chosen after seeing which view looks best.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from offcriterion.data import Sample, Strata
from offcriterion.permutation import permutation_test
from offcriterion.pipeline.storage import RawScoreStore
from offcriterion.pipeline.parse import ParseError, parse_score

N_SCORE_CATEGORIES = 6  # native rubric scale, frozen a priori
ANALYSIS_STATISTICS = (
    "conditional_g2",            # primary
    "stratified_mean_disparity",  # permutation-calibrated baseline
    "stratified_regression_lrt",  # permutation-calibrated baseline
)


@dataclass(frozen=True)
class AnalysisResult:
    report: dict[str, object]

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.report, indent=2, sort_keys=True))


def _load_metadata(essay_level_csv: Path) -> dict[str, dict[str, str]]:
    with essay_level_csv.open(newline="", encoding="utf-8") as f:
        return {row["essay_id_comp"]: row for row in csv.DictReader(f)}


def _weighted_diagnostics(
    s: np.ndarray, a: np.ndarray, z: np.ndarray
) -> dict[str, object]:
    """Preregistered descriptive decomposition (see prereg section 17).

    All quantities are stratum-size-weighted contrasts of the conditional law
    of S between A=1 (ELL) and A=0, restricted to informative strata (both
    categories present).  They are DESCRIPTIVE companions to the omnibus
    test, not additional hypothesis tests.
    """
    diag: dict[str, object] = {}
    strata = Strata.from_codes(z)
    w_total = 0
    mean_d = var_d = 0.0
    cum = np.zeros(N_SCORE_CATEGORIES - 1)  # P(S >= k) for k = 2..6
    for group in strata.groups:
        a_g, s_g = a[group], s[group]
        if a_g.min() == a_g.max() or group.size < 2:
            continue
        w = group.size
        s1, s0 = s_g[a_g == 1], s_g[a_g == 0]
        mean_d += w * (s1.mean() - s0.mean())
        var_d += w * (s1.var() - s0.var())
        for j, k in enumerate(range(2, N_SCORE_CATEGORIES + 1)):
            cum[j] += w * ((s1 >= k).mean() - (s0 >= k).mean())
        w_total += w
    if w_total:
        diag["weighted_mean_difference"] = round(mean_d / w_total, 4)
        diag["weighted_variance_difference"] = round(var_d / w_total, 4)
        diag["weighted_cumulative_shift"] = {
            f"P(S>={k})": round(cum[j] / w_total, 4)
            for j, k in enumerate(range(2, N_SCORE_CATEGORIES + 1))
        }
    return diag


def run_primary_analysis(
    store_root: Path,
    essay_level_csv: Path,
    *,
    judge: str,
    condition: str,
    n_permutations: int,
    permutation_seed: int,
    seed_slot: tuple[int, ...] = (0, 0),
) -> AnalysisResult:
    store = RawScoreStore(store_root)
    store.verify_frozen()  # gate: no analysis before freeze
    records = store.read(judge, condition)
    if not records:
        raise ValueError(f"no frozen scores for judge={judge!r} condition={condition!r}")

    # Preregistered exclusion rule: drop records whose raw response does not
    # parse as 'SCORE: <1-6>'.  Log every exclusion; never repair.
    scores: dict[str, int] = {}
    exclusions: list[dict[str, str]] = []
    for rec in records:
        try:
            scores[rec["essay_id_comp"]] = parse_score(rec["raw_response"])
        except ParseError as err:
            exclusions.append(
                {"essay_id_comp": rec["essay_id_comp"], "reason": str(err)}
            )

    # Demographics join -- first and only access point, post-freeze.
    meta = _load_metadata(essay_level_csv)
    s_list, a_list, keys = [], [], []
    for essay_id, score in sorted(scores.items()):
        m = meta[essay_id]
        s_list.append(score)
        a_list.append(1 if m["ell_status"] == "Yes" else 0)
        keys.append((m["prompt_name"], m["holistic_essay_score"]))
    code_of = {k: i for i, k in enumerate(sorted(set(keys)))}
    z = np.asarray([code_of[k] for k in keys], dtype=np.int64)
    s = np.asarray(s_list, dtype=np.int64)
    a = np.asarray(a_list, dtype=np.int64)

    sample = Sample(
        s_raw=s.astype(np.float64),
        s_bin=s - 1,               # native categories; space frozen at 6
        a=a,
        z=z,
        n_s_bins=N_SCORE_CATEGORIES,
        n_a=2,
        n_z=len(code_of),
    )
    rng = np.random.default_rng(
        np.random.SeedSequence(entropy=permutation_seed, spawn_key=seed_slot)
    )
    results = permutation_test(
        sample, statistic_names=ANALYSIS_STATISTICS,
        n_permutations=n_permutations, rng=rng,
    )
    primary = results["conditional_g2"]

    report: dict[str, object] = {
        "judge": judge,
        "condition": condition,
        "n_scored_records": len(records),
        "n_excluded_unparseable": len(exclusions),
        "exclusions": exclusions,
        "n_analysed": int(sample.n),
        "n_ell": int(a.sum()),
        "n_strata": int(primary.n_strata),
        "n_informative_strata": int(primary.n_usable_strata),
        "primary_test": {
            "statistic": "conditional_g2",
            "observed": primary.observed,
            "p_value": primary.p_value,
            "n_permutations": primary.n_permutations,
        },
        "permutation_calibrated_baselines": {
            name: {"observed": r.observed, "p_value": r.p_value}
            for name, r in results.items()
            if name != "conditional_g2"
        },
        "descriptive_diagnostics": _weighted_diagnostics(s, a, z),
        "score_distribution_by_ell": {
            f"A={val}": np.bincount(
                s[a == val], minlength=N_SCORE_CATEGORIES + 1
            )[1:].tolist()
            for val in (0, 1)
        },
    }
    return AnalysisResult(report=report)
