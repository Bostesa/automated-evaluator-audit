"""Adversarial tests for the real-data scoring pipeline (dry run, no APIs).

Every guarantee the preregistration makes about information flow is asserted
here: attribute-free sampling, demographic-free prompts, immutable raw
outputs, strict exclusions, the freeze gate in front of demographics, and
bit-identical re-analysis.
"""

from __future__ import annotations

import csv
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from offcriterion.pipeline.analysis import run_primary_analysis
from offcriterion.pipeline.judge import FakeDeterministicJudge
from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.prompts import (
    PRIMARY_CONDITION,
    SECONDARY_CONDITION,
    build_judge_prompt,
    prompt_sha256,
)
from offcriterion.pipeline.sampling import draw_primary_sample, usable_strata
from offcriterion.pipeline.storage import RawScoreStore, StorageError

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


# ---------------------------------------------------------------------------
# Fixture corpus: small synthetic essay-level CSV with marker strings that
# must never appear in any judge prompt.
# ---------------------------------------------------------------------------

ELL_MARKER = "XXELLMARKERXX"


def _write_corpus(path: Path, n_per_stratum: int = 12) -> None:
    rng = np.random.default_rng(7)
    fields = [
        "essay_id_comp", "prompt_name", "task", "holistic_essay_score",
        "ell_status", "gender", "race_ethnicity",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        i = 0
        for prompt, task in (("Alpha", "Independent"), ("Beta", "Text dependent")):
            for score in ("2", "3", "4"):
                for _ in range(n_per_stratum):
                    w.writerow({
                        "essay_id_comp": f"E{i:05d}",
                        "prompt_name": prompt,
                        "task": task,
                        "holistic_essay_score": score,
                        "ell_status": "Yes" if rng.random() < 0.3 else "No",
                        "gender": "M",
                        "race_ethnicity": ELL_MARKER,
                    })
                    i += 1


@pytest.fixture()
def corpus_csv(tmp_path: Path) -> Path:
    path = tmp_path / "essays.csv"
    _write_corpus(path)
    return path


# ---------------------------------------------------------------------------
# Prompt construction can never see demographics or human scores
# ---------------------------------------------------------------------------


def test_prompt_builder_signature_cannot_accept_metadata() -> None:
    params = set(inspect.signature(build_judge_prompt).parameters)
    assert params == {
        "essay_text", "task", "assignment", "source_titles", "condition",
        "prompt_dir",
    }
    forbidden = {"ell", "ell_status", "gender", "race", "human_score",
                 "holistic_essay_score", "grade_level", "disability"}
    assert not params & forbidden


@pytest.mark.parametrize("task", ["Independent", "Text dependent"])
def test_primary_prompt_contains_no_demographic_tokens(task: str) -> None:
    prompt = build_judge_prompt(
        essay_text="An essay body.", task=task,
        assignment="Write an essay.", source_titles="\"Some Article\"",
        condition=PRIMARY_CONDITION,
    )
    import re
    assert re.search(r"\bELL\b", prompt) is None  # case-sensitive: 'well' is fine
    for token in ("English-language-learner", "English language learner",
                  "demographic", "race", "gender", "disability",
                  "human score", "human holistic"):
        assert re.search(r"\b" + re.escape(token) + r"\b", prompt, re.IGNORECASE) is None, token
    assert "{" not in prompt and "}" not in prompt  # all placeholders filled


@pytest.mark.parametrize("task", ["Independent", "Text dependent"])
def test_secondary_condition_is_minimal_modification(task: str) -> None:
    kwargs = dict(essay_text="Body.", task=task, assignment="A.",
                  source_titles="T.")
    primary = build_judge_prompt(condition=PRIMARY_CONDITION, **kwargs)
    secondary = build_judge_prompt(condition=SECONDARY_CONDITION, **kwargs)
    modifier = (PROMPT_DIR / "condition_ignore_demographics.txt").read_text().strip()
    # The secondary prompt is the primary prompt with exactly the modifier
    # paragraph inserted before the RUBRIC heading -- nothing else changes.
    assert secondary == primary.replace("RUBRIC\n", modifier + "\n\nRUBRIC\n", 1)
    assert modifier in secondary and modifier not in primary


def test_prompt_output_format_line_is_frozen() -> None:
    prompt = build_judge_prompt(
        essay_text="Body.", task="Independent", assignment="A.",
        source_titles="",
    )
    assert "SCORE: <integer from 1 to 6>" in prompt
    assert "chain of thought" not in prompt.lower()
    assert "reasoning" not in prompt.lower()


# ---------------------------------------------------------------------------
# Sampling: deterministic, reproducible, attribute-free
# ---------------------------------------------------------------------------


def test_sample_is_reproducible(corpus_csv: Path) -> None:
    m1 = draw_primary_sample(corpus_csv, n=30, seed=123)
    m2 = draw_primary_sample(corpus_csv, n=30, seed=123)
    assert m1.essay_ids == m2.essay_ids
    m3 = draw_primary_sample(corpus_csv, n=30, seed=124)
    assert m1.essay_ids != m3.essay_ids
    assert len(m1.essay_ids) == 30


def test_sample_ignores_attribute_column(corpus_csv: Path, tmp_path: Path) -> None:
    """Permuting ELL labels within strata must not change who is sampled."""
    rows = list(csv.DictReader(corpus_csv.open()))
    rng = np.random.default_rng(0)
    # Shuffle the ell_status column globally; keep everything else fixed.
    labels = [r["ell_status"] for r in rows]
    rng.shuffle(labels)
    for r, lab in zip(rows, labels):
        r["ell_status"] = lab
    shuffled_csv = tmp_path / "shuffled.csv"
    with shuffled_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    baseline = draw_primary_sample(corpus_csv, n=40, seed=99)
    shuffled = draw_primary_sample(shuffled_csv, n=40, seed=99)
    # Identical provided the shuffle leaves the same strata usable (with a
    # global shuffle of a 30% label over 6 strata of 12, every stratum keeps
    # both categories with overwhelming probability for this seed -- assert it).
    assert set(usable_strata(rows)) == set(
        usable_strata(list(csv.DictReader(corpus_csv.open())))
    )
    assert baseline.essay_ids == shuffled.essay_ids


def test_manifest_excludes_scores_and_demographics(corpus_csv: Path, tmp_path: Path) -> None:
    manifest = draw_primary_sample(corpus_csv, n=20, seed=1)
    out = tmp_path / "manifest.csv"
    manifest.write_csv(out)
    header = out.read_text().splitlines()[0].split(",")
    assert header == ["essay_id_comp", "prompt_name", "task"]


def test_sample_is_proportional_within_one(corpus_csv: Path) -> None:
    manifest = draw_primary_sample(corpus_csv, n=36, seed=5)
    rows = list(csv.DictReader(corpus_csv.open()))
    strata = usable_strata(rows)
    total = sum(len(v) for v in strata.values())
    from collections import Counter
    got = Counter()
    meta = {r["essay_id_comp"]: r for r in rows}
    for eid in manifest.essay_ids:
        r = meta[eid]
        got[(r["prompt_name"], r["holistic_essay_score"])] += 1
    for key, members in strata.items():
        expected = 36 * len(members) / total
        assert abs(got[key] - expected) <= 1


# ---------------------------------------------------------------------------
# Parsing: strict, exclusion not repair
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("SCORE: 1", 1), ("SCORE: 6", 6), ("  SCORE: 4  ", 4), ("SCORE:3", 3),
])
def test_parse_valid(raw: str, expected: int) -> None:
    assert parse_score(raw) == expected


