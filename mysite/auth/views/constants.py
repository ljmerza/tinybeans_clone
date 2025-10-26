"""Shared constants and helpers for auth views."""
from __future__ import annotations

from django.conf import settings


def _rate_from_settings(setting_name: str, default: str):
    """Allow rate limits to be tuned via settings without redeploys."""
    def _rate(group, request):
        return getattr(settings, setting_name, default)

    return _rate


PASSWORD_RESET_RATE = _rate_from_settings('PASSWORD_RESET_RATELIMIT', '5/15m')
PASSWORD_RESET_CONFIRM_RATE = _rate_from_settings('PASSWORD_RESET_CONFIRM_RATELIMIT', '10/15m')
EMAIL_VERIFICATION_RESEND_RATE = _rate_from_settings('EMAIL_VERIFICATION_RESEND_RATELIMIT', '5/15m')
EMAIL_VERIFICATION_CONFIRM_RATE = _rate_from_settings('EMAIL_VERIFICATION_CONFIRM_RATELIMIT', '10/15m')
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = getattr(
    settings,
    'EMAIL_VERIFICATION_TOKEN_TTL_SECONDS',
    48 * 60 * 60,
)
