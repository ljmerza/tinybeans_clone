"""Shared constants and helpers for auth views."""

from __future__ import annotations

import json
from collections.abc import Mapping

from django.conf import settings


def _rate_from_settings(setting_name: str, default: str):
    """Allow rate limits to be tuned via settings without redeploys."""

    def _rate(group, request):
        return getattr(settings, setting_name, default)

    return _rate


def _request_body(request) -> Mapping:
    data = getattr(request, "data", None)  # DRF Request: parsed JSON or form data
    if data is None:
        if request.POST:
            return request.POST
        data = json.loads(request.body or b"{}")
    return data if isinstance(data, Mapping) else {}


def body_field_key(field: str):
    """django-ratelimit key on a request body field, trimmed and lowercased.

    ``key="post:<field>"`` reads ``request.POST``, which is empty for JSON
    bodies, so every caller would share one bucket. This reads the parsed body
    instead. A missing or unparseable value gives ``""``; the view rejects
    those requests anyway, and the IP limit still applies to them.
    """

    def _key(group, request) -> str:
        try:
            value = _request_body(request).get(field)
        except Exception:  # malformed body: let the view return its own 400
            return ""
        return value.strip().lower() if isinstance(value, str) else ""

    return _key


PASSWORD_RESET_RATE = _rate_from_settings("PASSWORD_RESET_RATELIMIT", "5/15m")
PASSWORD_RESET_CONFIRM_RATE = _rate_from_settings("PASSWORD_RESET_CONFIRM_RATELIMIT", "10/15m")
PASSWORD_CHANGE_RATE = _rate_from_settings("PASSWORD_CHANGE_RATELIMIT", "5/15m")
EMAIL_VERIFICATION_RESEND_RATE = _rate_from_settings("EMAIL_VERIFICATION_RESEND_RATELIMIT", "5/15m")
EMAIL_VERIFICATION_CONFIRM_RATE = _rate_from_settings("EMAIL_VERIFICATION_CONFIRM_RATELIMIT", "10/15m")
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = getattr(
    settings,
    "EMAIL_VERIFICATION_TOKEN_TTL_SECONDS",
    48 * 60 * 60,
)
