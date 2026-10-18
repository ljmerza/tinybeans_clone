"""Calls to the operator's OpenAI-compatible ``/chat/completions`` endpoint.

Failures are reduced to fixed codes (``AiError.code``). The provider's
response body is never put into an exception, a log line or an API response:
it may echo the prompt, i.e. a family's caption.

- ``timeout``, ``unreachable``: the request didn't complete
- ``auth_failed``: 401/403, the operator's key is wrong
- ``model_missing``: 404, no such model (or path) on the endpoint
- ``provider_unavailable``: 429/503, the endpoint is busy or overloaded
- ``http_error``: any other non-2xx, including a redirect (never followed)
- ``bad_response``: a 2xx that isn't a chat completion, or one cut off at
  ``max_tokens`` (``finish_reason: length``, e.g. a reasoning model that
  thought too long): a transport-style failure, so no row is written

``InvalidOutput`` is different: the endpoint worked but the model's answer
doesn't fit the verdict schema. Ollama silently ignores a ``response_format``
it can't honour, so ``parse_verdict`` is the real guard.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests

from mysite.agent_api.hygiene import strip_hidden

from . import prompts
from .providers import ProviderConfig

OK = "ok"
TIMEOUT = "timeout"
UNREACHABLE = "unreachable"
AUTH_FAILED = "auth_failed"
MODEL_MISSING = "model_missing"
HTTP_ERROR = "http_error"
BAD_RESPONSE = "bad_response"
PROVIDER_UNAVAILABLE = "provider_unavailable"

CONNECT_TIMEOUT_SECONDS = 5
MAX_TOKENS = 1024
LABEL_MAX = 80
REASON_MAX = 160

_STATUS_CODES = {
    401: AUTH_FAILED,
    403: AUTH_FAILED,
    404: MODEL_MISSING,
    429: PROVIDER_UNAVAILABLE,
    503: PROVIDER_UNAVAILABLE,
}

# A reasoning model's leading <think>…</think> block, and ``` fences around the JSON.
_THINK_RE = re.compile(r"^\s*<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")


class AiError(Exception):
    """The call failed; ``code`` says how. The message is the code and nothing else."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class InvalidOutput(Exception):  # noqa: N818 - an outcome, not a programming error
    """The model answered, but not with a usable verdict."""


@dataclass(frozen=True)
class Verdict:
    is_milestone: bool
    label: str
    reason: str


def chat_json(config: ProviderConfig, messages: list[dict], *, schema_name: str, schema: dict) -> dict:
    """Send ``messages`` and return the model's answer parsed as a JSON object.

    Raises ``AiError`` when the request fails and ``InvalidOutput`` when the
    answer isn't a JSON object.
    """
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema}},
    }
    # ``from None`` everywhere: the original exception can carry the response or request.
    try:
        response = requests.post(
            f"{config.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=(CONNECT_TIMEOUT_SECONDS, config.timeout_seconds),
            allow_redirects=False,
        )
    except requests.Timeout:
        raise AiError(TIMEOUT) from None
    except requests.RequestException:
        raise AiError(UNREACHABLE) from None

    if not 200 <= response.status_code < 300:
        raise AiError(_STATUS_CODES.get(response.status_code, HTTP_ERROR))
    try:
        choice = response.json()["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise AiError(BAD_RESPONSE) from None
    if finish_reason == "length":
        raise AiError(BAD_RESPONSE)
    if not isinstance(content, str):
        raise AiError(BAD_RESPONSE)
    return parse_json_content(content)


def parse_json_content(content: str) -> dict:
    """The JSON object in a model's answer, after dropping a leading <think> block and code fences."""
    text = _THINK_RE.sub("", content, count=1).strip()
    fenced = _FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except ValueError:
        raise InvalidOutput from None
    if not isinstance(data, dict):
        raise InvalidOutput
    return data


def _clean(value: str, limit: int) -> str:
    # Control and invisible characters out, whitespace (newlines included) collapsed.
    return _WHITESPACE_RE.sub(" ", strip_hidden(value).replace("\n", " ").replace("\t", " ")).strip()[:limit]


def parse_verdict(data: dict) -> Verdict:
    """Check a parsed answer against the verdict schema; ``is_milestone`` must be a real bool."""
    is_milestone = data.get("is_milestone")
    label = data.get("label", "")
    reason = data.get("reason", "")
    if not isinstance(is_milestone, bool) or not isinstance(label, str) or not isinstance(reason, str):
        raise InvalidOutput
    return Verdict(is_milestone=is_milestone, label=_clean(label, LABEL_MAX), reason=_clean(reason, REASON_MAX))


def classify_post(config: ProviderConfig, title: str, caption: str) -> Verdict:
    """Ask the model whether one post is a milestone. Raises ``AiError`` or ``InvalidOutput``."""
    messages = prompts.build_messages(title, caption, config.max_caption_chars)
    data = chat_json(config, messages, schema_name=prompts.SCHEMA_NAME, schema=prompts.VERDICT_SCHEMA)
    return parse_verdict(data)
