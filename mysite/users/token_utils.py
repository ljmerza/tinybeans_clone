"""Token management utilities for user authentication.

This module provides utility functions for managing authentication tokens,
including JWT token generation, cache-based token storage/retrieval, and
HTTP cookie handling for refresh tokens.

Constants:
    DEFAULT_TOKEN_TTL_SECONDS: Default time-to-live for cached tokens (900s)
    REFRESH_COOKIE_NAME: Name of the HTTP cookie storing refresh tokens
    REFRESH_COOKIE_PATH: Path restriction for the refresh token cookie
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .custom_tokens import CustomRefreshToken
from .models import User


DEFAULT_TOKEN_TTL_SECONDS = int(os.environ.get('AUTH_TOKEN_TTL', 900))
TOKEN_TTL_SECONDS = DEFAULT_TOKEN_TTL_SECONDS
REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_PATH = '/api/users/auth/token/refresh/'


def token_cache_key(prefix: str, token: str) -> str:
    """Generate a cache key for storing authentication tokens.
    
    Args:
        prefix: A string prefix to categorize the token type
        token: The actual token string
        
    Returns:
        A formatted cache key string in the format 'auth:{prefix}:{token}'
    """
    return f"auth:{prefix}:{token}"


def store_token(prefix: str, payload: dict[str, Any], ttl: int | None = None) -> str:
    """Store a token with its payload in the cache.
    
    Args:
        prefix: A string prefix to categorize the token type
        payload: Dictionary containing token data to store
        ttl: Time-to-live in seconds. If None, uses DEFAULT_TOKEN_TTL_SECONDS
        
    Returns:
        The generated token string (UUID hex)
    """
    token = uuid.uuid4().hex
    cache.set(
        token_cache_key(prefix, token),
        payload,
        ttl if ttl is not None else DEFAULT_TOKEN_TTL_SECONDS,
    )
    return token


def pop_token(prefix: str, token: str):
    """Retrieve and remove a token from the cache.
    
    This function gets the token payload and then deletes it from the cache
    in a single operation, ensuring the token can only be used once.
    
    Args:
        prefix: A string prefix to categorize the token type
        token: The token string to retrieve and remove
        
    Returns:
        The token payload dictionary if found, None otherwise
    """
    key = token_cache_key(prefix, token)
    payload = cache.get(key)
    if payload is not None:
        cache.delete(key)
    return payload


def delete_token(prefix: str, token: str) -> None:
    """Delete a token from the cache without retrieving its payload.
    
    Args:
        prefix: A string prefix to categorize the token type
        token: The token string to delete
    """
    cache.delete(token_cache_key(prefix, token))


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the refresh token as an HTTP-only cookie to the response.
    
    Sets a secure, HTTP-only cookie containing the refresh token. The cookie
    is configured with appropriate security settings based on DEBUG mode.
    
    Args:
        response: The DRF Response object to attach the cookie to
        refresh_token: The JWT refresh token string to store in the cookie
    """
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
    """Remove the refresh token cookie from the response.
    
    Args:
        response: The DRF Response object to remove the cookie from
    """
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def get_tokens_for_user(user: User) -> dict[str, str]:
    """Generate JWT access and refresh tokens for the given user.
    
    Uses CustomRefreshToken to include circle membership information
    in both the refresh and access tokens.
    
    Args:
        user: The User instance to generate tokens for
        
    Returns:
        Dictionary containing 'refresh' and 'access' token strings
    """
    refresh = CustomRefreshToken.for_user(user)
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