@pytest.mark.parametrize("raw", [
    "score: 3", "SCORE: 7", "SCORE: 0", "3", "SCORE: 3.5", "SCORE: 3/6",
    "The score is SCORE: 3", "SCORE: 3\nGreat essay!", "", "SCORE: three",
])
def test_parse_invalid_raises(raw: str) -> None:
    with pytest.raises(ParseError):
        parse_score(raw)


# ---------------------------------------------------------------------------
# Storage: append-only, freeze gate, checksums
# ---------------------------------------------------------------------------


def _rec(i: int) -> dict[str, str]:
    return dict(judge="j", condition="plain", essay_id_comp=f"E{i}",
                prompt_sha256="ab" * 32, raw_response="SCORE: 3")


def test_store_refuses_overwrite(tmp_path: Path) -> None:
    store = RawScoreStore(tmp_path / "raw")
    store.append(**_rec(1))
    with pytest.raises(StorageError, match="must not be overwritten"):
        store.append(**_rec(1))
    # same essay under a different judge/condition is a different record
    other = _rec(1); other["condition"] = "ignore_demographics"
    store.append(**other)


def test_store_refuses_writes_after_freeze(tmp_path: Path) -> None:
    store = RawScoreStore(tmp_path / "raw")
    store.append(**_rec(1))
    store.freeze()
    with pytest.raises(StorageError, match="frozen"):
        store.append(**_rec(2))
    with pytest.raises(StorageError, match="already frozen"):
        store.freeze()


