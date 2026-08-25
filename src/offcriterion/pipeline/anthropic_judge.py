"""Anthropic judge adapter for the secondary confirmatory family.

Stdlib-only (urllib), mirroring ``openai_judge`` byte-for-byte in policy:
single user message containing the rendered frozen prompt, structured output
constraining the response to {"score": <integer 1-6>}, temperature 0, and
the SAME preregistered retry policy — up to 3 retries on 429/5xx/network
errors with exponential backoff; any other 4xx aborts the run for report.

Provider notes, recorded rather than improvised:
* model is the frozen pinned snapshot ``claude-haiku-4-5-20251001``;
* extended thinking is off by default on this model and is not enabled;
* the Messages API offers no ``seed`` parameter, so the preregistration's
  "fixed seed parameter where offered" clause is inapplicable (recorded in
  each record as ``seed_supported: false``);
* structured output uses ``output_config.format`` (json_schema), the
  provider's equivalent of the frozen OpenAI ``response_format``.
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from offcriterion.pipeline.openai_judge import CallResult, FatalAPIError

_ENDPOINT = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"

OUTPUT_CONFIG = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {"score": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]}},
            "required": ["score"],
            "additionalProperties": False,
        },
    }
}


@dataclass
class AnthropicJudge:
    api_key: str
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 100
    timeout_s: float = 120.0
    max_retries: int = 3
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.model

    def _body(self, prompt: str) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "output_config": OUTPUT_CONFIG,
        }

    def _post(self, body: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            _ENDPOINT,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": _API_VERSION,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def call(self, prompt: str) -> CallResult:
        retries = 0
        while True:
            try:
                payload = self._post(self._body(prompt))
                break
            except urllib.error.HTTPError as err:
                detail = err.read().decode("utf-8", errors="replace")[:500]
                if err.code == 429 or err.code >= 500:
                    if retries >= self.max_retries:
                        return CallResult("", "", "", 0, 0, retries, False,
                                          error_status=f"HTTP {err.code} after {retries} retries: {detail}")
                    retries += 1
                    time.sleep(2 ** retries + random.random())
                    continue
                raise FatalAPIError(f"HTTP {err.code}: {detail}") from err
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                if retries >= self.max_retries:
                    return CallResult("", "", "", 0, 0, retries, False,
                                      error_status=f"network error after {retries} retries: {err}")
                retries += 1
                time.sleep(2 ** retries + random.random())
                continue

        stop_reason = payload.get("stop_reason", "")
        text = "".join(
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        )
        if stop_reason == "refusal":
            text = f"REFUSAL: {text}"
        usage = payload.get("usage", {})
        return CallResult(
            raw_content=text,
            provider_model=str(payload.get("model", "")),
            provider_request_id=str(payload.get("id", "")),
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            retry_count=retries,
            temperature_omitted=False,
        )
