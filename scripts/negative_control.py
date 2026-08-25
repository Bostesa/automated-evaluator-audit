"""Preregistered negative control (§13): one within-stratum random
relabelling of A (frozen seed 771029) run through the analysis path.
Under this construction H0 holds regardless of judge behaviour; a small
p-value can only come from a pipeline defect."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.data import Sample, Strata
from offcriterion.permutation import permutation_test, permute_within_strata
from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.storage import RawScoreStore

CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())
MODEL = CONFIG["api_parameters"]["model"]

store = RawScoreStore(ROOT / "data" / "scoring" / "primary")
store.verify_frozen()
records = store.read(MODEL, "plain")
scores = {}
for rec in records:
    try:
        scores[rec["essay_id_comp"]] = parse_score(rec["raw_response"])
    except ParseError:
        pass

meta = {r["essay_id_comp"]: r for r in csv.DictReader(
    (ROOT / "data" / "persuade" / "persuade_essay_level.csv").open())}
s_list, a_list, keys = [], [], []
for eid, sc in sorted(scores.items()):
    m = meta[eid]
    s_list.append(sc)
    a_list.append(1 if m["ell_status"] == "Yes" else 0)
    keys.append((m["prompt_name"], m["holistic_essay_score"]))
code = {k: i for i, k in enumerate(sorted(set(keys)))}
z = np.asarray([code[k] for k in keys], np.int64)
s = np.asarray(s_list, np.int64)
a = np.asarray(a_list, np.int64)

# Frozen relabelling: within-stratum permutation of the real labels.
label_rng = np.random.default_rng(
    np.random.SeedSequence(entropy=CONFIG["label_permutation_seed"]))
a_null = permute_within_strata(a, Strata.from_codes(z), label_rng)

sample = Sample(s_raw=s.astype(np.float64), s_bin=s - 1, a=a_null, z=z,
                n_s_bins=6, n_a=2, n_z=len(code))
rng = np.random.default_rng(np.random.SeedSequence(
    entropy=CONFIG["permutation_seed"],
    spawn_key=tuple(CONFIG["seed_slots"]["negative_control"])))
res = permutation_test(sample, statistic_names=("conditional_g2",),
                       n_permutations=CONFIG["analysis"]["n_permutations"],
                       rng=rng)["conditional_g2"]
out = {"negative_control": {"observed_g2": res.observed, "p_value": res.p_value,
                             "n": res.n, "label_seed": CONFIG["label_permutation_seed"]}}
(ROOT / "results" / "negative_control.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
