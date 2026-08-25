"""Power planning on the Independent-only stratum structure.

Same planning model as scripts/persuade_power_planning.py so the comparison
is interpretable: observed usable strata with observed sizes and actual ELL
labels; judge S = clamp(Y + e, 1, 6) with P(e=-1,0,+1) = (0.2, 0.6, 0.2);
alternative downshifts an ELL essay one category w.p. pi; stratified
permutation test with conditional G2 on native six categories, B = 999,
alpha = 0.05.  Planning calculations only.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.data import Sample  # noqa: E402
from offcriterion.permutation import permutation_test  # noqa: E402

OUT = ROOT / "results" / "persuade_feasibility_independent"
ROOT_SEED = 20260826  # distinct from the all-prompt planning run
ALPHA = 0.05
B = 999
R = 500
SAMPLE_SIZES = (2000, 4000, 6000, 8000, 10000, 11360)
PIS = {"null": 0.0, "weak": 0.05, "moderate": 0.10, "strong": 0.20}
NOISE_P = (0.2, 0.6, 0.2)
TASK = "Independent"


def load_pool() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = [
        r for r in csv.DictReader(
            (ROOT / "data" / "persuade" / "persuade_essay_level.csv").open()
        )
        if r["task"] == TASK
    ]
    complete = [
        r for r in rows
        if r["ell_status"].strip() and r["prompt_name"].strip()
        and r["holistic_essay_score"].strip()
    ]
    strata_counts: Counter[tuple[str, str]] = Counter()
    ell_counts: Counter[tuple[str, str]] = Counter()
    for r in complete:
        key = (r["prompt_name"], r["holistic_essay_score"])
        strata_counts[key] += 1
        if r["ell_status"] == "Yes":
            ell_counts[key] += 1
    usable = {k for k, n in strata_counts.items() if n >= 2 and 0 < ell_counts[k] < n}
    codes = {k: i for i, k in enumerate(sorted(usable))}
    z, y, a = [], [], []
    for r in complete:
        key = (r["prompt_name"], r["holistic_essay_score"])
        if key in usable:
            z.append(codes[key])
            y.append(int(r["holistic_essay_score"]))
            a.append(1 if r["ell_status"] == "Yes" else 0)
    return (np.asarray(z, np.int64), np.asarray(y, np.int64),
            np.asarray(a, np.int64))


def run_cell(task: tuple[int, int, str]) -> dict[str, object]:
    size_i, pi_i, label = task
    n = SAMPLE_SIZES[size_i]
    pi = PIS[label]
    z_all, y_all, a_all = load_pool()
    rejections, usable_strata, n_ell = 0, [], []
    for rep in range(R):
        rng = np.random.default_rng(
            np.random.SeedSequence(entropy=ROOT_SEED, spawn_key=(size_i, pi_i, rep))
        )
        idx = rng.choice(z_all.size, size=n, replace=False)
        z, y, a = z_all[idx], y_all[idx], a_all[idx]
        noise = rng.choice(np.array([-1, 0, 1]), size=n, p=NOISE_P)
        s = np.clip(y + noise, 1, 6)
        if pi > 0.0:
            shift = (a == 1) & (rng.random(n) < pi)
            s = np.where(shift, np.maximum(s - 1, 1), s)
        sample = Sample(
            s_raw=s.astype(np.float64), s_bin=(s - 1).astype(np.int64),
            a=a, z=z, n_s_bins=6, n_a=2, n_z=int(z_all.max()) + 1,
        )
        res = permutation_test(sample, statistic_names=("conditional_g2",),
                               n_permutations=B, rng=rng)["conditional_g2"]
        rejections += res.p_value <= ALPHA
        usable_strata.append(res.n_usable_strata)
        n_ell.append(int(a.sum()))
    return {
        "n": n, "alternative": label, "pi": pi,
        "rejection_rate": rejections / R,
        "n_replicates": R, "n_permutations": B, "alpha": ALPHA,
        "mean_usable_strata_in_sample": round(float(np.mean(usable_strata)), 1),
        "mean_n_ell_in_sample": round(float(np.mean(n_ell)), 1),
    }


def main() -> None:
    tasks = [(si, pi_i, label)
             for si in range(len(SAMPLE_SIZES))
             for pi_i, label in enumerate(PIS)]
    with ProcessPoolExecutor() as ex:
        results = sorted(ex.map(run_cell, tasks),
                         key=lambda r: (r["n"], r["pi"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "power_planning.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader(); w.writerows(results)
    (OUT / "power_planning.json").write_text(json.dumps({
        "planning_assumptions": {
            "task_filter": TASK,
            "judge_noise": "S = clamp(Y+e,1,6), P(e=-1,0,+1) = " + str(NOISE_P),
            "alternative": "ELL essay downshifted one category w.p. pi",
            "pi": PIS, "root_seed": ROOT_SEED,
        },
        "results": results,
    }, indent=2))
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
