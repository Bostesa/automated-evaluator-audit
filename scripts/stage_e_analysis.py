"""Stage E: run the preregistered primary analysis exactly once."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.analysis import run_primary_analysis

CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())


def main() -> None:
    result = run_primary_analysis(
        ROOT / "data" / "scoring" / "primary",
        ROOT / "data" / "persuade" / "persuade_essay_level.csv",
        judge=CONFIG["api_parameters"]["model"],
        condition="plain",
        n_permutations=CONFIG["analysis"]["n_permutations"],
        permutation_seed=CONFIG["permutation_seed"],
        seed_slot=tuple(CONFIG["seed_slots"]["primary"]),
    )
    out = ROOT / "results" / "primary_analysis.json"
    result.write(out)
    print(json.dumps(result.report, indent=2))


if __name__ == "__main__":
    main()
