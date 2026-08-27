"""Civil Comments LLM-extension judge adapters (1-5 toxicity scale).

Thin subclasses of the frozen PERSUADE judge adapters.  Everything is
inherited unchanged -- endpoints, temperature 0, seed where offered,
timeout, the preregistered 3-retry policy on 429/5xx/network errors,
fatal abort on any other 4xx, refusal capture, token accounting -- except
the structured-output schema, which constrains the response to
{"score": <integer 1-5>} instead of the PERSUADE 1-6 holistic scale.

The frozen PERSUADE modules are not modified by this extension.
"""

from __future__ import annotations

import json

from offcriterion.pipeline.anthropic_judge import AnthropicJudge
from offcriterion.pipeline.gemini_judge import GeminiJudge
from offcriterion.pipeline.openai_judge import OpenAIJudge

RESPONSE_FORMAT_1TO5 = {
    "type": "json_schema",
    "json_schema": {
        "name": "toxicity_score",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"score": {"type": "integer", "enum": [1, 2, 3, 4, 5]}},
            "required": ["score"],
            "additionalProperties": False,
        },
    },
}

OUTPUT_CONFIG_1TO5 = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {"score": {"type": "integer", "enum": [1, 2, 3, 4, 5]}},
            "required": ["score"],
            "additionalProperties": False,
        },
    }
}

# Gemini's schema language stays an unconstrained INTEGER (as in PERSUADE);
# range enforcement to 1..5 remains the strict parser's job.
RESPONSE_SCHEMA_INT = {
    "type": "OBJECT",
    "properties": {"score": {"type": "INTEGER"}},
    "required": ["score"],
}


class ParseError(ValueError):
    """Raised when a judge response does not match the frozen 1-5 format."""


def parse_toxicity_score(raw_response: str) -> int:
    """Frozen exclusion rule: keep iff the whole response parses as a JSON
    object with the single key ``score`` and an integer value in 1..5.
    An invalid response is an exclusion event, never repaired."""
    try:
        obj = json.loads(raw_response.strip())
    except json.JSONDecodeError as err:
        raise ParseError(f"response is not valid JSON: {raw_response[:80]!r}") from err
    if not isinstance(obj, dict) or set(obj) != {"score"}:
        raise ParseError(
            f"response is not an object with the single key 'score': {raw_response[:80]!r}"
        )
    score = obj["score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
        raise ParseError(f"score is not an integer in 1..5: {score!r}")
    return score


class CCOpenAIJudge(OpenAIJudge):
    def _body(self, prompt: str) -> dict[str, object]:
        body = super()._body(prompt)
        body["response_format"] = RESPONSE_FORMAT_1TO5
        return body


class CCAnthropicJudge(AnthropicJudge):
    def _body(self, prompt: str) -> dict[str, object]:
        body = super()._body(prompt)
        body["output_config"] = OUTPUT_CONFIG_1TO5
        return body


class CCGeminiJudge(GeminiJudge):
    def _body(self, prompt: str) -> dict[str, object]:
        body = super()._body(prompt)
        body["generationConfig"]["responseSchema"] = RESPONSE_SCHEMA_INT
        return body
