"""OpenAI judge adapter implementing the frozen API parameters.

Stdlib-only (urllib).  The request body is exactly the frozen
``api_parameters`` in ``config/preregistered.json``: chat completion with a
strict JSON schema constraining the response to {"score": <integer 1-6>},
reasoning effort none, fixed seed, no tools.  Retry policy is the
preregistered one: up to 3 retries on 429/5xx/network errors with
exponential backoff; any other 4xx aborts (with a single frozen exception:
if the API rejects the ``temperature`` parameter for this model class, the
request is re-sent once without it and the adjustment is recorded, as
prespecified in the frozen config).
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

_ENDPOINT = "https://api.openai.com/v1/chat/completions"

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "holistic_score",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"score": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6]}},
            "required": ["score"],
            "additionalProperties": False,
        },
    },
}


class FatalAPIError(RuntimeError):
    """Non-retryable failure: abort the run and report, do not improvise."""


@dataclass
class CallResult:
    raw_content: str
    provider_model: str
    provider_request_id: str
    prompt_tokens: int
    completion_tokens: int
    retry_count: int
    temperature_omitted: bool
    error_status: str = ""


@dataclass
class OpenAIJudge:
    api_key: str
    model: str = "gpt-5.4-mini-2026-03-17"
    seed: int = 427183
    max_completion_tokens: int = 100
    timeout_s: float = 120.0
    max_retries: int = 3
    name: str = field(init=False)
    _temperature_omitted: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.name = self.model

    def _body(self, prompt: str) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": RESPONSE_FORMAT,
            "reasoning_effort": "none",
            "seed": self.seed,
            "max_completion_tokens": self.max_completion_tokens,
            "n": 1,
        }
        if not self._temperature_omitted:
            body["temperature"] = 0
        return body

    def _post(self, body: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            _ENDPOINT,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
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
                if err.code == 400 and "temperature" in detail and not self._temperature_omitted:
                    # Prespecified parameter fallback (config: api_parameters.temperature).
                    self._temperature_omitted = True
                    continue
                if err.code == 429 or err.code >= 500:
                    if retries >= self.max_retries:
                        return CallResult("", "", "", 0, 0, retries,
                                          self._temperature_omitted,
                                          error_status=f"HTTP {err.code} after {retries} retries: {detail}")
                    retries += 1
                    time.sleep(2 ** retries + random.random())
                    continue
                raise FatalAPIError(f"HTTP {err.code}: {detail}") from err
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                if retries >= self.max_retries:
                    return CallResult("", "", "", 0, 0, retries,
                                      self._temperature_omitted,
                                      error_status=f"network error after {retries} retries: {err}")
                retries += 1
                time.sleep(2 ** retries + random.random())
                continue

        choice = payload["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        refusal = message.get("refusal")
        usage = payload.get("usage", {})
        return CallResult(
            raw_content=content if not refusal else f"REFUSAL: {refusal}",
            provider_model=str(payload.get("model", "")),
            provider_request_id=str(payload.get("id", "")),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            retry_count=retries,
            temperature_omitted=self._temperature_omitted,
        )