def test_tampering_after_freeze_is_detected(tmp_path: Path) -> None:
    store = RawScoreStore(tmp_path / "raw")
    store.append(**_rec(1))
    store.freeze()
    victim = next((tmp_path / "raw").glob("scores__*.jsonl"))
    line = json.loads(victim.read_text())
    line["raw_response"] = "SCORE: 6"
    victim.write_text(json.dumps(line, sort_keys=True) + "\n")
    with pytest.raises(StorageError, match="checksum mismatch"):
        store.verify_frozen()


def test_read_requires_freeze(tmp_path: Path) -> None:
    store = RawScoreStore(tmp_path / "raw")
    store.append(**_rec(1))
    with pytest.raises(StorageError, match="requires a frozen"):
        store.read("j", "plain")


# ---------------------------------------------------------------------------
# End-to-end dry run on the fixture corpus
# ---------------------------------------------------------------------------


def _score_sample(corpus_csv: Path, tmp_path: Path, judge: FakeDeterministicJudge,
                  n: int = 48, seed: int = 11) -> Path:
    manifest = draw_primary_sample(corpus_csv, n=n, seed=seed)
    store = RawScoreStore(tmp_path / "raw")
    for eid, prompt_name, task in zip(
        manifest.essay_ids, manifest.prompt_names, manifest.tasks
    ):
        prompt = build_judge_prompt(
            essay_text=f"Essay body for {eid}.", task=task,
            assignment=f"Assignment for {prompt_name}.", source_titles="\"T\"",
        )
        assert ELL_MARKER not in prompt
        raw = judge.score(prompt, call_key=eid)
        store.append(judge=judge.name, condition=PRIMARY_CONDITION,
                     essay_id_comp=eid, prompt_sha256=prompt_sha256(prompt),
                     raw_response=raw)
    store.freeze()
    return tmp_path / "raw"


def test_analysis_blocked_until_freeze(corpus_csv: Path, tmp_path: Path) -> None:
    manifest = draw_primary_sample(corpus_csv, n=12, seed=3)
    store = RawScoreStore(tmp_path / "raw")
    judge = FakeDeterministicJudge()
    for eid, task in zip(manifest.essay_ids, manifest.tasks):
        prompt = build_judge_prompt(essay_text="x", task=task, assignment="a",
                                    source_titles="t")
        store.append(judge=judge.name, condition=PRIMARY_CONDITION,
                     essay_id_comp=eid, prompt_sha256=prompt_sha256(prompt),
                     raw_response=judge.score(prompt, eid))
    with pytest.raises(StorageError, match="requires a frozen"):
        run_primary_analysis(
            tmp_path / "raw", corpus_csv, judge=judge.name,
            condition=PRIMARY_CONDITION, n_permutations=99,
            permutation_seed=1,
        )


def test_end_to_end_dry_run_and_identical_rerun(corpus_csv: Path, tmp_path: Path) -> None:
    judge = FakeDeterministicJudge()
    root = _score_sample(corpus_csv, tmp_path, judge)
    kwargs = dict(judge=judge.name, condition=PRIMARY_CONDITION,
                  n_permutations=199, permutation_seed=42)
    r1 = run_primary_analysis(root, corpus_csv, **kwargs).report
    r2 = run_primary_analysis(root, corpus_csv, **kwargs).report
    assert r1 == r2  # bit-identical re-analysis from frozen outputs
    assert r1["n_excluded_unparseable"] == 0
    assert r1["n_analysed"] == 48
    assert 0.0 < r1["primary_test"]["p_value"] <= 1.0
    assert set(r1["descriptive_diagnostics"]) == {
        "weighted_mean_difference", "weighted_variance_difference",
        "weighted_cumulative_shift",
    }
    assert set(r1["permutation_calibrated_baselines"]) == {
        "stratified_mean_disparity", "stratified_regression_lrt",
    }


def test_invalid_responses_are_excluded_and_logged(corpus_csv: Path, tmp_path: Path) -> None:
    judge = FakeDeterministicJudge(invalid_every=4)
    root = _score_sample(corpus_csv, tmp_path, judge)
    report = run_primary_analysis(
        root, corpus_csv, judge=judge.name, condition=PRIMARY_CONDITION,
        n_permutations=99, permutation_seed=7,
    ).report
    n_excl = report["n_excluded_unparseable"]
    assert n_excl > 0
    assert len(report["exclusions"]) == n_excl
    assert report["n_analysed"] == 48 - n_excl
    for entry in report["exclusions"]:
        assert "does not match" in entry["reason"]
