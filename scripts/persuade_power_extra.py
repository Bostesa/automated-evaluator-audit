"""Supplemental power cells at n = 10000 and 12000; merges into power_planning.csv."""
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import persuade_power_planning as pp


def main() -> None:
    tasks = [(si, pi_i, label)
             for si, n in enumerate(pp.SAMPLE_SIZES) if n in (10000, 12000)
             for pi_i, label in enumerate(pp.PIS)]
    with ProcessPoolExecutor() as ex:
        new_rows = list(ex.map(pp.run_cell, tasks))
    path = Path("results/persuade_feasibility/power_planning.csv")
    old_rows = [r for r in csv.DictReader(path.open())
                if int(r["n"]) not in (10000, 12000)]
    for r in old_rows:
        for k in ("n", "n_replicates", "n_permutations"):
            r[k] = int(r[k])
        for k in ("pi", "rejection_rate", "alpha",
                  "mean_usable_strata_in_sample", "mean_n_ell_in_sample"):
            r[k] = float(r[k])
    rows = sorted(old_rows + new_rows, key=lambda r: (r["n"], r["pi"]))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in new_rows:
        print(r)


if __name__ == "__main__":
    main()
