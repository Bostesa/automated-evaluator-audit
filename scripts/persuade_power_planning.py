"""Power planning for the PERSUADE 2.0 real-data experiment.

Planning calculations only -- no claims about the unknown real effect and no
LLM calls.  The synthetic design is matched to the real structure:

* strata are the observed usable ``(prompt, human_score)`` strata, with their
  observed sizes;
* each simulated essay carries its *actual* ELL label from the corpus, so
  within-stratum ELL proportions are the observed ones exactly;
* the judge score is six-category ordinal, generated as
  ``S = clamp(Y + e, 1, 6)`` with ``P(e=-1)=0.2, P(e=0)=0.6, P(e=+1)=0.2``
  (a PLANNING ASSUMPTION about judge dispersion, stated, not estimated);
* the alternative downshifts an ELL essay's judge score by one rubric
  category with probability ``pi`` (weak 0.05, moderate 0.10, strong 0.20);
  ``pi = 0`` is the calibration check;
* the test is the planned stratified permutation test with the conditional
  G^2 statistic on the NATIVE six score categories (no discretisation).

For each candidate scored sample size ``n``, essays are drawn without
replacement from the usable-strata pool (simple random sampling, so sampled
stratum sizes are proportional to observed ones).  Rejection rates at
``alpha = 0.05`` estimate power.
"""
from __future__ import annotations

import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.data import Sample  # noqa: E402
from offcriterion.permutation import permutation_test  # noqa: E402

OUT = ROOT / "results" / "persuade_feasibility"
ROOT_SEED = 20260825
ALPHA = 0.05
B = 999
R = 500
SAMPLE_SIZES = (500, 1000, 2000, 4000, 8000, 16000, 23334)
PIS = {"null": 0.0, "weak": 0.05, "moderate": 0.10, "strong": 0.20}
NOISE_P = (0.2, 0.6, 0.2)  # P(e = -1, 0, +1): planning assumption


def load_pool() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (z, y, a) for every essay in a usable stratum.

    z: stratum code (0..n_strata-1) for (prompt, human_score)
    y: human holistic score 1..6
    a: 1 if ell_status == 'Yes' else 0
    """
    rows = list(csv.DictReader((ROOT / "data" / "persuade" / "persuade_essay_level.csv").open()))
    complete = [
        r for r in rows
        if r["ell_status"].strip() and r["prompt_name"].strip() and r["holistic_essay_score"].strip()
    ]
    from collections import Counter
    strata_counts: Counter[tuple[str, str]] = Counter()
    ell_counts: Counter[tuple[str, str]] = Counter()
    for r in complete:
        key = (r["prompt_name"], r["holistic_essay_score"])
        strata_counts[key] += 1
        if r["ell_status"] == "Yes":
            ell_counts[key] += 1
    usable = {
        k for k, n in strata_counts.items()
        if n >= 2 and 0 < ell_counts[k] < n
    }
    codes = {k: i for i, k in enumerate(sorted(usable))}
    z, y, a = [], [], []
    for r in complete:
        key = (r["prompt_name"], r["holistic_essay_score"])
        if key in usable:
            z.append(codes[key])
            y.append(int(r["holistic_essay_score"]))
            a.append(1 if r["ell_status"] == "Yes" else 0)
    return np.asarray(z, np.int64), np.asarray(y, np.int64), np.asarray(a, np.int64)


def one_replicate(pool: tuple[np.ndarray, np.ndarray, np.ndarray],
                  n: int, pi: float, rng: np.random.Generator) -> tuple[bool, int, int]:
    z_all, y_all, a_all = pool
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
    return res.p_value <= ALPHA, res.n_usable_strata, int(a.sum())


def run_cell(task: tuple[int, int, str]) -> dict[str, object]:
    size_i, pi_i, label = task
    n = SAMPLE_SIZES[size_i]
    pi = PIS[label]
    pool = load_pool()
    rejections = 0
    usable_strata = []
    n_ell = []
    for rep in range(R):
        seq = np.random.SeedSequence(entropy=ROOT_SEED, spawn_key=(size_i, pi_i, rep))
        rng = np.random.default_rng(seq)
        rej, n_us, ell = one_replicate(pool, n, pi, rng)
        rejections += rej
        usable_strata.append(n_us)
        n_ell.append(ell)
    return {
        "n": n, "alternative": label, "pi": pi,
        "rejection_rate": rejections / R,
        "n_replicates": R, "n_permutations": B, "alpha": ALPHA,
        "mean_usable_strata_in_sample": round(float(np.mean(usable_strata)), 1),
        "mean_n_ell_in_sample": round(float(np.mean(n_ell)), 1),
    }


def main() -> None:
    tasks = [
        (si, pi_i, label)
        for si in range(len(SAMPLE_SIZES))
        for pi_i, label in enumerate(PIS)
    ]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(run_cell, tasks))
    results.sort(key=lambda r: (r["n"], r["pi"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "power_planning.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    (OUT / "power_planning.json").write_text(json.dumps({
        "planning_assumptions": {
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
