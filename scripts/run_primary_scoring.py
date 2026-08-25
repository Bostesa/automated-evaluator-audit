"""Primary scoring runner: crash-safe, resumable, append-only.  Stage C.

Usage:
    run_primary_scoring.py --key-file PATH [--smoke]

--smoke scores a small set of essays from DEGENERATE strata (excluded from
the frozen primary sample) into data/scoring/smoke/ to verify mechanics
only.  Without --smoke it scores the frozen census manifest into
data/scoring/primary/.

Resume safety: on restart, essays already holding a successful record are
skipped; the store refuses overwrites structurally.  Technical failures
(after the preregistered 3-retry policy) are recorded with error_status and
revisited only by re-running the script, which retries ONLY essays with no
successful record.
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

from offcriterion.pipeline.openai_judge import FatalAPIError, OpenAIJudge
from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.prompts import (
    PRIMARY_CONDITION,
    build_judge_prompt,
    load_prompt_materials,
    prompt_sha256,
)
from offcriterion.pipeline.sampling import usable_strata
from offcriterion.pipeline.storage import RawScoreStore

DATA = ROOT / "data" / "persuade"
CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())
MODEL = CONFIG["api_parameters"]["model"]
WORKERS = 10


def request_id(essay_id: str) -> str:
    return hashlib.sha256(
        f"{MODEL}|{PRIMARY_CONDITION}|{essay_id}".encode()
    ).hexdigest()[:16]


def load_texts(wanted: set[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    with (DATA / "essay_texts.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["essay_id_comp"] in wanted:
                texts[row["essay_id_comp"]] = row["full_text"]
    return texts


def smoke_targets(k: int = 8) -> list[tuple[str, str]]:
    """Essays from DEGENERATE independent strata: complete ELL metadata but
    excluded from the primary census, so scoring them leaks nothing."""
    rows = list(csv.DictReader((DATA / "persuade_essay_level.csv").open()))
    usable = usable_strata(rows, task="Independent")
    usable_keys = set(usable)
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
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    key = Path(args.key_file).read_text().strip()

    if args.smoke:
        targets = smoke_targets()
        store_dir = ROOT / "data" / "scoring" / "smoke"
    else:
        manifest = list(csv.DictReader(
            (ROOT / "data" / "scoring" / "primary_sample_manifest.csv").open()
        ))
        targets = [(r["essay_id_comp"], r["prompt_name"]) for r in manifest]
        store_dir = ROOT / "data" / "scoring" / "primary"

    materials = load_prompt_materials(DATA / "prompt_materials.csv")
    texts = load_texts({e for e, _ in targets})
    store = RawScoreStore(store_dir)
    judge = OpenAIJudge(api_key=key, model=MODEL)

    # Resume: every existing record is FINAL under the preregistered rules --
    # a valid score, an invalid response (excluded, never re-prompted), or a
    # technical failure after the 3-retry policy (excluded).  Only essays
    # with no record at all are attempted.
    done: set[str] = set()
    prior_failures = 0
    score_file = store_dir / f"scores__{MODEL}__{PRIMARY_CONDITION}.jsonl"
    if score_file.exists():
        for line in score_file.open(encoding="utf-8"):
            rec = json.loads(line)
            done.add(rec["essay_id_comp"])
            if rec.get("error_status"):
                prior_failures += 1
    todo = [(e, p) for e, p in targets if e not in done]
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
            condition=PRIMARY_CONDITION,
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
        with lock:
            store.append(
                judge=MODEL, condition=PRIMARY_CONDITION,
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
