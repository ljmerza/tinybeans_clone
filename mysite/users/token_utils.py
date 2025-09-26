from __future__ import annotations

import os
import uuid
from typing import Any

from django.core.cache import cache


DEFAULT_TOKEN_TTL_SECONDS = int(os.environ.get('AUTH_TOKEN_TTL', 900))


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
