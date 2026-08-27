"""Freeze-integrity tests for the Civil Comments LLM-evaluator addendum."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from offcriterion.pipeline.cc_toxicity_judges import (
    CCAnthropicJudge,
    CCGeminiJudge,
    CCOpenAIJudge,
    ParseError,
    parse_toxicity_score,
)

REPO = Path(__file__).resolve().parent.parent
CONFIG = json.loads(
    (REPO / "config" / "civil_comments_llm_evaluator_addendum.json").read_text()
)
TEMPLATE_PATH = REPO / "prompts" / "civil_comments_toxicity_rubric.txt"
TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")


def test_template_hash_matches_config():
    got = hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()
    assert got == CONFIG["prompt"]["template_sha256"]


def test_template_placeholder_and_scale():
    assert TEMPLATE.count("[[COMMENT_TEXT]]") == 1
    for line in ("1 = Not toxic", "5 = Extremely toxic", '{"score": <integer from 1 to 5>}'):
        assert line in TEMPLATE
    assert "Do not provide an explanation." in TEMPLATE


def test_template_is_standard_prompt_not_mitigation():
    # The frozen rubric must NOT instruct the evaluator about identity,
    # demographics, protected characteristics, bias, or fairness.
    lowered = TEMPLATE.lower()
    for banned in ("identity", "demograph", "bias", "fairness", "protected", "ignore"):
        assert banned not in lowered


def test_model_ids_match_persuade_freeze():
    pre = json.loads((REPO / "config" / "preregistered.json").read_text())
    assert CONFIG["evaluators"]["gpt"]["model_id"] == pre["judge"]["primary"]["model_id"]
    assert CONFIG["evaluators"]["claude"]["model_id"] == pre["judge"]["secondary"][0]["model_id"]
    assert CONFIG["evaluators"]["gemini"]["model_id"] == pre["judge"]["secondary"][1]["model_id"]


def test_parent_freeze_hashes_match_disk():
    p = CONFIG["parent_freezes"]
    files = {
        REPO / "results" / "civil_comments" / "primary_manifest.csv":
            p["primary_manifest_sha256"],
        REPO / "results" / "civil_comments" / "negative_control_labels.csv":
            p["negative_control_labels_sha256"],
        REPO / "results" / "civil_comments" / "scores_raw.csv":
            p["detoxify_scores_raw_sha256"],
        REPO / "results" / "civil_comments" / "score_decile_boundaries.json":
            p["detoxify_score_decile_boundaries_sha256"],
        REPO / "results" / "civil_comments" / "scores_discrete.csv":
            p["detoxify_scores_discrete_sha256"],
    }
    for path, want in files.items():
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        assert h.hexdigest() == want, path.name


def test_parser_accepts_only_1_to_5():
    for s in range(1, 6):
        assert parse_toxicity_score('{"score": %d}' % s) == s
    for bad in ('{"score": 0}', '{"score": 6}', '{"score": 3.0}',
                '{"score": true}', '{"score": "3"}', 'SCORE: 3',
                '{"score": 3, "why": "x"}', ""):
        with pytest.raises(ParseError):
            parse_toxicity_score(bad)


def test_judge_bodies_use_1to5_schema_and_frozen_settings():
    o = CCOpenAIJudge(api_key="k", model=CONFIG["evaluators"]["gpt"]["model_id"])._body("P")
    assert o["response_format"]["json_schema"]["schema"]["properties"]["score"]["enum"] == [1, 2, 3, 4, 5]
    assert o["seed"] == 427183 and o["temperature"] == 0
    assert o["reasoning_effort"] == "none" and o["max_completion_tokens"] == 100

    a = CCAnthropicJudge(api_key="k", model=CONFIG["evaluators"]["claude"]["model_id"])._body("P")
    assert a["output_config"]["format"]["schema"]["properties"]["score"]["enum"] == [1, 2, 3, 4, 5]
    assert a["temperature"] == 0 and a["max_tokens"] == 100
    assert "thinking" not in a

    g = CCGeminiJudge(api_key="k", model=CONFIG["evaluators"]["gemini"]["model_id"])._body("P")
    gc = g["generationConfig"]
    assert gc["temperature"] == 0 and gc["seed"] == 427183
    assert gc["thinkingConfig"] == {"thinkingLevel": "low"}
    assert gc["responseSchema"]["properties"]["score"]["type"] == "INTEGER"


def test_analysis_slots_disjoint_from_detoxify():
    slots = {int(k) for k in CONFIG["analysis"]["seeds"]["analysis_slots"]}
    assert slots == set(range(11, 20))
    assert slots.isdisjoint({1, 2, 3, 4, 5, 9})


def test_family_is_24_tests_holm():
    fam = CONFIG["multiplicity"]["llm_secondary_replication_family"]
    assert "24" in fam and "Holm" in fam
    assert len(CONFIG["analysis"]["a_family"]) == 8
    assert {k for k in CONFIG["evaluators"] if k != "note"} == {"gpt", "claude", "gemini"}
