"""Full-scale end-to-end dry run of the scoring pipeline.  NO external calls.

Uses the frozen configuration (config/preregistered.json), the real corpus,
and the fake deterministic judge, exercising exactly the path the real
experiment will take: sample -> prompts -> (fake) judge -> immutable store ->
freeze -> analysis -> report.  Outputs under results/dryrun/ are clearly
labelled DRY RUN; the fake scores are hash noise, so the analysis output has
no scientific content -- it validates plumbing only.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.analysis import run_primary_analysis
from offcriterion.pipeline.judge import FakeDeterministicJudge
from offcriterion.pipeline.prompts import (
    PRIMARY_CONDITION,
    build_judge_prompt,
    load_prompt_materials,
    prompt_sha256,
)
from offcriterion.pipeline.sampling import draw_primary_sample
from offcriterion.pipeline.storage import RawScoreStore


def main() -> None:
    config = json.loads((ROOT / "config" / "preregistered.json").read_text())
    n = config["primary_sample_size"]
    data = ROOT / "data" / "persuade"
    out = ROOT / "results" / "dryrun"
    if out.exists():
        shutil.rmtree(out)  # dry-run outputs are disposable by definition
    out.mkdir(parents=True)

    print(f"[1/5] drawing primary sample: n={n}, seed={config['sampling_seed']}")
    manifest = draw_primary_sample(
        data / "persuade_essay_level.csv", n=n, seed=config["sampling_seed"],
        task=config["population"].get("task_filter"),
    )
    manifest.write_csv(out / "sample_manifest.csv")

    print("[2/5] loading essay texts and prompt materials")
    materials = load_prompt_materials(data / "prompt_materials.csv")
    wanted = set(manifest.essay_ids)
    texts: dict[str, str] = {}
    with (data / "essay_texts.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["essay_id_comp"] in wanted:
                texts[row["essay_id_comp"]] = row["full_text"]
    assert len(texts) == n, f"missing texts for {n - len(texts)} sampled essays"

    print("[3/5] building prompts and scoring with the FAKE deterministic judge")
    judge = FakeDeterministicJudge()
    store = RawScoreStore(out / "raw")
    for eid, prompt_name, task in zip(
        manifest.essay_ids, manifest.prompt_names, manifest.tasks
    ):
        mat = materials[prompt_name]
        prompt = build_judge_prompt(
            essay_text=texts[eid],
            task=task,
            assignment=mat["assignment"],
            source_titles=mat["source_text"],
            condition=PRIMARY_CONDITION,
        )
        store.append(
            judge=judge.name,
            condition=PRIMARY_CONDITION,
            essay_id_comp=eid,
            prompt_sha256=prompt_sha256(prompt),
            raw_response=judge.score(prompt, call_key=eid),
        )

    print("[4/5] freezing raw store")
    store.freeze()

    print("[5/5] running primary analysis from the frozen store")
    result = run_primary_analysis(
        out / "raw",
        data / "persuade_essay_level.csv",
        judge=judge.name,
        condition=PRIMARY_CONDITION,
        n_permutations=config["analysis"]["n_permutations"],
        permutation_seed=config["permutation_seed"],
        seed_slot=(0, 0),
    )
    result.report["DRY_RUN"] = (
        "Scores are from the fake deterministic judge; this report validates "
        "the pipeline only and has no scientific content."
    )
    result.write(out / "dryrun_report.json")
    print(json.dumps({k: v for k, v in result.report.items()
                      if k not in ("exclusions",)}, indent=2)[:2000])


if __name__ == "__main__":
    main()
