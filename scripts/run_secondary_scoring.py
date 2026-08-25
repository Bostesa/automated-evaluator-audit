"""Secondary confirmatory scoring runner: crash-safe, resumable, append-only.

Runs exactly one of the three preregistered secondary confirmatory cells
(config/preregistered.json, multiplicity.secondary_confirmatory_family):

    haiku_plain   claude-haiku-4-5-20251001, plain rubric
    gemini_plain  gemini-3.7-flash, plain rubric (approved low thinking)
    gpt_ignore    gpt-5.4-mini-2026-03-17, ignore_demographics rubric

Usage:
    run_secondary_scoring.py --cell CELL --key-file PATH [--smoke]

Identical mechanics and information barrier to the Stage C primary runner:
the frozen census manifest defines the targets; the prompt builder can only
receive essay text, task, assignment, and source titles (no demographic or
human-score code path exists); successful records are append-only and the
store refuses overwrites structurally; technical failures follow the frozen
3-retry policy and are excluded, never re-scored.  --smoke scores 8 essays
from DEGENERATE strata (outside the frozen census) to verify mechanics only.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.anthropic_judge import AnthropicJudge
from offcriterion.pipeline.gemini_judge import GeminiJudge
from offcriterion.pipeline.openai_judge import FatalAPIError, OpenAIJudge
from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.prompts import (
    PRIMARY_CONDITION,
    SECONDARY_CONDITION,
    build_judge_prompt,
    load_prompt_materials,
    prompt_sha256,
)
from offcriterion.pipeline.sampling import usable_strata
from offcriterion.pipeline.storage import RawScoreStore

DATA = ROOT / "data" / "persuade"
CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())
WORKERS = 10

CELLS = {
    "haiku_plain": {
        "judge_cls": AnthropicJudge,
        "model": CONFIG["judge"]["secondary"][0]["model_id"],
        "condition": PRIMARY_CONDITION,
        "store": "secondary_haiku_plain",
    },
    "gemini_plain": {
        "judge_cls": GeminiJudge,
        "model": CONFIG["judge"]["secondary"][1]["model_id"],
        "condition": PRIMARY_CONDITION,
        "store": "secondary_gemini_plain",
    },
    "gpt_ignore": {
        "judge_cls": OpenAIJudge,
        "model": CONFIG["api_parameters"]["model"],
        "condition": SECONDARY_CONDITION,
        "store": "secondary_gpt_ignore",
    },
}


def load_texts(wanted: set[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    with (DATA / "essay_texts.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["essay_id_comp"] in wanted:
                texts[row["essay_id_comp"]] = row["full_text"]
    return texts


def smoke_targets(k: int = 8) -> list[tuple[str, str]]:
    """Essays from DEGENERATE independent strata: complete metadata but
    outside the frozen census, so scoring them leaks nothing."""
    rows = list(csv.DictReader((DATA / "persuade_essay_level.csv").open()))
    usable_keys = set(usable_strata(rows, task="Independent"))
    picks = []
    for r in sorted(rows, key=lambda r: r["essay_id_comp"]):
        if r["task"] != "Independent":
            continue
        if not (r["ell_status"].strip() and r["holistic_essay_score"].strip()):
            continue
        if (r["prompt_name"], r["holistic_essay_score"]) in usable_keys:
            continue
        picks.append((r["essay_id_comp"], r["prompt_name"]))
        if len(picks) == k:
            break
    return picks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, choices=sorted(CELLS))
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cell = CELLS[args.cell]
    model, condition = cell["model"], cell["condition"]
    key = Path(args.key_file).read_text().strip()

    if args.smoke:
        targets = smoke_targets()
        store_dir = ROOT / "data" / "scoring" / "smoke"
    else:
        manifest = list(csv.DictReader(
            (ROOT / "data" / "scoring" / "primary_sample_manifest.csv").open()
        ))
        targets = [(r["essay_id_comp"], r["prompt_name"]) for r in manifest]
        store_dir = ROOT / "data" / "scoring" / cell["store"]

    materials = load_prompt_materials(DATA / "prompt_materials.csv")
    texts = load_texts({e for e, _ in targets})
    store = RawScoreStore(store_dir)
    judge = cell["judge_cls"](api_key=key, model=model)

    def request_id(essay_id: str) -> str:
        return hashlib.sha256(
            f"{model}|{condition}|{essay_id}".encode()
        ).hexdigest()[:16]

    # Resume: every existing record is FINAL under the preregistered rules.
    done: set[str] = set()
    prior_failures = 0
    score_file = store_dir / f"scores__{model}__{condition}.jsonl"
    if score_file.exists():
        for line in score_file.open(encoding="utf-8"):
            rec = json.loads(line)
            done.add(rec["essay_id_comp"])
            if rec.get("error_status"):
                prior_failures += 1
    todo = [(e, p) for e, p in targets if e not in done]
    print(f"cell={args.cell} model={model} condition={condition}")
    print(f"targets={len(targets)} done={len(done)} "
          f"prior_technical_failures={prior_failures} todo={len(todo)}")

    lock = threading.Lock()
    counters = {"ok": 0, "invalid": 0, "tech_fail": 0}
    fatal: list[str] = []

    def work(item: tuple[str, str]) -> None:
        essay_id, prompt_name = item
        if fatal:
            return
        mat = materials[prompt_name]
        prompt = build_judge_prompt(
            essay_text=texts[essay_id], task=mat["task"],
            assignment=mat["assignment"], source_titles=mat["source_text"],
            condition=condition,
        )
        try:
            result = judge.call(prompt)
        except FatalAPIError as err:
            with lock:
                fatal.append(str(err))
            return
        parsed: int | None = None
        parse_error = ""
        if not result.error_status:
            try:
                parsed = parse_score(result.raw_content)
            except ParseError as err:
                parse_error = str(err)
        extra = {
            "request_id": request_id(essay_id),
            "provider_model": result.provider_model,
            "provider_request_id": result.provider_request_id,
            "parsed_score": parsed,
            "parse_error": parse_error,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "retry_count": result.retry_count,
            "temperature_omitted": result.temperature_omitted,
            "error_status": result.error_status,
        }
        if hasattr(result, "thinking_tokens"):
            extra["thinking_tokens"] = result.thinking_tokens
        if args.cell == "haiku_plain":
            extra["seed_supported"] = False
        with lock:
            store.append(
                judge=model, condition=condition,
                essay_id_comp=essay_id, prompt_sha256=prompt_sha256(prompt),
                raw_response=result.raw_content, extra=extra,
            )
            if result.error_status:
                counters["tech_fail"] += 1
            elif parsed is None:
                counters["invalid"] += 1
            else:
                counters["ok"] += 1
            total = sum(counters.values())
            if total % 250 == 0:
                print(f"progress {total}/{len(todo)} {counters}", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, todo))

    if fatal:
        print("FATAL:", fatal[0])
        sys.exit(2)
    print("finished:", counters)


if __name__ == "__main__":
    main()
