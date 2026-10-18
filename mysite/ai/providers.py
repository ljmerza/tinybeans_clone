"""The operator's AI provider, checked when it is used.

``mysite.config.settings.ai`` only reads the env. Here the values are checked
each time they are needed, so a bad value turns the feature off (and logs
``ai.config_invalid``) instead of breaking startup:

- ``AI_BASE_URL`` and ``AI_MODEL`` must both be set;
- the URL must be ``http`` or ``https`` with a host and no ``user:password@``;
- ``http`` only without ``AI_API_KEY``, so a key never crosses the network in clear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.conf import settings

from mysite.audit import log_security_event

# Problems already logged, so a bad config is reported once per process, not on every request.
_reported: set[str] = set()


@dataclass(frozen=True)
class ProviderConfig:
    """The checked provider settings. ``api_key`` is left out of ``repr`` so it can't reach a log."""

    base_url: str
    model: str
    api_key: str = field(default="", repr=False)
    timeout_seconds: int = 120
    max_calls_per_run: int = 200
    max_caption_chars: int = 1500


def _problem(base_url: str, api_key: str) -> str | None:
    try:
        parts = urlsplit(base_url)
        hostname = parts.hostname
    except ValueError:
        return "url"
    if parts.scheme not in ("http", "https") or not hostname:
        return "url"
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return "userinfo"
    if parts.scheme == "http" and api_key:
        return "http_with_key"
    return None


def _report(problem: str) -> None:
    if problem in _reported:
        return
    _reported.add(problem)
    # The problem's name only: the URL or key may be what's wrong, and either could hold a secret.
    log_security_event("ai.config_invalid", status="failure", metadata={"problem": problem})


def provider_config() -> ProviderConfig | None:
    """The operator's provider, or None when AI is off (unset, or set to something invalid)."""
    base_url = (getattr(settings, "AI_BASE_URL", "") or "").strip()
    model = (getattr(settings, "AI_MODEL", "") or "").strip()
    api_key = (getattr(settings, "AI_API_KEY", "") or "").strip()
    if not base_url or not model:
        return None
    problem = _problem(base_url, api_key)
    if problem is not None:
        _report(problem)
        return None
    return ProviderConfig(
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=api_key,
        timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
        max_calls_per_run=settings.AI_MAX_CALLS_PER_RUN,
        max_caption_chars=settings.AI_MAX_CAPTION_CHARS,
    )


def ai_enabled() -> bool:
    """Whether the operator configured a valid provider. Circles still each have to turn AI on."""
    return provider_config() is not None
