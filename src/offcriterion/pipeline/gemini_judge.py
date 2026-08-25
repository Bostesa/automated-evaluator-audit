"""Google Gemini judge adapter for the secondary confirmatory family.

Stdlib-only (urllib), mirroring ``openai_judge`` in policy: single user
message containing the rendered frozen prompt, JSON-constrained output,
temperature 0 plus the provider's ``seed`` parameter (offered here), and
the SAME preregistered retry policy — up to 3 retries on 429/5xx/network
errors with exponential backoff; any other 4xx aborts the run for report.

Provider notes, recorded rather than improvised:
* model is the frozen stable version ID ``gemini-3.7-flash``;
* thinking uses the approved LOW setting (``thinkingConfig.thinkingLevel:
  "low"``); billed thinking tokens are recorded separately per record as
  ``thinking_tokens`` (from ``usageMetadata.thoughtsTokenCount``) because
  the provider bills them as output;
* structured output uses ``responseMimeType: application/json`` plus a
  ``responseSchema``, the provider's equivalent of the frozen OpenAI
  ``response_format``; range enforcement to 1..6 remains the frozen strict
  parser's job (an out-of-range integer is an exclusion, never repaired);
* ``maxOutputTokens`` is 1000 rather than the OpenAI adapter's 100 because
  this provider counts billed thinking tokens against the output cap; the
  cap exists to bound cost, not to shape the response, and truncation would
  simply produce a preregistered unparseable-response exclusion.
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from offcriterion.pipeline.openai_judge import CallResult, FatalAPIError

_ENDPOINT_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"score": {"type": "INTEGER"}},
    "required": ["score"],
}


@dataclass
class GeminiCallResult(CallResult):
    thinking_tokens: int = 0


@dataclass
class GeminiJudge:
    api_key: str
    model: str = "gemini-3.7-flash"
    seed: int = 427183
    max_output_tokens: int = 1000
    timeout_s: float = 120.0
    max_retries: int = 3
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.model

    def _body(self, prompt: str) -> dict[str, object]:
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "seed": self.seed,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
                "thinkingConfig": {"thinkingLevel": "low"},
            },
        }

    def _post(self, body: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            _ENDPOINT_TMPL.format(model=self.model),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def call(self, prompt: str) -> GeminiCallResult:
        retries = 0
        while True:
            try:
                payload = self._post(self._body(prompt))
                break
            except urllib.error.HTTPError as err:
                detail = err.read().decode("utf-8", errors="replace")[:500]
                if err.code == 429 or err.code >= 500:
                    if retries >= self.max_retries:
                        return GeminiCallResult("", "", "", 0, 0, retries, False,
                                                error_status=f"HTTP {err.code} after {retries} retries: {detail}")
                    retries += 1
                    time.sleep(2 ** retries + random.random())
                    continue
                raise FatalAPIError(f"HTTP {err.code}: {detail}") from err
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                if retries >= self.max_retries:
                    return GeminiCallResult("", "", "", 0, 0, retries, False,
                                            error_status=f"network error after {retries} retries: {err}")
                retries += 1
                time.sleep(2 ** retries + random.random())
                continue

        candidates = payload.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if "text" in p)
        usage = payload.get("usageMetadata", {})
        return GeminiCallResult(
            raw_content=text,
            provider_model=str(payload.get("modelVersion", self.model)),
            provider_request_id=str(payload.get("responseId", "")),
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            retry_count=retries,
            temperature_omitted=False,
            thinking_tokens=int(usage.get("thoughtsTokenCount", 0)),
        )
