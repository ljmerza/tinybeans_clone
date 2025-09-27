from __future__ import annotations

import os
import uuid
from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


DEFAULT_TOKEN_TTL_SECONDS = int(os.environ.get('AUTH_TOKEN_TTL', 900))
TOKEN_TTL_SECONDS = DEFAULT_TOKEN_TTL_SECONDS
REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_PATH = '/api/users/auth/token/refresh/'


def token_cache_key(prefix: str, token: str) -> str:
    return f"auth:{prefix}:{token}"


def store_token(prefix: str, payload: dict[str, Any], ttl: int | None = None) -> str:
    token = uuid.uuid4().hex
    cache.set(
        token_cache_key(prefix, token),
        payload,
        ttl if ttl is not None else DEFAULT_TOKEN_TTL_SECONDS,
    )
    return token


def pop_token(prefix: str, token: str):
    key = token_cache_key(prefix, token)
    payload = cache.get(key)
    if payload is not None:
        cache.delete(key)
    return payload


def delete_token(prefix: str, token: str) -> None:
    cache.delete(token_cache_key(prefix, token))


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
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


def clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh token cookie."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def get_tokens_for_user(user: User) -> dict[str, str]:
    """Generate JWT access and refresh tokens for the given user."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


__all__ = [
    'DEFAULT_TOKEN_TTL_SECONDS',
    'TOKEN_TTL_SECONDS',
    'REFRESH_COOKIE_NAME',
    'REFRESH_COOKIE_PATH',
    'token_cache_key',
    'store_token',
    'pop_token',
    'delete_token',
    'set_refresh_cookie',
    'clear_refresh_cookie',
    'get_tokens_for_user',
]
