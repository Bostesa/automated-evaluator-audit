"""Rebuild the derived PERSUADE input files from the canonical raw corpus.

Reconstructs, deterministically, the three derived files every pipeline stage
consumes, from the two canonical discourse-element-level CSVs documented in
``data/persuade/README.md``:

  persuade_essay_level.csv   one row per unique ``essay_id_comp`` (25,996),
                             essay-level metadata + SHA-1 of ``full_text`` +
                             source file; metadata is verified constant across
                             each essay's discourse rows (an error otherwise)
  essay_texts.csv            ``essay_id_comp, full_text``
  prompt_materials.csv       one row per ``prompt_name`` with ``task``,
                             ``assignment``, ``source_text`` (source *titles*
                             only -- the corpus does not distribute passages);
                             verified constant per prompt

Faithful to the original ad-hoc derivation (2026-08-25): plain ``csv`` module
string passthrough (no pandas, no type coercion -- Excel-mangled numeric
``essay_id`` values and blank/space ELL encodings survive verbatim), scan
order train-then-test, first occurrence kept, output sorted by key, default
``csv.writer`` quoting and CRLF line terminators.

No demographic attribute is used in any filtering or ordering decision; rows
pass through unmodified.

Usage:
    python scripts/prepare_persuade.py [--out-dir DIR]

``--out-dir`` defaults to a NEW directory ``data/persuade/prepared/`` so the
canonical copies are never overwritten; pass ``--out-dir data/persuade``
explicitly to (re)create them in place.  After writing, the script prints the
SHA-256 of each output and compares ``persuade_essay_level.csv`` against the
project-recorded value (docs/posthoc_robustness_plan.md).

Inputs required in ``data/persuade/`` (see its README for download
provenance and SHA-256 values):
    persuade_train.csv, persuade_corpus_2.0_test.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "persuade"
RAW_FILES = ["persuade_train.csv", "persuade_corpus_2.0_test.csv"]

META_COLS = [
    "essay_id", "essay_id_comp", "competition_set", "holistic_essay_score",
    "provider", "task", "prompt_name", "gender", "grade_level", "ell_status",
    "race_ethnicity", "economically_disadvantaged",
    "student_disability_status", "essay_word_count",
]
ESSAY_LEVEL_HEADER = META_COLS + ["text_sha1", "source_file"]
PROMPT_COLS = ["prompt_name", "task", "assignment", "source_text"]

# Recorded reference hashes of the canonical derived files (SHA-256).
# persuade_essay_level.csv is recorded in docs/posthoc_robustness_plan.md;
# the other two are the hashes of the copies used for every scoring run.
EXPECTED_SHA256 = {
    "persuade_essay_level.csv":
        "b45aa58f7c4b4d9018511515cd1cf1dd409299ea093329272a05571f8203be8f",
    "essay_texts.csv":
        "df3b411a8644e81e72289d96baae59aa75a5e49805008aa58a7231ff4330f0d7",
    "prompt_materials.csv":
        "2e169ec033627459e4199750710143cbf87e693a5a78de76a53fafe0bb71e0e6",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(DATA / "prepared"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(sys.maxsize)

    essays: dict[str, dict[str, str]] = {}       # essay_id_comp -> row
    texts: dict[str, str] = {}                   # essay_id_comp -> full_text
    prompts: dict[str, dict[str, str]] = {}      # prompt_name -> materials
    n_rows = 0
    conflicts = 0

    for raw_name in RAW_FILES:
        raw = DATA / raw_name
        if not raw.exists():
            sys.exit(f"missing raw corpus file: {raw} (see data/persuade/README.md)")
        with raw.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                n_rows += 1
                eid = row["essay_id_comp"]
                meta = {c: row[c] for c in META_COLS}
                if eid not in essays:
                    meta["text_sha1"] = hashlib.sha1(
                        row["full_text"].encode("utf-8")
                    ).hexdigest()
                    meta["source_file"] = raw_name
                    essays[eid] = meta
                    texts[eid] = row["full_text"]
                else:
                    prior = {c: essays[eid][c] for c in META_COLS}
                    if prior != meta:
                        conflicts += 1
                pname = row["prompt_name"]
                pmat = {"prompt_name": pname, "task": row["task"],
                        "assignment": row["assignment"],
                        "source_text": row["source_text"]}
                if pname not in prompts:
                    prompts[pname] = pmat
                elif prompts[pname] != pmat:
                    sys.exit(f"prompt materials not constant for {pname!r}")

    if conflicts:
        sys.exit(f"{conflicts} essays had non-constant metadata across "
                 "discourse rows; refusing to write")

    p_level = out / "persuade_essay_level.csv"
    with p_level.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ESSAY_LEVEL_HEADER)
        w.writeheader()
        for eid in sorted(essays):
            w.writerow(essays[eid])

    p_texts = out / "essay_texts.csv"
    with p_texts.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["essay_id_comp", "full_text"])
        for eid in sorted(texts):
            w.writerow([eid, texts[eid]])

    p_prompts = out / "prompt_materials.csv"
    with p_prompts.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PROMPT_COLS)
        w.writeheader()
        for pname in sorted(prompts):
            w.writerow(prompts[pname])

    print(f"read {n_rows} discourse rows -> {len(essays)} unique essays, "
          f"{len(prompts)} prompts, 0 metadata conflicts")
    status = 0
    for p in [p_level, p_texts, p_prompts]:
        digest = sha256(p)
        expected = EXPECTED_SHA256.get(p.name)
        verdict = ("MATCHES recorded hash" if digest == expected
                   else "RECORDED-HASH MISMATCH" if expected
                   else "(no project-recorded hash)")
        if expected and digest != expected:
            status = 1
        print(f"{p.name}: sha256={digest} {verdict}")
    sys.exit(status)


if __name__ == "__main__":
    main()
