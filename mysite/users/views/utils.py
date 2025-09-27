"""Shared utilities for user-facing API views."""
from __future__ import annotations

from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User
from ..token_utils import DEFAULT_TOKEN_TTL_SECONDS

TOKEN_TTL_SECONDS = DEFAULT_TOKEN_TTL_SECONDS
REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_PATH = '/api/users/token/refresh/'


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the refresh token as an HTTP-only cookie."""
    secure = not settings.DEBUG
    max_age = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite='Strict' if secure else 'Lax',
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh token cookie."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _get_tokens_for_user(user: User) -> dict:
    """Generate JWT access and refresh tokens for the given user."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}
